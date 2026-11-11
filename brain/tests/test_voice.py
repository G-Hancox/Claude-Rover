"""The hands-free loop: local commands, persona prompts, and calling Claude Code."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import tars_voice  # noqa: E402
from tars_voice import Voice, split_emotion, spoken  # noqa: E402


class FakeTars:
    url = "http://fake:8080"

    def __init__(self):
        self.p = {"mode": "claude", "honesty": 90, "humor": 75}
        self.said, self.shown, self.stopped = [], [], 0

    def persona(self, **changes):
        self.p.update(changes)
        return dict(self.p)

    def stop(self):
        self.stopped += 1

    def say(self, text, emotion=None):
        self.said.append((text, emotion))

    def show(self, text, seconds=15):
        self.shown.append(text)


class FakeClaude:
    """Stands in for `claude -p ... --output-format json`."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return subprocess.CompletedProcess(cmd, 0, stdout=reply, stderr="")


def ok(result, session="s1"):
    return json.dumps({"type": "result", "is_error": False, "result": result, "session_id": session})


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class LocalCommandTests(unittest.TestCase):
    def setUp(self):
        self.tars = FakeTars()
        self.claude = FakeClaude([])
        self.v = Voice(self.tars, claude_cmd="claude", run=self.claude)

    def test_stop_is_instant_and_never_asks_claude(self):
        for phrase in ("Stop!", "hey tars stop", "Freeze."):
            self.v.handle(phrase)
        self.assertEqual(self.tars.stopped, 3)
        self.assertEqual(self.claude.calls, [])

    def test_mode_switching_survives_misheard_words(self):
        self.v.handle("Switch to TARS mode.")
        self.assertEqual(self.tars.p["mode"], "tars")
        self.assertIn("Honesty 90 percent", self.tars.said[-1][0])
        self.v.handle("claude mode")
        self.assertEqual(self.tars.p["mode"], "claude")
        self.v.handle("Stars mode")          # common mishearing
        self.assertEqual(self.tars.p["mode"], "tars")
        self.v.handle("Cloud mode.")
        self.assertEqual(self.tars.p["mode"], "claude")
        self.assertEqual(self.claude.calls, [])

    def test_settings(self):
        self.v.handle("Set humor to 60 percent.")
        self.v.handle("honesty setting 95")
        self.assertEqual((self.tars.p["humor"], self.tars.p["honesty"]), (60, 95))
        self.v.handle("set humor to 250")
        self.assertEqual(self.tars.p["humor"], 60)
        self.assertIn("only goes up to 100", self.tars.said[-1][0])

    def test_ordinary_questions_go_to_claude(self):
        self.claude.replies.append(ok("It's a workbench."))
        self.v.handle("What do you see on the table?")
        self.assertEqual(len(self.claude.calls), 1)


class ClaudeCallTests(unittest.TestCase):
    def setUp(self):
        self.tars = FakeTars()
        self.clock = Clock()

    def voice(self, replies):
        self.claude = FakeClaude(replies)
        return Voice(self.tars, claude_cmd="claude", run=self.claude, clock=self.clock)

    def arg(self, cmd, flag):
        return cmd[cmd.index(flag) + 1]

    def test_command_is_locked_down(self):
        v = self.voice([ok("Hi.")])
        v.handle("hello")
        cmd = self.claude.calls[0]
        self.assertEqual(cmd[:3], ["claude", "-p", "hello"])
        self.assertEqual(self.arg(cmd, "--output-format"), "json")
        self.assertIn("--strict-mcp-config", cmd)
        self.assertTrue(self.arg(cmd, "--mcp-config").endswith(".mcp.json"))
        denied = self.arg(cmd, "--disallowedTools").split(",")
        for tool in ("Bash", "Write", "Edit", "Read", "mcp__tars__say"):
            self.assertIn(tool, denied)
        allowed = self.arg(cmd, "--allowedTools").split(",")
        self.assertIn("mcp__tars__look", allowed)
        self.assertNotIn("Bash", allowed)
        self.assertNotIn("--resume", cmd)

    def test_conversation_continues_then_resets_on_idle_and_mode_change(self):
        v = self.voice([ok("One.", "s1"), ok("Two.", "s2"), ok("Three.", "s3"), ok("Four.", "s4")])
        v.handle("first")
        v.handle("second")
        self.assertEqual(self.arg(self.claude.calls[1], "--resume"), "s1")
        self.clock.t += 11 * 60
        v.handle("much later")
        self.assertNotIn("--resume", self.claude.calls[2])
        self.tars.p["mode"] = "tars"
        v.handle("now in tars mode")
        self.assertNotIn("--resume", self.claude.calls[3])

    def test_persona_prompts(self):
        v = self.voice([ok("Affirmative."), ok("Sure.")])
        self.tars.p.update(mode="tars", humor=60)
        v.handle("status report")
        system = self.arg(self.claude.calls[0], "--append-system-prompt")
        self.assertIn("playing TARS", system)
        self.assertIn("humor 60%", system)
        self.assertIn("never give G false information", system)
        self.tars.p["mode"] = "claude"
        v.handle("hello")
        self.assertIn("You are Claude, speaking as yourself", self.arg(self.claude.calls[1], "--append-system-prompt"))

    def test_reply_is_spoken_with_emotion_and_thinking_screen_cleared(self):
        v = self.voice([ok("[joy] That's **great** news! See https://example.com")])
        v.handle("I finished the legs")
        self.assertEqual(self.tars.said[-1], ("That's great news! See", "joy"))
        self.assertEqual(self.tars.shown, ["…", ""])

    def test_failures_are_spoken_not_crashes(self):
        v = self.voice([json.dumps({"is_error": True, "result": "auth"}), "not json at all",
                        subprocess.TimeoutExpired("claude", 240)])
        for q in ("a", "b", "c"):
            v.handle(q)
        self.assertEqual(len(self.tars.said), 3)
        self.assertIn("too long", self.tars.said[-1][0])
        self.assertIsNone(v.session)

    def test_no_claude_installed(self):
        v = Voice(self.tars, claude_cmd=None, run=None)
        v.claude = None
        v.handle("hello")
        self.assertIn("can't find Claude Code", self.tars.said[-1][0])


