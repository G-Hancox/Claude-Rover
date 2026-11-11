# brain/ — runs on your PC

This connects Claude to TARS using **Claude Code on your existing subscription**, so
there's no separate API bill. It gives Claude these tools:

| Tool | What it does |
|---|---|
| `look` | Takes a photo through TARS's camera |
| `move` | Does a move (step, turn, bow, laugh...) and waits for it to finish |
| `list_moves` | Lists the moves with a line about each |
| `stop` | Cuts a move short; TARS eases back to standing |
| `say` | Speaks through TARS's speaker (with an emotion, in the TARS voice) and puts the words on its screen |
| `show` | Puts text on TARS's front screen without speaking |
| `personality` | Reads or switches the mode (Claude or TARS) and TARS's honesty/humor settings |
| `remember`, `recall`, `forget` | Notes that last between conversations (see below) |
| `listen` | Records TARS's mics and turns the speech into text (on this PC) |

> Tested end to end against a **simulated** TARS using the same protocol Claude Code
> speaks. Not yet tried inside Claude Code itself, and not yet with the real robot.
> Speech-to-text (`faster-whisper`) is written but was not installed where this was
> tested, so `listen` and spoken questions are the least proven parts. The voice program
> was tested with typed questions and a stand-in for Claude Code.

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

**After the first time, just double-click `Start TARS.bat`** in this folder (you can drag a
shortcut to it onto your desktop). It checks TARS is reachable, then opens Claude Code.

If the tools don't show up, type `/mcp` inside Claude Code to see the server's status. On
Mac or Linux, change `"command": "python"` to `"python3"` in `.mcp.json`.

## Hands-free: "Hey TARS"

**Double-click `Start TARS voice.bat`** and leave the window open. Then just say
**"Hey TARS"**, wait for the beep, and talk. TARS answers out loud. You can also type
questions into **Ask something** on the phone page.

Needs speech-to-text on this PC, once: `pip install faster-whisper` (it downloads a
~150 MB speech model the first time).

Things it handles instantly, without asking Claude:

| Say | What happens |
|---|---|
| "Stop" / "Freeze" | Stops moving right away |
| "TARS mode" / "Claude mode" | Switches personality (also a button on the phone page) |
| "Set humor to 60" / "Set honesty to 95" | Changes TARS's settings (shown on its screen) |
| "New conversation" / "Start over" | Forgets the conversation so far |

**The two modes.** In **Claude mode** you're talking to Claude, as itself. In **TARS mode**
it's still Claude underneath, playing TARS: dry, deadpan, short answers.

**The dials** work in both modes (lighter in Claude mode, full strength as TARS):

| Humor | Style |
|---|---|
| 0–10 | No jokes |
| 11–35 | Very dry, rare remarks |
| 36–60 | Deadpan wit now and then |
| 61–80 | Regular dry jokes, gentle teasing (default 75) |
| 81–94 | Sardonic, mischievous, running gags |
| 95–100 | Fully twisted: dark, absurd, mock-sinister robot humor |

Honesty sets **bluntness**, from diplomatic to blunt (default 90). At every level it tells
the truth. At any humor level it stays kind: no cruel jokes, and none when someone is
upset or asking about safety. The screen's title shows which mode is on. Switching starts a fresh
conversation.

**How it works:** each question runs `claude -p` in this folder with TARS's tools, and
answers stay in one conversation until you pause for 10 minutes. Voice turns are locked
down: they can look, move, show things on the screen and search the web, but can't read
or change files or run commands on this PC (anyone in the room can talk to TARS).
Every question uses your Claude plan, and answers take a few seconds.

## Memory between conversations

Claude keeps a notebook in **`brain/memory.md`** on this PC (never uploaded to GitHub). It
saves notes on its own when something is worth knowing next time: an unfinished job and
where it stopped, the house layout, who's who as you introduce people, and how you like
things done. It says "Noted." when it saves. Every conversation starts with the notes.

- "Remember that the printer is on the left bench." / "What do you remember?" /
  "Forget the printer note."
- Open `memory.md` in Notepad any time to read, fix or delete notes.

For things you want it to always know without saying them, add lines to `CLAUDE.md`.

## Try it with no robot

On the PC, in one window: `cd pi` then `python -m tars --mock`.
In another: `set TARS_URL=http://127.0.0.1:8080`, `cd brain`, `claude`.
Claude will "see" a test pattern and walk a TARS that isn't there. Open
`http://localhost:8080` to watch its moves on the control page.

## Files

- `tars_mcp.py` — the tools (an MCP server that Claude Code starts by itself)
- `tars_voice.py` — the hands-free "Hey TARS" program (`Start TARS voice.bat`)
- `tars_memory.py` — the notebook (`memory.md`)
- `tars_client.py` — plain Python wrapper around TARS's web API
- `.mcp.json` — tells Claude Code how to start the tools
- `CLAUDE.md` — moving and talking rules Claude reads when started in this folder

## Tests

```bash
python -m unittest discover -s tests
```
