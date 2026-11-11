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

from tars import config as config_mod
from tars.audio import Busy, MockMic, MockSpeaker, run_pipeline
from tars.camera import FrameBuffer, MockCamera
from tars.config import Config
from tars.legs import JOINTS, Busy as LegsBusy, Legs, value_to_us
from tars.moves import MOVES, STANCE
from tars.pca9685 import MockPCA9685
from tars.server import make_server


class RecordingPWM(MockPCA9685):
    def __init__(self):
        super().__init__()
        self.log = []

    def set_pulse_us(self, channel, us):
        super().set_pulse_us(channel, us)
        self.log.append((channel, us))


def fast_sleep(scale=0.0):
    return lambda s: time.sleep(s * scale) if scale else None


def make_legs(positions_file="", scale=0.0, **overrides):
    cfg = Config(positions_file=positions_file, **overrides)
    pwm = RecordingPWM()
    return Legs(pwm, cfg, sleep=fast_sleep(scale)), pwm, cfg


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.005)
    return False


class MoveTableTests(unittest.TestCase):
    def test_every_move_ends_standing_and_is_in_range(self):
        for name, move in MOVES.items():
            legs = [s for s in move["steps"] if s[0] != "pause"]
            self.assertEqual(tuple(legs[-1][:4]), STANCE, name)
            self.assertTrue(move["about"], name)

    def test_unit_conversion_matches_tars_ai(self):
        self.assertEqual(value_to_us(0), 500)
        self.assertEqual(value_to_us(300), 1500)
        self.assertEqual(value_to_us(600), 2500)


