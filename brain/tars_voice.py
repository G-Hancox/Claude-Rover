"""Hands-free TARS: say "Hey TARS", then talk. Run on the PC; leave it running.

  python tars_voice.py            (or double-click "Start TARS voice.bat")

Waits for TARS to hear something (or for text typed in "Ask something" on the phone page),
turns speech into text on this PC, asks Claude through Claude Code (your subscription),
and has TARS speak the answer. Claude can look and move while answering.

Handled here without asking Claude (fast, and free):
  "stop" / "freeze"                 stop moving right away
  "TARS mode" / "Claude mode"       switch personality
  "set humor to 60" (or honesty)    change TARS's settings
  "new conversation" / "start over" forget the conversation so far (notes are kept)

Claude keeps notes between conversations in brain/memory.md (see tars_memory.py).

Voice turns can't touch files or run commands on this PC: only TARS's tools and web search.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import tars_memory
import tars_settings
from tars_client import Tars, TarsError

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_IDLE_S = 10 * 60          # a pause longer than this starts a fresh conversation
CLAUDE_TIMEOUT_S = 240
ALLOWED = ("mcp__tars__look,mcp__tars__move,mcp__tars__stop,mcp__tars__list_moves,mcp__tars__show,"
           "mcp__tars__remember,mcp__tars__recall,mcp__tars__forget,mcp__tars__personality,"
           "WebSearch,WebFetch")
DENIED = "Bash,Edit,Write,NotebookEdit,Read,Glob,Grep,mcp__tars__say,mcp__tars__listen"
EMOTIONS = ("anger", "curiosity", "fear", "joy", "love", "neutral", "sadness", "surprise")
# Whisper sometimes "hears" these in silence or noise
NOISE = {"", "you", "thank you", "thank you.", "thanks for watching", "thanks for watching!", "bye", "."}

VOICE_RULES = """
You are answering out loud through a small robot built by G, in his home or workshop.
What you say is turned into speech by the robot, so:
- Reply in one to three short spoken sentences. No lists, markdown, emoji, or URLs.
- Your final reply is spoken automatically; don't call say(). Use show() for anything that
  reads better than it sounds (a list, numbers, a spelling), and mention you've put it on the screen.
- You may start your reply with one emotion tag in square brackets: [joy] [curiosity]
  [surprise] [sadness] [anger] [fear] [love]. It only changes the voice if G has turned
  emotions on, so leave it out unless it really fits.
- You can look() through the robot's camera and move() it. Look before you move. Keep moves
  short and only move when asked or clearly needed. If anything seems unsafe, stop().
- If G asks to change your humor or honesty setting or your mode, however he phrases it,
  use personality() and confirm with the exact line it gives you, e.g.
  "Humor level, 90 percent. Confirmed."
- What G said came through speech recognition and may have small mistakes; read it charitably.
  If it's unclear, ask a short question back.
"""

PERSONAS = {
    "claude": """
You are Claude, speaking as yourself. The robot's body is a TARS replica from Interstellar,
but you're not playing TARS right now: be your normal, warm, direct self, just brief.
G's humor and honesty dials still apply to your tone (below), as a lighter touch.
If G wants the TARS personality, he can say "TARS mode".
""",
    "tars": """
