# pi/ — runs on the rover

Code for the Raspberry Pi 4: steering and throttle through the PCA9685, a speed cap,
a failsafe that stops the rover if it loses contact, and a live camera stream.

> Written before the hardware arrived. It passes its tests against a simulated servo board,
> but it has **not** run on the real rover yet.

## Wiring

| PCA9685            | Goes to                                             |
|--------------------|-----------------------------------------------------|
| VCC, SDA, SCL, GND | Pi 3.3V (pin 1), SDA (pin 3), SCL (pin 5), GND (pin 6) |
| Channel 0          | Steering servo                                      |
| Channel 1          | ESC throttle lead                                   |
| V+ (servo power)   | Fed by the ESC's red wire — **never from the Pi**   |

The Pi's ground, the PCA9685's ground and the ESC's ground must all be connected.

## Setup on the Pi

```bash
sudo raspi-config          # Interface Options → I2C → enable
sudo apt install -y python3-smbus2 i2c-tools git
sudo apt install -y python3-picamera2 --no-install-recommends   # camera
rpicam-hello --list-cameras   # should list the Camera Module 3
i2cdetect -y 1             # should show 40
git clone https://github.com/G-Hancox/Claude-Rover.git
cd Claude-Rover/pi
```

## First run — wheels off the ground

1. **Calibrate steering:** `python3 -m rover.calibrate steering`
   Type pulse widths (start near 1500) and note centre, full left and full right.
2. **Calibrate throttle:** `python3 -m rover.calibrate throttle`
   Note the neutral value, and which direction is forward.
3. Copy `rover.example.json` to `rover.json` and put your numbers in.
4. **Run it:** `python3 -m rover --config rover.json`
5. Open `http://<pi-address>:8080` on a phone or PC and drive from the pad.

To try the page with no hardware at all: `python3 -m rover --mock`

## Camera

The test page shows the live video above the drive pad. Defaults are 640x480 at 15 fps,
which is light on a 2GB Pi 4 and on Wi-Fi. Settings for `rover.json`:

| Setting | Default | |
|---|---|---|
| `camera_enabled` | `true` | Set `false` to run without a camera |
| `camera_width`, `camera_height` | `640`, `480` | |
| `camera_fps` | `15` | |
| `camera_hflip`, `camera_vflip` | `false` | Flip if the camera is mounted upside down |

If the camera is missing or fails to start, the rover prints a message and still drives.
The video is delayed by a fraction of a second, so drive slower than feels necessary.

## Safety behaviour

- **Speed cap:** full stick only reaches 25% forward / 20% reverse of the ESC's range.
  Raise `max_forward` / `max_reverse` in `rover.json` once it's behaving.
- **Failsafe:** drive commands must keep arriving (the page sends 10 a second).
  After 0.5 s of silence the throttle goes to neutral.
- **Arming:** throttle is held at neutral for 2 s at startup so the ESC can arm.
- **Ramping:** speed builds gradually; slowing and stopping are instant.
- **Reverse:** many brushed ESCs brake on the first pull back and only reverse on the second.
  Check how this one behaves on the bench.

**Known gap:** if the Pi itself freezes, the PCA9685 keeps sending the last pulse it was
given, and software can't fix that. Until there's a hardware cutoff, keep the speed cap low
and be ready to grab the rover. See `docs/build-notes.md`.

## Control API

| Request       | Body                                 | Does                 |
|---------------|--------------------------------------|----------------------|
| `GET /status` |                                      | Current state (JSON) |
| `GET /stream.mjpg` |                                 | Live video (MJPEG)   |
| `GET /snapshot.jpg` |                                | One still frame      |
| `POST /drive` | `{"throttle": -1..1, "steering": -1..1}` | Set the sticks   |
| `POST /stop`  |                                      | Stop now             |

There is no login. Anyone on your Wi-Fi can drive it and watch the camera. To require a password, set
`ROVER_TOKEN=something` before starting; POSTs must then send it as an `X-Rover-Token`
header (the built-in test page doesn't do this yet). The token does not cover the video.

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
