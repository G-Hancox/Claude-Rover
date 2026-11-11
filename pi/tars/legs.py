"""TARS legs: four servos moved together through keyframes, one move at a time.

  channel 0  left leg height      channel 2  left leg swing (forward / back)
  channel 1  right leg height     channel 3  right leg swing

Moves are finite: each one ends standing, then (by default) the servos go limp.
There is no "keep driving" signal to lose, so a dropped Wi-Fi link can't leave TARS
walking. stop() finishes by easing back to standing; release() goes limp at once.
"""
import json
import math
import os
import threading
import time

from .moves import MOVES, STANCE

JOINTS = ("left_height", "right_height", "left_leg", "right_leg")
FRAME_HZ = 100
STOP_SPEED = 0.5


class Busy(Exception):
    pass


def value_to_us(value):
    """TARS-AI servo units (0-600) to a pulse width in microseconds (500-2500)."""
    return 500 + value / 600 * 2000


class Legs:
    def __init__(self, pwm, cfg, sleep=time.sleep):
        self._pwm = pwm
        self._cfg = cfg
        self._sleep = sleep
        self._channels = {
            "left_height": cfg.left_height_channel, "right_height": cfg.right_height_channel,
            "left_leg": cfg.left_leg_channel, "right_leg": cfg.right_leg_channel,
        }
        self._ranges = {
            "left_height": (cfg.left_up_height, cfg.left_down_height),
            "right_height": (cfg.right_up_height, cfg.right_down_height),
            "left_leg": (cfg.forward_left_leg, cfg.back_left_leg),
            "right_leg": (cfg.forward_right_leg, cfg.back_right_leg),
        }
        self._preset = {
            "left_height": cfg.preset_left_height, "right_height": cfg.preset_right_height,
            "left_leg": cfg.preset_left_leg, "right_leg": cfg.preset_right_leg,
        }
        self._file = os.path.expanduser(cfg.positions_file) if cfg.positions_file else None
        self._io = threading.Lock()       # guards servo writes and the released flag
        self._state = threading.Lock()    # guards which move is running
        self._pos = self._load_positions()
        self._released = True             # servos start limp; nothing moves at startup
        self._abort = threading.Event()
        self._hard = False
        self._thread = None
        self._move = None
        self._error = None
        self._completed = 0

    # ---- public -------------------------------------------------------------

    def start(self, name, times=1):
        """Begin a move in the background. Raises KeyError, ValueError or Busy."""
        if name not in MOVES:
            raise KeyError(name)
        times = int(times)
        if not 1 <= times <= self._cfg.max_repeats:
            raise ValueError(f"times must be 1 to {self._cfg.max_repeats}")
        if self._cfg.swap_turns and name.startswith("turn_"):
            name = name.replace("left", "~").replace("right", "left").replace("~", "right")
        with self._state:
            if self._thread and self._thread.is_alive():
                raise Busy(f"already doing {self._move}")
            self._abort.clear()
            self._hard = False
            self._error = None
            self._move = name
            self._thread = threading.Thread(target=self._run, args=(name, times), daemon=True)
            self._thread.start()
        return name

    def stop(self):
        """Cut the current move short and ease back to standing."""
        self._abort.set()

    def release(self):
        """Let every leg servo go limp right now. TARS will settle onto its feet."""
        with self._io:
            self._hard = True
            self._abort.set()
            for ch in self._channels.values():
                self._pwm.off(ch)
            self._released = True

    def preset(self):
        """Hold every leg servo at the assembly position (for fitting the servo horns)."""
        with self._state:
            if self._thread and self._thread.is_alive():
                raise Busy(f"already doing {self._move}")
        with self._io:
            for joint, value in self._preset.items():
                self._pwm.set_pulse_us(self._channels[joint], value_to_us(value))
                self._pos[joint] = float(value)
            self._released = False
        self._save_positions()

    def wait(self, timeout=None):
        t = self._thread
        if t:
            t.join(timeout)
        return not (t and t.is_alive())

    def busy(self):
        t = self._thread
        return bool(t and t.is_alive())

    def status(self):
        return {
            "moving": self.busy(),
            "move": self._move if self.busy() else None,
            "released": self._released,
            "error": self._error,
            "completed": self._completed,
            "positions": {j: round(v) for j, v in self._pos.items()},
        }

    def percent_to_value(self, joint, percent):
        lo, hi = self._ranges[joint]
        p = max(1.0, min(100.0, float(percent)))
        return lo + (hi - lo) * (p - 1) / 99

    # ---- worker -------------------------------------------------------------

    def _run(self, name, times):
        steps = MOVES[name]["steps"]
        try:
            for _ in range(times):
                for step in steps:
                    if self._abort.is_set():
                        break
                    if step[0] == "pause":
                        self._pause(step[1])
                    else:
                        self._keyframe(step[:4], step[4])
                if self._abort.is_set():
                    break
            if self._abort.is_set() and not self._hard:
                self._keyframe(STANCE, STOP_SPEED, abortable=False)
            if not self._abort.is_set():
                self._completed += 1
        except Exception as e:  # noqa: BLE001 - a dead I2C link etc.: report it, go limp
            self._error = repr(e)
            self.release()
            return
        if self._cfg.release_after_move and not self._hard:
            self._sleep(0.1)
            self.release()

    def _pause(self, seconds):
        end = seconds
        while end > 0 and not self._abort.is_set():
            chunk = min(0.05, end)
            self._sleep(chunk)
            end -= chunk

    def _keyframe(self, percents, speed, abortable=True):
        targets = {j: self.percent_to_value(j, p) for j, p in zip(JOINTS, percents) if p is not None}
        with self._io:
            if self._hard:
                return
            if self._released:
                # Gently re-engage where the servos were last told to be, so nothing snaps.
                for joint, value in self._pos.items():
                    self._pwm.set_pulse_us(self._channels[joint], value_to_us(value))
                self._released = False
        if self._pos.keys() != set(JOINTS):
            speed = min(speed, 0.3)  # first ever move: positions unknown, go slowly
        start = {j: self._pos.get(j, self._preset[j]) for j in targets}

        distance = max((abs(targets[j] - start[j]) for j in targets), default=0)
        if distance < 0.5:
            return
        per_unit = self._cfg.move_time_scale * (0.026 * (1 - speed) + 0.004)
        duration = max(0.05, distance * per_unit)
        frames = max(1, math.ceil(duration * FRAME_HZ))
        ease = self._cfg.easing

        for i in range(1, frames + 1):
            if abortable and self._abort.is_set():
                break
            p = i / frames
            e = (1 - ease) * p + ease * p * p * (3 - 2 * p)
            with self._io:
                if self._hard:
                    return
                for joint, target in targets.items():
                    value = start[joint] + (target - start[joint]) * e
                    self._pwm.set_pulse_us(self._channels[joint], value_to_us(value))
                    self._pos[joint] = value
            self._sleep(duration / frames)
        self._save_positions()

    # ---- remembering where the legs are -----------------------------------------

    def _load_positions(self):
        if not self._file:
            return {}
        try:
            with open(self._file) as f:
                data = json.load(f)
            return {j: float(data[j]) for j in JOINTS if j in data and 0 <= float(data[j]) <= 600}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_positions(self):
        if not self._file:
            return
        try:
            tmp = self._file + ".tmp"
            with open(tmp, "w") as f:
                json.dump({j: round(v, 1) for j, v in self._pos.items()}, f)
            os.replace(tmp, self._file)
        except OSError:
            pass  # not worth stopping a move over
