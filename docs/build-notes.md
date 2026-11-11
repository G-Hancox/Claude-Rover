# Build notes

## Decisions so far

- **Rover first, TARS later.** The rover is the easier build; its software carries over.
- **Brain on the PC.** The Pi 4 is 2GB, so it only does hardware I/O. Speech-to-text,
  Claude, and text-to-speech run on the PC.
- **Power:** Milwaukee M12 → fuse block → main switch → buck converter (5V for the Pi)
  and the ESC / servo rail.
- **Servos through a PCA9685**, not straight off the GPIO — software PWM on the Pi makes
  servos jitter. The RC car's ESC and steering servo take standard servo signals, so the
  PCA9685 can likely drive them directly.
- **Two-way voice:** I2S amp + speaker for the voice, USB mic for listening.

## Donor RC car

- **ESC:** Dynamite DYNS2210 (Horizon Hobby), brushed, jumper for LiPo / NiMH.
  Rated 5–7 cell NiMH or LiPo: **2S with 12T–55T motors, 3S with 35T–55T motors.**
- **Steering:** standard 3-wire servo.
- **Throttle:** ESC takes a standard 3-wire servo signal.
- Both go straight to the PCA9685 — no separate motor driver needed.
- M12 (~12.6V full) counts as 3S → **only OK if the motor is 35T or higher.**
  If so, set the ESC jumper to **LiPo** so its low-voltage cutoff protects the battery.
- ESC red wire (BEC) can feed the PCA9685 servo rail (V+), **never the Pi**. Common ground everywhere.
- The pan/tilt MG996Rs may be too much for the ESC's BEC; may need a separate 6V servo supply.

## Open questions

- [ ] Motor turn count (needs to be 35T+ for 3S)
- [ ] Does the existing buck converter pass the load test?

## Things to watch

- **Motor noise vs. mic.** Speech recognition won't work well while driving. Start with
  "stop to talk"; a wake word can come later.
- **Mic and speaker placement.** Keep them apart so the rover doesn't hear itself, and
  keep the speaker away from the drive motor's gear whine.
- **12V on the ESC.** Many RC cars are built for 7.2V packs.

## Software plan (rough)

- `pi/` — Python on Pi OS Lite: PCA9685 drive/steering/pan-tilt, camera stream,
  distance-sensor safety stop, audio in/out, all exposed over the network to the PC.
- `brain/` — PC side: speech-to-text (Whisper or Vosk), Claude, text-to-speech (Piper),
  camera viewer and drive controls.

## Later: TARS body

Charlie Diaz's TARS replica (CAD and code on Hackster) and the GPTARS fork use the same
PCA9685 board and a similar battery voltage, so the `pi/` and `brain/` code should carry
over to a walking body. That project is non-commercial-only.
