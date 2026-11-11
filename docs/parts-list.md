# Shop list — Claude TARS (legs only, no arms)

Based on the TARS-AI V3 bill of materials
([wiki](https://github.com/TARS-AI-Community/TARS-AI/wiki/V3)), changed for this build:
your Pi 4 instead of a Pi 5, and the screen left out to start. The links are the ones the
V3 guide uses. They're all Amazon US, and I haven't checked current prices or stock.

The V3 builders recommend asking in their Discord before swapping in a different part.

## To buy

### Servos and control

- [ ] **4× MG996R servos** (180°) — [link](https://www.amazon.com/dp/B0D7M2Y2BR).
  Check how many come in the pack; spares are handy.
- [ ] **PCA9685 16-channel servo board** — [link](https://www.amazon.com/dp/B07BRS249H)

### Power

- [ ] **12V 3000 mAh Li-ion battery with charger** — [link](https://www.amazon.com/dp/B0DF7T3LG1).
  This is the pack the body is designed around; it straps inside the torso. The M12 is
  too big to go inside, but an M12 adapter makes a good bench supply while you build.
- [ ] **XL4015 5A adjustable buck converter** (12V → 6.2V for the servos) — [link](https://www.amazon.com/dp/B085T73CSD)
- [ ] **12V → 5V USB regulator, 5A+** (for the Pi) — [link](https://www.amazon.com/dp/B07X5H4M42/).
  The printed buck-converter bracket is shaped for these two converters, so your old buck
  converter is better kept for the bench.
- [ ] **Micro rocker switch** — [link](https://www.amazon.com/dp/B07Y1GDRQG)
- [ ] **USB-C cable for the Pi, short, angled** — [link](https://www.amazon.com/dp/B0DPF8TFC9).
  Or a USB-C breakout board if you'd rather solder ([link](https://www.amazon.com/dp/B0D9W8B97B)).
- [ ] **Spade connectors** for the switch — [link](https://www.amazon.com/dp/B0FPQ3YS6M)
- [ ] INA260 battery sensor — *optional, skip for now*; this repo's software doesn't read it yet

### Audio and camera

- [ ] **USB sound card with speakers and mics** — [link](https://www.amazon.com/dp/B0CN1C1VPR).
  The V3 guide says the speakers come with this one; check before buying the 8Ω 5W speakers separately.
- [ ] **OV5647 5MP camera** — [link](https://www.amazon.com/dp/B08Q34FKFY).
  The V3 lid is designed for this camera. **Make sure you have a standard 15-pin camera
  ribbon for the Pi 4.** The V3 guide is written for a Pi 5, which uses a smaller 22-pin
  connector, so a kit bought for a Pi 5 may come with the wrong cable.

### Wiring and hardware

- [ ] **M3 flat-head screw kit** — [link](https://www.amazon.com/dp/B0B38GL3F8).
  About 116 M3 screws for the legs-only build. Flat heads, any drive type.
- [ ] **40 cm female-to-female Dupont jumpers** (8 needed) — [link](https://www.amazon.com/dp/B07GCZV4BS)
- [ ] **20 AWG 2-conductor wire**, about 2 m — [link](https://www.amazon.com/dp/B0B9JCXN9M)
- [ ] **6" Velcro straps** (2 needed) — [link](https://www.amazon.com/dp/B081HH5X61)

### Filament

- [ ] **PETG, about 1 kg**
- [ ] TPU, about 200 g — *optional*, for the foot pads

## Probably already have

- [x] Raspberry Pi 4 (2GB) — fine for this setup, because the heavy work (speech, Claude)
      runs on your PC. The V3 guide recommends a Pi 5 only because its own software runs
      everything on the robot.
- [x] microSD card (32 GB+)
- [x] 3D printer (bed at least 180 × 180 mm)
- [x] Solder station, heat shrink, small screwdrivers
- [ ] A heatsink or small fan for the Pi 4 — *optional but worth it*; it's enclosed

## Later, if you want them

- **5" DSI screen** for the face. Check it works with a Pi 4 (15-pin DSI) and print the
  matching screen support.
- **Arms:** 2 more MG996R, 4 MG90S, 6 servo extension cables, 4 magnets (10 × 3 mm), and
  a second screw kit. Run the extension cables through the torso during the first build.

## Parts from the rover plan you no longer need

Pan/tilt servos, the MAX98357A amp and separate speaker, the USB mini mic (the sound card
covers both), the HC-SR04 and its resistors, and the Camera Module 3 (the lid is shaped
for the OV5647). The RC car stays a car.
