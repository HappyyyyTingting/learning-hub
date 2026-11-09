#!/usr/bin/env python3
"""Render and send one day's task push email.

Examples:
    python scripts/send_email.py --task english --date 2026-11-09 --dry-run
    python scripts/send_email.py --task english --date 2026-11-09
    python scripts/send_email.py --task english --date 2026-11-09 --force
"""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

import common
import email_layout

RESEND_ENDPOINT = "https://api.resend.com/emails"


class NonRetryableSendError(RuntimeError):
    """A configuration or permission error that should not be retried."""


def _split_addresses(value: str) -> list[str]:
    addresses = [part.strip() for part in (value or "").replace(";", ",").split(",") if part.strip()]
    if not addresses:
        raise ValueError("MAIL_TO 为空")
    for address in addresses:
        if "@" not in address:
            raise ValueError(f"邮箱地址格式不正确：{address}")
    return addresses


def _extract_email_address(value: str) -> str:
    import re

    match = re.search(r"[\w.+-]+@[\w.-]+", value or "")
    return match.group(0) if match else value


def build_message(
    rendered: email_layout.RenderedContent,
    from_addr: str,
    to_addrs: list[str],
    reply_to: str = "",
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = " ".join(rendered.subject.split())
    message["From"] = from_addr
    message["To"] = ", ".join(to_addrs)
    if reply_to:
        message["Reply-To"] = reply_to
    message["Date"] = formatdate(localtime=True)
    domain = _extract_email_address(from_addr).split("@")[-1] or "localhost"
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(rendered.text)
    message.add_alternative(rendered.html, subtype="html")
    return message


def _retry(operation, attempts: int = 3, base_delay: float = 2.0):
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except NonRetryableSendError:
            raise
        except Exception as exc:  # noqa: BLE001 - retry boundary
            last_error = exc
            if attempt >= attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            print(
                f"发送失败（第 {attempt}/{attempts} 次）：{exc}；{delay:g}s 后重试",
                file=sys.stderr,
            )
            time.sleep(delay)
    raise RuntimeError(f"发送失败（已重试 {attempts} 次）：{last_error}") from last_error


def _send_via_smtp(
    rendered: email_layout.RenderedContent,
    from_addr: str,
    to_addrs: list[str],
    reply_to: str,
) -> str:
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    security = os.getenv("SMTP_SECURITY", "").strip().lower()
    port_raw = os.getenv("SMTP_PORT", "").strip()

    missing = [
        name
        for name, value in (
            ("SMTP_HOST", host),
            ("SMTP_USER", user),
            ("SMTP_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise ValueError("缺少 SMTP 配置：" + ", ".join(missing))

    if not security:
        security = "ssl" if (not port_raw or port_raw == "465") else "starttls"
    if security not in {"ssl", "starttls", "none"}:
        raise ValueError("SMTP_SECURITY 只能是 ssl、starttls 或 none")

    port = int(port_raw) if port_raw else (465 if security == "ssl" else 587)
    message = build_message(rendered, from_addr, to_addrs, reply_to)

    def attempt() -> str:
        context = ssl.create_default_context()
        if security == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            if security == "starttls":
                server.starttls(context=context)
                server.ehlo()

        try:
            try:
                server.login(user, password)
            except smtplib.SMTPAuthenticationError as exc:
                raise NonRetryableSendError(
                    "SMTP 登录失败，请确认 SMTP_USER 和 SMTP_PASSWORD（QQ/Foxmail 使用的是授权码）"
                ) from exc
            try:
                server.send_message(message)
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as exc:
                raise NonRetryableSendError(f"SMTP 拒绝收件人或发件人：{exc}") from exc
        finally:
            try:
                server.quit()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
        return "smtp"

    return _retry(attempt)


def _send_via_resend(
    rendered: email_layout.RenderedContent,
    from_addr: str,
    to_addrs: list[str],
    reply_to: str,
) -> str:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 RESEND_API_KEY")

    payload: dict[str, object] = {
        "from": from_addr,
        "to": to_addrs,
        "subject": rendered.subject,
        "html": rendered.html,
        "text": rendered.text,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    def attempt() -> str:
        request = urllib.request.Request(
            RESEND_ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "learning-hub/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            message = f"Resend HTTP {exc.code}：{detail}"
            if exc.code == 429 or exc.code >= 500:
                raise RuntimeError(message) from exc
            raise NonRetryableSendError(message) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Resend 网络错误：{exc.reason}") from exc

        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        return str(data.get("id") or "resend")

    return _retry(attempt)


def send_email(
    rendered: email_layout.RenderedContent,
    to_value: str,
    from_addr: str,
    reply_to: str = "",
) -> str:
    to_addrs = _split_addresses(to_value)
    if not from_addr.strip():
        raise ValueError("缺少 MAIL_FROM")

    provider = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    if not provider:
        provider = "resend" if os.getenv("RESEND_API_KEY", "").strip() else "smtp"
    if provider not in {"resend", "smtp"}:
        raise ValueError("EMAIL_PROVIDER 只能是 resend 或 smtp")

    if provider == "resend":
        return _send_via_resend(rendered, from_addr, to_addrs, reply_to)
    return _send_via_smtp(rendered, from_addr, to_addrs, reply_to)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(common.ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渲染并发送一天的任务推送邮件。")
    parser.add_argument("--task", default="", help="任务名，例如 english（默认）")
    parser.add_argument("--date", help="日期 YYYY-MM-DD；默认按 config 时区取今天")
    parser.add_argument("--dry-run", action="store_true", help="只生成预览，不发送")
    parser.add_argument("--force", action="store_true", help="即使已发送过也重发")
    parser.add_argument("--out-dir", default="", help="dry-run 预览输出目录")
    parser.add_argument("--to", help="覆盖 MAIL_TO（仅本地测试）")
    parser.add_argument("--from", dest="from_addr", help="覆盖 MAIL_FROM（仅本地测试）")
    parser.add_argument("--subject", help="覆盖邮件主题")
    parser.add_argument("--site-url", default="", help="邮件里的往期链接")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        task = common.normalize_task(args.task)
        config = common.load_config(task)
        date_text = common.resolve_date(args.date, config)
        content = common.load_content(task, date_text, config)

        if not args.dry_run and common.is_sent(task, date_text, config) and not args.force:
            print(f"{date_text} 已发送过，跳过（--force 可重发）。")
            return 0

        renderer = common.load_renderer(task)
        rendered = renderer.render_content(
            content,
            config,
            args.site_url or common.derive_site_url(task),
        )
        if args.subject:
            rendered.subject = args.subject

        print(f"内容文件：{_display_path(common.content_path(task, date_text, config))}")
        print(f"邮件主题：{rendered.subject}")

        if args.dry_run:
            out_dir = (
                Path(args.out_dir).expanduser()
                if args.out_dir
                else common.ROOT / "preview" / task / date_text
            )
            if not out_dir.is_absolute():
                out_dir = Path.cwd() / out_dir
            html_path, text_path = email_layout.write_preview(rendered, out_dir)
            print(f"HTML 预览：{html_path}")
            print(f"纯文本预览：{text_path}")
            print("dry-run：未发送邮件。")
            return 0

        to_value = args.to or os.getenv("MAIL_TO", "")
        from_addr = args.from_addr or os.getenv("MAIL_FROM", "")
        reply_to = os.getenv("MAIL_REPLY_TO", "").strip()
        message_id = send_email(rendered, to_value, from_addr, reply_to)
        common.mark_sent(task, date_text, config)

        provider = os.getenv("EMAIL_PROVIDER", "").strip().lower() or (
            "resend" if os.getenv("RESEND_API_KEY", "").strip() else "smtp"
        )
        print(f"发送成功：provider={provider} id={message_id}")
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
