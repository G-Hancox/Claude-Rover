"""Servo setup and calibration for the TARS legs.

  python3 -m tars.calibrate preset
      Hold all four leg servos at the assembly position while you fit the servo
      horns (build guide, torso step 7). Press Enter to let them go limp.

  python3 -m tars.calibrate left_height     (also: right_height, left_leg, right_leg)
      Move one servo by hand. Type a value from 0 to 600 and press Enter.
      Enter alone goes back to the assembly position. q quits (servo goes limp).
      Note the values for each end of the joint's travel and put them in tars.json.

Values are TARS-AI servo units (0-600 = 500-2500 microseconds), the same units the
TARS-AI calibration video and config.ini use.

Keep the robot on its base (lower_chassis_base) with the legs free to move.
"""
import sys

from . import config as config_mod
from .legs import JOINTS, Legs, value_to_us
from .pca9685 import PCA9685

LIMITS = {
    "left_height": ("left_up_height", "left_down_height", "preset_left_height"),
    "right_height": ("right_up_height", "right_down_height", "preset_right_height"),
    "left_leg": ("forward_left_leg", "back_left_leg", "preset_left_leg"),
    "right_leg": ("forward_right_leg", "back_right_leg", "preset_right_leg"),
}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("preset", *JOINTS):
        print(__doc__)
        return 1
    which = args[0]
    cfg = config_mod.load(args[1] if len(args) > 1 else None)
    pwm = PCA9685(cfg.i2c_bus, cfg.i2c_address, cfg.pwm_freq_hz)
    legs = Legs(pwm, cfg)
    try:
        if which == "preset":
            legs.preset()
            print("All four leg servos are holding the assembly position.")
            print("Don't force them. Fit the horns, then press Enter to release.")
            input()
            return 0

        channel = getattr(cfg, f"{which}_channel")
        a, b, p = (getattr(cfg, k) for k in LIMITS[which])
        preset = getattr(cfg, LIMITS[which][2])
        print(f"{which} on channel {channel}. Current settings: {LIMITS[which][0]}={a}, "
              f"{LIMITS[which][1]}={b}, preset={p}")
        print("Move in small steps (10-20 at a time) and stop if anything binds.")
        pwm.set_pulse_us(channel, value_to_us(preset))
        print(f"holding {preset}")
        while True:
            text = input("value 0-600> ").strip().lower()
            if text == "q":
                break
            try:
                value = int(text) if text else preset
            except ValueError:
                print("Type a number, Enter, or q")
                continue
            if not 0 <= value <= 600:
                print("Keep it between 0 and 600")
                continue
            pwm.set_pulse_us(channel, value_to_us(value))
            print(f"holding {value}")
        return 0
    except (KeyboardInterrupt, EOFError):
        return 0
    finally:
        legs.release()
        pwm.close()
        print("\nServos released.")


if __name__ == "__main__":
    sys.exit(main())
