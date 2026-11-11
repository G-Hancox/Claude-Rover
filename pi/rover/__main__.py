"""Run the rover:  python3 -m rover [--mock] [--config rover.json] [--port 8080]"""
import argparse
import signal
import sys

from . import config as config_mod
from .audio import Mic, MockMic, MockSpeaker, Speaker
from .camera import MockCamera, PiCamera
from .distance import Guard, MockSensor, make_sensor
from .drive import Drive
from .head import Head
from .pca9685 import PCA9685, MockPCA9685
from .server import make_server


def optional(name, factory):
    """Start an extra. If it fails, say so and carry on: extras must never stop driving."""
    try:
        return factory()
    except Exception as e:  # noqa: BLE001 - missing package, loose cable, anything
        print(f"{name} not available, carrying on without it: {e!r}", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser(description="Claude Rover server")
    ap.add_argument("--config", help="JSON file with setting overrides")
    ap.add_argument("--port", type=int)
    ap.add_argument("--mock", action="store_true", help="no hardware; for testing on a PC")
    args = ap.parse_args()

    cfg = config_mod.load(args.config)
    if args.port:
        cfg.port = args.port
    mock = args.mock

    pwm = MockPCA9685() if mock else PCA9685(cfg.i2c_bus, cfg.i2c_address, cfg.pwm_freq_hz)
    drive = Drive(pwm, cfg)
    drive.start()

    head = camera = speaker = mic = guard = None

    if cfg.head_enabled:
        head = Head(pwm, cfg)
        head.start()

    if cfg.camera_enabled:
        camera = optional("Camera", lambda: MockCamera() if mock else PiCamera(
            cfg.camera_width, cfg.camera_height, cfg.camera_fps, cfg.camera_hflip, cfg.camera_vflip))

    if cfg.speaker_enabled:
        speaker = optional("Speaker", lambda: MockSpeaker(cfg) if mock else Speaker(cfg))
    if cfg.mic_enabled:
        mic = optional("Mic", lambda: MockMic(cfg) if mock else Mic(cfg))

    if cfg.distance_sensor != "none" or mock:
        sensor = optional("Distance sensor", lambda: MockSensor() if mock else make_sensor(cfg))
        if sensor:
            guard = Guard(sensor, drive, cfg)
            guard.start()
        elif not mock:
            # A sensor was asked for and isn't working: don't drive forward blind.
            drive.set_forward_blocked(True)
            print("Forward driving is BLOCKED until the distance sensor works "
                  '(or set "distance_sensor": "none").', flush=True)

    server = make_server(drive, cfg.host, cfg.port, camera=camera, head=head,
                         speaker=speaker, mic=mic, guard=guard)

    def quit_(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, quit_)

    def on(x):
        return "on" if x else "off"

    print(f"Rover listening on http://{cfg.host}:{cfg.port}{'  [MOCK]' if mock else ''}\n"
          f"  speed cap: {cfg.max_forward:.0%} forward, {cfg.max_reverse:.0%} reverse\n"
          f"  camera {on(camera)} · pan/tilt {on(head)} · speaker {on(speaker)} · "
          f"mic {on(mic)} · distance sensor {on(guard)}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if guard:
            guard.shutdown()
        drive.shutdown()  # leaves throttle at neutral, steering centred
        if head:
            head.shutdown()
        server.server_close()
        for part in (camera, speaker):
            if part:
                try:
                    part.close()
                except Exception as e:  # noqa: BLE001
                    print(f"Close failed: {e!r}")
        pwm.close()
        print("Rover stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
