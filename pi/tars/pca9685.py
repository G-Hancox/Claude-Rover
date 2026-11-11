"""Minimal PCA9685 driver (16-channel PWM board over I2C), plus a mock for testing off the Pi."""
import threading

MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06

SLEEP = 0x10
AUTO_INCREMENT = 0x20
RESTART = 0x80


class PCA9685:
    def __init__(self, bus=1, address=0x40, freq_hz=50.0, osc_hz=25_000_000):
        from smbus2 import SMBus  # only needed on the Pi

        self._bus = SMBus(bus)
        self._addr = address
        self._lock = threading.Lock()
        prescale = max(3, min(255, round(osc_hz / (4096 * freq_hz)) - 1))
        self.freq_hz = osc_hz / (4096 * (prescale + 1))

        self._bus.write_byte_data(self._addr, MODE1, SLEEP)
        self._bus.write_byte_data(self._addr, PRESCALE, prescale)
        self._bus.write_byte_data(self._addr, MODE1, AUTO_INCREMENT)
        import time

        time.sleep(0.005)  # oscillator needs 500us to start
        self._bus.write_byte_data(self._addr, MODE1, AUTO_INCREMENT | RESTART)

    def set_pulse_us(self, channel, us):
        counts = max(0, min(4095, round(us * 4096 * self.freq_hz / 1_000_000)))
        self._write(channel, [0, 0, counts & 0xFF, counts >> 8])

    def off(self, channel):
        """Stop sending pulses on a channel (full-off bit)."""
        self._write(channel, [0, 0, 0, 0x10])

    def _write(self, channel, data):
        if not 0 <= channel <= 15:
            raise ValueError("channel must be 0-15")
        with self._lock:
            self._bus.write_i2c_block_data(self._addr, LED0_ON_L + 4 * channel, data)

    def close(self):
        self._bus.close()


class MockPCA9685:
    """Stands in for the board so the code can run on any computer."""

    def __init__(self, *args, **kwargs):
        self.pulses = {}

    def set_pulse_us(self, channel, us):
        self.pulses[channel] = us

    def off(self, channel):
        self.pulses[channel] = None

    def close(self):
        pass
