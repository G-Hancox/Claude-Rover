"""TARS move library (legs only, no arms).

Keyframes adapted from TARS-AI V3 `src/modules/module_movements.py`
(https://github.com/TARS-AI-Community/TARS-AI) by Charles-Olivier Dion (AtomikSpace),
building on Charlie Diaz's original TARS replica. That file is licensed CC-BY-NC 4.0,
so this file is too: free for personal, non-commercial use with attribution.
"Contains contributions by Charles-Olivier Dion (AtomikSpace)."

Each step is either:
  (left_height, right_height, left_leg, right_leg, speed)
      positions are percentages 1-100 of each joint's calibrated range, or None to
      leave that joint where it is. Height 1 = up limit, 100 = down limit.
      Leg 1 = forward limit, 100 = back limit. speed is 0-1, higher is faster.
  ("pause", seconds)

Every move starts and ends in the standing position (all 50).
"""

STANCE = (50, 50, 50, 50)


def _walk_forward():
    cycle = [(40, 70, 50, 50), (40, 70, 35, 50), (50, 50, 35, 50),
             (70, 40, 50, 50), (70, 40, 50, 35), (50, 50, 50, 35)]
    steps = [(50, 50, 50, 50, 0.8)]
    steps += [(*k, 0.5) for k in cycle * 2]
    steps += [(*k, 0.5) for k in cycle[:3]]
    steps += [(70, 40, 35, 50, 0.5), (70, 40, 50, 50, 0.5), (50, 50, 50, 50, 0.8)]
    return steps


def _turn(direction, slow):
    if slow:
        if direction == "right":
            return [(50, 50, 50, 50, 0.9), (40, 70, 50, 50, 0.7), (40, 70, 40, 50, 0.7),
                    (70, 50, 40, 50, 0.7), (70, 50, 50, 50, 0.7), (50, 50, 50, 50, 0.9)]
        return [(50, 50, 50, 50, 0.9), (70, 40, 50, 50, 0.7), (70, 40, 50, 40, 0.7),
                (50, 70, 50, 40, 0.7), (50, 70, 50, 50, 0.7), (50, 50, 50, 50, 0.9)]
    legs = (65, 35) if direction == "right" else (35, 65)
    return [(50, 50, 50, 50, 0.9), (70, 70, 50, 50, 0.9), (70, 70, *legs, 0.9),
            (45, 45, *legs, 0.9), (52, 52, 50, 50, 0.8), (50, 50, 50, 50, 0.8)]


