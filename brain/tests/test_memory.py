import datetime
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import tars_memory as m  # noqa: E402


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "memory.md")

    def tearDown(self):
        self.dir.cleanup()

    def test_remember_recall_forget(self):
        self.assertEqual(m.for_prompt(self.path), "Your notes are empty so far.")
        day = datetime.date(2026, 11, 11)
        self.assertEqual(m.remember("Explored  the workshop;\n hallway not yet", self.path, day), "Noted.")
        self.assertEqual(m.remember("Explored the workshop; hallway not yet", self.path, day), "Already noted.")
        m.remember("The 3D printer is on the left bench", self.path, day)
        self.assertEqual(m.notes(self.path), ["2026-11-11: Explored the workshop; hallway not yet",
                                              "2026-11-11: The 3D printer is on the left bench"])
        self.assertIn("left bench", m.for_prompt(self.path))
        self.assertEqual(m.forget("PRINTER", self.path), ["2026-11-11: The 3D printer is on the left bench"])
        self.assertEqual(m.forget("nothing like this", self.path), [])
        self.assertEqual(len(m.notes(self.path)), 1)
        with open(self.path, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("# TARS's notes"))   # readable in Notepad

    def test_hand_edits_are_respected(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("# my notes\nsome text G typed\n- 2026-01-01: dog is called Max\n")
        self.assertEqual(m.notes(self.path), ["2026-01-01: dog is called Max"])

    def test_limits(self):
        with self.assertRaises(ValueError):
            m.remember("   ", self.path)
        with self.assertRaises(ValueError):
            m.forget("a", self.path)
        m.remember("x" * 1000, self.path)
        self.assertLessEqual(len(m.notes(self.path)[0]), 320)
        for i in range(m.MAX_NOTES + 5):
            m.remember(f"note {i}", self.path)
        self.assertEqual(len(m.notes(self.path)), m.MAX_NOTES)
        self.assertTrue(m.notes(self.path)[-1].endswith(f"note {m.MAX_NOTES + 4}"))
        self.assertLessEqual(len(m.for_prompt(self.path, limit=500)), 600)


if __name__ == "__main__":
    unittest.main()
