#!/usr/bin/env python3
"""Best-effort failure alert for the daily workflow.

Never exits non-zero: an alert failure must not hide the original error.
"""

from __future__ import annotations

import argparse
import html
import os
import sys

import common
import email_layout
import send_email


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def build_alert(message: str, run_url: str = "", name: str = "Daily English") -> email_layout.RenderedContent:
    subject = f"【{name}】今天的推送失败了"
    text_lines = [
        subject,
        "",
        message.strip(),
    ]
    if run_url:
        text_lines += ["", f"运行日志：{run_url}"]

    link_html = (
        f'<p><a href="{_e(run_url)}">查看运行日志</a></p>' if run_url else ""
    )
    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:24px;background:#f2f5f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;color:#1f2328;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e1e7ed;border-radius:14px;padding:24px;">
    <h1 style="font-size:20px;margin:0 0 12px;">今天的推送失败了</h1>
    <p style="margin:0 0 14px;line-height:1.7;white-space:pre-wrap;">{_e(message.strip())}</p>
    {link_html}
    <p style="margin:18px 0 0;color:#667085;font-size:13px;">这是自动告警。修好后再手动运行一次工作流即可补发。</p>
  </div>
</body>
</html>
"""
    return email_layout.RenderedContent(
        date="",
        subject=subject,
        preheader="定时任务失败",
        html=html_doc,
        text="\n".join(text_lines).strip() + "\n",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="发送工作流失败告警邮件。")
    parser.add_argument("--task", default="", help="任务名，例如 english（默认）")
    parser.add_argument("--message", default="定时任务运行失败，请查看日志。")
    parser.add_argument("--run-url", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    to_value = os.getenv("MAIL_TO", "").strip()
    from_addr = os.getenv("MAIL_FROM", "").strip()
    if not to_value or not from_addr:
        print("未配置 MAIL_TO / MAIL_FROM，跳过告警。")
        return 0

    try:
        task = common.normalize_task(args.task)
        try:
            config = common.load_config(task)
            name = str(config.get("name") or config.get("site_title") or "Daily English")
        except (OSError, ValueError):
            name = "Daily English"
        rendered = build_alert(args.message, args.run_url, name)
        reply_to = os.getenv("MAIL_REPLY_TO", "").strip()
        send_email.send_email(rendered, to_value, from_addr, reply_to)
        print("告警邮件已发送。")
    except Exception as exc:  # noqa: BLE001 - alerting is best-effort
        print(f"告警邮件发送失败：{exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
