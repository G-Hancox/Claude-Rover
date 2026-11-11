# Build notes

## Where this is going

**Claude in a TARS body.** We started with a camera rover on an RC car chassis, then
switched to TARS: it's carried rather than driven outdoors, and walking is just four
servos. The rover plan is in the git history if it's ever wanted.

The body is the **TARS-AI V3** community design (Charlie Diaz's original, reworked by
Charles-Olivier Dion / AtomikSpace and the TARS-AI community). Print files are in
[`cad/tars/`](../cad/tars/README.md); the shop list is [`parts-list.md`](parts-list.md);
assembly follows the [V3 wiki guide](https://github.com/TARS-AI-Community/TARS-AI/wiki/V3).

## Decisions

- **Legs-only build first.** The arms add 6 servos and a lot of weight; they can come later.
- **Our own software, not the TARS-AI app.** Their app runs everything on a Pi 5 and uses
  OpenAI. Ours keeps the Pi 4 (2GB) doing hardware only, and the brain is Claude Code on
  the PC, on the existing subscription.
- **Same servo numbering and units as TARS-AI V3**, so their build guide, calibration
  video and community help all apply:
  - channel 0 left leg height, 1 right leg height, 2 left leg swing, 3 right leg swing
  - servo values 0–600 (= 500–2500 µs pulses), same as their `config.ini`
- **Walking keyframes adapted from TARS-AI V3** (`pi/tars/moves.py`, CC-BY-NC 4.0).
- **Power as designed:** 12V Li-ion pack inside → switch → XL4015 set to **6.2V** for the
  servos, and a 5V USB regulator for the Pi.
- **Audio through the USB sound card** (speakers and mics on one board).
- **Screen: Waveshare 5" DSI (800×480)** on the Pi 4's DSI port, in the standard 5" upper
  lid. Our software draws it straight to the framebuffer: captions of what Claude says,
  what TARS is doing, and an honesty/humor readout when idle. No desktop needed.
- **Voice: the TARS-AI community's TARS voice** (a Piper model with one speaker per
  emotion), downloaded on the Pi with `python3 -m tars.voice download`. espeak stays as the
  fallback. It's trained on the film's TARS lines (Bill Irwin), so it stays a personal-use
  thing: no publishing clips of it.
- **No distance sensor.** TARS walks slowly and Claude judges distance from the camera.

## Safety, as built

- Moves are finite and end standing. There's no "keep going" signal to lose, so dropped
  Wi-Fi can't leave TARS walking.
- Servos go limp between moves (cooler and quieter; TARS rests on its feet).
- STOP eases back to standing; "Go limp" cuts servo power at once.
- Leg positions are saved after each move, so the next move picks up where the servos
  actually are instead of snapping.

## Open questions

- [ ] Real move timing. The speeds are a guess at matching TARS-AI's; adjust
      `move_time_scale` once it's walking.
- [ ] Waveshare screen on the Pi 4: confirm `dtoverlay=vc4-kms-dsi-7inch` lights it up.
- [ ] Framebuffer depth (16 or 32-bit) on the real Pi; both are supported.
- [ ] Turn direction on the real build: if "turn left" turns right, set `swap_turns`.

## If the upstream TARS-AI repo disappears

What we already have here: the print files and their license (`cad/tars/`), the build
guide text (`docs/tars-v3-guide.md`), the bill of materials (`parts-list.md`), the servo
layout and calibration values (`pi/tars/config.py`), and the walking moves
(`pi/tars/moves.py`).

What we don't have: the guide's **photos** (save the wiki page as a PDF), the **CAD
source** (only STLs, so big redesigns would mean remodelling; small fixes can be done on
the STLs), and the **TARS voice** file, which lives on Hugging Face. Once it's on the Pi,
keep a copy of `~/tars-voice` on your PC.

## Things to watch

- **Calibrate before walking.** Fit the servo horns at the preset position
  (`python3 -m tars.calibrate preset`), then find each joint's limits.
- **6.2V on the servo rail, not 12V.** Set the XL4015 before connecting any servo.
- **Camera cable:** the Pi 4 needs a 15-pin ribbon.
- **Pi 4 heat** inside a closed torso; a heatsink or fan helps.
- **Floors:** walking needs flat, firm floors. Carry it outside.
