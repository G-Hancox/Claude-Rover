"""End to end: a simulated TARS (pi/ in mock mode) driven through the real MCP tools."""
import asyncio
import os
import subprocess
import sys
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
PI = os.path.join(os.path.dirname(BRAIN), "pi")
PORT = 8137
URL = f"http://127.0.0.1:{PORT}"

sys.path.insert(0, BRAIN)
from tars_client import Tars, TarsError  # noqa: E402

try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False


def setUpModule():
    global pi
    pi = subprocess.Popen([sys.executable, "-m", "tars", "--mock", "--port", str(PORT)],
                          cwd=PI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(URL + "/status", timeout=0.5).read()
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("mock TARS didn't start")


def tearDownModule():
    pi.terminate()
    pi.wait(timeout=10)


def is_error(res):
    return res.is_error if hasattr(res, "is_error") else res.isError


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tars = Tars(URL)

    def test_move_waits_until_done(self):
        name, seconds, status = self.tars.move("tilt_left")
        self.assertEqual(name, "tilt_left")
        self.assertGreater(seconds, 3.0)  # tilt holds for 3 s
        self.assertFalse(status["legs"]["moving"])

    def test_snapshot_listen_moves(self):
        self.assertEqual(self.tars.snapshot()[:2], b"\xff\xd8")
        self.assertEqual(self.tars.listen(1)[:4], b"RIFF")
        self.assertIn("step_forward", {m["name"] for m in self.tars.moves()})

    def test_errors_are_plain(self):
        with self.assertRaises(TarsError) as cm:
            Tars("http://127.0.0.1:9").status()
        self.assertIn("Can't reach TARS", str(cm.exception))
        with self.assertRaises(TarsError) as cm:
            self.tars.start_move("moonwalk")
        self.assertIn("400", str(cm.exception))


@unittest.skipUnless(HAVE_MCP, "mcp package not installed")
class ToolTests(unittest.TestCase):
    def call(self, *calls, url=URL):
        async def go():
            params = StdioServerParameters(command=sys.executable,
                                           args=[os.path.join(BRAIN, "tars_mcp.py")],
                                           env={**os.environ, "TARS_URL": url})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name for t in (await session.list_tools()).tools}
                    return tools, [await session.call_tool(n, a) for n, a in calls]
        return asyncio.run(go())

    def test_all_tools_through_claude_codes_protocol(self):
        tools, r = self.call(
            ("look", {}),
            ("list_moves", {}),
            ("move", {"name": "turn_left"}),
            ("move", {"name": "moonwalk"}),
            ("say", {"text": "Honesty setting ninety percent.", "emotion": "joy"}),
            ("show", {"text": "Shopping list: servos, screws", "seconds": 5}),
            ("stop", {}),
            ("listen", {"seconds": 1}),
        )
        self.assertEqual(tools, {"look", "list_moves", "move", "stop", "say", "show", "listen"})
        look, moves, turn, bad, say, show, stop, listen = r
        self.assertIn("Showing on screen", show.content[0].text)
        for name, res in (("look", look), ("moves", moves), ("turn", turn), ("say", say), ("show", show),
                          ("stop", stop), ("listen", listen)):
            self.assertFalse(is_error(res), name)
        self.assertTrue(is_error(bad))
        self.assertIn("unknown move", bad.content[0].text)

        image = next(c for c in look.content if c.type == "image")
        self.assertEqual(getattr(image, "mime_type", None) or image.mimeType, "image/jpeg")
        self.assertIn("Standing", next(c for c in look.content if c.type == "text").text)
        self.assertIn("step_forward (changes position)", moves.content[0].text)
        self.assertIn("Done: turn_left x1", turn.content[0].text)
        self.assertIn("Honesty setting", say.content[0].text)
        self.assertTrue("Heard" in listen.content[0].text or "faster-whisper" in listen.content[0].text)

    def test_unreachable_tars_is_a_tool_error(self):
        _, (res,) = self.call(("look", {}), url="http://127.0.0.1:9")
        self.assertTrue(is_error(res))
        self.assertIn("Can't reach TARS", res.content[0].text)


if __name__ == "__main__":
    unittest.main()
