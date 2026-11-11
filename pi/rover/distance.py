"""Forward distance sensor and the guard that refuses forward throttle near an obstacle.

A sensor is anything with read_m() -> distance in metres, or None when nothing is in
range. A sensor that raises is treated as broken, and a broken sensor blocks forward
driving (set "distance_sensor": "none" to drive without one).
"""
import threading
import time
from collections import deque

FAULT_AFTER_S = 1.0


class HCSR04:
    """Ultrasonic sensor via gpiozero. The Echo pin is 5V: it needs a voltage divider."""

    MAX_M = 4.0

    def __init__(self, trigger_pin, echo_pin):
        from gpiozero import DistanceSensor

        self._sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin,
                                      max_distance=self.MAX_M, queue_len=1)

    def read_m(self):
        d = self._sensor.distance
        return None if d is None or d >= self.MAX_M else d

    def close(self):
        self._sensor.close()


class VL53L1XSensor:
    """Laser time-of-flight sensor via the `VL53L1X` Python package (pip install vl53l1x)."""

    def __init__(self, i2c_bus=1, address=0x29):
        import VL53L1X

        self._tof = VL53L1X.VL53L1X(i2c_bus=i2c_bus, i2c_address=address)
        self._tof.open()
        self._tof.start_ranging(1)  # 1 = short range (about 1.3 m), the fastest mode

    def read_m(self):
        mm = self._tof.get_distance()
        return None if mm <= 0 else mm / 1000.0

    def close(self):
        self._tof.stop_ranging()
        self._tof.close()


class MockSensor:
    def __init__(self, value=2.0):
        self.value = value  # metres, None for "nothing in range", or an Exception to raise

    def read_m(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    def close(self):
        pass


def make_sensor(cfg):
    if cfg.distance_sensor == "hcsr04":
        return HCSR04(cfg.hcsr04_trigger_pin, cfg.hcsr04_echo_pin)
    if cfg.distance_sensor == "vl53l1x":
        return VL53L1XSensor(cfg.i2c_bus, cfg.vl53l1x_address)
    return None


class Guard:
    def __init__(self, sensor, drive, cfg, clock=time.monotonic):
        self._sensor = sensor
        self._drive = drive
        self._cfg = cfg
        self._clock = clock
        self._lock = threading.Lock()
        self._recent = deque(maxlen=3)
        self._distance = None
        self._blocked = False
        self._fault = False
        self._last_ok = clock()
        self._thread = None
        self._running = False

    def start(self):
        self._last_ok = self._clock()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        period = 1.0 / self._cfg.distance_hz
        while self._running:
            self.step()
            time.sleep(period)

    def step(self, now=None):
        now = self._clock() if now is None else now
        try:
            d = self._sensor.read_m()
            ok = True
        except Exception:  # noqa: BLE001 - any sensor failure counts
            d, ok = None, False

        with self._lock:
            if ok:
                self._last_ok = now
                self._distance = d
                self._recent.append(float("inf") if d is None else d)
            self._fault = (now - self._last_ok) > FAULT_AFTER_S

            # Two of the last three readings must agree, so one bad echo can't stop the rover.
            r = sorted(self._recent)
            typical = r[1] if len(r) == 3 else (r[0] if r else float("inf"))
            if self._fault or typical < self._cfg.distance_stop_m:
                self._blocked = True
            elif typical > self._cfg.distance_clear_m:
                self._blocked = False
            blocked = self._blocked
        self._drive.set_forward_blocked(blocked)

    def shutdown(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        try:
            self._sensor.close()
        except Exception:  # noqa: BLE001
            pass

    def status(self):
        with self._lock:
            return {
                "distance_m": None if self._distance is None else round(self._distance, 2),
                "blocked": self._blocked,
                "fault": self._fault,
                "stop_m": self._cfg.distance_stop_m,
            }
