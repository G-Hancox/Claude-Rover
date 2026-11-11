"""Camera pan and tilt: two servos, moved smoothly instead of snapping."""
import threading
import time


def _clamp(x):
    return max(-1.0, min(1.0, float(x)))


def _toward(current, target, max_step):
    return current + max(-max_step, min(max_step, target - current))


class Head:
    def __init__(self, pwm, cfg, clock=time.monotonic):
        self._pwm = pwm
        self._cfg = cfg
        self._clock = clock
        self._lock = threading.Lock()
        self._target = [0.0, 0.0]  # pan, tilt
        self._pos = [0.0, 0.0]
        self._last_step = None
        self._thread = None
        self._running = False

    def look(self, pan, tilt):
        """pan: -1 left .. 1 right.  tilt: -1 down .. 1 up."""
        with self._lock:
            self._target = [_clamp(pan), _clamp(tilt)]

    def center(self):
        self.look(0, 0)

    def start(self):
        self._write()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        period = 1.0 / self._cfg.loop_hz
        while self._running:
            self.step()
            time.sleep(period)

    def step(self, now=None):
        now = self._clock() if now is None else now
        with self._lock:
            dt = 0.0 if self._last_step is None else max(0.0, now - self._last_step)
            self._last_step = now
            # A full sweep is 2 units (-1 to 1).
            max_step = 2.0 * self._cfg.head_speed_per_s * dt
            moved = self._pos != self._target
            self._pos = [_toward(p, t, max_step) for p, t in zip(self._pos, self._target)]
        if moved:
            self._write()

    def shutdown(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def pan_us(self, v):
        c = self._cfg
        if v >= 0:
            return c.pan_center_us + v * (c.pan_right_us - c.pan_center_us)
        return c.pan_center_us + v * (c.pan_center_us - c.pan_left_us)

    def tilt_us(self, v):
        c = self._cfg
        if v >= 0:
            return c.tilt_center_us + v * (c.tilt_up_us - c.tilt_center_us)
        return c.tilt_center_us + v * (c.tilt_center_us - c.tilt_down_us)

    def _write(self):
        with self._lock:
            pan, tilt = self._pos
        self._pwm.set_pulse_us(self._cfg.pan_channel, self.pan_us(pan))
        self._pwm.set_pulse_us(self._cfg.tilt_channel, self.tilt_us(tilt))

    def status(self):
        with self._lock:
            return {"pan": round(self._pos[0], 3), "tilt": round(self._pos[1], 3)}
