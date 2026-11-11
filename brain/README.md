# brain/ — runs on your PC

This connects Claude to TARS using **Claude Code on your existing subscription**, so
there's no separate API bill. It gives Claude six tools:

| Tool | What it does |
|---|---|
| `look` | Takes a photo through TARS's camera |
| `move` | Does a move (step, turn, bow, laugh...) and waits for it to finish |
| `list_moves` | Lists the moves with a line about each |
| `stop` | Cuts a move short; TARS eases back to standing |
| `say` | Speaks through TARS's speaker |
| `listen` | Records TARS's mics and turns the speech into text (on this PC) |

> Tested end to end against a **simulated** TARS using the same protocol Claude Code
> speaks. Not yet tried inside Claude Code itself, and not yet with the real robot.
> Speech-to-text (`faster-whisper`) is written but was not installed where this was
> tested, so `listen` is the least proven tool.

## What to expect

- **It's slow, on purpose.** Claude looks, thinks for a few seconds, takes a step or a turn,
  and looks again. TARS itself walks slowly, so that's a good match.
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
3. Tell it where TARS is. The default is `http://tars.local:8080`, which works if you named
   the Pi `tars` when you set up its SD card. Otherwise set `TARS_URL` before starting,
   for example on Windows:
   ```
   set TARS_URL=http://192.168.1.50:8080
   ```
4. Check the connection (the TARS program must be running on the Pi):
   ```bash
   python tars_mcp.py --check
   ```
5. Start Claude Code **from this folder** and approve the `tars` server when asked:
   ```bash
   cd brain
   claude
   ```
   Then try: *"Take a look around and tell me what you see."*

If the tools don't show up, type `/mcp` inside Claude Code to see the server's status. On
Mac or Linux, change `"command": "python"` to `"python3"` in `.mcp.json`.

## Try it with no robot

On the PC, in one window: `cd pi` then `python -m tars --mock`.
In another: `set TARS_URL=http://127.0.0.1:8080`, `cd brain`, `claude`.
Claude will "see" a test pattern and walk a TARS that isn't there. Open
`http://localhost:8080` to watch its moves on the control page.

## Files

- `tars_mcp.py` — the tools (an MCP server that Claude Code starts by itself)
- `tars_client.py` — plain Python wrapper around TARS's web API
- `.mcp.json` — tells Claude Code how to start the tools
- `CLAUDE.md` — moving and talking rules Claude reads when started in this folder

## Tests

```bash
python -m unittest discover -s tests
```
