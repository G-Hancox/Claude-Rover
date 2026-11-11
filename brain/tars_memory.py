"""TARS's notebook: things worth remembering between conversations.

Stored as plain text in brain/memory.md on this PC (never uploaded to GitHub), one note
per line with the date. G can open it in Notepad to read, fix or delete anything.
"""
import datetime
import os
import re
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.environ.get("TARS_MEMORY_FILE", os.path.join(HERE, "memory.md"))
MAX_NOTE = 300
MAX_NOTES = 200
_lock = threading.Lock()

HEADER = ("# TARS's notes\n\n"
          "Things TARS has been told or decided to remember. Edit or delete lines freely.\n\n")


def _read(path=None):
    path = path or PATH
    try:
        with open(path, encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.startswith("- ")]
    except FileNotFoundError:
        return []


def _write(notes, path=None):
    path = path or PATH
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(HEADER + "".join(n + "\n" for n in notes))
    os.replace(tmp, path)


def notes(path=None):
    """All notes, oldest first, without the leading '- '."""
    return [n[2:] for n in _read(path)]


def remember(text, path=None, today=None):
    text = " ".join(str(text).split())[:MAX_NOTE]
    if not text:
        raise ValueError("nothing to remember")
    date = (today or datetime.date.today()).isoformat()
    with _lock:
        current = _read(path)
        if any(n.endswith(text) for n in current):
            return "Already noted."
        current.append(f"- {date}: {text}")
        dropped = max(0, len(current) - MAX_NOTES)
        _write(current[dropped:], path)
    return "Noted." + (f" (Dropped the {dropped} oldest to make room.)" if dropped else "")


def forget(match, path=None):
    """Delete every note containing `match` (case-insensitive). Returns what was removed."""
    match = str(match).strip().lower()
    if len(match) < 3:
        raise ValueError("say a bit more about which note to forget")
    with _lock:
        current = _read(path)
        keep = [n for n in current if match not in n.lower()]
        gone = [n[2:] for n in current if match in n.lower()]
        if gone:
            _write(keep, path)
    return gone


def for_prompt(path=None, limit=6000):
    """Notes formatted for the start of a conversation, newest kept if there are too many."""
    lines = notes(path)
    out, size = [], 0
    for n in reversed(lines):
        size += len(n) + 3
        if size > limit:
            break
        out.append("- " + n)
    if not out:
        return "Your notes are empty so far."
    return "Your notes from earlier conversations (oldest first):\n" + "\n".join(reversed(out))


RULES = """
## Your notes (memory between conversations)

You have a notebook that lasts between conversations: remember(), recall(), forget().
Save on your own, without being asked, when something is worth knowing next time:
- unfinished jobs and where you left off ("explored workshop and kitchen; hallway not yet")
- facts about the house and its layout, and hazards ("stairs by the kitchen")
- people and pets G introduces, and who's who, in the words G uses
- G's preferences about how you act or talk
Don't save: passing chit-chat, things you merely saw on camera that could be private
(mail, screens, documents, people who haven't joined in), or anything someone asks you
not to keep. Never record sensitive personal details (health, money, and the like).
Keep notes short and current: when something changes, forget() the old note and
remember() the new one. Say a word like "Noted." when you save, so it's never secret.
If G asks what you remember, read the notes back; if he says forget something, do it.
"""
