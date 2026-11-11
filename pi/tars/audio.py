"""Voice out (text-to-speech or WAV through the speaker) and in (recordings from the mic).

Everything goes through the standard ALSA tools aplay and arecord. Text is always passed
on stdin, never on a command line.
"""
import io
import math
import queue
import shutil
import struct
import subprocess
import threading
import wave

MIC_RATE = 16000
MAX_LISTEN_S = 30
MAX_QUEUE = 5


class Busy(Exception):
    pass


def run_pipeline(first, second, data, timeout=90):
    """Feed `data` to `first`, pipe its output into `second`, wait for both."""
    p1 = subprocess.Popen(first, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL)
    p2 = subprocess.Popen(second, stdin=p1.stdout, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
    p1.stdout.close()
    try:
        try:
            p1.stdin.write(data)
            p1.stdin.close()
        except BrokenPipeError:
            pass
        p2.wait(timeout=timeout)
        p1.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p1.kill()
        p2.kill()
        raise
    return p1.returncode == 0 and p2.returncode == 0


class Speaker:
    def __init__(self, cfg):
        self._cfg = cfg
        need = ["aplay", cfg.piper_bin if cfg.tts_engine == "piper" else "espeak-ng"]
        missing = [n for n in need if not shutil.which(n)]
        if missing:
            raise RuntimeError(f"not installed: {', '.join(missing)}")
        if cfg.tts_engine == "piper" and not cfg.piper_model:
            raise RuntimeError('tts_engine is "piper" but piper_model is not set')
        self._start()

    def _start(self):
        self._queue = queue.Queue(maxsize=MAX_QUEUE)
        self._speaking = False
        self._last_error = None
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ---- public ---------------------------------------------------------

    def say(self, text):
        text = " ".join(str(text).split())[: self._cfg.say_max_chars]
        if not text:
            raise ValueError("nothing to say")
        self._put(("say", text))
        return text

    def play_wav(self, wav_bytes):
        if wav_bytes[:4] != b"RIFF" or wav_bytes[8:12] != b"WAVE":
            raise ValueError("not a WAV file")
        self._put(("wav", wav_bytes))

    def _put(self, item):
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            raise Busy("still talking; too much queued") from None

    def status(self):
        return {"speaking": self._speaking or not self._queue.empty(), "error": self._last_error}

    def close(self):
        self._closed = True
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass  # worker is a daemon thread; it ends with the program

    # ---- worker ---------------------------------------------------------

    def _run(self):
        while not self._closed:
            item = self._queue.get()
            if item is None:
                break
            self._speaking = True
            try:
                kind, payload = item
                ok = self._speak(payload) if kind == "say" else self._play(payload)
                self._last_error = None if ok else "playback command failed"
            except Exception as e:  # noqa: BLE001 - audio trouble must never take TARS down
                self._last_error = repr(e)
            finally:
                self._speaking = False

    def _aplay(self, *extra):
        return ["aplay", "-q", "-D", self._cfg.audio_out_device, *extra, "-"]

    def _speak(self, text):
        c = self._cfg
        if c.tts_engine == "piper":
            tts = [c.piper_bin, "--model", c.piper_model, "--output-raw"]
            play = self._aplay("-r", str(c.piper_sample_rate), "-f", "S16_LE", "-c", "1", "-t", "raw")
        else:
            tts = ["espeak-ng", "--stdin", "--stdout"]
            play = self._aplay()
        return run_pipeline(tts, play, text.encode())

    def _play(self, wav_bytes):
        r = subprocess.run(self._aplay(), input=wav_bytes, timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0


class Mic:
    def __init__(self, cfg):
        if not shutil.which("arecord"):
            raise RuntimeError("not installed: arecord")
        self._cfg = cfg
        self._lock = threading.Lock()

    def record(self, seconds):
        """Record for a whole number of seconds (1-30) and return a 16 kHz mono WAV."""
        seconds = max(1, min(MAX_LISTEN_S, int(seconds)))
        if not self._lock.acquire(blocking=False):
            raise Busy("already listening")
        try:
            return self._record(seconds)
        finally:
            self._lock.release()

    def _record(self, seconds):
        r = subprocess.run(
            ["arecord", "-q", "-D", self._cfg.audio_in_device, "-f", "S16_LE",
             "-r", str(MIC_RATE), "-c", "1", "-d", str(seconds), "-t", "wav"],
            capture_output=True, timeout=seconds + 10)
        if r.returncode != 0 or len(r.stdout) < 44:
            raise RuntimeError(f"arecord failed: {r.stderr.decode(errors='replace').strip()[:200]}")
        return r.stdout


# ---- stand-ins for running without hardware --------------------------------


class MockSpeaker(Speaker):
    def __init__(self, cfg):
        self._cfg = cfg
        self.said = []
        self._start()

    def _speak(self, text):
        self.said.append(text)
        return True

    def _play(self, wav_bytes):
        self.said.append(f"<wav {len(wav_bytes)} bytes>")
        return True


class MockMic(Mic):
    """Returns a quiet beep instead of a real recording."""

    def __init__(self, cfg=None, seconds_scale=1.0):
        self._cfg = cfg
        self._lock = threading.Lock()
        self._scale = seconds_scale

    def _record(self, seconds):
        n = int(MIC_RATE * seconds * self._scale)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(MIC_RATE)
            w.writeframes(b"".join(
                struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / MIC_RATE))
                            if (i // (MIC_RATE // 2)) % 2 == 0 else 0)
                for i in range(n)))
        return buf.getvalue()
