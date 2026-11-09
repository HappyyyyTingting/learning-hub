import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = common.load_schema("english")
        self.fixture = common.load_json(ROOT / "daily-english" / "fixture.json")

    def test_fixture_is_valid(self):
        self.assertEqual(common.validate_content(self.fixture, self.schema), [])

    def test_missing_word_is_rejected(self):
        content = copy.deepcopy(self.fixture)
        content["words"] = content["words"][:4]
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("words" in error for error in errors))

    def test_bad_date_is_rejected(self):
        content = copy.deepcopy(self.fixture)
        content["date"] = "2026/11/09"
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("date" in error for error in errors))

    def test_answer_index_out_of_range_is_rejected(self):
        content = copy.deepcopy(self.fixture)
        content["quiz"][0]["answer_index"] = 4
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("answer_index" in error for error in errors))

    def test_unknown_field_is_rejected(self):
        content = copy.deepcopy(self.fixture)
        content["extra"] = "nope"
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("extra" in error for error in errors))

    def test_word_requires_senses(self):
        content = copy.deepcopy(self.fixture)
        del content["words"][0]["senses"]
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("senses" in error for error in errors))

    def test_exam_frequency_must_be_known_label(self):
        content = copy.deepcopy(self.fixture)
        content["words"][0]["exam_frequency"] = "very high"
        errors = common.validate_content(content, self.schema)
        self.assertTrue(any("exam_frequency" in error for error in errors))

    def test_api_schema_strips_unsupported_keywords(self):
        cleaned = common.api_schema(self.schema)
        dumped = json.dumps(cleaned)
        for keyword in ("$schema", "minItems", "maxItems", "pattern"):
            self.assertNotIn(f'"{keyword}"', dumped)
        self.assertIn("properties", dumped)


if __name__ == "__main__":
    unittest.main()
