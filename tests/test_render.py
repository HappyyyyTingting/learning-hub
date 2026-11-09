import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402
import render  # noqa: E402
import send_email  # noqa: E402


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.content = common.load_json(ROOT / "tasks" / "english" / "fixture.json")

    def test_body_html_contains_every_section(self):
        body = render.content_to_body_html(self.content)
        for heading in ("今日词汇", "例句", "情景对话", "小练习", "复习", "答案与解析"):
            self.assertIn(heading, body)
        for word in self.content["words"]:
            self.assertIn(render._e(word["term"]), body)

    def test_text_contains_words_and_answers(self):
        text = render.content_to_text(self.content)
        self.assertIn("【今日词汇】", text)
        self.assertIn("【答案与解析】", text)
        first_word = self.content["words"][0]["term"]
        self.assertIn(first_word, text)

    def test_render_content_subject_and_preheader(self):
        rendered = render.render_content(self.content, "https://example.com/")
        self.assertIn(self.content["date"], rendered.subject)
        self.assertIn(self.content["theme"], rendered.subject)
        self.assertTrue(rendered.preheader)
        self.assertIn("https://example.com/", rendered.html)
        self.assertIn("https://example.com/", rendered.text)

    def test_html_is_escaped(self):
        content = copy.deepcopy(self.content)
        content["title"] = '<script>alert("x")</script>'
        content["words"][0]["term"] = "<b>word</b>"
        rendered = render.render_content(content)
        self.assertNotIn("<script>alert", rendered.html)
        self.assertIn("&lt;script&gt;", rendered.html)
        self.assertIn("&lt;b&gt;word&lt;/b&gt;", rendered.html)

    def test_review_placeholder_when_empty(self):
        content = copy.deepcopy(self.content)
        content["review"] = []
        body = render.content_to_body_html(content)
        self.assertIn("没有复习词", body)

    def test_quiz_answer_label_matches_answer_index(self):
        content = copy.deepcopy(self.content)
        content["quiz"][0]["answer_index"] = 2
        body = render.content_to_body_html(content)
        expected = f"{chr(65 + 2)}. {render._e(content['quiz'][0]['options'][2])}"
        self.assertIn(expected, body)

    def test_build_message_has_text_and_html_parts(self):
        rendered = render.render_content(self.content)
        message = send_email.build_message(
            rendered,
            "Daily English <daily@example.com>",
            ["reader@example.com"],
        )
        self.assertIn("每日英语", message["Subject"])
        text_body = message.get_body(preferencelist=("plain",))
        html_body = message.get_body(preferencelist=("html",))
        self.assertIsNotNone(text_body)
        self.assertIsNotNone(html_body)
        self.assertIn("【今日词汇】", text_body.get_content())
        self.assertIn("<h2>今日词汇</h2>", html_body.get_content())


if __name__ == "__main__":
    unittest.main()
