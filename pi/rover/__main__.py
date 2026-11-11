"""Run the rover:  python3 -m rover [--mock] [--config rover.json] [--port 8080]"""
import argparse
import signal
import sys

from . import config as config_mod
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
    server = make_server(drive, cfg.host, cfg.port)

    def quit_(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, quit_)
    print(f"Rover listening on http://{cfg.host}:{cfg.port}"
          f"  (speed cap: {cfg.max_forward:.0%} forward, {cfg.max_reverse:.0%} reverse)"
          f"{'  [MOCK]' if args.mock else ''}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        drive.shutdown()  # leaves throttle at neutral, steering centred
        server.server_close()
        pwm.close()
        print("Rover stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
