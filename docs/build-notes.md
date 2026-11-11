# Build notes

## Decisions so far

- **Rover first, TARS later.** The rover is the easier build; its software carries over.
- **Brain on the PC.** The Pi 4 is 2GB, so it only does hardware I/O. Speech-to-text,
  Claude, and text-to-speech run on the PC.
- **Power: two batteries.**
  - Drive: car's **2S LiPo → ESC → 12T motor** (in spec: 2S allows 12T–55T). ESC jumper on **LiPo**.
  - Electronics: **M12 → fuse block → main switch → buck converter (5V)** → Pi, camera, audio, pan/tilt servos.
  - Keeps motor current spikes and sag away from the Pi.
  - **Grounds of both systems must be tied together**, or the throttle signal won't read right.
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
- Stock motor is **12T** → not allowed on 3S, so the M12 does **not** feed the ESC. Drive runs on the car's 2S LiPo.
- ESC red wire (BEC) can feed the PCA9685 servo rail (V+), **never the Pi**. Common ground everywhere.
- The pan/tilt MG996Rs may be too much for the ESC's BEC; may need a separate 6V servo supply.

## Open questions

- [x] Motor turn count: **12T** → keep it, run drive on 2S LiPo (see Power). Throttle limit in software anyway.
- [ ] Check LiPo packs: no puffing, ≥3.0V per cell, balance charge before use.
- [ ] Does the existing buck converter pass the load test?

## Things to watch

- **Pi freeze = runaway risk.** The PCA9685 keeps sending its last pulse if the Pi hangs, so the
  software failsafe can't cover that case. Fix later with a hardware cutoff: e.g. wire the
  board's OE pin so outputs drop unless the Pi keeps a heartbeat going, which makes the ESC
  see "no signal" and stop. Until then: low speed cap.
- **ESC BEC vs. Pi.** The ESC's red wire powers the servo rail only.

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