class HelperTests(unittest.TestCase):
    def test_split_emotion(self):
        self.assertEqual(split_emotion("[surprise] Oh!"), ("Oh!", "surprise"))
        self.assertEqual(split_emotion("[neutral] Fine."), ("Fine.", None))
        self.assertEqual(split_emotion("[smug] Fine."), ("[smug] Fine.", None))

    def test_spoken_trims_long_replies_at_a_sentence(self):
        long = "This is a sentence. " * 40
        out = spoken(long)
        self.assertLessEqual(len(out), 480)
        self.assertTrue(out.endswith("."))


class LiveLoopTest(unittest.TestCase):
    """The real voice program against the simulated TARS, with a fake `claude` on the PATH."""

    def test_typed_question_round_trip(self):
        import urllib.request
        port = 8141
        pi = subprocess.Popen([sys.executable, "-m", "tars", "--mock", "--port", str(port)],
                              cwd=os.path.join(os.path.dirname(os.path.dirname(HERE)), "pi"),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tmp = tempfile.mkdtemp()
        log = os.path.join(tmp, "claude-args.json")
        fake = os.path.join(tmp, "claude")
        with open(fake, "w") as f:
            f.write(f"#!{sys.executable}\nimport json,sys\njson.dump(sys.argv[1:], open({log!r}, 'w'))\n"
                    "print(json.dumps({'is_error': False, 'result': '[joy] Hello from the test.', 'session_id': 'x'}))\n")
        os.chmod(fake, 0o755)
        url = f"http://127.0.0.1:{port}"
        voice = None
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(url + "/status", timeout=0.5).read()
                    break
                except OSError:
                    import time
                    time.sleep(0.1)
            env = {**os.environ, "TARS_URL": url, "PATH": tmp + os.pathsep + os.environ["PATH"]}
            voice = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(HERE), "tars_voice.py")],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            import time
            time.sleep(1.5)

            def post(path, body):
                req = urllib.request.Request(url + path, data=json.dumps(body).encode(), method="POST")
                return json.loads(urllib.request.urlopen(req).read())

            post("/heard", {"text": "TARS mode"})
            for _ in range(50):
                if json.loads(urllib.request.urlopen(url + "/persona").read())["mode"] == "tars":
                    break
                time.sleep(0.1)
            self.assertEqual(json.loads(urllib.request.urlopen(url + "/persona").read())["mode"], "tars")

            post("/heard", {"text": "What's up?"})
            for _ in range(100):
                if os.path.exists(log):
                    break
                time.sleep(0.1)
            time.sleep(0.5)
            with open(log) as f:
                args = json.load(f)
            self.assertEqual(args[:2], ["-p", "What's up?"])
            self.assertIn("playing TARS", args[args.index("--append-system-prompt") + 1])
        finally:
            if voice:
                voice.terminate()
                out = voice.communicate(timeout=5)[0]
                self.assertIn("TARS:   Hello from the test.", out)
            pi.terminate()
            pi.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
