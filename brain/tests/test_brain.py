"""End-to-end: a simulated rover (pi/ in mock mode) driven through the real MCP tools."""
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
from rover_client import Rover, RoverError  # noqa: E402

try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False


def setUpModule():
    global pi
    pi = subprocess.Popen([sys.executable, "-m", "rover", "--mock", "--port", str(PORT)],
                          cwd=PI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(URL + "/status", timeout=0.5).read()
            break
        except OSError:
            time.sleep(0.1)
    time.sleep(2.1)  # let the simulated motor controller arm


def tearDownModule():
    pi.terminate()
    pi.wait(timeout=5)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.rover = Rover(URL)

    def test_drive_for_moves_then_stops(self):
        t0 = time.monotonic()
        elapsed, reason, status = self.rover.drive_for(1.0, 0.3, 0.5)
        self.assertEqual(reason, "finished")
        self.assertAlmostEqual(elapsed, 0.5, delta=0.3)
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(status["throttle"], 0.0)

    def test_snapshot_and_listen(self):
        self.assertEqual(self.rover.snapshot()[:2], b"\xff\xd8")
        self.assertEqual(self.rover.listen(1)[:4], b"RIFF")

    def test_unreachable_rover_gives_a_plain_message(self):
        with self.assertRaises(RoverError) as cm:
            Rover("http://127.0.0.1:9").status()
        self.assertIn("Can't reach the rover", str(cm.exception))

    def test_rover_refusal_is_reported(self):
        with self.assertRaises(RoverError) as cm:
            self.rover.say("   ")
        self.assertIn("400", str(cm.exception))


@unittest.skipUnless(HAVE_MCP, "mcp package not installed")
class ToolTests(unittest.TestCase):
    def call(self, *calls):
        async def go():
            params = StdioServerParameters(command=sys.executable,
                                           args=[os.path.join(BRAIN, "rover_mcp.py")],
                                           env={**os.environ, "ROVER_URL": URL})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name for t in (await session.list_tools()).tools}
                    return tools, [await session.call_tool(n, a) for n, a in calls]
        return asyncio.run(go())

    def test_all_tools_through_claude_codes_protocol(self):
        tools, r = self.call(
            ("look", {}),
            ("drive", {"throttle": 0.5, "steering": -0.2, "seconds": 0.4}),
            ("drive", {"throttle": 99, "seconds": 99}),
            ("point_camera", {"pan": 0.5, "tilt": -0.25}),
            ("say", {"text": "Hello from the test"}),
            ("stop", {}),
            ("listen", {"seconds": 1}),
        )
        self.assertEqual(tools, {"look", "drive", "stop", "point_camera", "say", "listen"})
        look, drive, capped, cam, say, stop, listen = r
        for name, res in zip(("look", "drive", "capped", "cam", "say", "stop", "listen"), r):
            self.assertFalse(res.is_error if hasattr(res, "is_error") else res.isError, name)

        kinds = [c.type for c in look.content]
        self.assertIn("image", kinds)
        self.assertIn("text", kinds)
        image = next(c for c in look.content if c.type == "image")
        self.assertEqual(image.mime_type if hasattr(image, "mime_type") else image.mimeType, "image/jpeg")
        self.assertIn("2.00 m", next(c for c in look.content if c.type == "text").text)

        self.assertIn("Drove 0.", drive.content[0].text)
        self.assertIn("throttle +1.00", capped.content[0].text)  # clamped
        self.assertIn("Drove 3.", capped.content[0].text)        # capped at 3 s
        self.assertIn("pan +0.50", cam.content[0].text)
        self.assertIn("Hello from the test", say.content[0].text)
        self.assertIn("Stopped", stop.content[0].text)
        self.assertTrue("Heard" in listen.content[0].text or "faster-whisper" in listen.content[0].text)

    def test_unreachable_rover_is_a_tool_error_not_a_crash(self):
        async def go():
            params = StdioServerParameters(command=sys.executable,
                                           args=[os.path.join(BRAIN, "rover_mcp.py")],
                                           env={**os.environ, "ROVER_URL": "http://127.0.0.1:9"})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.call_tool("look", {})
        res = asyncio.run(go())
        self.assertTrue(res.is_error if hasattr(res, "is_error") else res.isError)
        self.assertIn("Can't reach the rover", res.content[0].text)


if __name__ == "__main__":
    unittest.main()