MOVES = {
    "step_forward": {
        "about": "One step forward.",
        "steps": [(50, 50, 50, 50, 0.9), (42, 42, 40, 40, 0.9), (70, 70, 23, 23, 0.9),
                  (30, 30, 30, 30, 0.8), (70, 70, 35, 35, 0.9), (60, 60, 50, 50, 0.9),
                  (50, 50, 50, 50, 0.9)],
    },
    "step_backward": {
        "about": "One step backward.",
        "steps": [(50, 50, 50, 50, 0.9), (30, 30, 55, 55, 0.8), (68, 68, 82, 82, 0.8),
                  (30, 30, 70, 70, 0.8), (50, 50, 62, 62, 0.9), (65, 65, 50, 50, 0.9),
                  (50, 50, 50, 50, 0.9)],
    },
    "walk_forward": {
        "about": "Shuffle forward a few small steps, one leg at a time. Gentler than step_forward.",
        "steps": _walk_forward(),
    },
    "turn_left": {"about": "Turn left a little.", "steps": _turn("left", False)},
    "turn_right": {"about": "Turn right a little.", "steps": _turn("right", False)},
    "turn_left_slow": {"about": "Turn left gently, one leg at a time.", "steps": _turn("left", True)},
    "turn_right_slow": {"about": "Turn right gently, one leg at a time.", "steps": _turn("right", True)},
    "stand": {
        "about": "Settle into the standing position.",
        "steps": [(90, 90, None, None, 0.8), (90, 90, 50, 50, 0.8), (50, 50, 50, 50, 0.8)],
    },
    "pose": {
        "about": "Strike a pose for 3 seconds.",
        "steps": [(50, 50, 50, 50, 0.6), (30, 30, 40, 40, 0.6), (80, 80, 30, 30, 0.6), ("pause", 3),
                  (80, 80, 30, 30, 0.8), (30, 30, 30, 30, 0.8), (30, 30, 40, 40, 0.6),
                  (50, 50, 50, 50, 0.6)],
    },
    "bow": {
        "about": "Bow, hold it, and come back up.",
        "steps": [(50, 50, 50, 50, 0.4), (15, 15, 50, 50, 0.7), (15, 15, 70, 70, 0.7),
                  (60, 60, 70, 70, 0.7), (95, 95, 65, 65, 0.7), ("pause", 3),
                  (15, 15, 65, 65, 0.7), (50, 50, 50, 50, 0.4)],
    },
    "tilt_left": {
        "about": "Lean to the left for 3 seconds, like tilting your head.",
        "steps": [(50, 50, 50, 50, 0.9), (80, 20, 50, 50, 0.9), ("pause", 3), (50, 50, 50, 50, 0.9)],
    },
    "tilt_right": {
        "about": "Lean to the right for 3 seconds.",
        "steps": [(50, 50, 50, 50, 0.9), (20, 80, 50, 50, 0.9), ("pause", 3), (50, 50, 50, 50, 0.9)],
    },
    "side_side": {
        "about": "Rock side to side a few times.",
        "steps": [(50, 50, 50, 50, 0.8)] + [(10, 90, 50, 50, 0.9), (90, 10, 50, 50, 0.9)] * 3
                 + [(50, 50, 50, 50, 0.9)],
    },
    "laugh": {
        "about": "Bounce up and down, TARS's laugh.",
        "steps": [s for _ in range(5) for s in ((50, 50, 50, 50, 1.0), ("pause", 0.1),
                                                 (1, 1, 50, 50, 1.0), ("pause", 0.1))]
                 + [(50, 50, 50, 50, 1.0), ("pause", 0.2)],
    },
    "excited": {
        "about": "Wiggle excitedly.",
        "steps": [(50, 50, 50, 50, 0.9)] + [(40, 60, 45, 50, 0.95), (60, 40, 50, 45, 0.95)] * 4
                 + [(50, 50, 50, 50, 0.9)],
    },
    "swing_legs": {
        "about": "Lift up and swing both legs back and forth.",
        "steps": [(50, 50, 50, 50, 1.0), ("pause", 0.1), (100, 100, 50, 50, 1.0), ("pause", 0.1)]
                 + [s for _ in range(3) for s in ((None, None, 20, 80, 0.6), ("pause", 0.1),
                                                   (None, None, 80, 20, 0.6), ("pause", 0.1))]
                 + [(None, None, 50, 50, 0.6), ("pause", 0.1), (50, 50, 50, 50, 0.7), ("pause", 0.2)],
    },
}

# Moves that change where the robot is (the rest are on the spot).
TRAVEL = {"step_forward", "step_backward", "walk_forward",
          "turn_left", "turn_right", "turn_left_slow", "turn_right_slow"}


def check():
    """Sanity-check the table. Raises ValueError on a malformed step."""
    for name, move in MOVES.items():
        steps = move["steps"]
        legs = [s for s in steps if s[0] != "pause"]
        if not legs or tuple(legs[-1][:4]) != STANCE:
            raise ValueError(f"{name} must end standing")
        for s in steps:
            if s[0] == "pause":
                if len(s) != 2 or not 0 <= s[1] <= 5:
                    raise ValueError(f"{name}: bad pause {s}")
                continue
            if len(s) != 5 or not 0 < s[4] <= 1:
                raise ValueError(f"{name}: bad step {s}")
            for p in s[:4]:
                if p is not None and not 1 <= p <= 100:
                    raise ValueError(f"{name}: position out of range in {s}")


check()
