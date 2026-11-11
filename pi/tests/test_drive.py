import json
import threading
import unittest
import urllib.error
import urllib.request

from rover.config import Config
from rover.drive import Drive
from rover.pca9685 import MockPCA9685
from rover.server import make_server


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def make(**overrides):
    cfg = Config(**overrides)
    pwm, clock = MockPCA9685(), Clock()
    d = Drive(pwm, cfg, clock)
    d._armed_at = clock.t + cfg.arm_s
    d._write()
    return d, pwm, clock, cfg


def run(d, clock, seconds, throttle=None, steering=0.0, dt=0.02):
    for _ in range(round(seconds / dt)):
        clock.t += dt
        if throttle is not None:
            d.command(throttle, steering)
        d.step()


class DriveTests(unittest.TestCase):
    def test_starts_neutral_and_centred(self):
        d, pwm, clock, cfg = make()
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)
        self.assertEqual(pwm.pulses[cfg.steering_channel], 1500)

    def test_no_throttle_while_arming(self):
        d, pwm, clock, cfg = make()
        run(d, clock, 1.0, throttle=1.0)
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)

    def test_speed_cap(self):
        d, pwm, clock, cfg = make(max_forward=0.25, max_reverse=0.2)
        run(d, clock, 5.0, throttle=1.0)
        self.assertAlmostEqual(pwm.pulses[cfg.throttle_channel], 1625)  # 25% of the way to 2000
        run(d, clock, 5.0, throttle=-1.0)
        self.assertAlmostEqual(pwm.pulses[cfg.throttle_channel], 1400)  # 20% of the way to 1000

    def test_out_of_range_input_is_clamped(self):
        d, pwm, clock, cfg = make()
        run(d, clock, 5.0, throttle=50, steering=-9)
        self.assertAlmostEqual(pwm.pulses[cfg.throttle_channel], 1625)
        self.assertAlmostEqual(pwm.pulses[cfg.steering_channel], 1100)

    def test_ramps_up_but_stops_instantly(self):
        d, pwm, clock, cfg = make(arm_s=0, ramp_per_s=1.0)
        run(d, clock, 0.5, throttle=1.0)
        self.assertAlmostEqual(d.status()["throttle"], 0.5, places=1)
        d.command(0, 0)
        clock.t += 0.02
        d.step()
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)

    def test_reversing_passes_through_neutral(self):
        d, pwm, clock, cfg = make(arm_s=0)
        run(d, clock, 3.0, throttle=1.0)
        d.command(-1.0, 0)
        clock.t += 0.02
        d.step()
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)

    def test_failsafe_stops_when_commands_stop(self):
        d, pwm, clock, cfg = make(arm_s=0, command_timeout_s=0.5)
        run(d, clock, 3.0, throttle=1.0)
        self.assertGreater(pwm.pulses[cfg.throttle_channel], 1600)
        run(d, clock, 0.4)  # silence, still inside the timeout
        self.assertGreater(pwm.pulses[cfg.throttle_channel], 1600)
        run(d, clock, 0.2)  # now past it
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)
        self.assertTrue(d.status()["failsafe"])

    def test_stop_is_immediate(self):
        d, pwm, clock, cfg = make(arm_s=0)
        run(d, clock, 3.0, throttle=1.0)
        d.stop()
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)

    def test_forward_blocked_allows_reverse_only(self):
        d, pwm, clock, cfg = make(arm_s=0)
        d.set_forward_blocked(True)
        run(d, clock, 3.0, throttle=1.0)
        self.assertEqual(pwm.pulses[cfg.throttle_channel], 1500)
        run(d, clock, 3.0, throttle=-1.0)
        self.assertLess(pwm.pulses[cfg.throttle_channel], 1500)

    def test_steering_endpoints(self):
        d, pwm, clock, cfg = make(steering_left_us=1200, steering_right_us=1750)
        run(d, clock, 0.1, throttle=0, steering=-1)
        self.assertAlmostEqual(pwm.pulses[cfg.steering_channel], 1200)
        run(d, clock, 0.1, throttle=0, steering=1)
        self.assertAlmostEqual(pwm.pulses[cfg.steering_channel], 1750)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.d, self.pwm, self.clock, self.cfg = make(arm_s=0)
        self.server = make_server(self.d, "127.0.0.1", 0, token="secret")
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def post(self, path, body, token="secret"):
        req = urllib.request.Request(self.url + path, data=body, method="POST",
                                     headers={"X-Rover-Token": token} if token else {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_drive_and_status(self):
        code, _ = self.post("/drive", b'{"throttle": 0.5, "steering": -1}')
        self.assertEqual(code, 200)
        self.clock.t += 0.02
        self.d.step()
        with urllib.request.urlopen(self.url + "/status") as r:
            s = json.loads(r.read())
        self.assertEqual(s["steering"], -1.0)
        self.assertFalse(s["failsafe"])

    def test_rejects_bad_token_and_bad_input(self):
        self.assertEqual(self.post("/drive", b'{"throttle": 1}', token="nope")[0], 403)
        self.assertEqual(self.post("/drive", b'not json')[0], 400)
        self.assertEqual(self.post("/drive", b'{"throttle": "fast"}')[0], 400)
        self.assertEqual(self.post("/drive", b'{"throttle": NaN}')[0], 400)
        self.assertEqual(self.post("/drive", b'[1, 2]')[0], 400)
        self.assertEqual(self.pwm.pulses[self.cfg.throttle_channel], 1500)

    def test_page_loads(self):
        with urllib.request.urlopen(self.url + "/") as r:
            self.assertIn(b"Claude Rover", r.read())


if __name__ == "__main__":
    unittest.main()
