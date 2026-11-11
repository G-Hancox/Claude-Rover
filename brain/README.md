# brain/ — runs on your PC

This connects Claude to the rover using **Claude Code on your existing subscription**, so
there's no separate API bill. It gives Claude six tools:

| Tool | What it does |
|---|---|
| `look` | Takes a photo through the rover's camera and reads the distance sensor |
| `drive` | Drives for up to 3 seconds, then stops |
| `stop` | Stops now |
| `point_camera` | Aims the pan/tilt head |
| `say` | Speaks through the rover's speaker |
| `listen` | Records the rover's mic and turns the speech into text (on this PC) |

> Tested end to end against a **simulated** rover using the same protocol Claude Code
> speaks. Not yet tried inside Claude Code itself, and not yet with the real rover.
> Speech-to-text (`faster-whisper`) is written but was not installed where this was
> tested, so `listen` is the least proven tool.

## What to expect

- **It drives in steps, not smoothly.** Claude looks, thinks for a few seconds, moves for
  a second, and looks again. For smooth driving, use the phone page from `pi/` yourself.
- **It uses your Claude plan.** Every `look` sends a photo, which costs more of your usage
  than text does. A long exploring session will eat into your weekly cap.
- **Claude Code asks permission** the first time it uses each tool. You can allow them for
  the session.

## Setup

1. Install [Claude Code](https://code.claude.com/docs) and Python 3.10 or newer on the PC.
2. In this folder:
   ```bash
   pip install -r requirements.txt
   ```
   `faster-whisper` is only for `listen`. It downloads a speech model (roughly 150 MB) the
   first time it's used.
3. Tell it where the rover is. The default is `http://rover.local:8080`. If your Pi has a
   different name or you use its IP address, set `ROVER_URL` before starting, for example
   on Windows:
   ```
   set ROVER_URL=http://192.168.1.50:8080
   ```
4. Check the connection (the rover program must be running on the Pi):
   ```bash
   python rover_mcp.py --check
   ```
5. Start Claude Code **from this folder** and approve the `rover` server when asked:
   ```bash
   cd brain
   claude
   ```
   Then try: *"Take a look around and tell me what you see."*

If the tools don't show up, type `/mcp` inside Claude Code to see the server's status. On
Mac or Linux, change `"command": "python"` to `"python3"` in `.mcp.json`.

## Try it with no rover

On the PC, in one window: `cd pi` then `python -m rover --mock`.
In another: `set ROVER_URL=http://127.0.0.1:8080`, `cd brain`, `claude`.
Claude will "see" a test pattern and "drive" a rover that isn't there.

## Files

- `rover_mcp.py` — the tools (an MCP server that Claude Code starts by itself)
- `rover_client.py` — plain Python wrapper around the rover's web API
- `.mcp.json` — tells Claude Code how to start the tools
- `CLAUDE.md` — driving and talking rules Claude reads when started in this folder

## Tests

```bash
python -m unittest discover -s tests
```
