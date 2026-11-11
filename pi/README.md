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
| OV5647 camera | Pi **camera** connector (CSI, 15-pin ribbon) |
| Waveshare 5" screen | Pi **display** connector (DSI, 15-pin ribbon) |
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
sudo apt install -y python3-pil python3-numpy fonts-dejavu-core # screen
i2cdetect -y 1               # should show 40 (the PCA9685)
rpicam-hello --list-cameras  # should list the OV5647
git clone https://github.com/G-Hancox/Claude-TARS.git
cd Claude-TARS/pi
cp tars.example.json tars.json
python3 -m venv --system-site-packages ~/tars-venv            # for the TARS voice
~/tars-venv/bin/pip install piper-tts
```

From here on, run things with `~/tars-venv/bin/python3` instead of `python3`, so the
TARS voice is available. (Plain `python3` still works for everything else.)

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

## The screen

The Pi 4 has one display connector (DSI), labelled DISPLAY, next to the HDMI ports. The
camera goes in the other one (CAMERA).

Add this to the end of `/boot/firmware/config.txt` and reboot:

```
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dsi-7inch
```

That's the line Waveshare gives for this screen on a Pi 4 (despite the "7inch" in the
name). The V3 guide's `...waveshare-panel,7_0_inchC,dsi0` line is for a different screen on
a Pi 5, so don't copy that one.

The Pi's login prompt also draws on the screen and would flicker through TARS's display.
Turn it off (you'll still log in over SSH):

```bash
sudo systemctl disable --now getty@tty1
sudo sed -i 's/$/ consoleblank=0 vt.global_cursor_default=0/' /boot/firmware/cmdline.txt
sudo reboot
```

When TARS is running, the screen's title says **CLAUDE** or **TARS** (the current mode), and it shows:

- **Standing by:** an HONESTY 90% / HUMOR 75% readout, and the address of the control
  page (handy for finding TARS on your Wi-Fi)
- **Speaking:** the words being said, with a sound meter
- **Listening:** a pulsing LISTENING marker
- **Moving:** the move's name at the top

The control page shows a live copy of the screen, and `GET /screen.png` returns it. If
the picture is sideways or upside down, set `display_rotate` (90, 180 or 270).

## The TARS voice

```bash
python3 -m tars.voice download                  # about 60 MB, into ~/tars-voice
~/tars-venv/bin/python3 -m tars.voice test "Hello. I'm ready." --config tars.json
~/tars-venv/bin/python3 -m tars.voice test "That's great news" --emotion joy --config tars.json
~/tars-venv/bin/python3 -m tars.voice save "Testing my pace." pace.wav --pace 1.3
```

`--pace` tries a speed without changing anything (higher is slower). When you like one,
put it in `tars.json` as `"voice_pace"`.

Then in `tars.json`:

```json
"tts_engine": "piper",
"piper_model": "~/tars-voice/TARS.onnx"
```

The voice has eight emotions (neutral, joy, curiosity, surprise, sadness, anger, fear,
love), but each is trained on fewer lines than neutral and drifts further from TARS's sound,
so they're **off by default**: TARS stays in its flat, dry delivery. Set
`"voice_emotions": true` to use them. `--emotion` on the test command always works, for trying them.

`voice_steadiness` (0-1, default 0.6) turns down Piper's built-in randomness, so lines come
out consistent. Try `--steady 0.3` and `--steady 0.9` on the test command to compare.

This is the TARS-AI community's Piper voice, trained on TARS's lines from *Interstellar*,
voiced by the actor Bill Irwin. Keep it to this personal robot: don't post clips of it or
pass it off as him. Keep a backup of `~/tars-voice` on your PC; it lives on Hugging Face,
not in this repo.

If the voice can't load (piper-tts not installed, file missing), TARS says why at startup
and carries on without a speaker. Set `"tts_engine": "espeak"` to go back to the robotic voice.

## "Hey TARS"

The wake word runs on the Pi and starts by itself when TARS starts (once the USB sound
card is plugged in). Say **"Hey TARS"**, wait for the beep, and talk; TARS records until
you stop. The PC answers, using `brain/Start TARS voice.bat` (see `brain/README.md`).

It doesn't listen while TARS is talking or moving, so it won't wake itself up.

Check it once the sound card is in:

```bash
~/tars-venv/bin/python3 -m tars.wake test --config tars.json   # synthetic voices: "Hey TARS" should score highest
~/tars-venv/bin/python3 -m tars.wake live --config tars.json   # live meter: say "Hey TARS" a few times
```

If it wakes too easily (or not at all), lower or raise `wake_threshold` (default 0.84).
The model is the TARS-AI community's (`tars/wakeword/`, CC-BY-NC).

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
~/tars-venv/bin/python3 -m tars --config tars.json
```

