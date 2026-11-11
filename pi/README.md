# pi/ — runs on TARS

Everything the Raspberry Pi 4 inside TARS does: the four leg servos, the camera, the
speaker and the mics, plus a control page you can open on your phone. The PC side
([`brain/`](../brain/README.md)) talks to it over Wi-Fi.

> Written before the hardware arrived. It passes its tests against simulated hardware,
> but **none of it has run on a real TARS yet.** The camera, sound and real move speeds
> are the most likely to need adjusting on the bench.

## Build first

Print and assemble the body following the
[TARS-AI V3 guide](https://github.com/TARS-AI-Community/TARS-AI/wiki/V3) — print list in
[`cad/tars/`](../cad/tars/README.md), shop list in [`docs/parts-list.md`](../docs/parts-list.md).
Use **this** software instead of theirs where the guide runs `app-servotester.py`
(see "Fitting the servo horns" below). Everything else in their guide applies as written.

Before connecting any servo, **set the XL4015 buck converter to 6.2V** (guide: electronics step 2).

## Wiring

| Part | Connects to |
|---|---|
| PCA9685 VCC, SDA, SCL, GND | Pi 3.3V (pin 1), SDA (pin 3), SCL (pin 5), GND (pin 6) |
| PCA9685 V+ (servo power) | XL4015 output, 6.2V |
| Channel 0 | Left leg height servo |
| Channel 1 | Right leg height servo |
| Channel 2 | Left leg swing servo |
| Channel 3 | Right leg swing servo |
| USB sound card | Any Pi USB port |
| OV5647 camera | Pi camera connector (15-pin ribbon) |
| Pi power | 5V USB regulator → Pi USB-C |

Channels match the V3 guide's servo numbers (torso step 4 photo).

## Setup on the Pi

In Raspberry Pi Imager, pick **Raspberry Pi OS Lite (64-bit)**, and in its settings set the
hostname to **`tars`**, your Wi-Fi, a username, and turn on SSH. Then, over SSH:

```bash
sudo raspi-config          # Interface Options → I2C → enable
sudo apt update
sudo apt install -y git python3-smbus2 i2c-tools
sudo apt install -y python3-picamera2 --no-install-recommends   # camera
sudo apt install -y alsa-utils espeak-ng                        # speaker and mics
i2cdetect -y 1               # should show 40 (the PCA9685)
rpicam-hello --list-cameras  # should list the OV5647
git clone https://github.com/G-Hancox/Claude-TARS.git
cd Claude-TARS/pi
cp tars.example.json tars.json
```

If the repo isn't renamed yet, clone `Claude-Rover.git` instead; GitHub redirects old names
after a rename anyway.

**Test sound on its own** before involving TARS:

```bash
aplay -l                      # find the USB sound card
arecord -l                    # and its mics
espeak-ng --stdout "testing" | aplay -D plughw:1,0
arecord -D plughw:1,0 -d 3 -f S16_LE -r 16000 test.wav && aplay -D plughw:1,0 test.wav
```

Use the card number `aplay -l` shows. Then put it in `tars.json` as
`"audio_out_device": "plughw:1,0"` and `"audio_in_device": "plughw:1,0"`.

## Fitting the servo horns (guide torso steps 7–8)

Where the V3 guide runs `app-servotester.py` → "Set all servos to preset position", run:

```bash
python3 -m tars.calibrate preset
```

All four leg servos hold the assembly position (350, 350, 300, 300 — the same values as
TARS-AI). Fit the horns as the guide shows without forcing the servos, then press Enter
and they go limp.

## Calibrating the legs

Keep TARS on its base with the legs free to move. For each joint:

```bash
python3 -m tars.calibrate left_height     # then right_height, left_leg, right_leg
```

Type values (0–600) in small steps and note where each end of travel is, just before
anything binds. Put them in `tars.json`:

| Setting | Joint end |
|---|---|
| `left_up_height`, `left_down_height` | left leg fully up / fully down |
| `right_up_height`, `right_down_height` | right leg fully up / fully down |
| `forward_left_leg`, `back_left_leg` | left leg swung fully forward / back |
| `forward_right_leg`, `back_right_leg` | right leg swung fully forward / back |

The defaults are TARS-AI V3's, so a well-assembled build may only need small changes. The
TARS-AI [calibration video](https://www.youtube.com/watch?v=We_4mcOO7hI&t=20s) uses the
same units.

## Running it

```bash
python3 -m tars --config tars.json
```

Open **http://tars.local:8080** on your phone. You get the camera, walk buttons (step,
back, turn), the expressive moves (bow, laugh, tilt, pose…), STOP, Go limp, a Say box and
a Listen button. Keys on a PC: arrows to walk, Space to stop, L to go limp.

First moves: start with `stand` and `tilt_left` on the base, then `step_forward` on the
floor. If "turn left" turns right, set `"swap_turns": true`. If moves look too fast or too
slow, change `move_time_scale` (bigger is slower).

To try the page with no hardware: `python3 -m tars --mock`

## Settings (`tars.json`)

Anything not in your file keeps its default. All settings are in
[`tars/config.py`](tars/config.py). Besides the leg limits above:

| Setting | Default | |
|---|---|---|
| `move_time_scale` | `1.0` | Bigger = slower moves |
| `swap_turns` | `false` | Swap left and right turns |
| `release_after_move` | `true` | Servos go limp after each move |
| `easing` | `0.6` | 0 = constant speed, 1 = soft starts and stops |
| `camera_hflip`, `camera_vflip` | `false` | Flip the picture if it's mirrored or upside down |
| `camera_width`, `camera_height`, `camera_fps` | `640`, `480`, `15` | |
| `audio_out_device`, `audio_in_device` | `"default"` | ALSA device names |
| `tts_engine` | `"espeak"` | `"piper"` for a natural voice (also set `piper_model`) |
| `camera_enabled`, `speaker_enabled`, `mic_enabled` | `true` | Turn a part off |

**Voice:** espeak installs with one command and sounds robotic, which suits TARS. For a
natural voice, install [Piper](https://github.com/OHF-Voice/piper1-gpl) and a voice file,
then set `tts_engine` to `"piper"` and `piper_model` to the `.onnx` path. TARS runs
`<piper_bin> --model <file> --output-raw`, which matches the standalone Piper program; it
hasn't been tried against the newer Python package.

## How moves behave

- **One move at a time.** Each starts and ends standing.
- **Nothing moves at startup.** Servos stay limp until the first move.
- **Smooth re-engaging.** Leg positions are saved after each move, so the next one starts
  from where the servos really are. The very first move ever runs slowly.
- **STOP** cuts the move short and eases back to standing.
- **Go limp** cuts servo power immediately. TARS will drop onto its feet.
- **Servo errors** (for example the PCA9685 losing power) end the move, go limp, and show
  on the page.
- There's no distance sensor. Keep it away from table edges.

## Control API

| Request | Body | Does |
|---|---|---|
| `GET /status` | | Legs, camera, speaker, mic state (JSON) |
| `GET /moves` | | The moves, with a line about each |
| `GET /stream.mjpg` | | Live video (MJPEG) |
| `GET /snapshot.jpg` | | One still frame |
| `POST /move` | `{"name": "step_forward", "times": 1}` | Start a move (returns at once; 409 if busy) |
| `POST /stop` | | Cut the move short, return to standing |
| `POST /release` | | Servos limp now |
| `POST /say` | `{"text": "..."}` | Speak (up to 500 characters; returns at once) |
| `POST /play` | a WAV file | Play it through the speaker |
| `POST /listen` | `{"seconds": 1..30}` | Record the mics; returns a 16 kHz mono WAV |

**There is no login.** Anyone on your Wi-Fi can move TARS, watch the camera and listen
through the mics. To require a password for everything except video, set
`TARS_TOKEN=something` before starting; POSTs must then send it as an `X-TARS-Token`
header. The phone page doesn't send it yet, so with a token set the page can only watch.

## Start at boot (optional)

```bash
sudo cp claude-tars.service /etc/systemd/system/
sudo systemctl enable --now claude-tars
```

Edit the user and paths in the service file first if they don't match yours.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Credits

`tars/moves.py` adapts the leg keyframes from TARS-AI V3 by Charles-Olivier Dion
(AtomikSpace), CC-BY-NC 4.0. The servo units and channel layout follow the same project.
