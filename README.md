# Claude TARS

Claude in a TARS body: a 3D-printed robot from *Interstellar* that walks on servo legs,
sees through a camera, and talks through its own speaker and mics. Claude drives it from a
PC through Claude Code.

> Status: **software written and tested in simulation; parts not bought yet.**
> Repo will be renamed from Claude-Rover to Claude-TARS.

## How it fits together

```
 ┌──────────────── PC ("brain") ────────────────┐
 │ Claude Code · TARS tools · speech-to-text    │
 └──────────────────────┬───────────────────────┘
                        │ Wi-Fi
 ┌──────────────── TARS (Pi 4) ─────────────────┐
 │ legs (4 servos) · camera · speaker · mics    │
 │ text-to-speech · control page for your phone │
 └──────────────────────────────────────────────┘
```

The Pi 4 (2GB) stays lean (Pi OS Lite, no desktop) and only does hardware. Anything heavy
runs on the PC.

## Repo layout

| Folder | What's in it |
|--------|--------------|
| [`pi/`](pi/README.md) | Code that runs on TARS: legs, camera, speaker, mics, phone control page |
| [`brain/`](brain/README.md) | Code that runs on the PC: Claude Code tools, speech-to-text |
| [`cad/tars/`](cad/tars/README.md) | Print files and the print list (TARS-AI V3 design, CC-BY-NC) |
| [`docs/`](docs/) | [Shop list](docs/parts-list.md), [build notes](docs/build-notes.md) |

## Credits

The TARS body and walking moves come from the open-source TARS community: the original
miniature TARS by **Charlie Diaz**, and **TARS-AI V3** by Charles-Olivier Dion (AtomikSpace)
and the [TARS-AI Community](https://github.com/TARS-AI-Community/TARS-AI). TARS itself is
from the film *Interstellar*. This is a fan-made, non-commercial project.

## License

Code in this repo: GPL-3.0, see [LICENSE](LICENSE). Two exceptions, both CC-BY-NC 4.0
(non-commercial only, with credit): the print files in `cad/tars/` and the move keyframes
in `pi/tars/moves.py`.
