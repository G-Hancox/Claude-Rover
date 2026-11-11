"""Wake word: TARS listens for "Hey TARS", then records what you say next.

The detector is the TARS-AI community's "Hey TARS" model (wakeword/, CC-BY-NC 4.0). The
feature extraction and the checks around it are adapted from their module_atomik.py, so the
model hears audio the way it was trained. Needs numpy and onnxruntime (onnxruntime comes
with piper-tts, so it's in ~/tars-venv).

What happens:
  1. The mic streams continuously. Every 0.1 s the last second is checked for "Hey TARS".
  2. On a hit TARS beeps, then records until you stop talking (or 12 s).
  3. The recording is queued; the PC picks it up from GET /heard and answers.

Listening pauses while TARS is talking or moving, so it doesn't wake itself up.
"""
import io
import json
import math
import os
import shutil
import struct
import subprocess
import threading
import time
import wave
from collections import deque

RATE = 16000
CHUNK = RATE // 10          # 100 ms
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "wakeword", "hey_tars.onnx")


# ---- features (adapted from TARS-AI module_atomik.py) ---------------------------------

class Features:
    def __init__(self, n_mfcc=13, n_fft=512, n_mels=40, target_frames=62, deltas=True):
        import numpy as np
        self.np = np
        self.n_mfcc, self.n_fft, self.n_mels = n_mfcc, n_fft, n_mels
        self.target_frames, self.deltas = target_frames, deltas
        self.mel = self._mel_filterbank()
        n = n_mels
        k = np.arange(n)[:, None]
        i = np.arange(n)[None, :]
        dct = np.cos(np.pi * k * (2 * i + 1) / (2 * n))
        dct[0] *= math.sqrt(1 / n)
        dct[1:] *= math.sqrt(2 / n)
        self.dct = dct[:n_mfcc]   # orthonormal DCT-II, same as scipy dct(type=2, norm="ortho")

    def _mel_filterbank(self):
        np = self.np

        def hz_to_mel(hz):
            return 2595 * np.log10(1 + hz / 700.0)

        def mel_to_hz(mel):
            return 700 * (10 ** (mel / 2595.0) - 1)

        pts = mel_to_hz(np.linspace(0, hz_to_mel(RATE / 2), self.n_mels + 2))
        bins = np.floor((self.n_fft + 1) * pts / RATE).astype(int)
        fb = np.zeros((self.n_mels, self.n_fft // 2 + 1))
        for m in range(1, self.n_mels + 1):
            lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
            for k in range(lo, mid):
                fb[m - 1, k] = (k - lo) / (mid - lo)
            for k in range(mid, hi):
                fb[m - 1, k] = (hi - k) / (hi - mid)
        return fb

    def mfcc(self, audio):
        np = self.np
        if len(audio) < self.n_fft:
            return None
        x = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])
        step = self.n_fft // 2
        n = 1 + (len(x) - self.n_fft) // step
        idx = np.arange(self.n_fft)[None, :] + step * np.arange(n)[:, None]
        frames = x[idx] * np.hamming(self.n_fft)
        power = (np.abs(np.fft.rfft(frames, self.n_fft)) ** 2) / self.n_fft
        fb = power @ self.mel.T
        fb = np.where(fb == 0, np.finfo(float).eps, fb)
        m = (20 * np.log10(fb)) @ self.dct.T
        return (m - m.mean(axis=0)) / (m.std(axis=0) + 1e-8)

    def _delta(self, f, width=2):
        np = self.np
        n = f.shape[0]
        denom = 2 * sum(t * t for t in range(1, width + 1))
        out = np.zeros_like(f)
        for tau in range(1, width + 1):
            plus = f[np.minimum(np.arange(n) + tau, n - 1)]
            minus = f[np.maximum(np.arange(n) - tau, 0)]
            out += tau * (plus - minus)
        return out / denom

    def fixed(self, audio):
        np = self.np
        m = self.mfcc(audio)
        if m is None:
            return None
        if self.deltas:
            d = self._delta(m)
            m = np.hstack([m, d, self._delta(d)])
        if m.shape[0] >= self.target_frames:
            return m[: self.target_frames].astype(np.float32)
        pad = np.zeros((self.target_frames - m.shape[0], m.shape[1]))
        return np.vstack([m, pad]).astype(np.float32)


# ---- detector ---------------------------------------------------------------------------

