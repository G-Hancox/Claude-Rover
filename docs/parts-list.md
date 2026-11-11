# Parts list

## Already have

- [x] Raspberry Pi 4 (2GB) + microSD card
- [x] Milwaukee M12 batteries (electronics)
- [x] Car's 2S LiPo packs (drive) + balance charger
- [x] Buck converter (12V → 5V) — **must pass load test** (see below)
- [x] Fuse block
- [x] Donor RC car — drive motor, steering, tires *(model TBD)*
- [x] 3D printer — body and mounts
- [x] Metal, welders, solder station

## To buy

- [ ] Pi Camera Module 3 (Wide)
- [ ] PCA9685 16-channel servo board (I2C)
- [ ] 2× metal-gear servos (MG996R size) — camera pan & tilt
- [ ] M12 battery adapter with wire leads
- [ ] Main power switch
- [ ] Distance sensor — VL53L1X or ultrasonic
- [ ] MAX98357A I2S amp board
- [ ] Small 3W 4Ω speaker
- [ ] USB mini mic

## Maybe (depends on tests / RC car)

- [ ] 5V 5A buck converter — only if the existing one fails the load test

## Buck converter load test

The existing converter previously powered a BeagleBone Black (1–2A), and its history is unknown.
The Pi 4 + camera needs a solid 3A.

1. Read the label / chip number and check the rated current.
2. Feed it 12V, meter the output: should be 5.0–5.2V and steady.
3. Run the Pi on it with a stress test and the camera streaming, then run
   `vcgencmd get_throttled`. `0x0` = good. Anything else = voltage sagged; replace it.
