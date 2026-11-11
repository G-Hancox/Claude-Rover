# Claude Rover

A Raspberry Pi camera rover that Claude can drive, see through, and talk from.

Built on a donor RC car chassis with a 3D-printed body, powered by a Milwaukee M12 battery.
The Pi handles the hardware; a PC runs the "brain" (speech, vision, and the connection to Claude).

> Status: **software written, tested in simulation only** — waiting on parts.
> Rover side: [pi/](pi/README.md). PC side: [brain/](brain/README.md).

## How it fits together

```
 ┌──────────────── PC ("brain") ────────────────┐
 │ Claude Code · rover tools · speech-to-text   │
 └──────────────────────┬───────────────────────┘
                        │ Wi-Fi
 ┌──────────────── Rover (Pi 4) ────────────────┐
 │ camera stream · drive & steering · speaker   │
 │ mic · obstacle stop · text-to-speech         │
 └──────────────────────────────────────────────┘
```

The Pi 4 (2GB) stays lean (Pi OS Lite, no desktop) and only does hardware I/O.
Anything heavy runs on the PC.

## Repo layout

| Folder   | What's in it                                                        |
|----------|---------------------------------------------------------------------|
| `pi/`    | Code that runs on the rover: drive, steering, camera, audio, sensor |
| `brain/` | Code that runs on the PC: Claude Code tools, speech-to-text         |
| `cad/`   | STL files and source models for the body and mounts                 |
| `docs/`  | Parts list, wiring, build notes                                     |

## Docs

- [Parts list](docs/parts-list.md)
- [Build notes](docs/build-notes.md)

## Future

Once the rover works, the same `pi/` and `brain/` software is meant to carry over to a
TARS-style walking body (see build notes).

## License

GPL-3.0 — see [LICENSE](LICENSE).
