# pi/ — runs on the rover

Everything the Raspberry Pi 4 does: drive and steering, camera stream, camera pan and tilt,
obstacle stop, speaker and mic. A PC talks to it over Wi-Fi (see the control API below).

> Written before the hardware arrived. It passes its tests against simulated hardware,
> but **none of it has run on the real rover yet.** The parts that talk to real devices
> (camera, distance sensor, sound) are the most likely to need a tweak on the bench.

## Wiring

**PCA9685 servo board**

| PCA9685            | Goes to                                                |
|--------------------|--------------------------------------------------------|
| VCC, SDA, SCL, GND | Pi 3.3V (pin 1), SDA (pin 3), SCL (pin 5), GND (pin 6) |
| Channel 0          | Steering servo                                         |
| Channel 1          | ESC throttle lead                                      |
| Channel 2          | Camera pan servo                                       |
| Channel 3          | Camera tilt servo                                      |
| V+ (servo power)   | Fed by the ESC's red wire — **never from the Pi**      |

The Pi's ground, the PCA9685's ground and the ESC's ground must all be connected.
If the pan/tilt servos make the steering twitch or the ESC cut out, the ESC's built-in
5–6V supply is too weak for all three servos; give the servo rail its own 6V supply.

**Distance sensor** — mount it on the body facing forward, not on the camera head.

| Sensor | Wiring |
|---|---|
| HC-SR04 (ultrasonic) | VCC → 5V, GND → GND, Trig → GPIO23 (pin 16), Echo → **voltage divider** → GPIO24 (pin 18). Echo is 5V and the Pi's pins are 3.3V: use 1kΩ from Echo to the pin and 2kΩ from the pin to ground. |
| VL53L1X (laser) | VIN → 3.3V, GND → GND, SDA and SCL shared with the PCA9685 |

**Speaker amp (MAX98357A)** — pin numbers below are from memory of Adafruit's guide for
this board; check them against that guide before powering up.

| Amp | Pi |
|---|---|
| Vin, GND | 5V, GND |
| LRC | GPIO19 (pin 35) |
| BCLK | GPIO18 (pin 12) |
| DIN | GPIO21 (pin 40) |

The USB mic just plugs in.

## Setup on the Pi

```bash
sudo raspi-config          # Interface Options → I2C → enable
sudo apt install -y python3-smbus2 i2c-tools git
sudo apt install -y python3-picamera2 --no-install-recommends   # camera
sudo apt install -y alsa-utils espeak-ng                        # speaker and mic
sudo apt install -y python3-gpiozero                            # only for the HC-SR04
i2cdetect -y 1               # should show 40 (and 29 with a VL53L1X)
rpicam-hello --list-cameras  # should list the Camera Module 3
git clone https://github.com/G-Hancox/Claude-Rover.git
cd Claude-Rover/pi
```

For the speaker amp, add `dtoverlay=max98357a` to `/boot/firmware/config.txt` and reboot.
Then test sound on its own before involving the rover code:

```bash
aplay -l                      # find the amp;   arecord -l   to find the USB mic
espeak-ng --stdout "testing" | aplay
arecord -d 3 -f S16_LE -r 16000 test.wav && aplay test.wav
```

If the default device is wrong, set `audio_out_device` / `audio_in_device` in `rover.json`
(for example `"plughw:1,0"`).

The VL53L1X needs the `vl53l1x` Python package, which is installed with pip rather than apt.

## First run — wheels off the ground

1. **Calibrate** each servo. Type pulse widths (start near 1500) and note the values:
   - `python3 -m rover.calibrate steering` — centre, full left, full right
   - `python3 -m rover.calibrate throttle` — neutral, and which way is forward
   - `python3 -m rover.calibrate pan` and `tilt` — centre and how far each can go
     before the mount binds
2. Copy `rover.example.json` to `rover.json` and put your numbers in.
3. **Run it:** `python3 -m rover --config rover.json`
   The startup lines say which parts came up (camera, pan/tilt, speaker, mic, sensor).
4. Open `http://<pi-address>:8080` on a phone or PC.

To try the page with no hardware at all: `python3 -m rover --mock`

## Settings (`rover.json`)

Anything not listed in your file keeps its default. All settings and defaults are in
[`rover/config.py`](rover/config.py). The ones you're most likely to change:

