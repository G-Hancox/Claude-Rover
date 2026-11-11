# TARS print files

These are the **TARS-AI V3** print files, copied unchanged from
[TARS-AI-Community/TARS-AI](https://github.com/TARS-AI-Community/TARS-AI/tree/V3/3d%20Printer%20Files)
(commit `7593f8c`, April 2026). The folder layout matches theirs, so their build guide's
part names line up with these files.

> **License: these files are not GPL like the rest of this repo.** They're
> CC-BY-NC 4.0 (see `LICENSE.txt` and `ATTRIBUTION.md`): free to print, modify and share
> for non-commercial use, with credit. Don't sell prints, kits or the files.
>
> Based on the mechanical puppet designs by Christopher Nolan, Nathan Crowley, and the
> production team who originally brought TARS to life. Miniaturized CAD by Charlie Diaz,
> with additional modifications by the TARS-AI Community. Contains contributions by
> Charles-Olivier Dion (AtomikSpace).

Upstream may have fixed things since this copy. Check their repo before a big print run.

The full assembly guide, with photos, is the
[V3 page of the TARS-AI wiki](https://github.com/TARS-AI-Community/TARS-AI/wiki/V3).

## Print settings (from the V3 guide)

- **Material:** PETG recommended (about 1 kg for this build). PLA works but is less durable.
  TPU (about 200 g) is optional, for the foot pads.
- **Layer height:** 0.2 mm
- **Walls:** 3 minimum
- **Infill:** 20% gyroid
- **Top / bottom layers:** 5
- **No brim**
- **Supports:** automatic **tree** supports on every part, support threshold angle 10°
  (keeps supports out of the screw holes). Some areas need support that's hard to spot
  in the preview.
- **Keep the orientation and rotation as they come.** The parts are pre-oriented and the
  look of the finished robot depends on it.
- **Bed:** at least 180 x 180 mm. The biggest parts (upper chassis, upper lid, leg cases)
  are 176–188 mm in the file's orientation; check they fit your bed as-is before slicing.

**Print `Tools/Tars 3D Calibration Tool.stl` first.** It checks your printer's tolerances;
the parts allow for up to ±0.02 mm of dimensional error.

## What to print — legs-only build (no arms)

46 parts. Each line is one print unless it says otherwise.

### Tools

- [ ] `Tools/Tars 3D Calibration Tool.stl` — **print first**
- [ ] `Tools/leg_spacer.stl` — used while fitting the legs (torso step 12)

### Electronics support — `A. Required/A. Electronic Support/`

- [ ] `raspberrypi_support (pi4-5).stl` — the Pi 4 version
- [ ] `raspberrypi_bracket.stl`
- [ ] `buck_converter_support.stl`
- [ ] `buck_converter_bracket.stl`
- [ ] `PCA9685_support.stl`
- [ ] Screen support — **only if you add a screen**; print the one matching the screen you buy

### Torso — `A. Required/B. Torso/`

- [ ] `upper_chassis.stl`
- [ ] `lower_chassis.stl`
- [ ] `lower_chassis_base.stl`
- [ ] `lower_lid.stl`
- [ ] `chassis_foot_pad (TPU).stl` — TPU if you have it, otherwise PETG
- [ ] `power_door.stl`
- [ ] `soundcard_brace.stl`
- [ ] `Left_chassis_connector.stl`
- [ ] `middle_chassis_connector.stl`
- [ ] `right_chassis_connector.stl`
- [ ] `left_channel.stl` and `right_channel.stl`
- [ ] `left_pusher.stl` and `right_pusher.stl`
- [ ] `left_pusher_guide.stl` and `right_pusher_guide.stl`
- [ ] `left_shaft.stl` and `right_shaft.stl`
- [ ] `left_shaft_connector.stl` and `right_shaft_connector.stl`
- [ ] `left_servo_arm.stl` and `right_servo_arm.stl`
- [ ] `left_servo_clip.stl` and `right_servo_clip.stl`
- [ ] **Upper lid, pick one:**
  - `A. Required/B. Torso/upper_lid_5inch.stl` — with a 5" screen opening and camera mount
  - `B. Mods/Upper Lid - No Screen/upper_lid_no_screen.stl` — no screen. Going by the file
    names, this one keeps the camera mount and `upper_lid_no_screen_no_cam.stl` doesn't;
    check the camera hole in your slicer before printing. The letters and 12 dots in that
    folder are optional inlays: print extras of the dots, as some don't come out round.

### Legs — both sides

For each of `C. Left Leg` and `D. Right Leg`:

- [ ] `A. … Leg Common Parts/…_hull.stl`
- [ ] `A. … Leg Common Parts/…_hull_hub.stl`
- [ ] `A. … Leg Common Parts/…_hull_lid.stl`
- [ ] `A. … Leg Common Parts/…_hull_servo_clip.stl`
- [ ] `C. … Leg without Arm/…_leg_noarm_case.stl`
- [ ] `C. … Leg without Arm/…_leg_noarm_lid.stl`
- [ ] `C. … Leg without Arm/…_leg_noarm_foot_pad (TPU).stl`

The `B. … Leg with Arm` folders are for the arms version, which needs 2 more MG996R and
4 MG90S servos. The arms can be added later, but the V3 guide says to run the servo
extension cables through the torso during the first build so you don't have to take it
apart again. The software in this repo doesn't drive arms yet.
