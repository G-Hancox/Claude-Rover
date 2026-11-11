import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave

from rover import config as config_mod
from rover.audio import Busy, MockMic, MockSpeaker, run_pipeline
from rover.camera import MockCamera
from rover.config import Config
from rover.distance import Guard, MockSensor
from rover.drive import Drive
from rover.head import Head
from rover.pca9685 import MockPCA9685
from rover.server import make_server


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def wait_for(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


class HeadTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(head_speed_per_s=1.0)
        self.pwm, self.clock = MockPCA9685(), Clock()
        self.head = Head(self.pwm, self.cfg, self.clock)
        self.head._write()
        self.head.step()

    def run_for(self, seconds, dt=0.02):
        for _ in range(round(seconds / dt)):
            self.clock.t += dt
            self.head.step()

    def test_starts_centred(self):
        self.assertEqual(self.pwm.pulses[self.cfg.pan_channel], 1500)
        self.assertEqual(self.pwm.pulses[self.cfg.tilt_channel], 1500)

    def test_moves_smoothly_then_arrives(self):
        self.head.look(1, -1)
        self.run_for(0.25)  # a quarter of a sweep per second * 2 units = halfway to the end
        self.assertAlmostEqual(self.head.status()["pan"], 0.5, places=1)
        self.run_for(1.0)
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.pan_channel], self.cfg.pan_right_us)
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.tilt_channel], self.cfg.tilt_down_us)

    def test_clamps_and_centres(self):
        self.head.look(-40, 40)
        self.run_for(2.0)
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.pan_channel], self.cfg.pan_left_us)
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.tilt_channel], self.cfg.tilt_up_us)
        self.head.center()
        self.run_for(2.0)
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.pan_channel], 1500)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(arm_s=0, distance_stop_m=0.4, distance_clear_m=0.55)
        self.pwm, self.clock = MockPCA9685(), Clock()
        self.drive = Drive(self.pwm, self.cfg, self.clock)
        self.sensor = MockSensor(2.0)
        self.guard = Guard(self.sensor, self.drive, self.cfg, self.clock)

    def tick(self, n=1, dt=0.07, throttle=1.0):
        for _ in range(n):
            self.clock.t += dt
            self.guard.step()
            if throttle is not None:
                self.drive.command(throttle, 0)
            self.drive.step()

    def throttle_us(self):
        return self.pwm.pulses[self.cfg.throttle_channel]

    def test_clear_road_drives(self):
        self.tick(40)
        self.assertGreater(self.throttle_us(), 1600)
        self.assertFalse(self.guard.status()["blocked"])

    def test_obstacle_stops_forward_but_allows_reverse(self):
        self.tick(40)
        self.sensor.value = 0.2
        self.tick(1)
        self.assertGreater(self.throttle_us(), 1600)  # one reading alone is not trusted
        self.tick(1)
        self.assertEqual(self.throttle_us(), 1500)    # two of three: stopped
        self.tick(20, throttle=-1.0)
        self.assertLess(self.throttle_us(), 1500)

    def test_single_glitch_is_ignored(self):
        self.tick(40)
        self.sensor.value = 0.05
        self.tick(1)
        self.sensor.value = 2.0
        self.tick(5)
        self.assertGreater(self.throttle_us(), 1600)

    def test_needs_extra_room_before_releasing(self):
        self.sensor.value = 0.2
        self.tick(5)
        self.sensor.value = 0.5  # past stop, not yet past clear
        self.tick(5)
        self.assertTrue(self.guard.status()["blocked"])
        self.sensor.value = 0.6
        self.tick(5)
        self.assertFalse(self.guard.status()["blocked"])

    def test_nothing_in_range_counts_as_clear(self):
        self.sensor.value = None
        self.tick(40)
        self.assertGreater(self.throttle_us(), 1600)
        self.assertIsNone(self.guard.status()["distance_m"])

    def test_broken_sensor_blocks_forward(self):
        self.tick(40)
        self.sensor.value = OSError("sensor unplugged")
        self.tick(10)  # 0.7 s: not yet declared broken
        self.assertFalse(self.guard.status()["fault"])
        self.tick(10)
        self.assertTrue(self.guard.status()["fault"])
        self.assertEqual(self.throttle_us(), 1500)
        self.sensor.value = 2.0
        self.tick(5)
        self.assertFalse(self.guard.status()["fault"])
        self.assertFalse(self.guard.status()["blocked"])


class AudioTests(unittest.TestCase):
    def test_pipeline_passes_text_through_both_commands(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.bin")
            sink = ["python3", "-c", "import sys; open(sys.argv[1], 'wb').write(sys.stdin.buffer.read())", out]
            self.assertTrue(run_pipeline(["tr", "a-z", "A-Z"], sink, b"hello; rm -rf $(x) `y`"))
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"HELLO; RM -RF $(X) `Y`")

    def test_pipeline_reports_failure(self):
        self.assertFalse(run_pipeline(["cat"], ["false"], b"x"))

    def test_speaker_cleans_and_limits_text(self):
        sp = MockSpeaker(Config(say_max_chars=10))
        self.assertEqual(sp.say("  hello \n\n  there   everyone "), "hello ther")
        self.assertTrue(wait_for(lambda: sp.said == ["hello ther"]))
        with self.assertRaises(ValueError):
            sp.say("   ")
        with self.assertRaises(ValueError):
            sp.play_wav(b"definitely not audio")
        sp.close()

    def test_speaker_refuses_when_queue_is_full(self):
        sp = MockSpeaker(Config())
        gate = threading.Event()
        sp._speak = lambda text: gate.wait(5) or True
        with self.assertRaises(Busy):
            for i in range(20):
                sp.say(f"line {i}")
        gate.set()
        sp.close()

    def test_mock_mic_returns_a_real_wav(self):
        data = MockMic(seconds_scale=0.05).record(999)  # clamps to 30 s (scaled down here)
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, 16000))
            self.assertEqual(w.getnframes(), int(16000 * 30 * 0.05))


