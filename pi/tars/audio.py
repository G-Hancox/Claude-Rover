"""Voice out (text-to-speech or WAV through the speaker) and in (recordings from the mic).

Sound goes through the standard ALSA tools aplay and arecord. Two voices:
  espeak  robotic, installs with apt, text passed on stdin (never on a command line)
  piper   natural or character voices such as the TARS voice; runs in this process
          (pip install piper-tts) and can pick a speaker per emotion on multi-speaker models
"""
import io
import json
import math
import os
import queue
import shutil
import struct
import subprocess
import threading
import wave

MIC_RATE = 16000
MAX_LISTEN_S = 30
MAX_QUEUE = 5
EMOTIONS = ("anger", "curiosity", "fear", "joy", "love", "neutral", "sadness", "surprise")


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


class PiperVoiceEngine:
    """A Piper voice loaded once and kept in memory. Works with old and new piper-tts."""

    def __init__(self, model_path, default_speaker="neutral", length_scale=1.0, steadiness=0.0,
                 emotions=True, sentence_pause=0.0):
        model_path = os.path.expanduser(model_path)
        if not os.path.isfile(model_path):
            raise RuntimeError(f"Piper voice not found at {model_path} "
                               "(for the TARS voice: python3 -m tars.voice download)")
        if not os.path.isfile(model_path + ".json"):
            raise RuntimeError(f"Piper voice is missing its settings file {model_path}.json")
        with open(model_path + ".json") as f:
            meta = json.load(f)
        self.speakers = dict(meta.get("speaker_id_map") or {})
        self.sample_rate = int(meta.get("audio", {}).get("sample_rate", 22050))
        self.default_speaker = self.speaker_id(default_speaker)
        self.length_scale = float(length_scale)  # above 1 = slower, the same for every emotion
        # Piper adds randomness to tone (noise_scale, default 0.667) and timing (noise_w, 0.8).
        # steadiness 0 = Piper's defaults; 1 = almost none, so every line sounds alike.
        st = max(0.0, min(1.0, float(steadiness)))
        self.noise_scale = round(0.667 * (1 - 0.85 * st), 3)
        self.noise_w = round(0.8 * (1 - 0.85 * st), 3)
        self.emotions = emotions
        self.sentence_pause = max(0.0, min(2.0, float(sentence_pause)))  # seconds of quiet between sentences
        try:
            from piper import PiperVoice
        except ImportError:
            try:
                from piper.voice import PiperVoice
            except ImportError:
                raise RuntimeError("piper-tts is not installed (pip install piper-tts)") from None
        self._voice = PiperVoice.load(model_path)

    def speaker_id(self, name):
        """Emotion name or number -> speaker id, or None for single-speaker voices."""
        if not self.speakers or name is None:
            return None
        if isinstance(name, int) or str(name).isdigit():
            return int(name)
        return self.speakers.get(str(name), self.speakers.get("neutral"))

    def wav(self, text, emotion=None):
        """Speak text. With sentence_pause, each sentence is made separately and joined with
        a gap, the way TARS leaves room between lines."""
        parts = [text]
        if self.sentence_pause:
            import re
            parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p] or [text]
        if len(parts) == 1:
            return self._wav_one(text, emotion)
        gap = b"\0\0" * int(self.sample_rate * self.sentence_pause)
        frames, params = [], None
        for part in parts:
            with wave.open(io.BytesIO(self._wav_one(part, emotion))) as w:
                params = w.getparams()
                frames.append(w.readframes(w.getnframes()))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setparams(params)
            w.writeframes(gap.join(frames))
        return buf.getvalue()

    def _wav_one(self, text, emotion=None):
        sid = self.speaker_id(emotion) if (emotion and self.emotions) else self.default_speaker
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            if hasattr(self._voice, "synthesize_wav"):  # piper-tts 1.3 and later
                try:
                    from piper import SynthesisConfig
                    cfg = SynthesisConfig(speaker_id=sid, length_scale=self.length_scale,
                                          noise_scale=self.noise_scale, noise_w_scale=self.noise_w)
                    self._voice.synthesize_wav(text, w, syn_config=cfg)
                except ImportError:
                    if sid is not None:
                        self._voice.config.speaker_id = sid
                    self._voice.config.length_scale = self.length_scale
                    self._voice.config.noise_scale = self.noise_scale
                    self._voice.config.noise_w = self.noise_w
                    self._voice.synthesize_wav(text, w)
            else:  # piper-tts 1.2
                self._voice.synthesize(text, w, speaker_id=sid, length_scale=self.length_scale,
                                       noise_scale=self.noise_scale, noise_w=self.noise_w)
        return buf.getvalue()