class Detector:
    """Scores the last second of audio. Same gates as TARS-AI's: quiet, low SNR, bangs,
    rumbles and non-speech are rejected before the model runs; two hits in the last five
    checks are needed; then a 1.5 s cooldown."""

    def __init__(self, threshold=0.84, model_path=MODEL, model=None):
        import numpy as np
        self.np = np
        meta_path = model_path.replace(".onnx", "_meta.json")
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        self.features = Features(meta.get("n_mfcc", 13), meta.get("n_fft", 512), 40,
                                 meta.get("target_frames", 62), meta.get("n_features", 39) > 13)
        if model is None:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = opts.intra_op_num_threads = 1
            sess = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
            name_in, name_out = sess.get_inputs()[0].name, sess.get_outputs()[0].name
            model = lambda feat: float(sess.run([name_out], {name_in: feat[None].astype(np.float32)})[0][0][0])  # noqa: E731
        self.model = model
        self.threshold = threshold
        self.cooldown = 1.5
        self.reset()

    def reset(self):
        self.noise_floor = 0.005
        self.recent = deque(maxlen=5)
        self.last_hit = -1e9

    def check(self, window, now):
        """window: the last 1 s of audio, float32 in -1..1. Returns (hit, score)."""
        np = self.np
        if now - self.last_hit < self.cooldown:
            return False, 0.0
        rms = float(np.sqrt(np.mean(window ** 2)))
        if rms < 0.008:
            self.noise_floor = 0.98 * self.noise_floor + 0.02 * rms
            return False, 0.0
        if rms / (self.noise_floor + 1e-8) < 3.0:
            return False, 0.0
        if np.max(np.abs(window)) / (rms + 1e-8) > 15:   # bangs and clicks
            return False, 0.0
        mag = np.abs(np.fft.rfft(window))
        freqs = np.fft.rfftfreq(len(window), 1.0 / RATE)
        total = mag.sum() + 1e-8
        if mag[(freqs >= 300) & (freqs <= 3000)].sum() / total < 0.30:
            return False, 0.0
        if mag[freqs < 300].sum() / total > 0.60:          # rumbles and thuds
            return False, 0.0
        feat = self.features.fixed(window)
        if feat is None:
            return False, 0.0
        score = self.model(feat)
        if self.threshold * 0.6 < score < self.threshold:  # near miss: try a bit faster/slower
            for rate in (0.9, 1.1):
                idx = np.round(np.arange(0, len(window), rate))
                s = window[idx[idx < len(window)].astype(int)]
                if len(s) < RATE:
                    s = np.pad(s, (0, RATE - len(s)))
                f = self.features.fixed(s[:RATE])
                if f is not None:
                    score = max(score, self.model(f))
                    if score >= self.threshold:
                        break
        self.recent.append(score)
        if sum(1 for s in self.recent if s >= self.threshold) >= 2:
            self.recent.clear()
            if not self._speech_like(window):
                return False, score
            self.last_hit = now
            return True, score
        return False, score

    def _speech_like(self, audio):
        np = self.np
        signs = np.sign(audio)
        signs[signs == 0] = 1
        zcr = np.sum(np.abs(np.diff(signs))) / (2.0 * len(audio))
        if zcr > 0.20 or zcr < 0.002:
            return False
        size = RATE // 20
        n = max(1, len(audio) // size)
        e = np.array([np.sqrt(np.mean(audio[i * size:(i + 1) * size] ** 2)) for i in range(n)])
        if len(e) < 3:
            return True
        if np.std(e) / (np.mean(e) + 1e-8) < 0.15:
            return False
        smooth = np.convolve(e, np.ones(3) / 3, mode="same")
        above = smooth > np.mean(smooth) * 0.6
        peaks = int(np.sum(np.diff(above.astype(int)) == 1))
        if peaks < 1 or peaks > 5:
            return False
        dur = np.sum(e > np.mean(smooth) * 0.6) * size / RATE
        return 0.2 <= dur <= 2.5


# ---- what was heard ----------------------------------------------------------------------

def to_wav(pcm16):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm16)
    return buf.getvalue()