class ConfigTests(unittest.TestCase):
    def load(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(data, f)
        try:
            return config_mod.load(f.name)
        finally:
            os.unlink(f.name)

    def test_example_config_loads(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_mod.load(os.path.join(here, "rover.example.json"))

    def test_rejects_typos_and_bad_values(self):
        for bad in ({"max_foward": 0.5}, {"max_forward": 3}, {"distance_sensor": "sonar"},
                    {"distance_stop_m": 1.0, "distance_clear_m": 0.5}, {"tts_engine": "siri"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                self.load(bad)


class FullServerTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(arm_s=0)
        self.pwm, self.clock = MockPCA9685(), Clock()
        self.drive = Drive(self.pwm, self.cfg, self.clock)
        self.head = Head(self.pwm, self.cfg, self.clock)
        self.speaker = MockSpeaker(self.cfg)
        self.mic = MockMic(seconds_scale=0.01)
        self.sensor = MockSensor(1.23)
        self.guard = Guard(self.sensor, self.drive, self.cfg, self.clock)
        self.guard.step()
        self.camera = MockCamera(fps=50)
        self.server = make_server(self.drive, "127.0.0.1", 0, camera=self.camera, head=self.head,
                                  speaker=self.speaker, mic=self.mic, guard=self.guard)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.camera.close()
        self.speaker.close()

    def post(self, path, body=b"{}"):
        req = urllib.request.Request(self.url + path, data=body, method="POST")
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.headers["Content-Type"], r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers["Content-Type"], e.read()

    def test_status_reports_everything(self):
        with urllib.request.urlopen(self.url + "/status") as r:
            s = json.loads(r.read())
        self.assertTrue(s["camera"] and s["mic"])
        self.assertEqual(s["head"], {"pan": 0.0, "tilt": 0.0})
        self.assertEqual(s["distance"]["distance_m"], 1.23)
        self.assertFalse(s["speaker"]["speaking"])

    def test_look_and_center(self):
        self.assertEqual(self.post("/look", b'{"pan": 1, "tilt": 0.5}')[0], 200)
        for _ in range(100):
            self.clock.t += 0.02
            self.head.step()
        self.assertAlmostEqual(self.pwm.pulses[self.cfg.pan_channel], self.cfg.pan_right_us)
        self.assertEqual(self.post("/center")[0], 200)
        self.assertEqual(self.post("/look", b'{"pan": "left"}')[0], 400)
        self.assertEqual(self.post("/look", b'{"pan": Infinity}')[0], 400)

    def test_say(self):
        code, _, body = self.post("/say", json.dumps({"text": "Hello from the rover"}).encode())
        self.assertEqual((code, json.loads(body)["saying"]), (200, "Hello from the rover"))
        self.assertTrue(wait_for(lambda: self.speaker.said == ["Hello from the rover"]))
        self.assertEqual(self.post("/say", b'{"text": ""}')[0], 400)
        self.assertEqual(self.post("/say", b'{"text": 5}')[0], 400)

    def test_play_accepts_only_wav(self):
        wav = MockMic(seconds_scale=0.01).record(1)
        self.assertEqual(self.post("/play", wav)[0], 200)
        self.assertEqual(self.post("/play", b"MP3 or whatever")[0], 400)

    def test_listen_returns_wav(self):
        code, ctype, body = self.post("/listen", b'{"seconds": 2}')
        self.assertEqual((code, ctype), (200, "audio/wav"))
        with wave.open(io.BytesIO(body)) as w:
            self.assertEqual(w.getframerate(), 16000)

    def test_extras_missing_give_503(self):
        server = make_server(self.drive, "127.0.0.1", 0)
        url, self.url = self.url, f"http://127.0.0.1:{server.server_address[1]}"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for path in ("/look", "/center", "/say", "/play", "/listen"):
                self.assertEqual(self.post(path)[0], 503, path)
            self.assertEqual(self.post("/drive", b'{"throttle": 0.1}')[0], 200)
        finally:
            self.url = url
            server.shutdown()
            server.server_close()

    def test_a_crashing_extra_does_not_break_driving(self):
        def boom(seconds):
            raise RuntimeError("mic exploded")
        self.mic._record = boom
        self.assertEqual(self.post("/listen")[0], 500)
        self.assertEqual(self.post("/drive", b'{"throttle": 0.1}')[0], 200)
        self.assertEqual(self.post("/stop")[0], 200)


if __name__ == "__main__":
    unittest.main()
