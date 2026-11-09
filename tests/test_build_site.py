import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402
import common  # noqa: E402
import render  # noqa: E402


class BuildSiteTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "site_title": "Daily English",
            "site_description": "每天 5 分钟。",
        }
        self.content = common.load_json(ROOT / "tasks" / "english" / "fixture.json")

    def _build(self, contents, limit=0):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        site_dir = Path(temp_dir.name)
        paths = build_site.build_site(contents, site_dir, self.config, limit)
        return site_dir, paths

    def test_builds_index_and_pages(self):
        site_dir, paths = self._build([self.content])
        self.assertTrue((site_dir / "index.html").is_file())
        self.assertTrue((site_dir / "style.css").is_file())
        page = site_dir / f"{self.content['date']}.html"
        self.assertTrue(page.is_file())
        page_text = page.read_text(encoding="utf-8")
        self.assertIn(render._e(self.content["title"]), page_text)
        self.assertIn("今日词汇", page_text)

    def test_index_lists_dates_newest_first(self):
        older = copy.deepcopy(self.content)
        older["date"] = "2026-11-08"
        older["title"] = "Older"
        _, paths = self._build([older, self.content])
        index = paths["index"].read_text(encoding="utf-8")
        self.assertLess(index.index("2026-11-09"), index.index("2026-11-08"))
        self.assertIn("Older", index)

    def test_limit_keeps_recent_pages_only(self):
        older = copy.deepcopy(self.content)
        older["date"] = "2026-11-08"
        site_dir, _ = self._build([older, self.content], limit=1)
        self.assertTrue((site_dir / "2026-11-09.html").is_file())
        self.assertFalse((site_dir / "2026-11-08.html").is_file())

    def test_html_is_escaped(self):
        content = copy.deepcopy(self.content)
        content["title"] = "<script>alert(1)</script>"
        site_dir, _ = self._build([content])
        page_text = (site_dir / f"{content['date']}.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page_text)
        self.assertIn("&lt;script&gt;", page_text)


if __name__ == "__main__":
    unittest.main()
