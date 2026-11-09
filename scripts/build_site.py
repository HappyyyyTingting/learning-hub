#!/usr/bin/env python3
"""Build a task's GitHub Pages archive and the shared Learning Hub index.

The task renderer supplies the body HTML and site CSS; this module owns the
page shell, the archive listing and the root page that links every built task.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import common


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


HUB_CSS = """
:root {
  color-scheme: light;
  --bg: #f2f5f8;
  --surface: #ffffff;
  --ink: #1f2328;
  --muted: #667085;
  --line: #e1e7ed;
  --brand: #0b5cad;
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
}
a { color: var(--brand); }
.container { width: min(100% - 32px, 720px); margin: 0 auto; padding: 36px 0 48px; }
h1 { margin: 0 0 6px; font-size: 30px; line-height: 1.3; }
.tagline { margin: 0 0 24px; color: var(--muted); }
.tasks { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; }
.tasks a {
  display: block; padding: 20px 22px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 14px;
  text-decoration: none; color: var(--ink);
  box-shadow: 0 8px 24px rgba(15, 35, 60, 0.04);
}
.tasks a:hover { border-color: var(--brand); }
.tasks strong { display: block; font-size: 19px; color: var(--brand); }
.tasks span { display: block; margin-top: 4px; color: var(--muted); font-size: 14px; }
.empty { color: var(--muted); }
.site-footer { margin-top: 26px; color: var(--muted); font-size: 12px; text-align: center; }
"""


def render_index(contents: list[dict], config: dict) -> str:
    title = str(config.get("site_title") or config.get("name") or "Learning Hub")
    description = str(config.get("site_description", ""))
    footer = str(config.get("site_footer", "由 DeepSeek + GitHub Actions 自动生成"))
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
  <footer class="site-footer">{_e(footer)}</footer>
</main>
</body>
</html>
"""


def render_page(content: dict, config: dict, body_renderer) -> str:
    title = str(config.get("site_title") or config.get("name") or "Learning Hub")
    footer = str(config.get("site_footer", "由 DeepSeek + GitHub Actions 自动生成"))
    date_text = str(content.get("date", ""))
    page_title = str(content.get("title", ""))
    body = body_renderer(content)
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
  <footer class="site-footer">{_e(footer)}</footer>
</main>
</body>
</html>
"""


def build_site(
    contents: list[dict],
    site_dir: Path,
    config: dict,
    limit: int = 0,
    body_renderer=None,
    site_css: str = "",
) -> dict[str, Path]:
    if body_renderer is None:
        raise ValueError("build_site 需要 body_renderer")
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
    style_path.write_text(site_css, encoding="utf-8")

    paths: dict[str, Path] = {"style": style_path}
    for content in items:
        date_text = str(content["date"])
        page_path = site_dir / f"{date_text}.html"
        page_path.write_text(
            render_page(content, config, body_renderer),
            encoding="utf-8",
        )
        paths[date_text] = page_path

    index_path = site_dir / "index.html"
    index_path.write_text(render_index(items, config), encoding="utf-8")
    paths["index"] = index_path
    return paths


def build_hub(site_root: Path) -> Path:
    site_root = Path(site_root)
    site_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for index_path in sorted(site_root.glob("*/index.html")):
        task = index_path.parent.name
        try:
            config = common.load_config(task)
        except (OSError, ValueError):
            config = {}
        title = str(config.get("site_title") or config.get("name") or task)
        description = str(config.get("site_description", ""))
        entries.append(
            f'<li><a href="{_e(task)}/index.html"><strong>{_e(title)}</strong>'
            f"<span>{_e(description)}</span></a></li>"
        )
    body = (
        f'<ul class="tasks">{"".join(entries)}</ul>'
        if entries
        else '<p class="empty">还没有构建任何任务。</p>'
    )
    hub_path = site_root / "index.html"
    hub_path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Learning Hub</title>
<meta name="description" content="每天一点，长期积累。">
<style>{HUB_CSS}</style>
</head>
<body>
<main class="container">
  <h1>Learning Hub</h1>
  <p class="tagline">每天一点，长期积累。</p>
  {body}
  <footer class="site-footer">由 DeepSeek + GitHub Actions 自动生成</footer>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return hub_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建任务归档站和 Learning Hub 入口。")
    parser.add_argument("--task", default="", help="任务名，例如 english（默认）")
    parser.add_argument("--site-dir", default="", help="输出目录，默认 site/<task>")
    parser.add_argument("--limit", type=int, default=0, help="只保留最近 N 天的页面，0 表示全部")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        task = common.normalize_task(args.task)
        config = common.load_config(task)
        contents = common.load_all_contents(task, config)
        renderer = common.load_renderer(task)
        site_dir = (
            Path(args.site_dir).expanduser()
            if args.site_dir
            else common.site_dir(task, config)
        )
        if not site_dir.is_absolute():
            site_dir = Path.cwd() / site_dir
        paths = build_site(
            contents,
            site_dir,
            config,
            args.limit,
            body_renderer=renderer.content_to_body_html,
            site_css=getattr(renderer, "SITE_CSS", ""),
        )
        hub_path = build_hub(site_dir.parent)
        print(f"已构建 {len([key for key in paths if key not in {'index', 'style'}])} 篇内容")
        print(f"任务首页：{paths['index']}")
        print(f"站点入口：{hub_path}")
        return 0
    except (OSError, ValueError, ImportError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
