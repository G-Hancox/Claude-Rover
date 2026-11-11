"""Who's talking: Claude as itself, or Claude playing TARS. Switchable on the fly."""
import json
import os
import threading

MODES = ("claude", "tars")


class Persona:
    def __init__(self, cfg):
        self._lock = threading.Lock()
        self._file = os.path.expanduser(cfg.persona_file) if cfg.persona_file else None
        self.mode, self.honesty, self.humor = cfg.persona, cfg.honesty, cfg.humor
        self._load()

    def _load(self):
        if not self._file:
            return
        try:
            with open(self._file) as f:
                data = json.load(f)
            self.update(save=False, **{k: data[k] for k in ("mode", "honesty", "humor") if k in data})
        except (OSError, ValueError, TypeError):
            pass

    def update(self, mode=None, honesty=None, humor=None, save=True):
        with self._lock:
            if mode is not None:
                if mode not in MODES:
                    raise ValueError('mode must be "claude" or "tars"')
                self.mode = mode
            for name, value in (("honesty", honesty), ("humor", humor)):
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
                    raise ValueError(f"{name} must be 0 to 100")
                setattr(self, name, int(round(value)))
        if save and self._file:
            try:
                with open(self._file, "w") as f:
                    json.dump(self.to_dict(), f)
            except OSError:
                pass
        return self.to_dict()

    def to_dict(self):
        return {"mode": self.mode, "honesty": self.honesty, "humor": self.humor}
