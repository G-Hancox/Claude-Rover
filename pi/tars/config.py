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
    tts_engine: str = "espeak"      # "espeak", or "piper" for the TARS voice
    piper_model: str = "~/tars-voice/TARS.onnx"   # get it with: python3 -m tars.voice download
    piper_speaker: str = "neutral"  # default emotion on multi-speaker voices like TARS
    voice_pace: float = 1.3         # TARS voice speed: 1.0 = as trained, higher = slower
    say_max_chars: int = 500

    # Screen (5" DSI on the front). Drawn straight to the Linux framebuffer: no desktop needed.
    display_enabled: bool = True
    display_device: str = "/dev/fb0"
    display_fps: float = 10.0
    display_rotate: int = 0         # 0, 90, 180 or 270 if the picture is turned
    honesty: int = 90               # shown on the idle screen. 90 percent, as in the film.
    humor: int = 75

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
    if not isinstance(cfg.voice_pace, (int, float)) or not 0.5 <= cfg.voice_pace <= 2.0:
        raise ValueError("voice_pace must be between 0.5 and 2.0 (1.0 = normal, higher = slower)")
    if cfg.display_rotate not in (0, 90, 180, 270):
        raise ValueError("display_rotate must be 0, 90, 180 or 270")
    if not all(isinstance(v, int) and 0 <= v <= 100 for v in (cfg.honesty, cfg.humor)):
        raise ValueError("honesty and humor are percentages, 0 to 100")
    return cfg
