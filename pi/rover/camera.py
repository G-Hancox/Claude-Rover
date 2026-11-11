"""Camera: MJPEG frames from the Pi camera, shared with any number of viewers."""
import base64
import io
import threading
import time


class FrameBuffer(io.BufferedIOBase):
    """Holds the newest JPEG frame. The camera writes to it; viewers wait on it."""

    def __init__(self):
        self._cond = threading.Condition()
        self._frame = None
        self._id = 0

    def write(self, buf):
        with self._cond:
            self._frame = bytes(buf)
            self._id += 1
            self._cond.notify_all()
        return len(buf)

    def latest(self):
        with self._cond:
            return self._id, self._frame

    def wait_frame(self, last_id=0, timeout=2.0):
        """Return (id, jpeg) for a frame newer than last_id, or None if none arrives in time."""
        with self._cond:
            if self._cond.wait_for(lambda: self._id != last_id, timeout):
                return self._id, self._frame
            return None


class PiCamera:
    """The real camera, through picamera2 (sudo apt install python3-picamera2)."""

    def __init__(self, width=640, height=480, fps=15, hflip=False, vflip=False):
        from libcamera import Transform
        from picamera2 import Picamera2
        from picamera2.outputs import FileOutput

        try:
            from picamera2.encoders import MJPEGEncoder as Encoder  # Pi 4 hardware encoder
        except ImportError:
            from picamera2.encoders import JpegEncoder as Encoder

        self.frames = FrameBuffer()
        self.closed = False
        self._cam = Picamera2()
        self._cam.configure(self._cam.create_video_configuration(
            main={"size": (width, height)},
            controls={"FrameRate": fps},
            transform=Transform(hflip=hflip, vflip=vflip),
        ))
        self._cam.start_recording(Encoder(), FileOutput(self.frames))

    def close(self):
        self.closed = True
        try:
            self._cam.stop_recording()
        finally:
            self._cam.close()


class MockCamera:
    """A moving test pattern, so the stream can be tried on any computer."""

    def __init__(self, fps=5, **_):
        from ._mock_frames import FRAMES

        self.frames = FrameBuffer()
        self.closed = False
        self._jpegs = [base64.b64decode(f) for f in FRAMES]
        self._period = 1.0 / fps
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        i = 0
        while not self.closed:
            self.frames.write(self._jpegs[i % len(self._jpegs)])
            i += 1
            time.sleep(self._period)

    def close(self):
        self.closed = True
