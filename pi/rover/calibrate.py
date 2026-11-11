"""Find the real pulse widths for steering and throttle.

  python3 -m rover.calibrate steering
  python3 -m rover.calibrate throttle     <-- WHEELS OFF THE GROUND
  python3 -m rover.calibrate pan
  python3 -m rover.calibrate tilt

Type a pulse width in microseconds (900-2100) and press Enter to send it.
Press Enter alone to go back to 1500. Type q to quit. Write down the values
that give you centre / full left / full right (or neutral / forward / reverse,
or centre / down / up)
and put them in rover.json.
"""
import sys

from . import config as config_mod
from .pca9685 import PCA9685

LOW, HIGH, MID = 900, 2100, 1500


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("steering", "throttle", "pan", "tilt"):
        print(__doc__)
        return 1
    which = sys.argv[1]
    cfg = config_mod.load(sys.argv[2] if len(sys.argv) > 2 else None)
    channel = getattr(cfg, f"{which}_channel")

    if which == "throttle":
        if input("Are the wheels OFF the ground? Type yes: ").strip().lower() != "yes":
            return 1

    pwm = PCA9685(cfg.i2c_bus, cfg.i2c_address, cfg.pwm_freq_hz)
    pwm.set_pulse_us(channel, MID)
    print(f"{which} on channel {channel}: sending {MID}")
    try:
        while True:
            text = input("pulse us> ").strip().lower()
            if text == "q":
                break
            try:
                us = int(text) if text else MID
            except ValueError:
                print("Type a number, Enter, or q")
                continue
            if not LOW <= us <= HIGH:
                print(f"Keep it between {LOW} and {HIGH}")
                continue
            pwm.set_pulse_us(channel, us)
            print(f"sending {us}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        pwm.set_pulse_us(channel, MID)
        pwm.close()
        print(f"\nBack to {MID}. Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
