"""Steering and throttle with a speed cap, ramping and a lost-contact failsafe."""
import threading
import time


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, float(x)))


def _ramp(current, target, max_step):
    """Slowing down is instant; speeding up is limited; reversing passes through zero."""
    if target == 0 or (current * target > 0 and abs(target) < abs(current)):
        return target
    if current * target < 0:
        return 0.0
    return current + max(-max_step, min(max_step, target - current))


class Drive:
    def __init__(self, pwm, cfg, clock=time.monotonic):
        self._pwm = pwm
        self._cfg = cfg
        self._clock = clock
        self._lock = threading.Lock()
        self._target_throttle = 0.0
        self._target_steering = 0.0
        self._throttle = 0.0
        self._steering = 0.0
        self._deadline = 0.0
        self._armed_at = 0.0
        self._last_step = None
        self._failsafe = True
        self._forward_blocked = False
        self._thread = None
        self._running = False

    # ---- commands -------------------------------------------------------

    def command(self, throttle, steering):
        """Set the stick positions, each -1..1. Must be repeated or the failsafe stops the rover."""
        with self._lock:
            self._target_throttle = _clamp(throttle)
            self._target_steering = _clamp(steering)
            self._deadline = self._clock() + self._cfg.command_timeout_s
            self._failsafe = False

    def stop(self):
        with self._lock:
            self._target_throttle = 0.0
            self._throttle = 0.0
            self._deadline = 0.0
        self._write()

    def set_forward_blocked(self, blocked):
        """Hook for the distance sensor: when True, forward throttle is refused."""
        with self._lock:
            self._forward_blocked = bool(blocked)

    # ---- loop -----------------------------------------------------------

    def start(self):
        now = self._clock()
        self._armed_at = now + self._cfg.arm_s
        self._write()  # neutral throttle, centred steering
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        period = 1.0 / self._cfg.loop_hz
        while self._running:
            self.step()
            time.sleep(period)

    def step(self, now=None):
        """One pass of the control loop. Public so tests can drive time by hand."""
        now = self._clock() if now is None else now
        with self._lock:
            dt = 0.0 if self._last_step is None else max(0.0, now - self._last_step)
            self._last_step = now

            if now > self._deadline:
                self._failsafe = True
                self._target_throttle = 0.0

            target = self._target_throttle
            if now < self._armed_at:
                target = 0.0
            if self._forward_blocked and target > 0:
                target = 0.0

            self._throttle = _ramp(self._throttle, target, self._cfg.ramp_per_s * dt)
            self._steering = self._target_steering
        self._write()

    def shutdown(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.stop()

    # ---- output ---------------------------------------------------------

    def throttle_us(self, t):
        c = self._cfg
        if t >= 0:
            return c.throttle_neutral_us + t * c.max_forward * (c.throttle_forward_us - c.throttle_neutral_us)
        return c.throttle_neutral_us + t * c.max_reverse * (c.throttle_neutral_us - c.throttle_reverse_us)

    def steering_us(self, s):
        c = self._cfg
        if s >= 0:
            return c.steering_center_us + s * (c.steering_right_us - c.steering_center_us)
        return c.steering_center_us + s * (c.steering_center_us - c.steering_left_us)

    def _write(self):
        with self._lock:
            t, s = self._throttle, self._steering
        self._pwm.set_pulse_us(self._cfg.throttle_channel, self.throttle_us(t))
        self._pwm.set_pulse_us(self._cfg.steering_channel, self.steering_us(s))

    def status(self):
        with self._lock:
            return {
                "throttle": round(self._throttle, 3),
                "steering": round(self._steering, 3),
                "armed": self._clock() >= self._armed_at,
                "failsafe": self._failsafe,
                "forward_blocked": self._forward_blocked,
                "max_forward": self._cfg.max_forward,
                "max_reverse": self._cfg.max_reverse,
            }
