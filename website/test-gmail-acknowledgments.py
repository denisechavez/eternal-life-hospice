#!/usr/bin/env python3
"""No email is sent: Gmail and internal transports are intercepted."""
import base64
import json
import subprocess
import unittest
from email.parser import BytesParser
from email.policy import default
from types import SimpleNamespace
from unittest.mock import Mock, patch

import acknowledgments
import form_intake as intake
from gmail_acknowledgments import GmailAcknowledgmentMailer, GmailDeliveryError


FIELDS = {"form-name":"elh-family", "first_name":"Synthetic",
          "last_name":"Visitor", "phone":"2025550190",
          "email":"synthetic@example.invalid", "message":"PRIVATE-INTAKE-DETAIL"}


def letter(key="family"):
    subject, text, html = acknowledgments.render(
        key, "Synthetic", "AB1234CD5678", "info@eternallifehospice.com")
    return {"to":[{"email":"synthetic@example.invalid"}],
            "replyTo":{"email":"info@eternallifehospice.com","name":"Eternal Life Hospice"},
            "subject":subject, "textContent":text, "htmlContent":html,
            "headers":{"X-ELH-Form":"elh-family","X-ELH-Receipt":"AB1234CD5678"},
            "tags":["website-acknowledgement","elh-family"]}


class GmailRoutingTests(unittest.TestCase):
    def test_default_transports_are_separate_and_client_never_uses_brevo(self):
        with patch.object(intake, "BrevoMailer") as internal, patch.object(
                intake, "GmailAcknowledgmentMailer") as gmail:
            internal.return_value.send.return_value = "synthetic-internal"
            gmail.return_value.send.return_value = "synthetic-gmail"
            result = intake.process_submission(FIELDS, {})
        self.assertTrue(result["acknowledgement_sent"])
        internal.return_value.send.assert_called_once()
        gmail.return_value.send.assert_called_once()
        internal_payload = internal.return_value.send.call_args.args[0]
        client_payload = gmail.return_value.send.call_args.args[0]
        self.assertIn("website-intake", internal_payload["tags"])
        self.assertIn("website-acknowledgement", client_payload["tags"])
        self.assertNotIn("PRIVATE-INTAKE-DETAIL", client_payload["htmlContent"])
        self.assertEqual(client_payload["to"], [{"email":FIELDS["email"]}])

    def test_gmail_failure_does_not_fall_back_or_duplicate_the_intake(self):
        internal = Mock()
        with patch.object(intake, "GmailAcknowledgmentMailer") as gmail, patch.object(
                intake, "notify_acknowledgement_failure") as alert:
            gmail.return_value.send.side_effect = GmailDeliveryError("synthetic")
            result = intake.process_submission(FIELDS, {}, mailer=internal)
        self.assertTrue(result["accepted"])
        self.assertTrue(result["acknowledgement_error"])
        self.assertFalse(result["acknowledgement_sent"])
        internal.send.assert_called_once()
        gmail.return_value.send.assert_called_once()
        alert.assert_called_once()

    def test_no_email_or_honeypot_never_opens_gmail(self):
        with patch.object(intake, "GmailAcknowledgmentMailer") as gmail:
            intake.process_submission(dict(FIELDS, email=""), {}, mailer=Mock())
            intake.process_submission(dict(FIELDS, **{"bot-field":"synthetic"}), {}, mailer=Mock())
        gmail.assert_not_called()

    def test_internal_failure_prevents_client_receipt(self):
        internal = Mock()
        internal.send.side_effect = intake.DeliveryError("synthetic")
        with patch.object(intake, "GmailAcknowledgmentMailer") as gmail:
            with self.assertRaises(intake.DeliveryError):
                intake.process_submission(FIELDS, {}, mailer=internal)
        gmail.assert_not_called()


class GmailMimeTests(unittest.TestCase):
    def test_all_approved_letters_preserve_both_bodies_and_routing(self):
        completed = SimpleNamespace(returncode=0, stdout='{"ok":true,"message_id":"synthetic-gmail"}')
        with patch("gmail_acknowledgments.subprocess.run", return_value=completed) as run:
            for key in acknowledgments.TEMPLATES:
                with self.subTest(template=key):
                    payload = letter(key)
                    self.assertEqual(GmailAcknowledgmentMailer().send(payload), "synthetic-gmail")
                    args, kwargs = run.call_args
                    request = json.loads(kwargs["input"])
                    raw = base64.urlsafe_b64decode(request["raw"] + "=" * (-len(request["raw"]) % 4))
                    message = BytesParser(policy=default).parsebytes(raw)
                    self.assertIsNone(message["From"])  # Gmail supplies verified primary mailbox.
                    self.assertEqual(message["To"], "synthetic@example.invalid")
                    self.assertIn("info@eternallifehospice.com", str(message["Reply-To"]))
                    self.assertEqual(message["Subject"], payload["subject"])
                    self.assertEqual(message["X-ELH-Receipt"], "AB1234CD5678")
                    for content_type, expected in (("plain",payload["textContent"]),
                                                   ("html",payload["htmlContent"])):
                        actual = message.get_body(preferencelist=(content_type,)).get_content()
                        self.assertEqual(actual.replace("\r\n","\n").rstrip("\n"),
                                         expected.rstrip("\n"))
                    self.assertNotIn(FIELDS["email"], " ".join(args[0]))
                    self.assertEqual(kwargs["timeout"], 25)
                    self.assertNotIn("shell", kwargs)
        self.assertEqual(run.call_count, len(acknowledgments.TEMPLATES))

    def test_failures_never_retry(self):
        for outcome in (subprocess.TimeoutExpired("node",25), OSError("synthetic"),
                        SimpleNamespace(returncode=1,stdout='{"ok":false}'),
                        SimpleNamespace(returncode=0,stdout="not-json"),
                        SimpleNamespace(returncode=0,stdout='{"ok":true}')):
            with self.subTest(outcome=type(outcome).__name__):
                kwargs = {"side_effect":outcome} if isinstance(outcome,Exception) else {"return_value":outcome}
                with patch("gmail_acknowledgments.subprocess.run", **kwargs) as run:
                    with self.assertRaises(GmailDeliveryError):
                        GmailAcknowledgmentMailer().send(letter())
                run.assert_called_once()

    def test_non_acknowledgments_attachments_and_header_injection_are_rejected(self):
        for field, value in (("tags",["website-intake"]),
                             ("attachment",[{"content":"PRIVATE"}]),
                             ("subject","Approved\r\nBcc: unwanted@example.invalid"),
                             ("to",[{"email":"one@example.invalid"},{"email":"two@example.invalid"}])):
            with self.subTest(field=field):
                with patch("gmail_acknowledgments.subprocess.run") as run:
                    with self.assertRaises(GmailDeliveryError):
                        GmailAcknowledgmentMailer().send(dict(letter(), **{field:value}))
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
