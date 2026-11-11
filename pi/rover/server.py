"""Small HTTP control server (standard library only).

  GET  /              test page: video, drive pad, look pad, say, listen
  GET  /status        current state as JSON
  GET  /stream.mjpg   live video (MJPEG)
  GET  /snapshot.jpg  one still frame
  POST /drive         {"throttle": -1..1, "steering": -1..1}
  POST /stop          stop now
  POST /look          {"pan": -1..1, "tilt": -1..1}
  POST /center        point the camera straight ahead
  POST /say           {"text": "..."}            speak through the speaker
  POST /play          WAV file as the body       play it through the speaker
  POST /listen        {"seconds": 1..30}         record the mic, returns a WAV

If the ROVER_TOKEN environment variable is set, POST requests must send the same
value in an X-Rover-Token header.
"""
import json
import math
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .audio import Busy

STATIC = Path(__file__).parent / "static"
MAX_JSON = 4096
MAX_WAV = 5 * 1024 * 1024


class BadRequest(Exception):
    pass


def _number(data, key, default=0.0):
    try:
        value = float(data.get(key, default))
    except (TypeError, ValueError):
        raise BadRequest(f"{key} must be a number") from None
    if not math.isfinite(value):
        raise BadRequest(f"{key} must be a finite number")
    return value


def make_server(drive, host, port, token=None, camera=None, head=None, speaker=None,
                mic=None, guard=None):
    token = token if token is not None else os.environ.get("ROVER_TOKEN") or None
    index = (STATIC / "index.html").read_bytes()
    stopping = threading.Event()

    def full_status():
        s = drive.status()
        s["camera"] = camera is not None
        s["head"] = head.status() if head else None
        s["distance"] = guard.status() if guard else None
        s["speaker"] = speaker.status() if speaker else None
        s["mic"] = mic is not None
        return s

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self, limit):
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                raise BadRequest("bad Content-Length") from None
            if length < 0 or length > limit:
                raise BadRequest("body too large")
            return self.rfile.read(length)

        def _json(self):
            try:
                data = json.loads(self._body(MAX_JSON) or b"{}")
            except ValueError:
                raise BadRequest("body is not valid JSON") from None
            if not isinstance(data, dict):
                raise BadRequest("body must be a JSON object")
            return data

        # ---- GET --------------------------------------------------------

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                self._send(200, index, "text/html; charset=utf-8")
            elif path == "/status":
                self._send(200, full_status())
            elif path == "/snapshot.jpg":
                got = camera.frames.wait_frame(0, timeout=2.0) if camera else None
                if got:
                    self._send(200, got[1], "image/jpeg")
                else:
                    self._send(503, {"error": "no camera"})
            elif path == "/stream.mjpg":
                self._stream()
            else:
                self._send(404, {"error": "not found"})

        def _stream(self):
            if not camera:
                return self._send(503, {"error": "no camera"})
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()
            last = 0
            try:
                while not camera.closed and not stopping.is_set():
                    got = camera.frames.wait_frame(last, timeout=1.0)
                    if not got:
                        continue
                    last, jpeg = got
                    self.wfile.write(b"--FRAME\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # viewer went away

        # ---- POST -------------------------------------------------------

        def do_POST(self):
            if token and self.headers.get("X-Rover-Token") != token:
                return self._send(403, {"error": "bad token"})
            path = self.path.split("?")[0]
            route = {
                "/stop": self._stop, "/drive": self._drive, "/look": self._look,
                "/center": self._center, "/say": self._say, "/play": self._play,
                "/listen": self._listen,
            }.get(path)
            if not route:
                return self._send(404, {"error": "not found"})
            try:
                route()
            except BadRequest as e:
                self._send(400, {"error": str(e)})
            except ValueError as e:
                self._send(400, {"error": str(e)})
            except Busy as e:
                self._send(409, {"error": str(e)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:  # noqa: BLE001 - report it; the drive loop is unaffected
                self._send(500, {"error": repr(e)})

        def _stop(self):
            drive.stop()
            self._send(200, full_status())

        def _drive(self):
            data = self._json()
            drive.command(_number(data, "throttle"), _number(data, "steering"))
            self._send(200, full_status())

        def _look(self):
            if not head:
                return self._send(503, {"error": "no pan/tilt"})
            data = self._json()
            head.look(_number(data, "pan"), _number(data, "tilt"))
            self._send(200, full_status())

        def _center(self):
            if not head:
                return self._send(503, {"error": "no pan/tilt"})
            head.center()
            self._send(200, full_status())

        def _say(self):
            if not speaker:
                return self._send(503, {"error": "no speaker"})
            text = self._json().get("text", "")
            if not isinstance(text, str):
                raise BadRequest("text must be a string")
            self._send(200, {"saying": speaker.say(text)})

        def _play(self):
            if not speaker:
                return self._send(503, {"error": "no speaker"})
            speaker.play_wav(self._body(MAX_WAV))
            self._send(200, {"playing": True})

        def _listen(self):
            if not mic:
                return self._send(503, {"error": "no mic"})
            seconds = _number(self._json(), "seconds", 5)
            self._send(200, mic.record(seconds), "audio/wav")

        def log_message(self, fmt, *args):
            pass  # drive commands arrive 10x a second; keep the log quiet

    class Server(ThreadingHTTPServer):
        daemon_threads = True  # open video streams must not block shutdown

        def shutdown(self):
            stopping.set()
            super().shutdown()

    return Server((host, port), Handler)
