import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_audio  # noqa: E402


class SegmentGroupTests(unittest.TestCase):
    def test_merges_consecutive_same_language(self):
        groups = make_audio.group_segments(
            [("zh", "第一个词。"), ("zh", "形容词。"), ("en", "float."), ("zh", "翻译。")]
        )
        self.assertEqual(
            groups,
            [("zh", "第一个词。 形容词。"), ("en", "float."), ("zh", "翻译。")],
        )

    def test_drops_blank_segments(self):
        self.assertEqual(make_audio.group_segments([("zh", "  "), ("en", "")]), [])


class PruneTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.audio_dir = Path(temp_dir.name)

    def _touch(self, name: str) -> Path:
        path = self.audio_dir / name
        path.write_bytes(b"mp3")
        return path

    def test_removes_only_audio_older_than_retention(self):
        old = self._touch("2026-11-01.mp3")
        edge = self._touch("2026-11-12.mp3")
        recent = self._touch("2026-11-19.mp3")
        note = self._touch("notes.txt")

        removed = make_audio.prune_audio(self.audio_dir, 7, date(2026, 11, 19))

        self.assertEqual(removed, ["2026-11-01.mp3"])
        self.assertFalse(old.exists())
        self.assertTrue(edge.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(note.exists())

    def test_keeps_everything_when_retention_disabled(self):
        path = self._touch("2026-01-01.mp3")
        self.assertEqual(make_audio.prune_audio(self.audio_dir, 0, date(2026, 11, 19)), [])
        self.assertTrue(path.exists())

    def test_missing_directory_is_not_an_error(self):
        self.assertEqual(
            make_audio.prune_audio(self.audio_dir / "missing", 7, date(2026, 11, 19)),
            [],
        )


if __name__ == "__main__":
    unittest.main()
