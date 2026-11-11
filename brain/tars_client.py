"""Talks to TARS's web API (pi/). Standard library only."""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://tars.local:8080"


class TarsError(Exception):
    pass


class Tars:
    def __init__(self, url=None, token=None):
        self.url = (url or os.environ.get("TARS_URL") or DEFAULT_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get("TARS_TOKEN") or None

    def _request(self, method, path, body=None, timeout=5.0, raw=False):
        headers = {}
        data = None
        if method == "POST":
            if isinstance(body, bytes):
                data = body
                headers["Content-Type"] = "audio/wav"
            else:
                data = json.dumps(body or {}).encode()
                headers["Content-Type"] = "application/json"
            if self.token:
                headers["X-TARS-Token"] = self.token
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("error", "")
            except Exception:  # noqa: BLE001
                detail = ""
            raise TarsError(f"TARS said no ({e.code}): {detail or e.reason}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TarsError(f"Can't reach TARS at {self.url} ({getattr(e, 'reason', e)}). "
                            "Is it powered on, on Wi-Fi, and is the TARS program running?") from None
        return payload if raw else json.loads(payload)

    def status(self):
        return self._request("GET", "/status")

    def moves(self):
        return self._request("GET", "/moves")

    def snapshot(self):
        return self._request("GET", "/snapshot.jpg", raw=True)

    def stop(self):
        return self._request("POST", "/stop")

    def release(self):
        return self._request("POST", "/release")

    def say(self, text, emotion=None):
        body = {"text": text}
        if emotion:
            body["emotion"] = emotion
        return self._request("POST", "/say", body)

    def show(self, text, seconds=15):
        return self._request("POST", "/display", {"text": text, "seconds": seconds})

    def listen(self, seconds):
        return self._request("POST", "/listen", {"seconds": seconds}, timeout=seconds + 15, raw=True)

    def persona(self, **changes):
        if changes:
            return self._request("POST", "/persona", changes)
        return self._request("GET", "/persona")

    def next_heard(self, after, wait=25):
        """Wait for the next thing said to TARS. Returns (id, kind, payload) or (latest_id, None, None)."""
        req = urllib.request.Request(f"{self.url}/heard?after={int(after)}&wait={wait}")
        try:
            with urllib.request.urlopen(req, timeout=wait + 10) as r:
                num = int(r.headers.get("X-Heard-Id", after))
                if r.status == 204:
                    return num, None, None
                body = r.read()
                if r.headers.get("Content-Type", "").startswith("audio/"):
                    return num, "wav", body
                return num, "text", json.loads(body)["text"]
        except urllib.error.HTTPError as e:
            raise TarsError(f"TARS said no ({e.code}) to /heard") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TarsError(f"Can't reach TARS at {self.url} ({getattr(e, 'reason', e)}).") from None

    def start_move(self, name, times=1):
        return self._request("POST", "/move", {"name": name, "times": times})

    def move(self, name, times=1, timeout=90.0, poll=0.2):
        """Do a move and wait for it to finish. Returns (seconds taken, final status)."""
        started = self.start_move(name, times)["started"]
        t0 = time.monotonic()
        while True:
            time.sleep(poll)
            status = self.status()
            if not status["legs"]["moving"]:
                return started, time.monotonic() - t0, status
            if time.monotonic() - t0 > timeout:
                self.stop()
                raise TarsError(f"{name} took longer than {timeout:.0f} s; asked TARS to stop.")
