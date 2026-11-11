"""Claude Rover tools for Claude Code (an MCP server).

Claude Code starts this program by itself (see .mcp.json). It gives Claude a handful of
tools - look, drive, point the camera, say, listen - that call the rover over Wi-Fi.

  python rover_mcp.py --check    test the connection to the rover without Claude
"""
import asyncio
import os
import sys
import tempfile

from rover_client import Rover, RoverError

try:  # mcp 2.x
    from mcp.server.mcpserver import Image, MCPServer as Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server, Image
    from mcp.server.fastmcp.exceptions import ToolError

MAX_DRIVE_S = 3.0
MAX_LISTEN_S = 20

rover = Rover()
mcp = Server("rover", instructions=(
    "Tools for a small camera rover in the user's home or workshop. Look before you move, "
    "move in short steps, and look again. The rover limits its own speed and stops by itself "
    "if contact is lost."))

_whisper = None


def _describe(s):
    parts = []
    d = s.get("distance")
    if d:
        if d.get("fault"):
            parts.append("distance sensor FAULT (forward driving is blocked)")
        elif d.get("distance_m") is None:
            parts.append("nothing within sensor range ahead")
        else:
            parts.append(f"{d['distance_m']:.2f} m to the nearest thing straight ahead")
    else:
        parts.append("no distance sensor fitted")
    if s.get("forward_blocked"):
        parts.append("forward is BLOCKED")
    if s.get("head"):
        parts.append(f"camera pan {s['head']['pan']:+.2f}, tilt {s['head']['tilt']:+.2f}")
    if not s.get("armed", True):
        parts.append("motor controller still arming")
    return "; ".join(parts) + "."


async def _call(fn, *args):
    try:
        return await asyncio.to_thread(fn, *args)
    except RoverError as e:
        raise ToolError(str(e)) from None  # the message reaches Claude as the tool's error


@mcp.tool()
async def look() -> list:
    """See through the rover's camera right now. Returns a photo and the distance reading.
    The distance sensor points straight ahead of the body, not where the camera is aimed."""
    jpeg = await _call(rover.snapshot)
    status = await _call(rover.status)
    return [Image(data=jpeg, format="jpeg"), _describe(status)]


@mcp.tool()
async def drive(throttle: float, steering: float = 0.0, seconds: float = 1.0) -> str:
    """Drive for a short time, then stop.

    throttle: -1 (full reverse) to 1 (full forward). The rover caps real speed itself.
    steering: -1 (full left) to 1 (full right). This is a car: it can't turn on the spot.
    seconds: how long, 0.1 to 3. Use short moves and look() between them.

    Nothing watches behind the rover when it reverses.
    """
    throttle = max(-1.0, min(1.0, float(throttle)))
    steering = max(-1.0, min(1.0, float(steering)))
    seconds = max(0.1, min(MAX_DRIVE_S, float(seconds)))
    try:
        elapsed, reason, status = await _call(rover.drive_for, throttle, steering, seconds)
    except asyncio.CancelledError:
        await asyncio.shield(asyncio.to_thread(rover.stop))
        raise
    how = ("Stopped early: the rover refused to go forward (obstacle or sensor fault)."
           if reason == "blocked" else "Stopped.")
    return f"Drove {elapsed:.1f} s at throttle {throttle:+.2f}, steering {steering:+.2f}. {how} {_describe(status)}"


@mcp.tool()
async def stop() -> str:
    """Stop the rover immediately."""
    return "Stopped. " + _describe(await _call(rover.stop))


@mcp.tool()
async def point_camera(pan: float = 0.0, tilt: float = 0.0) -> str:
    """Aim the camera. pan: -1 (left) to 1 (right). tilt: -1 (down) to 1 (up). 0, 0 is straight ahead.
    Waits for the camera to get there. Call look() afterwards to see."""
    pan = max(-1.0, min(1.0, float(pan)))
    tilt = max(-1.0, min(1.0, float(tilt)))
    await _call(rover.look, pan, tilt)
    for _ in range(30):  # up to 3 s
        await asyncio.sleep(0.1)
        head = (await _call(rover.status)).get("head") or {}
        if abs(head.get("pan", pan) - pan) < 0.02 and abs(head.get("tilt", tilt) - tilt) < 0.02:
            break
    return f"Camera aimed at pan {pan:+.2f}, tilt {tilt:+.2f}."


@mcp.tool()
async def say(text: str) -> str:
    """Speak out loud through the rover's speaker (up to 500 characters). Waits until it has finished."""
    said = (await _call(rover.say, text))["saying"]
    for _ in range(600):  # up to 60 s
        await asyncio.sleep(0.1)
        speaker = (await _call(rover.status)).get("speaker") or {}
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
        _whisper = WhisperModel(os.environ.get("ROVER_WHISPER_MODEL", "base.en"),
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
    """Listen through the rover's microphone for a few seconds (1 to 20) and return what was said.
    Don't call this while driving: motor noise drowns out speech."""
    seconds = int(max(1, min(MAX_LISTEN_S, float(seconds))))
    wav = await _call(rover.listen, seconds)
    text = await asyncio.to_thread(_transcribe, wav)
    if text is None:
        return ("Recorded the audio, but speech-to-text isn't installed on this PC. "
                "The user needs to run: pip install faster-whisper")
    return f'Heard: "{text}"' if text else "Heard nothing I could make out."


def check():
    print(f"Rover address: {rover.url}")
    try:
        s = rover.status()
    except RoverError as e:
        print(f"FAILED: {e}")
        return 1
    print("Connected.")
    print(f"  camera: {'yes' if s.get('camera') else 'no'}   pan/tilt: {'yes' if s.get('head') else 'no'}   "
          f"speaker: {'yes' if s.get('speaker') else 'no'}   mic: {'yes' if s.get('mic') else 'no'}")
    print("  " + _describe(s))
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