class LegsTests(unittest.TestCase):
    def test_nothing_moves_at_startup(self):
        legs, pwm, cfg = make_legs()
        self.assertEqual(pwm.pulses, {})
        self.assertTrue(legs.status()["released"])

    def test_percent_mapping_uses_calibrated_ends(self):
        legs, pwm, cfg = make_legs()
        self.assertAlmostEqual(legs.percent_to_value("left_height", 1), cfg.left_up_height)
        self.assertAlmostEqual(legs.percent_to_value("left_height", 100), cfg.left_down_height)
        self.assertAlmostEqual(legs.percent_to_value("right_leg", 1), cfg.forward_right_leg)
        self.assertAlmostEqual(legs.percent_to_value("right_leg", 500), cfg.back_right_leg)  # clamped

    def test_a_move_runs_to_standing_then_goes_limp(self):
        legs, pwm, cfg = make_legs()
        legs.start("step_forward")
        self.assertTrue(legs.wait(5))
        s = legs.status()
        self.assertEqual(s["completed"], 1)
        self.assertIsNone(s["error"])
        self.assertTrue(s["released"])
        for ch in range(4):
            self.assertIsNone(pwm.pulses[ch])  # limp
        for j in JOINTS:
            self.assertAlmostEqual(s["positions"][j], round(legs.percent_to_value(j, 50)), delta=1)

    def test_pulses_stay_inside_calibrated_limits(self):
        legs, pwm, cfg = make_legs()
        for name in MOVES:
            legs.start(name)
            self.assertTrue(legs.wait(10), name)
        lo = value_to_us(min(cfg.left_up_height, cfg.right_down_height,
                             cfg.forward_left_leg, cfg.back_right_leg, cfg.preset_left_leg))
        hi = value_to_us(max(cfg.left_down_height, cfg.right_up_height,
                             cfg.back_left_leg, cfg.forward_right_leg, cfg.preset_left_height))
        self.assertTrue(all(lo - 0.01 <= us <= hi + 0.01 for _, us in pwm.log))

    def test_moves_are_smooth_not_jumps(self):
        legs, pwm, cfg = make_legs()
        legs.start("stand")
        legs.wait(5)
        pwm.log.clear()
        legs.start("bow")
        legs.wait(5)
        last = {}
        for ch, us in pwm.log:
            if ch in last:
                self.assertLess(abs(us - last[ch]), 60, "a servo jumped")
            last[ch] = us

    def test_only_one_move_at_a_time(self):
        legs, pwm, cfg = make_legs(scale=1.0)
        legs.start("pose")
        with self.assertRaises(LegsBusy):
            legs.start("bow")
        legs.release()
        legs.wait(2)

    def test_stop_returns_to_standing(self):
        legs, pwm, cfg = make_legs(scale=1.0)
        legs.start("bow")
        time.sleep(0.4)
        legs.stop()
        self.assertTrue(legs.wait(5))
        s = legs.status()
        self.assertEqual(s["completed"], 0)
        for j in JOINTS:
            self.assertAlmostEqual(s["positions"][j], round(legs.percent_to_value(j, 50)), delta=1)

    def test_release_goes_limp_immediately_and_stays_limp(self):
        legs, pwm, cfg = make_legs(scale=1.0)
        legs.start("side_side")
        time.sleep(0.2)
        legs.release()
        n = len(pwm.log)
        self.assertTrue(legs.wait(2))
        time.sleep(0.1)
        self.assertEqual(len(pwm.log), n, "servo written after release")
        for ch in range(4):
            self.assertIsNone(pwm.pulses[ch])

    def test_reengages_where_it_left_off(self):
        legs, pwm, cfg = make_legs()
        legs.start("tilt_left")
        legs.wait(5)
        pos = legs.status()["positions"]
        pwm.log.clear()
        legs.start("stand")
        legs.wait(5)
        first = {ch: us for ch, us in pwm.log[:4]}
        for j, ch in zip(JOINTS, range(4)):
            self.assertAlmostEqual(first[ch], value_to_us(pos[j]), delta=3.4)  # status rounds to whole units

    def test_positions_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pos.json")
            legs, pwm, cfg = make_legs(positions_file=path)
            legs.start("tilt_right")
            legs.wait(5)
            again, _, _ = make_legs(positions_file=path)
            self.assertEqual(again.status()["positions"], legs.status()["positions"])

    def test_swap_turns(self):
        legs, pwm, cfg = make_legs(swap_turns=True)
        self.assertEqual(legs.start("turn_left"), "turn_right")
        legs.wait(5)
        self.assertEqual(legs.start("turn_right_slow"), "turn_left_slow")
        legs.wait(5)

    def test_bad_requests(self):
        legs, pwm, cfg = make_legs()
        with self.assertRaises(KeyError):
            legs.start("moonwalk")
        with self.assertRaises(ValueError):
            legs.start("bow", times=99)

    def test_servo_failure_is_reported_and_goes_limp(self):
        legs, pwm, cfg = make_legs()

        def broken(ch, us):
            raise OSError(121, "Remote I/O error")
        pwm.set_pulse_us = broken
        legs.start("stand")
        legs.wait(5)
        s = legs.status()
        self.assertIn("Remote I/O", s["error"])
        self.assertTrue(s["released"])

    def test_preset_holds_assembly_position(self):
        legs, pwm, cfg = make_legs()
        legs.preset()
        self.assertEqual(pwm.pulses[0], value_to_us(350))
        self.assertEqual(pwm.pulses[3], value_to_us(300))
        self.assertFalse(legs.status()["released"])

    def test_repeats(self):
        legs, pwm, cfg = make_legs()
        legs.start("turn_left", times=3)
        legs.wait(5)
        self.assertEqual(legs.status()["completed"], 1)  # one request, run three times
        self.assertIsNone(legs.status()["error"])


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
        config_mod.load(os.path.join(here, "tars.example.json"))

    def test_rejects_typos_and_bad_values(self):
        for bad in ({"left_up_heigth": 200}, {"left_up_height": 700}, {"back_left_leg": "far"},
                    {"right_leg_channel": 0}, {"easing": 2}, {"tts_engine": "siri"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                self.load(bad)


class AudioTests(unittest.TestCase):
    def test_pipeline_passes_text_safely(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.bin")
            sink = ["python3", "-c", "import sys; open(sys.argv[1], 'wb').write(sys.stdin.buffer.read())", out]
            self.assertTrue(run_pipeline(["tr", "a-z", "A-Z"], sink, b"hi; rm -rf $(x)"))
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"HI; RM -RF $(X)")

    def test_speaker_limits_and_queues(self):
        sp = MockSpeaker(Config(say_max_chars=10))
        self.assertEqual(sp.say("  hello \n there everyone "), "hello ther")
        self.assertTrue(wait_for(lambda: sp.said == ["hello ther"]))
        with self.assertRaises(ValueError):
            sp.say("   ")
        gate = threading.Event()
        sp._speak = lambda text: gate.wait(5) or True
        with self.assertRaises(Busy):
            for i in range(20):
                sp.say(f"line {i}")
        gate.set()
        sp.close()

    def test_mock_mic_wav(self):
        data = MockMic(seconds_scale=0.05).record(2)
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual((w.getnchannels(), w.getframerate()), (1, 16000))


class FrameBufferTests(unittest.TestCase):
    def test_wait(self):
        fb = FrameBuffer()
        self.assertIsNone(fb.wait_frame(0, timeout=0.05))
        fb.write(b"abc")
        self.assertEqual(fb.wait_frame(0, timeout=0.05), (1, b"abc"))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.legs, self.pwm, self.cfg = make_legs(scale=0.2)
        self.camera = MockCamera(fps=50)
        self.speaker = MockSpeaker(self.cfg)
        self.server = make_server(self.legs, "127.0.0.1", 0, token="secret", camera=self.camera,
                                  speaker=self.speaker, mic=MockMic(seconds_scale=0.01))
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.legs.release()
        self.server.shutdown()
        self.server.server_close()
        self.camera.close()
        self.speaker.close()

    def post(self, path, body=b"{}", token="secret"):
        req = urllib.request.Request(self.url + path, data=body, method="POST",
                                     headers={"X-TARS-Token": token} if token else {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.headers["Content-Type"], r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers["Content-Type"], e.read()

    def get(self, path):
        with urllib.request.urlopen(self.url + path) as r:
            return r.read()

    def test_move_flow(self):
        code, _, body = self.post("/move", b'{"name": "step_forward"}')
        self.assertEqual((code, json.loads(body)["started"]), (202, "step_forward"))
        self.assertEqual(self.post("/move", b'{"name": "bow"}')[0], 409)
        self.assertTrue(wait_for(lambda: not json.loads(self.get("/status"))["legs"]["moving"], 10))
        self.assertEqual(json.loads(self.get("/status"))["legs"]["completed"], 1)

    def test_stop_and_release(self):
        self.post("/move", b'{"name": "pose"}')
        self.assertEqual(self.post("/stop")[0], 200)
        self.assertTrue(self.legs.wait(5))
        self.post("/move", b'{"name": "pose"}')
        self.assertEqual(self.post("/release")[0], 200)
        self.assertTrue(json.loads(self.get("/status"))["legs"]["released"])

    def test_bad_moves_and_token(self):
        self.assertEqual(self.post("/move", b'{"name": "moonwalk"}')[0], 400)
        self.assertEqual(self.post("/move", b'{"name": "bow", "times": 1.5}')[0], 400)
        self.assertEqual(self.post("/move", b'{"name": "bow", "times": 50}')[0], 400)
        self.assertEqual(self.post("/move", b'[1]')[0], 400)
        self.assertEqual(self.post("/move", b'{"name": "bow"}', token="nope")[0], 403)
        self.assertFalse(self.legs.busy())

    def test_moves_list_and_page(self):
        moves = json.loads(self.get("/moves"))
        self.assertEqual({m["name"] for m in moves}, set(MOVES))
        self.assertTrue(next(m for m in moves if m["name"] == "step_forward")["travels"])
        self.assertIn(b"CLAUDE", self.get("/"))

    def test_camera_and_voice(self):
        self.assertEqual(self.get("/snapshot.jpg")[:2], b"\xff\xd8")
        with urllib.request.urlopen(self.url + "/stream.mjpg") as r:
            self.assertGreaterEqual(r.read(20000).count(b"--FRAME"), 2)
        self.assertEqual(self.post("/say", b'{"text": "Honesty, ninety percent."}')[0], 200)
        self.assertTrue(wait_for(lambda: self.speaker.said == ["Honesty, ninety percent."]))
        code, ctype, body = self.post("/listen", b'{"seconds": 1}')
        self.assertEqual((code, ctype, body[:4]), (200, "audio/wav", b"RIFF"))

    def test_missing_extras_give_503(self):
        server = make_server(self.legs, "127.0.0.1", 0)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for path in ("/say", "/listen", "/play"):
                req = urllib.request.Request(url + path, data=b"{}", method="POST")
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(req)
                self.assertEqual(cm.exception.code, 503, path)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
