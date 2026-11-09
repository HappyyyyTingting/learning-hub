#!/usr/bin/env python3
"""Shared email shell and preview helpers.

Task renderers provide the body HTML, an optional extra CSS string, and the
header/footer labels; this module owns the outer table layout, base typography
and the plain files written for dry runs.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RenderedContent:
    date: str
    subject: str
    preheader: str
    html: str
    text: str


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


BASE_CSS = """
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


def wrap_email_html(
    title: str,
    date_text: str,
    meta: str,
    preheader: str,
    body_html: str,
    header_label: str = "",
    footer_text: str = "",
    extra_css: str = "",
) -> str:
    safe_title = escape(title)
    safe_date = escape(date_text)
    safe_meta = escape(meta)
    safe_preheader = escape(preheader)
    label_html = (
        f'<div style="font-size:12px;letter-spacing:1.5px;text-transform:uppercase;'
        f'opacity:0.82;margin-bottom:8px;">{escape(header_label)}</div>'
        if header_label
        else ""
    )
    footer_html = (
        f"""
        <tr>
          <td class="email-footer" style="padding:20px 32px 28px;color:#7a8493;font-size:12px;line-height:1.7;border-top:1px solid #eef1f4;">
            {escape(footer_text)}
          </td>
        </tr>"""
        if footer_text
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="x-apple-disable-message-reformatting">
<title>{safe_title}</title>
<style>{BASE_CSS}{extra_css}</style>
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
            {label_html}
            <div class="email-title" style="font-size:26px;line-height:1.35;font-weight:700;color:#ffffff;">{safe_title}</div>
            <div style="font-size:14px;line-height:1.5;opacity:0.86;margin-top:10px;">{safe_date} · {safe_meta}</div>
          </td>
        </tr>
        <tr>
          <td class="email-body" style="padding:28px 32px 10px;">{body_html}</td>
        </tr>{footer_html}
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def write_preview(rendered: RenderedContent, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "email.html"
    text_path = out_dir / "email.txt"
    html_path.write_text(rendered.html, encoding="utf-8")
    text_path.write_text(rendered.text + "\n", encoding="utf-8")
    return html_path, text_path
