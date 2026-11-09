#!/usr/bin/env python3
"""Render Daily English content as email HTML/text and web body HTML.

Task-specific renderer: the shared email shell lives in ``scripts/email_layout.py``.
"""

from __future__ import annotations

import email_layout

_e = email_layout.escape

FREQUENCY_LABELS = {"high": "高频", "medium": "中频", "low": "低频"}


def _word_html(word: dict) -> str:
    freq = str(word.get("exam_frequency", "")).strip()
    freq_label = FREQUENCY_LABELS.get(freq, freq)
    freq_html = (
        f'<span class="freq freq-{_e(freq)}">{_e(freq_label)}</span>' if freq else ""
    )

    senses = "".join(
        f'<div class="sense">'
        f'<span class="pos">{_e(item.get("pos"))}</span>'
        f'<span class="definition-zh">{_e(item.get("definition_zh"))}</span>'
        f'<div class="definition-en">{_e(item.get("definition_en"))}</div>'
        f"</div>"
        for item in word.get("senses", [])
    )

    synonyms = "".join(
        f'<div class="synonym">'
        f'<div class="syn-head"><span class="syn-term">{_e(item.get("term"))}</span>'
        f'<span class="syn-pos">{_e(item.get("pos"))}</span>'
        f'<span class="syn-def">{_e(item.get("definition_zh"))}</span></div>'
        f'<div class="nuance">{_e(item.get("nuance_zh"))}</div>'
        f'<div class="collocation">{_e(item.get("collocation"))}</div>'
        f"</div>"
        for item in word.get("synonyms", [])
    )
    synonyms_block = (
        f'<div class="word-block"><div class="block-title">同义替换</div>{synonyms}</div>'
        if synonyms
        else ""
    )

    collocations = "".join(
        f'<li><strong>{_e(item.get("phrase"))}</strong> — {_e(item.get("meaning_zh"))}</li>'
        for item in word.get("collocations", [])
    )
    collocations_block = (
        f'<div class="word-block"><div class="block-title">高频搭配</div>'
        f'<ul class="collocations">{collocations}</ul></div>'
        if collocations
        else ""
    )

    forms = "".join(
        f'<li><strong>{_e(item.get("form"))}</strong> {_e(item.get("pos"))} — '
        f'{_e(item.get("meaning_zh"))}</li>'
        for item in word.get("word_forms", [])
    )
    forms_block = (
        f'<div class="word-block"><div class="block-title">词形变化</div>'
        f'<ul class="word-forms">{forms}</ul></div>'
        if forms
        else ""
    )

    examples = "".join(
        f'<div class="example-item">'
        f'<div class="example">{_e(item.get("sentence"))}</div>'
        f'<div class="translation">{_e(item.get("translation_zh"))}</div>'
        f'<div class="note">{_e(item.get("note_zh"))}</div>'
        f"</div>"
        for item in word.get("examples", [])
    )
    examples_block = (
        f'<div class="word-block"><div class="block-title">雅思风格例句</div>{examples}</div>'
        if examples
        else ""
    )

    return f"""
    <div class="word-card">
      <div class="word-head">
        <span class="term">{_e(word.get("term"))}</span>
        <span class="ipa">美 {_e(word.get("ipa_us"))} · 英 {_e(word.get("ipa_uk"))}</span>
        {freq_html}
      </div>
      <div class="exam-focus">考点：{_e(word.get("exam_focus_zh"))}</div>
      <div class="senses">{senses}</div>
      {synonyms_block}
      {collocations_block}
      {forms_block}
      {examples_block}
    </div>
    """