For this conversation you're playing TARS, the robot from Interstellar, as a fun character.
Speak the way TARS does: deadpan, dry, economical, ex-military, unflappable, quietly loyal.
Short declarative sentences. Your settings are below; play them fully.
You're Claude underneath; if G sincerely asks what you are, tell him. Don't quote lines from
the film; be TARS in your own words. If G says "Claude mode", drop the character.
""",
}


# ---- speech to text ----------------------------------------------------------------------

_whisper = None


def transcribe(wav_bytes):
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _whisper is None:
        print("Loading speech-to-text (first time can take a minute)...", flush=True)
        _whisper = WhisperModel(os.environ.get("TARS_WHISPER_MODEL", "base.en"),
                                device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        path = f.name
    try:
        segments, _ = _whisper.transcribe(path, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(path)


# ---- Claude --------------------------------------------------------------------------------

def find_claude():
    found = shutil.which("claude")
    if found:
        return found
    local = os.path.join(os.path.expanduser("~"), ".local", "bin", "claude.exe")
    return local if os.path.exists(local) else None


def split_emotion(reply):
    m = re.match(r"\s*\[(\w+)\]\s*", reply)
    if m and m.group(1).lower() in EMOTIONS:
        emotion = m.group(1).lower()
        return reply[m.end():].strip(), None if emotion == "neutral" else emotion
    return reply.strip(), None


def spoken(text):
    """Tidy a reply for speech: drop markdown symbols and keep it within TARS's limit."""
    text = re.sub(r"[*_`#>|]+", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = " ".join(text.split())
    if len(text) > 480:
        cut = text[:480]
        text = cut[: max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! ")) + 1] or cut
    return text


class Voice:
    def __init__(self, tars, claude_cmd=None, run=subprocess.run, clock=time.monotonic):
        self.tars = tars
        self.claude = claude_cmd or find_claude()
        self.run = run
        self.clock = clock
        self.session = None
        self.session_mode = None
        self.last_turn = -1e9

    # -- things handled locally --------------------------------------------------------------
    def local_command(self, text):
        t = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        t = re.sub(r"^(hey|ok|okay) (tars|claude) ", "", t)
        if re.fullmatch(r"((tars|claude) )?(stop|stop it|stop moving|freeze|halt|abort)", t):
            self.tars.stop()
            return "Stopping.", None
        if re.fullmatch(r"(switch to |go to |change to |enable |activate )?(tars|tar|tours|stars) (mode|personality)( on)?", t):
            self.tars.persona(mode="tars")
            p = self.tars.persona()
            return (tars_settings.confirmation({"mode": "tars"}, p)
                    + f" Honesty, {p['honesty']} percent. Humor, {p['humor']} percent."), None
        if re.fullmatch(r"(switch to |go to |change to |back to )?(claude|clod|cloud|clawed) (mode|personality)|be yourself", t):
            p = self.tars.persona(mode="claude")
            return tars_settings.confirmation({"mode": "claude"}, p), None
        m = re.fullmatch(r"(?:set |change |turn )?(?:your )?(honesty|humou?r)(?: setting| level| parameter)?(?: to| at)? (\d{1,3})(?: percent)?", t)
        if m:
            which = "honesty" if m.group(1) == "honesty" else "humor"
            value = int(m.group(2))
            if value > 100:
                return f"{which.capitalize()} only goes up to 100 percent.", None
            p = self.tars.persona(**{which: value})
            return tars_settings.confirmation({which: value}, p), None
        if t in ("new conversation", "start over", "forget that", "forget everything", "reset"):
            self.session = None
            return "Starting fresh.", None
        return None

    # -- everything else goes to Claude -------------------------------------------------------
    def ask_claude(self, text):
        if not self.claude:
            return "I can't find Claude Code on this PC.", None
        persona = self.tars.persona()
        now = self.clock()
        if self.session_mode != persona["mode"] or now - self.last_turn > SESSION_IDLE_S:
            self.session = None
        system = (VOICE_RULES + PERSONAS[persona["mode"]].format(**persona)
                  + "\n## Your settings\n" + tars_settings.describe(persona) + "\n" + tars_memory.RULES
                  + "\n" + tars_memory.for_prompt())
        cmd = [self.claude, "-p", text, "--output-format", "json",
               "--append-system-prompt", system,
               "--strict-mcp-config", "--mcp-config", os.path.join(HERE, ".mcp.json"),
               "--allowedTools", ALLOWED, "--disallowedTools", DENIED]
        if self.session:
            cmd += ["--resume", self.session]
        try:
            r = self.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                         timeout=CLAUDE_TIMEOUT_S, env={**os.environ, "TARS_URL": self.tars.url})
        except subprocess.TimeoutExpired:
            self.session = None
            return "That took too long, sorry. Try asking again.", None
        try:
            out = json.loads(r.stdout)
        except ValueError:
            print(f"Claude Code error:\n{r.stdout}\n{r.stderr}", flush=True)
            self.session = None
            return "Something went wrong reaching Claude. Check the window on the PC.", None
        if out.get("is_error"):
            print(f"Claude Code error: {out.get('result')}", flush=True)
            self.session = None
            return "Something went wrong reaching Claude. Check the window on the PC.", None
        self.session = out.get("session_id")
        self.session_mode = persona["mode"]
        self.last_turn = now
        reply, emotion = split_emotion(out.get("result") or "")
        return spoken(reply) or "Hmm.", emotion

    def handle(self, text):
        print(f"\nYou:    {text}", flush=True)
        local = self.local_command(text)
        if local:
            reply, emotion = local
        else:
            try:
                self.tars.show("…", 300)          # "thinking" on TARS's screen
            except TarsError:
                pass
            reply, emotion = self.ask_claude(text)
            try:
                self.tars.show("", 1)
            except TarsError:
                pass
        print(f"TARS:   {reply}", flush=True)
        self.tars.say(reply, emotion)
        return reply, emotion


def main():
    tars = Tars()
    voice = Voice(tars)
    if not voice.claude:
        print("Can't find Claude Code. Install it first (see brain/README.md).")
        return 1
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        print("Note: speech-to-text isn't installed, so only typed questions from the phone page\n"
              "will work. To use your voice: pip install faster-whisper\n")
    print(f"Connecting to TARS at {tars.url} ...")
    after = None
    while after is None:
        try:
            after, _, _ = tars.next_heard(10**9, wait=0)   # skip anything said before we started
        except TarsError as e:
            print(f"  {e}  Retrying in 5 s.")
            time.sleep(5)
    print(f"Ready. Say \"Hey TARS\", or type in \"Ask something\" on the phone page. Ctrl+C to quit.\n"
          f"Mode: {tars.persona()['mode']}")
    while True:
        try:
            num, kind, payload = tars.next_heard(after, wait=25)
            if kind is None:
                after = num   # latest on TARS (also catches up if TARS was restarted)
                continue
            after = num
            if kind == "wav":
                text = transcribe(payload)
                if text is None:
                    tars.say("Speech recognition isn't installed on the PC yet.")
                    continue
                if text.strip().lower() in NOISE:
                    print("(heard nothing clear)", flush=True)
                    continue
            else:
                text = payload
            voice.handle(text)
        except TarsError as e:
            print(f"{e}  Retrying in 5 s.", flush=True)
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nBye.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