class Heard:
    """Things said to TARS after "Hey TARS" (or typed on the phone page), waiting for the PC
    to collect them. Each item is (id, kind, payload): kind "wav" (bytes) or "text" (str)."""

    def __init__(self, keep=5):
        self._cond = threading.Condition()
        self._items = deque(maxlen=keep)
        self._next = 1

    def add(self, payload, kind="wav"):
        with self._cond:
            self._items.append((self._next, kind, payload))
            self._next += 1
            self._cond.notify_all()
            return self._next - 1

    def latest_id(self):
        with self._cond:
            return self._next - 1

    def wait_after(self, after, timeout):
        """Oldest item newer than `after`, waiting up to `timeout` s. None if nothing."""
        with self._cond:
            def find():
                return next((item for item in self._items if item[0] > after), None)
            found = find()
            if found is None:
                self._cond.wait_for(lambda: find() is not None, timeout)
                found = find()
            return found


def beep_wav():
    """Two short rising tones: 'I'm listening'."""
    frames = []
    for freq, dur in ((660, 0.07), (0, 0.03), (990, 0.09)):
        for i in range(int(RATE * dur)):
            v = 0.0 if freq == 0 else math.sin(2 * math.pi * freq * i / RATE)
            fade = min(1.0, i / 80, (int(RATE * dur) - i) / 80)
            frames.append(struct.pack("<h", int(9000 * v * fade)))
    return to_wav(b"".join(frames))


# ---- the listener ------------------------------------------------------------------------