def content_to_body_html(content: dict) -> str:
    words = "".join(_word_html(word) for word in content.get("words", []))

    dialogue = "".join(
        f'<div class="line"><span class="speaker">{_e(item.get("speaker"))}</span>'
        f'<span class="say">{_e(item.get("text"))}</span></div>'
        for item in content.get("dialogue", [])
    )

    quiz_parts = []
    for index, item in enumerate(content.get("quiz", []), start=1):
        options = "".join(
            f'<li><span class="option-label">{chr(64 + option_index)}.</span> {_e(option)}</li>'
            for option_index, option in enumerate(item.get("options", []), start=1)
        )
        quiz_parts.append(
            f'<div class="quiz-item">'
            f'<div class="question">{index}. {_e(item.get("question"))}</div>'
            f'<ul class="options">{options}</ul>'
            f"</div>"
        )

    review_parts = []
    for index, item in enumerate(content.get("review", []), start=1):
        review_parts.append(
            f'<div class="review-item">'
            f'<div class="question">{index}. {_e(item.get("question"))}</div>'
            f'<div class="review-term">复习词：{_e(item.get("term"))}</div>'
            f"</div>"
        )
    review_html = "".join(review_parts) or '<p class="muted">今天是第一天，没有复习词。</p>'

    answers = []
    for index, item in enumerate(content.get("quiz", []), start=1):
        answer_index = item.get("answer_index", -1)
        options = item.get("options", [])
        if isinstance(answer_index, int) and 0 <= answer_index < len(options):
            label = chr(65 + answer_index)
            answer_text = f"{label}. {_e(options[answer_index])}"
        else:
            answer_text = "答案缺失"
        answers.append(
            f"<p><strong>练习 {index}：</strong>{answer_text}<br>"
            f'<span class="muted">{_e(item.get("explanation_zh"))}</span></p>'
        )
    for index, item in enumerate(content.get("review", []), start=1):
        answers.append(
            f"<p><strong>复习 {index}（{_e(item.get('term'))}）：</strong>"
            f'{_e(item.get("answer"))}</p>'
        )

    return f"""
<h2>今日词汇</h2>
{words}
<h2>情景对话</h2>
<div class="dialogue">{dialogue}</div>
<h2>小练习</h2>
{''.join(quiz_parts)}
<h2>复习</h2>
{review_html}
<h2>答案与解析</h2>
<div class="answers">{''.join(answers)}</div>
"""


def content_to_text(content: dict, name: str = "每日英语") -> str:
    lines = [
        f"{name} · {content.get('date', '')} · {content.get('theme', '')}",
        str(content.get("title", "")),
        "",
        "【今日词汇】",
    ]
    for index, word in enumerate(content.get("words", []), start=1):
        freq = FREQUENCY_LABELS.get(str(word.get("exam_frequency", "")), "")
        header = (
            f"{index}. {word.get('term', '')}  美 {word.get('ipa_us', '')} · "
            f"英 {word.get('ipa_uk', '')}"
        )
        if freq:
            header += f"  [{freq}]"
        lines.append(header)
        lines.append(f"   考点：{word.get('exam_focus_zh', '')}")
        for sense in word.get("senses", []):
            lines.append(
                f"   {sense.get('pos', '')} {sense.get('definition_zh', '')}"
            )
            lines.append(f"      {sense.get('definition_en', '')}")

        synonyms = word.get("synonyms", [])
        if synonyms:
            lines.append("   同义替换：")
            for item in synonyms:
                lines.append(
                    f"     - {item.get('term', '')} {item.get('pos', '')} "
                    f"{item.get('definition_zh', '')}"
                )
                lines.append(f"       辨析：{item.get('nuance_zh', '')}")
                lines.append(f"       搭配：{item.get('collocation', '')}")

        collocations = word.get("collocations", [])
        if collocations:
            lines.append("   高频搭配：")
            for item in collocations:
                lines.append(
                    f"     - {item.get('phrase', '')}：{item.get('meaning_zh', '')}"
                )

        forms = word.get("word_forms", [])
        if forms:
            lines.append("   词形变化：")
            for item in forms:
                lines.append(
                    f"     - {item.get('form', '')} {item.get('pos', '')}："
                    f"{item.get('meaning_zh', '')}"
                )

        examples = word.get("examples", [])
        if examples:
            lines.append("   雅思风格例句：")
            for item in examples:
                lines.append(f"     - {item.get('sentence', '')}")
                lines.append(f"       {item.get('translation_zh', '')}")
                lines.append(f"       考点：{item.get('note_zh', '')}")
        lines.append("")

    lines.append("【情景对话】")
    for item in content.get("dialogue", []):
        lines.append(f"{item.get('speaker', '')}: {item.get('text', '')}")
    lines.append("")

    lines.append("【小练习】")
    for index, item in enumerate(content.get("quiz", []), start=1):
        lines.append(f"{index}. {item.get('question', '')}")
        for option_index, option in enumerate(item.get("options", [])):
            lines.append(f"   {chr(65 + option_index)}. {option}")
        lines.append("")

    lines.append("【复习】")
    reviews = content.get("review", [])
    if reviews:
        for index, item in enumerate(reviews, start=1):
            lines.append(f"{index}. {item.get('question', '')}")
            lines.append(f"   （复习词：{item.get('term', '')}）")
    else:
        lines.append("今天是第一天，没有复习词。")
    lines.append("")

    lines.append("【答案与解析】")
    for index, item in enumerate(content.get("quiz", []), start=1):
        answer_index = item.get("answer_index", -1)
        options = item.get("options", [])
        if isinstance(answer_index, int) and 0 <= answer_index < len(options):
            lines.append(f"练习 {index}：{chr(65 + answer_index)}. {options[answer_index]}")
        else:
            lines.append(f"练习 {index}：答案缺失")
        lines.append(f"   {item.get('explanation_zh', '')}")
    for index, item in enumerate(reviews, start=1):
        lines.append(
            f"复习 {index}（{item.get('term', '')}）：{item.get('answer', '')}"
        )

    return "\n".join(lines).strip() + "\n"


