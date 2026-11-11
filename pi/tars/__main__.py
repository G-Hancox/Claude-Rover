"""Run TARS:  python3 -m tars [--mock] [--config tars.json] [--port 8080]"""
import argparse
import signal
import sys

from . import config as config_mod
from .audio import Mic, MockMic, MockSpeaker, Speaker
from .camera import MockCamera, PiCamera
from .display import Display, Framebuffer, MockFramebuffer
from .legs import Legs
from .pca9685 import PCA9685, MockPCA9685
from .persona import Persona
from .server import make_server


def optional(name, factory):
    """Start an extra. If it fails, say so and carry on without it."""
    try:
        return factory()
    except Exception as e:  # noqa: BLE001 - missing package, loose cable, anything
        print(f"{name} not available, carrying on without it: {e!r}", flush=True)
        return None


def main():
    ap = argparse.ArgumentParser(description="Claude TARS server")
    ap.add_argument("--config", help="JSON file with setting overrides")
    ap.add_argument("--port", type=int)
    ap.add_argument("--mock", action="store_true", help="no hardware; for testing on a PC")
    args = ap.parse_args()

    cfg = config_mod.load(args.config)
    if args.port:
        cfg.port = args.port
    mock = args.mock or cfg.mock
    if mock:
        cfg.positions_file = ""  # don't touch the real robot's saved leg positions
        cfg.persona_file = ""

    pwm = MockPCA9685() if mock else PCA9685(cfg.i2c_bus, cfg.i2c_address, cfg.pwm_freq_hz)
    legs = Legs(pwm, cfg)

    camera = speaker = mic = None
    if cfg.camera_enabled:
        camera = optional("Camera", lambda: MockCamera() if mock else PiCamera(
            cfg.camera_width, cfg.camera_height, cfg.camera_fps, cfg.camera_hflip, cfg.camera_vflip))
    if cfg.speaker_enabled:
        speaker = optional("Speaker", lambda: MockSpeaker(cfg, talk_s=0.3) if mock else Speaker(cfg))
    if cfg.mic_enabled:
        mic = optional("Mic", lambda: MockMic(cfg) if mock else Mic(cfg))

    persona = Persona(cfg)
    heard = listener = None
    if cfg.wake_enabled:
        from .wake import ArecordStream, Detector, Heard, WakeListener, beep_wav
        heard = Heard()   # also takes typed messages from the phone page, mock or not
        if not mock and mic:
            def start_listener():
                def busy():
                    return bool((speaker and speaker.status()["speaking"]) or legs.busy())

                def beep():
                    if speaker:
                        speaker.play_wav(beep_wav())

                lst = WakeListener(ArecordStream(cfg.audio_in_device), Detector(cfg.wake_threshold),
                                   heard, busy=busy, beep=beep)
                mic.before_record, mic.after_record = lst.pause, lst.resume
                lst.start()
                return lst
            listener = optional("Wake word", start_listener)

    display = None
    if cfg.display_enabled:
        def start_display():
            fb = MockFramebuffer() if mock else Framebuffer(cfg.display_device)
            d = Display(fb, cfg, legs=legs, speaker=speaker, mic=mic, persona=persona,
                        listener=listener)
            d.start()
            return d
        display = optional("Screen", start_display)

    server = make_server(legs, cfg.host, cfg.port, camera=camera, speaker=speaker, mic=mic,
                         display=display, heard=heard, persona=persona, listener=listener)

    def quit_(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, quit_)

    def on(x):
        return "on" if x else "off"

    print(f"TARS listening on http://{cfg.host}:{cfg.port}{'  [MOCK]' if mock else ''}\n"
          f"  legs ready (servos limp until the first move) · camera {on(camera)} · "
          f"speaker {on(speaker)} · mic {on(mic)} · screen {on(display)} · "
          f"wake word {on(listener)}{' (mock: type on the phone page instead)' if mock and heard else ''}\n"
          f"  persona: {persona.mode}"
          + (f"\n  voice: {speaker.status()['voice']}" if speaker else ""), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        legs.stop()
        legs.wait(timeout=5)   # let a move finish standing up rather than drop mid-step
        legs.release()
        server.server_close()
        if listener:
            listener.close()
        for part in (display, camera, speaker):
            if part:
                try:
                    part.close()
                except Exception as e:  # noqa: BLE001
                    print(f"Close failed: {e!r}")
        pwm.close()
        print("TARS stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
