"""Run the rover:  python3 -m rover [--mock] [--config rover.json] [--port 8080]"""
import argparse
import signal
import sys

from . import config as config_mod
from .camera import MockCamera, PiCamera
from .drive import Drive
from .pca9685 import PCA9685, MockPCA9685
from .server import make_server


def main():
    ap = argparse.ArgumentParser(description="Claude Rover drive server")
    ap.add_argument("--config", help="JSON file with setting overrides")
    ap.add_argument("--port", type=int)
    ap.add_argument("--mock", action="store_true", help="no hardware; for testing on a PC")
    args = ap.parse_args()

    cfg = config_mod.load(args.config)
    if args.port:
        cfg.port = args.port

    if args.mock:
        pwm = MockPCA9685()
    else:
        pwm = PCA9685(cfg.i2c_bus, cfg.i2c_address, cfg.pwm_freq_hz)

    drive = Drive(pwm, cfg)
    drive.start()

    # A camera problem must never stop the rover from driving (or stopping).
    camera = None
    if cfg.camera_enabled:
        try:
            if args.mock:
                camera = MockCamera()
            else:
                camera = PiCamera(cfg.camera_width, cfg.camera_height, cfg.camera_fps,
                                  cfg.camera_hflip, cfg.camera_vflip)
        except Exception as e:  # noqa: BLE001 - anything from a missing package to a loose ribbon
            print(f"Camera not available, driving without it: {e!r}", flush=True)

    server = make_server(drive, cfg.host, cfg.port, camera=camera)

    def quit_(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, quit_)
    print(f"Rover listening on http://{cfg.host}:{cfg.port}"
          f"  (speed cap: {cfg.max_forward:.0%} forward, {cfg.max_reverse:.0%} reverse)"
          f"  camera: {'on' if camera else 'off'}"
          f"{'  [MOCK]' if args.mock else ''}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        drive.shutdown()  # leaves throttle at neutral, steering centred
        server.server_close()
        if camera:
            try:
                camera.close()
            except Exception as e:  # noqa: BLE001
                print(f"Camera close failed: {e!r}")
        pwm.close()
        print("Rover stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