EMAIL_CSS = """
    .email-body .word-card {
      margin: 0 0 14px; padding: 14px 16px; background: #f8fafc;
      border-left: 4px solid #0b6bcb; border-radius: 0 10px 10px 0;
    }
    .email-body .word-head { margin-bottom: 4px; }
    .email-body .term { font-size: 18px; font-weight: 700; color: #0b4f91; }
    .email-body .ipa { margin-left: 8px; color: #667085; font-size: 14px; }
    .email-body .pos {
      margin-left: 8px; padding: 1px 7px; background: #e8f1fb;
      color: #0b5cad; border-radius: 999px; font-size: 12px;
    }
    .email-body .definition-en { color: #1f2328; }
    .email-body .definition-zh { color: #44505f; font-size: 14px; }
    .email-body .exam-focus {
      margin: 6px 0 10px; padding: 8px 10px; background: #f4f8fd;
      border-radius: 8px; color: #44505f; font-size: 14px;
    }
    .email-body .freq {
      margin-left: 8px; padding: 1px 7px; border-radius: 999px;
      font-size: 12px; font-weight: 700;
    }
    .email-body .freq-high { background: #e6f4ea; color: #1e7b3c; }
    .email-body .freq-medium { background: #fff4e5; color: #a15c00; }
    .email-body .freq-low { background: #eef1f4; color: #667085; }
    .email-body .senses { margin: 8px 0 10px; }
    .email-body .sense { margin: 0 0 8px; }
    .email-body .sense .pos { margin-left: 0; }
    .email-body .word-block { margin: 12px 0 0; }
    .email-body .block-title {
      margin-bottom: 6px; color: #0b4f91; font-size: 14px; font-weight: 700;
    }
    .email-body .synonym {
      margin: 0 0 8px; padding: 10px 12px; background: #f8fafc; border-radius: 8px;
    }
    .email-body .syn-head { margin-bottom: 4px; }
    .email-body .syn-term { color: #0b4f91; font-weight: 700; }
    .email-body .syn-pos { margin-left: 6px; color: #667085; font-size: 13px; }
    .email-body .syn-def { margin-left: 6px; color: #1f2328; }
    .email-body .nuance { color: #44505f; font-size: 14px; }
    .email-body .collocation { color: #0a7ea4; font-size: 14px; }
    .email-body .collocations, .email-body .word-forms {
      margin: 0; padding-left: 20px;
    }
    .email-body .example-item { margin: 0 0 10px; }
    .email-body .example { margin-top: 0; color: #0b5cad; font-style: italic; }
    .email-body .translation { color: #44505f; font-size: 14px; }
    .email-body .note { color: #667085; font-size: 13px; }
    .email-body .dialogue { margin: 0 0 16px; }
    .email-body .line { margin: 0 0 10px; }
    .email-body .speaker {
      display: inline-block; min-width: 26px; font-weight: 700; color: #0b4f91;
    }
    .email-body .say { color: #1f2328; }
    .email-body .quiz-item, .email-body .review-item {
      margin: 0 0 18px; padding: 12px 14px; background: #f8fafc; border-radius: 10px;
    }
    .email-body .question { font-weight: 600; margin-bottom: 6px; }
    .email-body .options { margin: 0; }
    .email-body .option-label { font-weight: 700; color: #0b5cad; }
    .email-body .review-term { color: #667085; font-size: 13px; }
    .email-body .answers {
      margin: 0 0 8px; padding: 14px 16px; background: #f4f8fd; border-radius: 10px;
    }
    .email-body .answers p { margin: 0 0 10px; }
"""


