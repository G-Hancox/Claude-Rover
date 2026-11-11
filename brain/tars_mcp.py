"""Claude TARS tools for Claude Code (an MCP server).

Claude Code starts this program by itself (see .mcp.json). It gives Claude a handful of
tools - look, move, stop, say, listen - that call TARS over Wi-Fi.

  python tars_mcp.py --check    test the connection to TARS without Claude
"""
import asyncio
import os
import sys
import tempfile

from tars_client import Tars, TarsError

try:  # mcp 2.x
    from mcp.server.mcpserver import Image, MCPServer as Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server, Image
    from mcp.server.fastmcp.exceptions import ToolError

MAX_LISTEN_S = 20

tars = Tars()
mcp = Server("tars", instructions=(
    "Tools for a small TARS robot (from Interstellar) in the user's home. It walks slowly "
    "on two servo-driven legs and sees through a fixed camera in its front. Look before you "
    "move and look again after."))

_whisper = None


async def _call(fn, *args):
    try:
        return await asyncio.to_thread(fn, *args)
    except TarsError as e:
        raise ToolError(str(e)) from None  # the message reaches Claude as the tool's error


def _legs_line(status):
    legs = status["legs"]
    if legs.get("error"):
        return f"Servo problem: {legs['error']}. The legs have gone limp."
    return "Standing." if not legs["moving"] else f"Busy doing {legs['move']}."


@mcp.tool()
async def look() -> list:
    """See through TARS's camera right now (it faces forward from the front of the body).
    To look somewhere else, turn TARS with move("turn_left") or move("turn_right")."""
    jpeg = await _call(tars.snapshot)
    status = await _call(tars.status)
    return [Image(data=jpeg, format="jpeg"), _legs_line(status)]


@mcp.tool()
async def list_moves() -> str:
    """List every move TARS can do, with a line about each."""
    moves = await _call(tars.moves)
    return "\n".join(f"- {m['name']}{' (changes position)' if m['travels'] else ''}: {m['about']}"
                     for m in moves)


@mcp.tool()
async def move(name: str, times: int = 1) -> str:
    """Do one of TARS's moves and wait until it's finished.

    Walking: step_forward, step_backward, walk_forward (a few small shuffling steps),
    turn_left, turn_right, turn_left_slow, turn_right_slow.
    On the spot: stand, pose, bow, tilt_left, tilt_right, side_side, laugh, excited, swing_legs.
    times: repeat 1-5 times. Each step covers only a few centimetres and takes a few seconds.
    Call list_moves() for descriptions.
    """
    try:
        started, seconds, status = await _call(tars.move, name, int(times))
    except asyncio.CancelledError:
        await asyncio.shield(asyncio.to_thread(tars.stop))
        raise
    legs = status["legs"]
    if legs.get("error"):
        raise ToolError(f"{started} failed: {legs['error']}. The legs have gone limp; tell the user.")
    swapped = f" (ran as {started}: turns are swapped in settings)" if started != name else ""
    return f"Done: {name} x{int(times)}{swapped}, {seconds:.1f} s. {_legs_line(status)}"


@mcp.tool()
async def stop() -> str:
    """Cut the current move short. TARS eases back to standing."""
    await _call(tars.stop)
    return "Stopping; TARS will settle into standing."


@mcp.tool()
async def say(text: str) -> str:
    """Speak out loud through TARS's speaker (up to 500 characters). Waits until it has finished."""
    said = (await _call(tars.say, text))["saying"]
    for _ in range(600):  # up to 60 s
        await asyncio.sleep(0.1)
        speaker = (await _call(tars.status)).get("speaker") or {}
        if not speaker.get("speaking"):
            if speaker.get("error"):
                return f"Tried to say it, but the speaker reported a problem: {speaker['error']}"
            break
    return f'Said: "{said}"'


def _transcribe(wav_bytes):
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _whisper is None:
        _whisper = WhisperModel(os.environ.get("TARS_WHISPER_MODEL", "base.en"),
                                device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        path = f.name
    try:
        segments, _info = _whisper.transcribe(path)
        return " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        os.unlink(path)


@mcp.tool()
async def listen(seconds: float = 6.0) -> str:
    """Listen through TARS's microphone for a few seconds (1 to 20) and return what was said.
    Don't call this during a move: servo noise drowns out speech."""
    seconds = int(max(1, min(MAX_LISTEN_S, float(seconds))))
    wav = await _call(tars.listen, seconds)
    text = await asyncio.to_thread(_transcribe, wav)
    if text is None:
        return ("Recorded the audio, but speech-to-text isn't installed on this PC. "
                "The user needs to run: pip install faster-whisper")
    return f'Heard: "{text}"' if text else "Heard nothing I could make out."


def check():
    print(f"TARS address: {tars.url}")
    try:
        s = tars.status()
    except TarsError as e:
        print(f"FAILED: {e}")
        return 1
    print("Connected.")
    print(f"  camera: {'yes' if s.get('camera') else 'no'}   speaker: {'yes' if s.get('speaker') else 'no'}   "
          f"mic: {'yes' if s.get('mic') else 'no'}")
    print("  legs: " + _legs_line(s))
    try:
        import faster_whisper  # noqa: F401
        print("  speech-to-text: installed")
    except ImportError:
        print("  speech-to-text: NOT installed (pip install faster-whisper)")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    mcp.run()