class ArecordStream:
    def __init__(self, device):
        if not shutil.which("arecord"):
            raise RuntimeError("not installed: arecord")
        self._device = device
        self._proc = None

    def open(self):
        self._proc = subprocess.Popen(
            ["arecord", "-q", "-D", self._device, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def read(self, n_samples):
        data = self._proc.stdout.read(n_samples * 2)
        if not data or len(data) < n_samples * 2:
            raise EOFError("microphone stream ended")
        return data

    def close(self):
        if self._proc:
            self._proc.kill()
            self._proc.wait()
            self._proc = None


class WakeListener:
    def __init__(self, stream, detector, heard, busy=lambda: False, beep=None, clock=time.monotonic):
        import numpy as np
        self.np = np
        self._stream = stream
        self._detector = detector
        self._heard = heard
        self._busy = busy            # True while TARS is talking or moving
        self._beep = beep            # plays the "listening" beep
        self._clock = clock
        self._buf = deque(maxlen=RATE // CHUNK)   # last 1 s, as 100 ms chunks
        self._lock = threading.Lock()
        self._paused = 0
        self._resume = threading.Event()
        self._resume.set()
        self.capturing = False
        self.last_score = 0.0
        self.error = None
        self._running = False
        self._thread = None

    # Another part of TARS (the /listen endpoint) needs the mic to itself for a moment.
    def pause(self):
        with self._lock:
            self._paused += 1
            self._resume.clear()
        self._stream.close()

    def resume(self):
        with self._lock:
            self._paused = max(0, self._paused - 1)
            if self._paused == 0:
                self._resume.set()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def close(self):
        self._running = False
        self._resume.set()
        self._stream.close()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        while self._running:
            self._resume.wait()
            if not self._running:
                break
            try:
                self._stream.open()
                self.error = None
                quiet_until = 0.0
                while self._running and self._resume.is_set():
                    pcm = self._stream.read(CHUNK)
                    now = self._clock()
                    if self._busy():
                        quiet_until = now + 0.5   # ignore TARS's own voice and its echo tail
                        self._buf.clear()
                        self._detector.reset()
                        continue
                    if now < quiet_until:
                        continue
                    self._buf.append(pcm)
                    if len(self._buf) < self._buf.maxlen:
                        continue
                    window = self._floats(b"".join(self._buf))
                    hit, self.last_score = self._detector.check(window, now)
                    if hit:
                        self._buf.clear()
                        self._capture()
            except EOFError:
                if self._resume.is_set() and self._running:
                    self.error = "microphone stream ended"
                    time.sleep(1)
            except Exception as e:  # noqa: BLE001 - keep listening after hiccups
                self.error = repr(e)
                time.sleep(1)
            finally:
                self._stream.close()

    def _floats(self, pcm):
        np = self.np
        return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0

    def _capture(self, start_timeout=5.0, end_silence=0.9, max_s=12.0):
        """Record until the speaker stops. Queues a WAV, or nothing if no one spoke."""
        if self._beep:
            self._beep()
            t0 = self._clock()
            while self._busy() and self._clock() - t0 < 2:   # let the beep finish
                self._stream.read(CHUNK)
        self.capturing = True
        try:
            floor = max(0.008, self._detector.noise_floor * 3)
            chunks, started, silent, total = [], False, 0.0, 0.0
            pre = deque(maxlen=3)
            while total < max_s:
                pcm = self._stream.read(CHUNK)
                total += 0.1
                loud = float(self.np.sqrt(self.np.mean(self._floats(pcm) ** 2))) > floor
                if not started:
                    pre.append(pcm)
                    if loud:
                        started = True
                        chunks.extend(pre)
                    elif total >= start_timeout:
                        return None
                    continue
                chunks.append(pcm)
                silent = 0.0 if loud else silent + 0.1
                if silent >= end_silence:
                    break
            return self._heard.add(to_wav(b"".join(chunks)))
        finally:
            self.capturing = False


# ---- try it --------------------------------------------------------------------------------

def _scores(detector, pcm16):
    """Best score anywhere in a recording, sliding a 1 s window in 0.1 s steps."""
    np = detector.np
    a = np.frombuffer(pcm16, dtype="<i2").astype(np.float32) / 32768.0
    a = np.concatenate([np.zeros(RATE // 2, np.float32), a, np.zeros(RATE // 2, np.float32)])
    best = 0.0
    for start in range(0, len(a) - RATE + 1, CHUNK):
        f = detector.features.fixed(a[start:start + RATE])
        if f is not None:
            best = max(best, detector.model(f))
    return best


def _say_pcm16(cmd, text):
    """Synthesize text with espeak-ng or Piper into 16 kHz PCM via sox-free resampling."""
    np = __import__("numpy")
    out = subprocess.run(cmd, input=text.encode(), capture_output=True, check=True).stdout
    with wave.open(io.BytesIO(out)) as w:
        rate, data = w.getframerate(), w.readframes(w.getnframes())
    a = np.frombuffer(data, dtype="<i2").astype(np.float32)
    if rate != RATE:
        x = np.linspace(0, len(a) - 1, int(len(a) * RATE / rate))
        a = np.interp(x, np.arange(len(a)), a)
    return a.astype("<i2").tobytes()


def main():
    """python3 -m tars.wake test      check the model with synthetic speech
       python3 -m tars.wake live      print live scores from the mic (say "Hey TARS")"""
    import sys
    from . import config as config_mod
    args = sys.argv[1:]
    cfg = config_mod.load(args[1] if len(args) > 1 else None)
    det = Detector(cfg.wake_threshold)
    if args[:1] == ["test"]:
        print(f"threshold {det.threshold:.2f} (scores 0-1; the wake phrase should score well above the rest)")
        voices = [("espeak", ["espeak-ng", "--stdin", "--stdout"])]
        try:
            from .audio import PiperVoiceEngine
            eng = PiperVoiceEngine(cfg.piper_model)
            voices.append(("TARS voice", None))
        except Exception:
            eng = None
        for name, cmd in voices:
            for text in ("Hey TARS", "Hey tars.", "Hello there", "What time is it"):
                if cmd:
                    pcm = _say_pcm16(cmd, text)
                else:
                    with wave.open(io.BytesIO(eng.wav(text))) as w:
                        np = det.np
                        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
                        x = np.linspace(0, len(a) - 1, int(len(a) * RATE / w.getframerate()))
                        pcm = np.interp(x, np.arange(len(a)), a).astype("<i2").tobytes()
                print(f"  {name:10} {text!r:20} {_scores(det, pcm):.2f}")
        return 0
    if args[:1] == ["live"]:
        stream = ArecordStream(cfg.audio_in_device)
        stream.open()
        buf = deque(maxlen=RATE // CHUNK)
        print("Listening. Say 'Hey TARS'. Ctrl+C to stop.")
        try:
            while True:
                buf.append(stream.read(CHUNK))
                if len(buf) == buf.maxlen:
                    np = det.np
                    w = np.frombuffer(b"".join(buf), dtype="<i2").astype(np.float32) / 32768.0
                    hit, score = det.check(w, time.monotonic())
                    bar = "#" * int(score * 40)
                    print(f"\r{score:.2f} {bar:<40} {'HEY TARS!' if hit else '':10}", end="", flush=True)
        except KeyboardInterrupt:
            print()
        finally:
            stream.close()
        return 0
    print(main.__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