| Setting | Default | |
|---|---|---|
| `max_forward`, `max_reverse` | `0.25`, `0.20` | Speed cap, as a fraction of the ESC's range |
| `distance_sensor` | `"none"` | `"hcsr04"` or `"vl53l1x"` once one is fitted |
| `distance_stop_m`, `distance_clear_m` | `0.40`, `0.55` | Stop closer than the first; go again past the second |
| `camera_hflip`, `camera_vflip` | `false` | Flip if the camera is mounted upside down |
| `camera_width`, `camera_height`, `camera_fps` | `640`, `480`, `15` | |
| `head_speed_per_s` | `1.5` | How fast the camera swings |
| `tts_engine` | `"espeak"` | `"piper"` for a natural voice (also set `piper_model`) |
| `audio_out_device`, `audio_in_device` | `"default"` | ALSA device names |
| `camera_enabled`, `head_enabled`, `speaker_enabled`, `mic_enabled` | `true` | Turn a part off |

**Voice:** espeak is the default because it installs with one command and sounds like a
robot. For a natural voice, install [Piper](https://github.com/OHF-Voice/piper1-gpl) and a
voice file, then set `tts_engine` to `"piper"`, `piper_model` to the `.onnx` path and, if
your Piper is started differently, `piper_bin`. The rover runs
`<piper_bin> --model <file> --output-raw`; that matches the standalone Piper program, and
has not been tried against the newer Python package.

## Safety behaviour

- **Speed cap:** full stick only reaches 25% forward / 20% reverse of the ESC's range.
- **Failsafe:** drive commands must keep arriving (the page sends 10 a second).
  After 0.5 s of silence the throttle goes to neutral.
- **Arming:** throttle is held at neutral for 2 s at startup so the ESC can arm.
- **Ramping:** speed builds gradually; slowing and stopping are instant.
- **Obstacle stop:** with a distance sensor on, forward throttle is refused inside
  `distance_stop_m`. Reverse and steering still work so you can back out.
- **Broken sensor = no forward.** If a sensor is configured and stops answering for a
  second (or never starts), forward driving is blocked and the page says so.
- **Extras can't take down driving.** If the camera, speaker, mic or sensor fails, the rover
  reports it and keeps driving and stopping normally.

**Known gaps**

- If the Pi itself freezes, the PCA9685 keeps sending the last pulse it was given, and
  software can't fix that. Until there's a hardware cutoff, keep the speed cap low. See
  `docs/build-notes.md`.
- The obstacle stop cuts throttle; it does not brake. The rover coasts, and the sensor only
  looks straight ahead (not behind, not down stairs). The 0.40 m default is a guess to
  tune on the bench at your chosen speed.
- Many brushed ESCs brake on the first pull back and only reverse on the second. Check how
  this one behaves.
- The video is a fraction of a second behind.

## Control API

| Request | Body | Does |
|---|---|---|
| `GET /status` | | Everything's current state (JSON) |
| `GET /stream.mjpg` | | Live video (MJPEG) |
| `GET /snapshot.jpg` | | One still frame |
| `POST /drive` | `{"throttle": -1..1, "steering": -1..1}` | Set the sticks; repeat at least twice a second |
| `POST /stop` | | Stop now |
| `POST /look` | `{"pan": -1..1, "tilt": -1..1}` | Aim the camera (left/down are negative) |
| `POST /center` | | Camera straight ahead |
| `POST /say` | `{"text": "..."}` | Speak (up to 500 characters; returns right away) |
| `POST /play` | a WAV file | Play it through the speaker |
| `POST /listen` | `{"seconds": 1..30}` | Record the mic; returns a 16 kHz mono WAV |

**There is no login.** Anyone on your Wi-Fi can drive it, watch the camera and listen
through the mic. To require a password for everything except video, set
`ROVER_TOKEN=something` before starting; POSTs must then send it as an `X-Rover-Token`
header. The built-in test page doesn't send it yet, so with a token set the page can only watch.

## Start at boot (optional)

```bash
sudo cp claude-rover.service /etc/systemd/system/
sudo systemctl enable --now claude-rover
```

Edit the paths and user in the service file first if the repo isn't in `/home/pi/Claude-Rover`.

## Tests

```bash
python3 -m unittest discover -s tests
```
