#!/usr/bin/env python3
"""Render structured English content as email HTML/text and web body HTML."""

from __future__ import annotations

import argparse
import html
import sys
from dataclasses import dataclass
from pathlib import Path

import common


@dataclass
class RenderedContent:
    date: str
    subject: str
    preheader: str
    html: str
    text: str


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _word_html(word: dict) -> str:
    pos = str(word.get("part_of_speech", "")).strip()
    pos_label = f'<span class="pos">{_e(pos)}</span>' if pos else ""
    return f"""
    <div class="word-card">
      <div class="word-head">
        <span class="term">{_e(word.get("term"))}</span>
        <span class="ipa">{_e(word.get("ipa"))}</span>
        {pos_label}
      </div>
      <div class="definition-en">{_e(word.get("definition_en"))}</div>
      <div class="definition-zh">{_e(word.get("definition_zh"))}</div>
      <div class="example">{_e(word.get("example"))}</div>
    </div>
    """


def content_to_body_html(content: dict) -> str:
    words = "".join(_word_html(word) for word in content.get("words", []))

    examples = "".join(
        f"<li>{_e(item)}</li>" for item in content.get("examples", [])
    )

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
<h2>例句</h2>
<ul class="examples">{examples}</ul>
<h2>情景对话</h2>
<div class="dialogue">{dialogue}</div>
<h2>小练习</h2>
{''.join(quiz_parts)}
<h2>复习</h2>
{review_html}
<h2>答案与解析</h2>
<div class="answers">{''.join(answers)}</div>
"""


def content_to_text(content: dict) -> str:
    lines = [
        f"每日英语 · {content.get('date', '')} · {content.get('theme', '')}",
        str(content.get("title", "")),
        "",
        "【今日词汇】",
    ]
    for index, word in enumerate(content.get("words", []), start=1):
        lines.append(
            f"{index}. {word.get('term', '')} {word.get('ipa', '')} "
            f"({word.get('part_of_speech', '')})"
        )
        lines.append(f"   英文释义：{word.get('definition_en', '')}")
        lines.append(f"   中文释义：{word.get('definition_zh', '')}")
        lines.append(f"   例句：{word.get('example', '')}")
        lines.append("")

    lines.append("【例句】")
    for item in content.get("examples", []):
        lines.append(f"- {item}")
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


def _email_css() -> str:
    return """
    :root { color-scheme: light; }
    body { margin: 0; padding: 0; background: #eef2f6; }
    .email-body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      font-size: 16px; line-height: 1.75; color: #1f2328; overflow-wrap: anywhere;
    }
    .email-body h2 {
      font-size: 19px; line-height: 1.45; margin: 30px 0 12px;
      padding-bottom: 8px; border-bottom: 1px solid #e4e8ec; color: #111827;
    }
    .email-body p { margin: 0 0 14px; }
    .email-body ul { margin: 0 0 16px; padding-left: 22px; }
    .email-body li { margin: 0 0 8px; }
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
    .email-body .example { margin-top: 6px; color: #0b5cad; font-style: italic; }
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
    .email-body .muted { color: #667085; font-size: 14px; }
    @media (max-width: 620px) {
      .email-outer { padding: 12px 8px !important; }
      .email-card { border-radius: 12px !important; }
      .email-header { padding: 24px 20px !important; }
      .email-title { font-size: 22px !important; }
      .email-body { padding: 22px 18px !important; }
      .email-body h2 { font-size: 18px !important; }
    }
    """


def wrap_email_html(title: str, date_text: str, meta: str, preheader: str, body_html: str) -> str:
    safe_title = _e(title)
    safe_date = _e(date_text)
    safe_meta = _e(meta)
    safe_preheader = _e(preheader)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="x-apple-disable-message-reformatting">
<title>{safe_title}</title>
<style>{_email_css()}</style>
</head>
<body style="margin:0;padding:0;background:#eef2f6;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">
{safe_preheader}
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#eef2f6;">
  <tr>
    <td class="email-outer" align="center" style="padding:28px 12px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-card" style="max-width:640px;background:#ffffff;border:1px solid #e1e7ed;border-radius:16px;overflow:hidden;">
        <tr>
          <td class="email-header" style="background-color:#0b5cad;background-image:linear-gradient(135deg,#0b5cad 0%,#0a7ea4 100%);padding:30px 32px;color:#ffffff;">
            <div style="font-size:12px;letter-spacing:1.5px;text-transform:uppercase;opacity:0.82;margin-bottom:8px;">Daily English · B1-B2</div>
            <div class="email-title" style="font-size:26px;line-height:1.35;font-weight:700;color:#ffffff;">{safe_title}</div>
            <div style="font-size:14px;line-height:1.5;opacity:0.86;margin-top:10px;">{safe_date} · {safe_meta}</div>
          </td>
        </tr>
        <tr>
          <td class="email-body" style="padding:28px 32px 10px;">{body_html}</td>
        </tr>
        <tr>
          <td class="email-footer" style="padding:20px 32px 28px;color:#7a8493;font-size:12px;line-height:1.7;border-top:1px solid #eef1f4;">
            由 Claude + GitHub Actions 自动生成 · 每天 5 分钟，坚持比一次学很多更重要。
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def render_content(content: dict, site_url: str = "") -> RenderedContent:
    date_text = str(content.get("date", ""))
    theme = str(content.get("theme", ""))
    title = str(content.get("title", ""))
    subject = " · ".join(part for part in ["每日英语", date_text, theme] if part)
    preheader = "5 个词 · 3 个例句 · 1 段对话 · 2 道练习"

    body_html = content_to_body_html(content)
    if site_url:
        body_html += (
            f'<p class="muted"><a href="{_e(site_url)}">查看往期推送</a></p>'
        )

    html_doc = wrap_email_html(title, date_text, theme, preheader, body_html)
    text = content_to_text(content)
    if site_url:
        text += f"\n往期推送：{site_url}\n"

    return RenderedContent(
        date=date_text,
        subject=subject,
        preheader=preheader,
        html=html_doc,
        text=text,
    )


def write_preview(rendered: RenderedContent, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "email.html"
    text_path = out_dir / "email.txt"
    html_path.write_text(rendered.html, encoding="utf-8")
    text_path.write_text(rendered.text + "\n", encoding="utf-8")
    return html_path, text_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把内容 JSON 渲染成邮件预览。")
    parser.add_argument("--date", help="日期 YYYY-MM-DD；默认按 config 时区取今天")
    parser.add_argument("--out-dir", default="", help="预览输出目录")
    parser.add_argument("--site-url", default="", help="邮件里的往期链接")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = common.load_config()
        date_text = common.resolve_date(args.date, config)
        content = common.load_content(date_text, config)
        rendered = render_content(content, args.site_url or common.derive_site_url())
        out_dir = (
            Path(args.out_dir).expanduser()
            if args.out_dir
            else common.ROOT / "preview" / date_text
        )
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir
        html_path, text_path = write_preview(rendered, out_dir)
        print(f"主题：{rendered.subject}")
        print(f"HTML 预览：{html_path}")
        print(f"纯文本预览：{text_path}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
