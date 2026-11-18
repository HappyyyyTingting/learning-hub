import copy
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402
import generate  # noqa: E402


def make_content(
    date_text: str,
    words: list[str],
    review: list[str] | None = None,
    mode: str | None = None,
    review_words: list[str] | None = None,
) -> dict:
    content = {
        "date": date_text,
        "theme": f"theme-{date_text}",
        "words": [{"term": term} for term in words],
        "review": [{"term": term} for term in (review or [])],
    }
    if mode:
        content["mode"] = mode
    if review_words is not None:
        content["review_words"] = [{"term": term} for term in review_words]
    return content


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

    def test_review_words_count_as_reviewed(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content(
                "2026-11-08", [], mode="review", review_words=["alpha"]
            ),
        ]
        candidates = generate.build_review_candidates(contents, self.today)
        self.assertNotIn("alpha", [item["term"] for item in candidates])

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
        self.config = {"level": "IELTS (B2-C1)", "prompt_version": "v2"}

    def test_context_excludes_today_and_dedupes(self):
        contents = [
            make_content("2026-11-07", ["alpha"]),
            make_content("2026-11-08", ["beta"]),
            make_content("2026-11-09", ["today"]),
        ]
        contents[0]["theme"] = "work"
        contents[1]["theme"] = "work"
        context = generate.build_context("english", "2026-11-09", self.config, contents, self.today)
        self.assertEqual(context["recent_words"], ["beta", "alpha"])
        self.assertEqual(context["recent_themes"], ["work"])
        self.assertNotIn("today", context["recent_words"])

    def test_review_candidates_use_history_only(self):
        contents = [
            make_content("2026-11-06", ["alpha"]),
            make_content("2026-11-09", ["today"]),
        ]
        context = generate.build_context("english", "2026-11-09", self.config, contents, self.today)
        self.assertEqual([item["term"] for item in context["review_candidates"]], ["alpha"])

    def test_recent_themes_are_capped(self):
        contents = [
            make_content(f"2026-10-{day:02d}", [f"w{day}"]) for day in range(1, 15)
        ]
        context = generate.build_context("english", "2026-11-09", self.config, contents, self.today)
        self.assertEqual(len(context["recent_themes"]), 7)

    def test_review_context_contains_targets(self):
        contents = [make_content("2026-11-08", ["alpha"])]
        targets = generate.build_review_targets(contents, "2026-11-09")
        context = generate.build_context(
            "english",
            "2026-11-09",
            self.config,
            contents,
            self.today,
            mode="review",
            review_targets=targets,
        )
        self.assertEqual(context["mode"], "review")
        self.assertEqual(context["review_of"], "2026-11-08")
        self.assertEqual(context["theme"], "theme-2026-11-08")
        self.assertEqual(context["review_targets"][0]["term"], "alpha")


class ModeTests(unittest.TestCase):
    def test_first_day_is_lesson(self):
        self.assertEqual(generate.detect_mode([], "2026-11-09"), "lesson")

    def test_lesson_is_followed_by_review(self):
        contents = [make_content("2026-11-08", ["alpha"])]
        self.assertEqual(generate.detect_mode(contents, "2026-11-09"), "review")

    def test_review_is_followed_by_lesson(self):
        contents = [make_content("2026-11-08", [], mode="review")]
        self.assertEqual(generate.detect_mode(contents, "2026-11-09"), "lesson")

    def test_latest_content_decides_mode(self):
        contents = [
            make_content("2026-11-07", ["alpha"]),
            make_content("2026-11-08", [], mode="review"),
        ]
        self.assertEqual(generate.detect_mode(contents, "2026-11-09"), "lesson")

    def test_old_content_without_mode_is_lesson(self):
        contents = [make_content("2026-11-08", ["alpha"])]
        self.assertEqual(common.content_mode(contents[0]), "lesson")

    def test_review_targets_use_latest_lesson(self):
        contents = [
            make_content("2026-11-07", ["alpha"]),
            make_content("2026-11-08", ["beta"]),
            make_content("2026-11-09", [], mode="review", review_words=["beta"]),
        ]
        targets = generate.build_review_targets(contents, "2026-11-10")
        self.assertEqual(targets["review_of"], "2026-11-08")
        self.assertEqual([item["term"] for item in targets["words"]], ["beta"])

    def test_review_targets_skip_review_days(self):
        contents = [
            make_content("2026-11-07", ["alpha"]),
            make_content("2026-11-08", [], mode="review", review_words=["alpha"]),
        ]
        targets = generate.build_review_targets(contents, "2026-11-09")
        self.assertEqual(targets["review_of"], "2026-11-07")
        self.assertEqual([item["term"] for item in targets["words"]], ["alpha"])

    def test_review_targets_include_exam_focus(self):
        contents = [
            {
                "date": "2026-11-08",
                "theme": "science",
                "words": [
                    {
                        "term": "empirical",
                        "exam_focus_zh": "常与 evidence 搭配",
                        "senses": [
                            {
                                "pos": "adj.",
                                "definition_zh": "实证的",
                                "definition_en": "based on evidence",
                            }
                        ],
                        "synonyms": [{"term": "observational", "nuance_zh": "强调观察"}],
                        "collocations": [{"phrase": "empirical evidence"}],
                        "examples": [{"sentence": "The claim lacks empirical evidence."}],
                    }
                ],
            }
        ]
        targets = generate.build_review_targets(contents, "2026-11-09")
        word = targets["words"][0]
        self.assertEqual(word["exam_focus_zh"], "常与 evidence 搭配")
        self.assertEqual(word["senses"][0]["definition_zh"], "实证的")
        self.assertEqual(word["collocations"], ["empirical evidence"])

    def test_no_review_targets_without_previous_lesson(self):
        self.assertIsNone(generate.build_review_targets([], "2026-11-09"))

    def test_review_targets_must_match_generated_words(self):
        targets = {
            "words": [{"term": "alpha"}, {"term": "beta"}],
        }
        good = {"review_words": [{"term": "beta"}, {"term": "alpha"}]}
        bad = {"review_words": [{"term": "alpha"}, {"term": "gamma"}]}
        self.assertEqual(generate.review_target_errors(good, targets), [])
        errors = generate.review_target_errors(bad, targets)
        self.assertTrue(errors)
        self.assertIn("alpha、beta", errors[0])


class ModelJsonTests(unittest.TestCase):
    def test_blank_content_is_rejected(self):
        with self.assertRaises(ValueError):
            generate._parse_json_object("   ")

    def test_non_object_is_rejected(self):
        with self.assertRaises(ValueError):
            generate._parse_json_object("[1, 2]")

    def test_object_is_parsed(self):
        self.assertEqual(generate._parse_json_object('{"a": 1}'), {"a": 1})


class TaskPathTests(unittest.TestCase):
    def test_normalize_task_accepts_directory_name(self):
        self.assertEqual(common.normalize_task("daily-english"), "english")

    def test_task_dir_is_top_level_daily_directory(self):
        self.assertEqual(common.task_dir("english"), ROOT / "daily-english")

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(ValueError):
            common.normalize_task("../english")


if __name__ == "__main__":
    unittest.main()
