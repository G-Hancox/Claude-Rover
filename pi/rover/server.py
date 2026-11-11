"""Small HTTP control server (standard library only).

  GET  /         test page with a touch pad and keyboard driving
  GET  /status        current state as JSON
  GET  /stream.mjpg   live video (MJPEG)
  GET  /snapshot.jpg  one still frame
  POST /drive    {"throttle": -1..1, "steering": -1..1}
  POST /stop     stop now

If the ROVER_TOKEN environment variable is set, POST requests must send the same
value in an X-Rover-Token header.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATIC = Path(__file__).parent / "static"


def make_server(drive, host, port, token=None, camera=None):
    token = token if token is not None else os.environ.get("ROVER_TOKEN") or None
    index = (STATIC / "index.html").read_bytes()
    stopping = threading.Event()

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

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                self._send(200, index, "text/html; charset=utf-8")
            elif path == "/status":
                self._send(200, dict(drive.status(), camera=camera is not None))
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

        def do_POST(self):
            if token and self.headers.get("X-Rover-Token") != token:
                return self._send(403, {"error": "bad token"})
            path = self.path.split("?")[0]
            if path == "/stop":
                drive.stop()
                return self._send(200, drive.status())
            if path == "/drive":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    if length > 1024:
                        raise ValueError("body too large")
                    data = json.loads(self.rfile.read(length) or b"{}")
                    throttle = float(data.get("throttle", 0))
                    steering = float(data.get("steering", 0))
                    if throttle != throttle or steering != steering:
                        raise ValueError("NaN")
                except (ValueError, TypeError, AttributeError) as e:
                    return self._send(400, {"error": f"bad request: {e}"})
                drive.command(throttle, steering)
                return self._send(200, drive.status())
            self._send(404, {"error": "not found"})

        def log_message(self, fmt, *args):
            pass  # drive commands arrive 10x a second; keep the log quiet

    class Server(ThreadingHTTPServer):
        daemon_threads = True  # open video streams must not block shutdown

        def shutdown(self):
            stopping.set()
            super().shutdown()

    return Server((host, port), Handler)