class Speaker:
    def __init__(self, cfg):
        self._cfg = cfg
        need = ["aplay"] + (["espeak-ng"] if cfg.tts_engine == "espeak" else [])
        missing = [n for n in need if not shutil.which(n)]
        if missing:
            raise RuntimeError(f"not installed: {', '.join(missing)}")
        self._piper = (PiperVoiceEngine(cfg.piper_model, cfg.piper_speaker, cfg.voice_pace,
                                        cfg.voice_steadiness, cfg.voice_emotions,
                                        cfg.voice_sentence_pause)
                       if cfg.tts_engine == "piper" else None)
        self._start()

    def _start(self):
        self._queue = queue.Queue(maxsize=MAX_QUEUE)
        self._speaking = False
        self.now_saying = None
        self.last_said = None   # (count, text): lets the screen catch even very short speech
        self._said_count = 0
        self._last_error = None
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ---- public ---------------------------------------------------------

    def say(self, text, emotion=None):
        text = " ".join(str(text).split())[: self._cfg.say_max_chars]
        if not text:
            raise ValueError("nothing to say")
        if emotion is not None and emotion not in EMOTIONS:
            raise ValueError(f"emotion must be one of: {', '.join(EMOTIONS)}")
        self._put(("say", (text, emotion)))
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
        return {"speaking": self._speaking or not self._queue.empty(), "error": self._last_error,
                "voice": "piper" if self._piper else self._cfg.tts_engine}

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
                if kind == "say":
                    self.now_saying = payload[0]
                    self._said_count += 1
                    self.last_said = (self._said_count, payload[0])
                    ok = self._speak(*payload)
                else:
                    ok = self._play(payload)
                self._last_error = None if ok else "playback command failed"
            except Exception as e:  # noqa: BLE001 - audio trouble must never take TARS down
                self._last_error = repr(e)
            finally:
                self._speaking = False
                self.now_saying = None

    def _aplay(self, *extra):
        return ["aplay", "-q", "-D", self._cfg.audio_out_device, *extra, "-"]

    def _speak(self, text, emotion=None):
        if self._piper:
            return self._play(self._piper.wav(text, emotion))
        return run_pipeline(["espeak-ng", "--stdin", "--stdout"], self._aplay(), text.encode())

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
        self.before_record = None   # set by the wake word listener, which shares the mic
        self.after_record = None

    @property
    def listening(self):
        return self._lock.locked()

    def record(self, seconds):
        """Record for a whole number of seconds (1-30) and return a 16 kHz mono WAV."""
        seconds = max(1, min(MAX_LISTEN_S, int(seconds)))
        if not self._lock.acquire(blocking=False):
            raise Busy("already listening")
        try:
            if self.before_record:
                self.before_record()
            return self._record(seconds)
        finally:
            if self.after_record:
                self.after_record()
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
    """Pretend speaker. talk_s: seconds per word to 'talk' for (0 = instant, for tests)."""

    def __init__(self, cfg, talk_s=0.0):
        self._cfg = cfg
        self._piper = None
        self.said = []
        self.emotions = []
        self._talk_s = talk_s
        self._start()

    def _speak(self, text, emotion=None):
        self.said.append(text)
        self.emotions.append(emotion)
        if self._talk_s:
            import time
            time.sleep(min(15.0, self._talk_s * len(text.split())))
        return True

    def _play(self, wav_bytes):
        self.said.append(f"<wav {len(wav_bytes)} bytes>")
        return True


class MockMic(Mic):
    """Returns a quiet beep instead of a real recording."""

    def __init__(self, cfg=None, seconds_scale=1.0):
        self._cfg = cfg
        self._lock = threading.Lock()
        self.before_record = self.after_record = None
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
