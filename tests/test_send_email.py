import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import email_layout  # noqa: E402
import send_email  # noqa: E402

ENV = {
    "SMTP_HOST": "smtp.qq.com",
    "SMTP_PORT": "465",
    "SMTP_SECURITY": "ssl",
    "SMTP_USER": "sender@qq.com",
    "SMTP_PASSWORD": "authorization-code",
}


def rendered() -> email_layout.RenderedContent:
    return email_layout.RenderedContent(
        date="2026-11-09",
        subject="测试",
        preheader="",
        html="<p>hi</p>",
        text="hi\n",
    )


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, *args, **kwargs):
        self.calls: list[tuple] = []
        FakeSMTP.instances.append(self)

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, message, from_addr=None, to_addrs=None):
        self.calls.append(("send_message", from_addr, list(to_addrs or [])))

    def quit(self):
        self.calls.append(("quit",))


class MailboxTests(unittest.TestCase):
    def test_extracts_address_from_display_name(self):
        self.assertEqual(send_email._mailbox("每日英语 <a@qq.com>", "MAIL_FROM"), "a@qq.com")

    def test_extracts_address_from_quoted_value(self):
        self.assertEqual(
            send_email._mailbox('"每日英语 <a@qq.com>"', "MAIL_FROM"), "a@qq.com"
        )

    def test_rejects_value_without_address(self):
        with self.assertRaises(ValueError):
            send_email._mailbox("每日英语", "MAIL_FROM")


class SenderCheckTests(unittest.TestCase):
    def test_qq_sender_must_match_login(self):
        with self.assertRaises(send_email.NonRetryableSendError):
            send_email._check_sender_matches_login(
                "smtp.qq.com", "other@qq.com", "sender@qq.com"
            )

    def test_qq_sender_matches_login_case_insensitive(self):
        send_email._check_sender_matches_login(
            "smtp.qq.com", "Sender@QQ.com", "sender@qq.com"
        )

    def test_non_qq_host_is_not_checked(self):
        send_email._check_sender_matches_login(
            "smtp.example.com", "other@example.com", "sender@example.com"
        )


class SmtpEnvelopeTests(unittest.TestCase):
    def setUp(self):
        FakeSMTP.instances = []

    def test_envelope_uses_bare_addresses(self):
        with patch.dict(os.environ, ENV, clear=False), patch(
            "smtplib.SMTP_SSL", FakeSMTP
        ):
            result = send_email._send_via_smtp(
                rendered(),
                "每日英语 <sender@qq.com>",
                ["Reader <reader@example.com>"],
                "",
            )
        self.assertEqual(result, "smtp")
        server = FakeSMTP.instances[0]
        send_call = [call for call in server.calls if call[0] == "send_message"][0]
        self.assertEqual(send_call[1], "sender@qq.com")
        self.assertEqual(send_call[2], ["reader@example.com"])

    def test_mismatch_fails_before_connecting(self):
        with patch.dict(os.environ, ENV, clear=False), patch(
            "smtplib.SMTP_SSL", FakeSMTP
        ):
            with self.assertRaises(send_email.NonRetryableSendError):
                send_email._send_via_smtp(
                    rendered(),
                    "other@qq.com",
                    ["reader@example.com"],
                    "",
                )
        self.assertEqual(FakeSMTP.instances, [])

    def test_recipient_error_does_not_leak_addresses(self):
        error = send_email._refusal_error(
            "SMTP 拒绝收件人",
            [(503, b"Send command mailfrom first.")],
        )
        text = str(error)
        self.assertIn("503", text)
        self.assertIn("Send command mailfrom first.", text)
        self.assertNotIn("reader@example.com", text)

    def test_sequence_error_is_retried(self):
        error = send_email._refusal_error(
            "SMTP 拒绝收件人", [(503, b"Send command mailfrom first.")]
        )
        self.assertIsInstance(error, RuntimeError)
        self.assertNotIsInstance(error, send_email.NonRetryableSendError)

    def test_permanent_refusal_is_not_retried(self):
        error = send_email._refusal_error(
            "SMTP 拒绝收件人", [(550, b"Mailbox unavailable")]
        )
        self.assertIsInstance(error, send_email.NonRetryableSendError)


if __name__ == "__main__":
    unittest.main()