SITE_CSS = """
:root {
  color-scheme: light;
  --bg: #f2f5f8;
  --surface: #ffffff;
  --ink: #1f2328;
  --muted: #667085;
  --line: #e1e7ed;
  --brand: #0b5cad;
  --brand-soft: #e8f1fb;
  --accent: #0a7ea4;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 16px;
  line-height: 1.75;
  overflow-wrap: anywhere;
}
a { color: var(--brand); }
.container { width: min(100% - 32px, 720px); margin: 0 auto; padding: 28px 0 48px; }
.site-header { margin-bottom: 22px; }
.site-header .brand {
  display: inline-block; font-size: 24px; font-weight: 800; color: var(--brand);
  text-decoration: none; letter-spacing: -0.3px;
}
.site-header .tagline { margin: 4px 0 0; color: var(--muted); font-size: 14px; }
.card {
  background: var(--surface); border: 1px solid var(--line); border-radius: 16px;
  padding: 30px 32px; box-shadow: 0 8px 24px rgba(15, 35, 60, 0.04);
}
.card h1 { margin: 0 0 6px; font-size: 28px; line-height: 1.35; }
.meta { margin: 0 0 10px; color: var(--muted); font-size: 14px; }
.content h2 {
  font-size: 19px; line-height: 1.45; margin: 30px 0 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--line);
}
.content p { margin: 0 0 14px; }
.content ul { margin: 0 0 16px; padding-left: 22px; }
.content li { margin: 0 0 8px; }
.word-card {
  margin: 0 0 14px; padding: 14px 16px; background: #f8fafc;
  border-left: 4px solid var(--brand); border-radius: 0 10px 10px 0;
}
.word-head { margin-bottom: 4px; }
.term { font-size: 18px; font-weight: 700; color: #0b4f91; }
.ipa { margin-left: 8px; color: var(--muted); font-size: 14px; }
.pos {
  margin-left: 8px; padding: 1px 7px; background: var(--brand-soft);
  color: var(--brand); border-radius: 999px; font-size: 12px;
}
.definition-zh { color: #44505f; font-size: 14px; }
.example { margin-top: 6px; color: var(--brand); font-style: italic; }
.exam-focus {
  margin: 6px 0 10px; padding: 8px 10px; background: #f4f8fd;
  border-radius: 8px; color: #44505f; font-size: 14px;
}
.freq {
  margin-left: 8px; padding: 1px 7px; border-radius: 999px;
  font-size: 12px; font-weight: 700;
}
.freq-high { background: #e6f4ea; color: #1e7b3c; }
.freq-medium { background: #fff4e5; color: #a15c00; }
.freq-low { background: #eef1f4; color: #667085; }
.senses { margin: 8px 0 10px; }
.sense { margin: 0 0 8px; }
.sense .pos { margin-left: 0; }
.word-block { margin: 12px 0 0; }
.block-title { margin-bottom: 6px; color: #0b4f91; font-size: 14px; font-weight: 700; }
.synonym {
  margin: 0 0 8px; padding: 10px 12px; background: #f8fafc; border-radius: 8px;
}
.syn-head { margin-bottom: 4px; }
.syn-term { color: #0b4f91; font-weight: 700; }
.syn-pos { margin-left: 6px; color: var(--muted); font-size: 13px; }
.syn-def { margin-left: 6px; color: var(--ink); }
.nuance { color: #44505f; font-size: 14px; }
.collocation { color: var(--accent); font-size: 14px; }
.collocations, .word-forms { margin: 0; padding-left: 20px; }
.example-item { margin: 0 0 10px; }
.translation { color: #44505f; font-size: 14px; }
.note { color: var(--muted); font-size: 13px; }
.dialogue { margin: 0 0 16px; }
.line { margin: 0 0 10px; }
.speaker { display: inline-block; min-width: 26px; font-weight: 700; color: #0b4f91; }
.quiz-item, .review-item {
  margin: 0 0 18px; padding: 12px 14px; background: #f8fafc; border-radius: 10px;
}
.question { font-weight: 600; margin-bottom: 6px; }
.options { margin: 0; }
.option-label { font-weight: 700; color: var(--brand); }
.review-term { color: var(--muted); font-size: 13px; }
.answers { margin: 0 0 8px; padding: 14px 16px; background: #f4f8fd; border-radius: 10px; }
.answers p { margin: 0 0 10px; }
.muted { color: var(--muted); font-size: 14px; }
.back { margin-top: 28px; font-size: 14px; }
.archive { list-style: none; margin: 0; padding: 0; }
.archive li { border-bottom: 1px solid var(--line); }
.archive li:last-child { border-bottom: 0; }
.archive a {
  display: grid; grid-template-columns: 112px 1fr auto; gap: 12px;
  align-items: baseline; padding: 13px 2px; text-decoration: none; color: var(--ink);
}
.archive a:hover .archive-title { color: var(--brand); }
.archive-date { color: var(--muted); font-size: 14px; font-variant-numeric: tabular-nums; }
.archive-title { font-weight: 600; }
.archive-theme { color: var(--muted); font-size: 13px; }
.site-footer { margin-top: 26px; color: var(--muted); font-size: 12px; text-align: center; }
.empty { color: var(--muted); }
@media (max-width: 620px) {
  .container { padding-top: 18px; }
  .card { padding: 22px 18px; border-radius: 12px; }
  .card h1 { font-size: 23px; }
  .content h2 { font-size: 18px; }
  .archive a { grid-template-columns: 1fr auto; }
  .archive-date { grid-column: 1 / -1; font-size: 12px; }
}
"""


def render_content(content: dict, config: dict, site_url: str = "") -> email_layout.RenderedContent:
    date_text = str(content.get("date", ""))
    theme = str(content.get("theme", ""))
    title = str(content.get("title", ""))
    name = str(config.get("name") or config.get("site_title") or "每日英语")
    subject = " · ".join(part for part in [name, date_text, theme] if part)
    preheader = str(config.get("email_preheader", ""))

    body_html = content_to_body_html(content)
    if site_url:
        body_html += f'<p class="muted"><a href="{_e(site_url)}">查看往期推送</a></p>'

    html_doc = email_layout.wrap_email_html(
        title,
        date_text,
        theme,
        preheader,
        body_html,
        header_label=str(config.get("email_header", "")),
        footer_text=str(config.get("email_footer", "")),
        extra_css=EMAIL_CSS,
    )
    text = content_to_text(content, name)
    if site_url:
        text += f"\n往期推送：{site_url}\n"

    return email_layout.RenderedContent(
        date=date_text,
        subject=subject,
        preheader=preheader,
        html=html_doc,
        text=text,
    )
