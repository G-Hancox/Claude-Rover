"""Talks to the rover's web API (pi/). Standard library only."""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_URL = "http://rover.local:8080"


class RoverError(Exception):
    pass


class Rover:
    def __init__(self, url=None, token=None):
        self.url = (url or os.environ.get("ROVER_URL") or DEFAULT_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get("ROVER_TOKEN") or None

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
                headers["X-Rover-Token"] = self.token
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("error", "")
            except Exception:  # noqa: BLE001
                detail = ""
            raise RoverError(f"Rover said no ({e.code}): {detail or e.reason}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RoverError(f"Can't reach the rover at {self.url} ({getattr(e, 'reason', e)}). "
                             "Is it powered on, on Wi-Fi, and is the rover program running?") from None
        return payload if raw else json.loads(payload)

    def status(self):
        return self._request("GET", "/status")

    def snapshot(self):
        return self._request("GET", "/snapshot.jpg", raw=True)

    def stop(self):
        return self._request("POST", "/stop")

    def look(self, pan, tilt):
        return self._request("POST", "/look", {"pan": pan, "tilt": tilt})

    def say(self, text):
        return self._request("POST", "/say", {"text": text})

    def listen(self, seconds):
        return self._request("POST", "/listen", {"seconds": seconds}, timeout=seconds + 15, raw=True)

    def drive_for(self, throttle, steering, seconds, interval=0.1):
        """Drive for a set time, then stop. Ends early if the rover blocks forward motion.

        The rover stops by itself if these commands stop arriving, so a crash here is safe.
        Returns (seconds actually driven, why it ended, last status).
        """
        start = time.monotonic()
        reason, status = "finished", None
        try:
            while True:
                status = self._request("POST", "/drive", {"throttle": throttle, "steering": steering},
                                       timeout=2.0)
                if throttle > 0 and status.get("forward_blocked"):
                    reason = "blocked"
                    break
                left = seconds - (time.monotonic() - start)
                if left <= 0:
                    break
                time.sleep(min(interval, left))
        finally:
            elapsed = time.monotonic() - start
            status = self.stop()
        return elapsed, reason, status
