"""TARS's front screen: what it's saying, what it's doing, and a TARS-style readout.

Draws with Pillow and writes straight to the Linux framebuffer (/dev/fb0), so it works on
Pi OS Lite with no desktop. On a PC (--mock) it draws into memory; either way the latest
frame is served at GET /screen.png.

  apt: python3-pil python3-numpy fonts-dejavu-core
"""
import io
import math
import os
import socket
import threading
import time

from PIL import Image, ImageDraw, ImageFont

BG = (6, 8, 10)
FG = (232, 236, 238)
DIM = (110, 120, 128)
LINE = (52, 60, 66)
ACCENT = (150, 220, 255)
WARN = (255, 170, 60)
FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu")
SPEECH_LINGER_S = 6.0


def _font(size, bold=False):
    name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    for d in FONT_DIRS:
        path = os.path.join(d, name)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is sent; this just picks the LAN interface
            return s.getsockname()[0]
    except OSError:
        return None


class Framebuffer:
    """The real screen, through /dev/fb0. 16-bit and 32-bit framebuffers are supported."""

    def __init__(self, device="/dev/fb0"):
        sysdir = f"/sys/class/graphics/{os.path.basename(device)}"

        def read(name):
            with open(os.path.join(sysdir, name)) as f:
                return f.read().strip()

        vw, vh = (int(v) for v in read("virtual_size").split(","))
        try:  # visible mode, e.g. "U:800x480p-0"; virtual height can be doubled for panning
            mode = read("modes").splitlines()[0].split(":")[1].split("p")[0]
            self.width, self.height = (int(v) for v in mode.split("x"))
        except (OSError, IndexError, ValueError):
            self.width, self.height = vw, vh
        self.bpp = int(read("bits_per_pixel"))
        try:
            self.stride = int(read("stride"))
        except OSError:
            self.stride = vw * self.bpp // 8
        if self.bpp not in (16, 32):
            raise RuntimeError(f"{self.bpp}-bit framebuffer not supported (16 or 32 only)")
        if self.bpp == 16:
            import numpy  # noqa: F401 - fail now, not on the first frame
        self._f = open(device, "r+b", buffering=0)

    def show(self, im):
        im = im.convert("RGB")
        if self.bpp == 32:
            data = im.convert("RGBA").tobytes("raw", "BGRA")
        else:
            import numpy as np
            a = np.asarray(im, dtype=np.uint16)
            v = ((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)
            data = v.astype("<u2").tobytes()
        row = self.width * self.bpp // 8
        if self.stride != row:
            pad = b"\0" * (self.stride - row)
            data = b"".join(data[i:i + row] + pad for i in range(0, len(data), row))
        self._f.seek(0)
        self._f.write(data)

    def clear(self):
        self.show(Image.new("RGB", (self.width, self.height), (0, 0, 0)))

    def close(self):
        self._f.close()


class MockFramebuffer:
    def __init__(self, width=800, height=480):
        self.width, self.height = width, height
        self.frames = 0
        self.last = None

    def show(self, im):
        self.frames += 1
        self.last = im

    def clear(self):
        pass

    def close(self):
        pass


class Display:
    def __init__(self, fb, cfg, legs=None, speaker=None, mic=None, clock=time.monotonic):
        self._fb = fb
        self._cfg = cfg
        self._legs = legs
        self._speaker = speaker
        self._mic = mic
        self._clock = clock
        rot = cfg.display_rotate
        self.width, self.height = ((fb.height, fb.width) if rot in (90, 270) else (fb.width, fb.height))
        self._lock = threading.Lock()
        self._shown = None          # (text, until) from show_text()
        self._spoken = None         # (text, until) lingering after speech
        self._png = None
        self._running = False
        self._thread = None
        self._ip = _local_ip()
        self._ip_checked = clock()
        s = min(self.width / 800, self.height / 480)
        self._f_title = _font(int(30 * s), bold=True)
        self._f_state = _font(int(20 * s))
        self._f_small = _font(int(16 * s))
        self._f_big = _font(int(40 * s), bold=True)
        self._caption_fonts = [_font(int(n * s)) for n in (44, 38, 32, 27, 22, 18)]

    # ---- public -----------------------------------------------------------------

    def show_text(self, text, seconds=15.0):
        text = " ".join(str(text).split())[:500]
        with self._lock:
            self._shown = (text, self._clock() + seconds) if text else None

    def clear_text(self):
        with self._lock:
            self._shown = None

    def png(self):
        with self._lock:
            return self._png

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def close(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        try:
            self._fb.clear()
        finally:
            self._fb.close()

    # ---- drawing ----------------------------------------------------------------

    def _loop(self):
        period = 1.0 / max(1.0, self._cfg.display_fps)
        frame = 0
        while self._running:
            t0 = time.monotonic()
            try:
                im = self.render()
                if self._cfg.display_rotate:
                    im = im.rotate(self._cfg.display_rotate, expand=True)
                self._fb.show(im)
                frame += 1
                if frame % 5 == 1:  # a PNG for /screen.png, a couple of times a second
                    buf = io.BytesIO()
                    im.save(buf, "PNG", compress_level=1)
                    with self._lock:
                        self._png = buf.getvalue()
            except Exception as e:  # noqa: BLE001 - a screen problem must never stop the robot
                print(f"Screen error: {e!r}", flush=True)
                time.sleep(2)
            time.sleep(max(0.0, period - (time.monotonic() - t0)))

    def _state(self, now):
        legs = self._legs.status() if self._legs else {}
        saying = getattr(self._speaker, "now_saying", None) if self._speaker else None
        listening = bool(self._mic and self._mic.listening)
        with self._lock:
            if saying:
                self._spoken = (saying, now + SPEECH_LINGER_S)
            shown = self._shown if self._shown and self._shown[1] > now else None
            spoken = self._spoken if self._spoken and self._spoken[1] > now else None
        caption = saying or (shown[0] if shown else None) or (spoken[0] if spoken else None)
        if legs.get("error"):
            state, color = "SERVO FAULT", WARN
        elif legs.get("moving"):
            state, color = "MOVING · " + legs["move"].replace("_", " ").upper(), ACCENT
        elif listening:
            state, color = "LISTENING", ACCENT
        elif saying:
            state, color = "SPEAKING", FG
        else:
            state, color = "STANDING BY", DIM
        return {"state": state, "color": color, "caption": caption, "speaking": bool(saying),
                "listening": listening}

    def render(self, now=None):
        now = self._clock() if now is None else now
        st = self._state(now)
        W, H = self.width, self.height
        s = min(W / 800, H / 480)
        m = int(24 * s)
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)

        # top bar
        d.text((m, m), "TARS", font=self._f_title, fill=FG)
        tw = d.textlength(st["state"], font=self._f_state)
        d.text((W - m - tw, m + int(8 * s)), st["state"], font=self._f_state, fill=st["color"])
        top = m + int(48 * s)
        d.line([(m, top), (W - m, top)], fill=LINE, width=max(1, int(2 * s)))
        bottom = H - m - int(64 * s)
        d.line([(m, bottom), (W - m, bottom)], fill=LINE, width=max(1, int(2 * s)))

        # middle
        if st["caption"]:
            self._caption(d, st["caption"], m, top + int(16 * s), W - 2 * m, bottom - top - int(32 * s))
        else:
            self._readout(d, m, top, W - 2 * m, bottom - top, s)

        # bottom strip
        y0 = bottom + int(12 * s)
        y1 = H - m
        if st["speaking"]:
            self._bars(d, now, m, y0, W - 2 * m, y1 - y0)
        elif st["listening"]:
            r = int((10 + 4 * math.sin(now * 6)) * s)
            cx, cy = m + int(16 * s), (y0 + y1) // 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
            d.text((cx + int(28 * s), cy - int(12 * s)), "LISTENING", font=self._f_state, fill=ACCENT)
        else:
            if now - self._ip_checked > 30:
                self._ip, self._ip_checked = _local_ip(), now
            where = f"{self._ip}:{self._cfg.port}" if self._ip else "no network"
            d.text((m, (y0 + y1) // 2 - int(10 * s)), where, font=self._f_small, fill=DIM)
            x = m + int((W - 2 * m) * ((now * 0.15) % 1.0))
            d.line([(x, y0), (x, y1)], fill=LINE, width=max(1, int(3 * s)))
        return im

    def _caption(self, d, text, x, y, width, height):
        for font in self._caption_fonts:
            lines = _wrap(d, text, font, width)
            line_h = int(font.size * 1.3)
            if len(lines) * line_h <= height:
                break
        else:
            lines = lines[: max(1, height // line_h)]
            lines[-1] = lines[-1][: max(0, len(lines[-1]) - 1)] + "…"
        top = y + (height - len(lines) * line_h) // 2
        for i, line in enumerate(lines):
            d.text((x, top + i * line_h), line, font=font, fill=FG)

    def _readout(self, d, x, y, width, height, s):
        rows = [("HONESTY", self._cfg.honesty), ("HUMOR", self._cfg.humor)]
        row_h = int(70 * s)
        top = y + (height - row_h * len(rows)) // 2
        label_w = int(200 * s)
        for i, (label, value) in enumerate(rows):
            ry = top + i * row_h
            d.text((x, ry), label, font=self._f_big, fill=DIM)
            pct = f"{value}%"
            pw = d.textlength(pct, font=self._f_big)
            d.text((x + width - pw, ry), pct, font=self._f_big, fill=FG)
            bx0, bx1 = x + label_w + int(20 * s), x + width - pw - int(24 * s)
            by0, by1 = ry + int(14 * s), ry + int(38 * s)
            if bx1 - bx0 < 20:
                continue  # too narrow for a bar (e.g. a rotated screen)
            d.rectangle([bx0, by0, bx1, by1], outline=LINE, width=max(1, int(2 * s)))
            fill_to = bx0 + int((bx1 - bx0) * value / 100)
            if fill_to > bx0 + 2:
                d.rectangle([bx0 + 2, by0 + 2, fill_to - 2, by1 - 2], fill=FG)

    def _bars(self, d, now, x, y, width, height):
        n = 32
        gap = max(2, width // (n * 6))
        bw = (width - gap * (n - 1)) / n
        for i in range(n):
            v = 0.25 + 0.75 * abs(math.sin(now * 9 + i * 0.7) * math.sin(now * 4.3 + i * 1.9))
            h = max(2, int(height * v))
            bx = x + i * (bw + gap)
            cy = y + height // 2
            d.rectangle([bx, cy - h // 2, bx + bw, cy + h // 2], fill=FG)
