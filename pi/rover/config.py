"""Rover settings. Defaults live here; override any of them in a JSON file."""
import json
from dataclasses import dataclass, fields


@dataclass
class Config:
    # PCA9685 servo board
    i2c_bus: int = 1
    i2c_address: int = 0x40
    pwm_freq_hz: float = 50.0
    steering_channel: int = 0
    throttle_channel: int = 1

    # Pulse widths in microseconds. Find the real values with `python3 -m rover.calibrate`.
    steering_left_us: int = 1100
    steering_center_us: int = 1500
    steering_right_us: int = 1900
    throttle_reverse_us: int = 1000
    throttle_neutral_us: int = 1500
    throttle_forward_us: int = 2000

    # Speed cap: fraction of the ESC's full range that "full stick" is allowed to reach.
    # The stock 12T motor is fast, so these start low on purpose.
    max_forward: float = 0.25
    max_reverse: float = 0.20

    # How fast throttle may build, in full sticks per second. Slowing down is always instant.
    ramp_per_s: float = 1.0

    # Failsafe: stop if no drive command arrives for this long.
    command_timeout_s: float = 0.5

    # Hold neutral this long at startup so the ESC can arm.
    arm_s: float = 2.0

    loop_hz: float = 50.0
    host: str = "0.0.0.0"
    port: int = 8080


def load(path=None):
    cfg = Config()
    if path:
        with open(path) as f:
            data = json.load(f)
        known = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key not in known:
                raise ValueError(f"Unknown setting in {path}: {key}")
            setattr(cfg, key, value)
    if not 0 <= cfg.max_forward <= 1 or not 0 <= cfg.max_reverse <= 1:
        raise ValueError("max_forward and max_reverse must be between 0 and 1")
    return cfg
