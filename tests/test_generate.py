import copy
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate  # noqa: E402


def make_content(date_text: str, words: list[str], review: list[str] | None = None) -> dict:
    return {
        "date": date_text,
        "theme": f"theme-{date_text}",
        "words": [{"term": term} for term in words],
        "review": [{"term": term} for term in (review or [])],
    }


class ReviewCandidateTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 9)

    def test_picks_words_first_seen_on_3_7_14_days(self):
        contents = [
            make_content("2026-11-06", ["three-days"]),
            make_content("2026-11-02", ["seven-days"]),
            make_content("2026-10-26", ["fourteen-days"]),
            make_content("2026-11-08", ["yesterday"]),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        terms = {item["term"]: item["days_since_first_seen"] for item in candidates}
        self.assertEqual(terms["three-days"], 3)
        self.assertEqual(terms["seven-days"], 7)
        self.assertEqual(terms["fourteen-days"], 14)
        self.assertNotIn("yesterday", terms)

    def test_recently_reviewed_word_is_skipped(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content("2026-11-08", [], review=["alpha"]),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        self.assertNotIn("alpha", [item["term"] for item in candidates])

    def test_word_reviewed_long_ago_is_kept(self):
        contents = [
            make_content("2026-11-02", ["alpha"]),
            make_content("2026-11-04", [], review=["alpha"]),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        terms = [item["term"] for item in candidates]
        self.assertIn("alpha", terms)

    def test_first_seen_is_earliest_occurrence(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content("2026-11-08", ["alpha"]),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        item = next(item for item in candidates if item["term"] == "alpha")
        self.assertEqual(item["first_seen"], "2026-11-06")

    def test_duplicates_are_collapsed(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content("2026-11-06", ["alpha"]),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        self.assertEqual(len([item for item in candidates if item["term"] == "alpha"]), 1)

    def test_candidates_are_capped(self):
        contents = [make_content("2026-11-06", [f"word-{index:02d}" for index in range(20)])]
        candidates = generate.build_review_candidates(contents, self.today)
        self.assertLessEqual(len(candidates), 10)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 9)
        self.config = {"level": "B1-B2", "prompt_version": "v1"}

    def test_context_excludes_today_and_dedupes(self):
        contents = [
            make_content("2026-11-07", ["alpha"]),
            make_content("2026-11-08", ["beta"]),
            make_content("2026-11-09", ["today"]),
        ]
        contents[0]["theme"] = "work"
        contents[1]["theme"] = "work"
        context = generate.build_context("2026-11-09", self.config, contents, self.today)
        self.assertEqual(context["recent_words"], ["beta", "alpha"])
        self.assertEqual(context["recent_themes"], ["work"])
        self.assertNotIn("today", context["recent_words"])

    def test_review_candidates_use_history_only(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content("2026-11-09", ["today"]),
        ]
        context = generate.build_context("2026-11-09", self.config, contents, self.today)
        self.assertEqual([item["term"] for item in context["review_candidates"]], ["alpha"])

    def test_recent_themes_are_capped(self):
        contents = [
            make_content(f"2026-10-{day:02d}", [f"w{day}"]) for day in range(1, 15)
        ]
        context = generate.build_context("2026-11-09", self.config, contents, self.today)
        self.assertEqual(len(context["recent_themes"]), 7)


if __name__ == "__main__":
    unittest.main()