Open **http://tars.local:8080** on your phone (the address is also on TARS's screen). You
get the camera, a copy of the front screen, walk buttons (step, back, turn), the expressive
moves (bow, laugh, tilt, pose…), STOP, Go limp, a Say box with an emotion picker and a
Listen button. Keys on a PC: arrows to walk, Space to stop, L to go limp.

First moves: start with `stand` and `tilt_left` on the base, then `step_forward` on the
floor. If "turn left" turns right, set `"swap_turns": true`. If moves look too fast or too
slow, change `move_time_scale` (bigger is slower).

To try the page with no hardware: `python3 -m tars --mock`

## Settings (`tars.json`)

Anything not in your file keeps its default. All settings are in
[`tars/config.py`](tars/config.py). Besides the leg limits above:

| Setting | Default | |
|---|---|---|
| `mock` | `false` | `true` = pretend hardware, for testing before the parts are wired |
| `move_time_scale` | `1.0` | Bigger = slower moves |
| `swap_turns` | `false` | Swap left and right turns |
| `release_after_move` | `true` | Servos go limp after each move |
| `easing` | `0.6` | 0 = constant speed, 1 = soft starts and stops |
| `camera_hflip`, `camera_vflip` | `false` | Flip the picture if it's mirrored or upside down |
| `camera_width`, `camera_height`, `camera_fps` | `640`, `480`, `15` | |
| `audio_out_device`, `audio_in_device` | `"default"` | ALSA device names |
| `tts_engine` | `"espeak"` | `"piper"` for the TARS voice |
| `piper_model` | `"~/tars-voice/TARS.onnx"` | Where the voice file is |
| `piper_speaker` | `"0"` | Which of the voice's 8 speakers TARS uses (0-7). 0 and 2 sound most like TARS |
| `voice_steadiness` | `0.6` | 0 = Piper's natural variation, 1 = every line delivered alike |
| `voice_sentence_pause` | `0.9` | Seconds of quiet between sentences (TARS leaves gaps). Emotional replies use 0.5 |
| `voice_emotions` | `false` | Use the emotion voices. Off by default: they drift from TARS's sound |
| `voice_pace` | `1.45` | TARS voice speed: 1.0 = as trained, higher = slower. Same for every emotion |
| `display_rotate` | `0` | Turn the screen picture 90, 180 or 270 |
| `honesty`, `humor` | `90`, `75` | TARS's settings, shown on the idle screen (also changeable by voice) |
| `persona` | `"claude"` | Starting mode: `"claude"` or `"tars"` (switchable on the fly) |
| `wake_enabled` | `true` | Listen for "Hey TARS" |
| `wake_threshold` | `0.84` | Lower = wakes more easily |
| `camera_enabled`, `speaker_enabled`, `mic_enabled`, `display_enabled` | `true` | Turn a part off |

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
| `GET /screen.png` | | What the front screen shows |
| `POST /say` | `{"text": "...", "emotion": "joy"}` | Speak (up to 500 characters; emotion optional; returns at once) |
| `POST /display` | `{"text": "...", "seconds": 15}` | Show text on the screen (`""` clears) |
| `GET /heard?after=N&wait=25` | | Next thing said after "Hey TARS" (WAV) or typed (JSON); 204 if none |
| `POST /heard` | `{"text": "..."}` or a WAV | Talk to TARS without the wake word |
| `GET`/`POST /persona` | `{"mode": "tars", "humor": 60}` | Read or change the mode and settings |
| `POST /play` | a WAV file | Play it through the speaker |
| `POST /listen` | `{"seconds": 1..30}` | Record the mics; returns a 16 kHz mono WAV |

**There is no login.** Anyone on your Wi-Fi can move TARS, watch the camera and listen
through the mics. To require a password for everything except video, set
`TARS_TOKEN=something` before starting; POSTs must then send it as an `X-TARS-Token`
header. The phone page doesn't send it yet, so with a token set the page can only watch.

## Start at boot

```bash
sh install-service.sh
```

TARS then starts by itself whenever the Pi powers on: no SSH needed. It uses `tars.json`,
so while the parts aren't wired up yet, set `"mock": true` there; set it back to `false`
once the servo board is connected.

After changing `tars.json` or pulling an update: `sudo systemctl restart claude-tars`.
To see its messages: `journalctl -u claude-tars -f`. To turn it off: `sh install-service.sh remove`.

**Switch the Pi off properly** before cutting power, or the SD card can get corrupted:
`sudo poweroff`, then wait for the green light to stop blinking.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Credits

`tars/moves.py` adapts the leg keyframes from TARS-AI V3 by Charles-Olivier Dion
(AtomikSpace), CC-BY-NC 4.0. The servo units and channel layout follow the same project,
and the TARS voice is theirs too.
