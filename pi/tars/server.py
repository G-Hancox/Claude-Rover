"""Small HTTP control server (standard library only).

  GET  /              control page: video, move buttons, say, listen
  GET  /status        current state as JSON
  GET  /moves         the moves TARS knows, with a line about each
  GET  /stream.mjpg   live video (MJPEG)
  GET  /snapshot.jpg  one still frame
  POST /move          {"name": "step_forward", "times": 1}   starts a move, returns at once
  POST /stop          cut the current move short and return to standing
  POST /release       let the leg servos go limp now
  GET  /screen.png    what the front screen is showing right now
  POST /say           {"text": "...", "emotion": "joy"}   speak (emotion optional, TARS voice)
  POST /display       {"text": "...", "seconds": 15}      show text on the screen ("" clears)
  GET  /heard?after=N&wait=25   next thing said after "Hey TARS" (audio/wav, or JSON for
                      typed text) with its number in X-Heard-Id; 204 if nothing yet
  POST /heard         {"text": "..."} or a WAV body: talk to TARS without the wake word
  GET/POST /persona   {"mode": "claude"|"tars", "honesty": 0-100, "humor": 0-100}
  POST /play          WAV file as the body       play it through the speaker
  POST /listen        {"seconds": 1..30}         record the mic, returns a WAV

If the TARS_TOKEN environment variable is set, POST requests must send the same
value in an X-TARS-Token header.
"""
import json
import math
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .audio import Busy
from .legs import Busy as LegsBusy
from .moves import MOVES, TRAVEL

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


def make_server(legs, host, port, token=None, camera=None, speaker=None, mic=None, display=None,
                heard=None, persona=None, listener=None):
    token = token if token is not None else os.environ.get("TARS_TOKEN") or None
    index = (STATIC / "index.html").read_bytes()
    stopping = threading.Event()

    def full_status():
        return {
            "legs": legs.status(),
            "camera": camera is not None,
            "speaker": speaker.status() if speaker else None,
            "mic": mic is not None,
            "display": display is not None,
            "persona": persona.to_dict() if persona else None,
            "wake": None if not listener else {
                "listening_for_wake_word": listener.error is None,
                "capturing": listener.capturing,
                "error": listener.error,
            },
            "heard_latest": heard.latest_id() if heard else None,
        }

    moves_list = [{"name": n, "about": m["about"], "travels": n in TRAVEL} for n, m in MOVES.items()]

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
            elif path == "/moves":
                self._send(200, moves_list)
            elif path == "/snapshot.jpg":
                got = camera.frames.wait_frame(0, timeout=2.0) if camera else None
                if got:
                    self._send(200, got[1], "image/jpeg")
                else:
                    self._send(503, {"error": "no camera"})
            elif path == "/heard":
                self._get_heard()
            elif path == "/persona":
                if persona:
                    self._send(200, persona.to_dict())
                else:
                    self._send(503, {"error": "no persona"})
            elif path == "/screen.png":
                png = display.png() if display else None
                if png:
                    self._send(200, png, "image/png")
                else:
                    self._send(503, {"error": "no screen"})
            elif path == "/stream.mjpg":
                self._stream()
            else:
                self._send(404, {"error": "not found"})

        def _get_heard(self):
            if not heard:
                return self._send(503, {"error": "not listening"})
            from urllib.parse import parse_qs, urlsplit
            q = parse_qs(urlsplit(self.path).query)
            try:
                after = int(q.get("after", ["0"])[0])
                wait = max(0.0, min(30.0, float(q.get("wait", ["0"])[0])))
            except ValueError:
                return self._send(400, {"error": "after and wait must be numbers"})
            item = heard.wait_after(after, wait)
            if not item:
                self.send_response(204)
                self.send_header("X-Heard-Id", str(heard.latest_id()))
                self.end_headers()
                return
            num, kind, payload = item
            body = payload if kind == "wav" else json.dumps({"text": payload}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav" if kind == "wav" else "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Heard-Id", str(num))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

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
            if token and self.headers.get("X-TARS-Token") != token:
                return self._send(403, {"error": "bad token"})
            path = self.path.split("?")[0]
            route = {
                "/stop": self._stop, "/release": self._release, "/move": self._move,
                "/say": self._say, "/play": self._play, "/listen": self._listen,
                "/display": self._display, "/heard": self._post_heard, "/persona": self._persona,
            }.get(path)
            if not route:
                return self._send(404, {"error": "not found"})
            try:
                route()
            except BadRequest as e:
                self._send(400, {"error": str(e)})
            except ValueError as e:
                self._send(400, {"error": str(e)})
            except (Busy, LegsBusy) as e:
                self._send(409, {"error": str(e)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:  # noqa: BLE001 - report it; a move in progress is unaffected
                self._send(500, {"error": repr(e)})

        def _stop(self):
            legs.stop()
            self._send(200, full_status())

        def _release(self):
            legs.release()
            self._send(200, full_status())

        def _move(self):
            data = self._json()
            name = data.get("name")
            if not isinstance(name, str) or name not in MOVES:
                raise BadRequest(f"unknown move {name!r}; GET /moves lists them")
            times = _number(data, "times", 1)
            if times != int(times):
                raise BadRequest("times must be a whole number")
            started = legs.start(name, int(times))
            self._send(202, {"started": started, "times": int(times)})

        def _say(self):
            if not speaker:
                return self._send(503, {"error": "no speaker"})
            data = self._json()
            text, emotion = data.get("text", ""), data.get("emotion")
            if not isinstance(text, str):
                raise BadRequest("text must be a string")
            if emotion is not None and not isinstance(emotion, str):
                raise BadRequest("emotion must be a string")
            self._send(200, {"saying": speaker.say(text, emotion)})

        def _post_heard(self):
            if not heard:
                return self._send(503, {"error": "not listening"})
            if self.headers.get("Content-Type", "").startswith("audio/"):
                body = self._body(MAX_WAV)
                if body[:4] != b"RIFF":
                    raise BadRequest("not a WAV file")
                return self._send(200, {"id": heard.add(body, "wav")})
            text = self._json().get("text", "")
            if not isinstance(text, str) or not text.strip():
                raise BadRequest("text must be a non-empty string")
            self._send(200, {"id": heard.add(" ".join(text.split())[:500], "text")})

        def _persona(self):
            if not persona:
                return self._send(503, {"error": "no persona"})
            data = self._json()
            unknown = set(data) - {"mode", "honesty", "humor"}
            if unknown:
                raise BadRequest(f"unknown setting: {', '.join(sorted(unknown))}")
            self._send(200, persona.update(**data))

        def _display(self):
            if not display:
                return self._send(503, {"error": "no screen"})
            data = self._json()
            text = data.get("text", "")
            if not isinstance(text, str):
                raise BadRequest("text must be a string")
            seconds = _number(data, "seconds", 15)
            if not 1 <= seconds <= 600:
                raise BadRequest("seconds must be 1 to 600")
            display.show_text(text, seconds)
            self._send(200, {"showing": text})

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
            pass  # the page polls /status several times a second; keep the log quiet

    class Server(ThreadingHTTPServer):
        daemon_threads = True  # open video streams must not block shutdown

        def shutdown(self):
            stopping.set()
            super().shutdown()

    return Server((host, port), Handler)
