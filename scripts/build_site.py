#!/usr/bin/env python3
"""Build the GitHub Pages archive from content JSON files."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import common
import render


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


WEB_CSS = """
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


def render_index(contents: list[dict], config: dict) -> str:
    title = str(config.get("site_title", "Daily English"))
    description = str(config.get("site_description", ""))
    rows = []
    for content in contents:
        date_text = str(content.get("date", ""))
        if not common.DATE_RE.match(date_text):
            continue
        rows.append(
            f'<li><a href="{_e(date_text)}.html">'
            f'<span class="archive-date">{_e(date_text)}</span>'
            f'<span class="archive-title">{_e(content.get("title"))}</span>'
            f'<span class="archive-theme">{_e(content.get("theme"))}</span>'
            f"</a></li>"
        )
    body = (
        f'<ul class="archive">{"".join(rows)}</ul>'
        if rows
        else '<p class="empty">还没有内容。运行 generate 后重新构建。</p>'
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<link rel="stylesheet" href="style.css">
</head>
<body>
<main class="container">
  <header class="site-header">
    <a class="brand" href="index.html">{_e(title)}</a>
    <p class="tagline">{_e(description)}</p>
  </header>
  <section class="card">{body}</section>
  <footer class="site-footer">由 Claude + GitHub Actions 自动生成</footer>
</main>
</body>
</html>
"""


def render_page(content: dict, config: dict) -> str:
    title = str(config.get("site_title", "Daily English"))
    date_text = str(content.get("date", ""))
    page_title = str(content.get("title", ""))
    body = render.content_to_body_html(content)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(page_title)} · {_e(title)}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main class="container">
  <header class="site-header">
    <a class="brand" href="index.html">{_e(title)}</a>
    <p class="tagline">{_e(config.get("site_description", ""))}</p>
  </header>
  <article class="card content">
    <h1>{_e(page_title)}</h1>
    <p class="meta">{_e(date_text)} · {_e(content.get("theme"))} · {_e(content.get("level"))}</p>
    {body}
    <p class="back"><a href="index.html">← 返回目录</a></p>
  </article>
  <footer class="site-footer">由 Claude + GitHub Actions 自动生成</footer>
</main>
</body>
</html>
"""


def build_site(
    contents: list[dict],
    site_dir: Path,
    config: dict,
    limit: int = 0,
) -> dict[str, Path]:
    site_dir = Path(site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)

    items = sorted(
        (content for content in contents if common.DATE_RE.match(str(content.get("date", "")))),
        key=lambda content: str(content.get("date", "")),
        reverse=True,
    )
    if limit > 0:
        items = items[:limit]

    style_path = site_dir / "style.css"
    style_path.write_text(WEB_CSS, encoding="utf-8")

    paths: dict[str, Path] = {"style": style_path}
    for content in items:
        date_text = str(content["date"])
        page_path = site_dir / f"{date_text}.html"
        page_path.write_text(render_page(content, config), encoding="utf-8")
        paths[date_text] = page_path

    index_path = site_dir / "index.html"
    index_path.write_text(render_index(items, config), encoding="utf-8")
    paths["index"] = index_path
    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建每日英语的静态归档站。")
    parser.add_argument("--site-dir", default="", help="输出目录，默认 config 的 site_dir")
    parser.add_argument("--limit", type=int, default=0, help="只保留最近 N 天的页面，0 表示全部")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = common.load_config()
        contents = common.load_all_contents(config)
        site_dir = (
            Path(args.site_dir).expanduser()
            if args.site_dir
            else common.ROOT / config.get("site_dir", "site")
        )
        if not site_dir.is_absolute():
            site_dir = Path.cwd() / site_dir
        paths = build_site(contents, site_dir, config, args.limit)
        print(f"已构建 {len([key for key in paths if key not in {'index', 'style'}])} 篇内容")
        print(f"首页：{paths['index']}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
