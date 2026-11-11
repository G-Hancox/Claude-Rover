"""The TARS voice.

  python3 -m tars.voice download          fetch the TARS voice (about 60 MB) into ~/tars-voice
  python3 -m tars.voice test "Hello"      say something in it   (add --emotion joy, etc.)
  python3 -m tars.voice save "Hello" out.wav
  add --pace 1.3 to try a different speed (higher = slower) before setting voice_pace
  add --steady 0.8 to try a steadier delivery (0-1) before setting voice_steadiness
  add --pause 0.7 to try a longer gap between sentences before setting voice_sentence_pause

The voice is the TARS-AI community's Piper model, trained on TARS's lines from
*Interstellar* (voiced by Bill Irwin), with one speaker per emotion. It's for this
personal, non-commercial robot: don't publish clips of it or pass it off as the actor.
"""
import argparse
import os
import subprocess
import sys
import urllib.request

from . import config as config_mod
from .audio import EMOTIONS, PiperVoiceEngine

BASE_URL = "https://huggingface.co/olivierdion007/TARS-AI/resolve/main"
FILES = ("TARS.onnx", "TARS.onnx.json")


def download(dest_dir):
    dest_dir = os.path.expanduser(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    for name in FILES:
        path = os.path.join(dest_dir, name)
        if os.path.isfile(path) and os.path.getsize(path) > 1024:
            print(f"Already have {path}")
            continue
        url = f"{BASE_URL}/{name}"
        print(f"Downloading {url}")
        tmp = path + ".part"
        with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        with open(tmp, "rb") as f:
            if f.read(40).startswith(b"version https://git-lfs"):
                os.remove(tmp)
                raise RuntimeError(f"{name} came back as a placeholder file, not the voice")
        os.replace(tmp, path)
        print(f"  saved {path} ({os.path.getsize(path) / 1e6:.1f} MB)")
    print("\nDone. In tars.json set:\n"
          '  "tts_engine": "piper",\n'
          f'  "piper_model": "{os.path.join(dest_dir, "TARS.onnx")}"')


def main():
    ap = argparse.ArgumentParser(description="The TARS voice")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("--dir", default="~/tars-voice")
    for name in ("test", "save"):
        p = sub.add_parser(name)
        p.add_argument("text")
        if name == "save":
            p.add_argument("out")
        p.add_argument("--emotion", choices=EMOTIONS)
        p.add_argument("--speaker", help="speaker number 0-7 (overrides piper_speaker)")
        p.add_argument("--pace", type=float, help="1.0 = as trained, higher = slower")
        p.add_argument("--steady", type=float, help="0 = natural variation, 1 = every line alike")
        p.add_argument("--pause", type=float, help="seconds of quiet between sentences")
        p.add_argument("--config")
    args = ap.parse_args()

    if args.cmd == "download":
        try:
            download(args.dir)
        except Exception as e:  # noqa: BLE001
            print(f"Download failed: {e}")
            return 1
        return 0

    cfg = config_mod.load(args.config)
    engine = PiperVoiceEngine(cfg.piper_model, args.speaker or cfg.piper_speaker,
                              args.pace if args.pace else cfg.voice_pace,
                              args.steady if args.steady is not None else cfg.voice_steadiness,
                              emotions=True,   # --emotion here always works, for trying them out
                              sentence_pause=args.pause if args.pause is not None else cfg.voice_sentence_pause)
    if engine.speakers:
        print("Emotions in this voice: " + ", ".join(sorted(engine.speakers)))
    wav = engine.wav(args.text, args.emotion)
    if args.cmd == "save":
        with open(args.out, "wb") as f:
            f.write(wav)
        print(f"Saved {args.out}")
        return 0
    return subprocess.run(["aplay", "-q", "-D", cfg.audio_out_device, "-"], input=wav).returncode


if __name__ == "__main__":
    sys.exit(main())
