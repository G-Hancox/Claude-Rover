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

    # Camera. 640x480 at 15 fps is easy on a 2GB Pi 4 and on Wi-Fi.
    camera_enabled: bool = True
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 15
    camera_hflip: bool = False
    camera_vflip: bool = False

    # Camera pan and tilt (two more servos on the PCA9685).
    head_enabled: bool = True
    pan_channel: int = 2
    tilt_channel: int = 3
    pan_left_us: int = 1100
    pan_center_us: int = 1500
    pan_right_us: int = 1900
    tilt_down_us: int = 1200
    tilt_center_us: int = 1500
    tilt_up_us: int = 1800
    head_speed_per_s: float = 1.5  # how fast the head may swing, in full sweeps per second

    # Forward distance sensor: "none", "hcsr04" (ultrasonic) or "vl53l1x" (laser).
    distance_sensor: str = "none"
    distance_stop_m: float = 0.40   # closer than this: forward throttle is refused
    distance_clear_m: float = 0.55  # farther than this again: forward is allowed
    distance_hz: float = 15.0
    hcsr04_trigger_pin: int = 23    # GPIO numbers, not header pin numbers
    hcsr04_echo_pin: int = 24
    vl53l1x_address: int = 0x29

    # Voice out (speaker) and in (mic), through ALSA.
    speaker_enabled: bool = True
    mic_enabled: bool = True
    audio_out_device: str = "default"
    audio_in_device: str = "default"
    tts_engine: str = "espeak"      # "espeak" or "piper"
    piper_bin: str = "piper"
    piper_model: str = ""           # path to a Piper .onnx voice
    piper_sample_rate: int = 22050
    say_max_chars: int = 500

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
    if cfg.distance_sensor not in ("none", "hcsr04", "vl53l1x"):
        raise ValueError('distance_sensor must be "none", "hcsr04" or "vl53l1x"')
    if cfg.distance_clear_m < cfg.distance_stop_m:
        raise ValueError("distance_clear_m must not be smaller than distance_stop_m")
    if cfg.tts_engine not in ("espeak", "piper"):
        raise ValueError('tts_engine must be "espeak" or "piper"')
    return cfg
