"""Robot settings. Defaults live here; override any of them in a JSON file (tars.json)."""
import json
from dataclasses import dataclass, fields

LEG_KEYS = ("left_up_height", "left_down_height", "right_up_height", "right_down_height",
            "forward_left_leg", "back_left_leg", "forward_right_leg", "back_right_leg",
            "preset_left_height", "preset_right_height", "preset_left_leg", "preset_right_leg")


@dataclass
class Config:
    # PCA9685 servo board
    i2c_bus: int = 1
    i2c_address: int = 0x40
    pwm_freq_hz: float = 50.0

    # Servo channels on the PCA9685 (same numbering as the TARS-AI V3 build guide)
    left_height_channel: int = 0
    right_height_channel: int = 1
    left_leg_channel: int = 2
    right_leg_channel: int = 3

    # Leg limits in TARS-AI servo units: 0-600 maps to a 500-2500 microsecond pulse.
    # Same units and defaults as TARS-AI V3's config.ini, so community calibration
    # values copy straight across. Find yours with `python3 -m tars.calibrate`.
    left_up_height: int = 220
    left_down_height: int = 460
    right_up_height: int = 460
    right_down_height: int = 220
    forward_left_leg: int = 160
    back_left_leg: int = 460
    forward_right_leg: int = 460
    back_right_leg: int = 160

    # Assembly position: where servos sit while you fit the horns (build guide step 7).
    preset_left_height: int = 350
    preset_right_height: int = 350
    preset_left_leg: int = 300
    preset_right_leg: int = 300

    # Movement feel
    move_time_scale: float = 1.0    # bigger = slower moves
    easing: float = 0.6             # 0 = constant speed, 1 = soft start and stop
    swap_turns: bool = False        # set true if "turn left" turns right on your build
    release_after_move: bool = True  # let the servos go limp between moves (cooler, quieter)
    max_repeats: int = 5
    positions_file: str = "~/.claude_tars_positions.json"

    # Camera. 640x480 at 15 fps is easy on a 2GB Pi 4 and on Wi-Fi.
    camera_enabled: bool = True
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 15
    camera_hflip: bool = False
    camera_vflip: bool = False

    # Voice out (speaker) and in (mic), through ALSA. The V3 build uses a USB sound card.
    speaker_enabled: bool = True
    mic_enabled: bool = True
    audio_out_device: str = "default"
    audio_in_device: str = "default"
    tts_engine: str = "espeak"      # "espeak" or "piper"
    piper_bin: str = "piper"
    piper_model: str = ""           # path to a Piper .onnx voice
    piper_sample_rate: int = 22050
    say_max_chars: int = 500

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
    for key in LEG_KEYS:
        value = getattr(cfg, key)
        if not isinstance(value, (int, float)) or not 0 <= value <= 600:
            raise ValueError(f"{key} must be a number from 0 to 600 (got {value!r})")
    channels = [cfg.left_height_channel, cfg.right_height_channel,
                cfg.left_leg_channel, cfg.right_leg_channel]
    if len(set(channels)) != 4 or not all(0 <= c <= 15 for c in channels):
        raise ValueError("the four leg channels must be different numbers from 0 to 15")
    if cfg.move_time_scale <= 0 or not 0 <= cfg.easing <= 1:
        raise ValueError("move_time_scale must be above 0 and easing between 0 and 1")
    if cfg.tts_engine not in ("espeak", "piper"):
        raise ValueError('tts_engine must be "espeak" or "piper"')
    return cfg
