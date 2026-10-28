#!/usr/bin/env python3
"""Intercept every SMTP operation; never connects or sends a real message."""
import base64
import contextlib
import importlib.util
import io
import json
import os
import smtplib
import ssl
import unittest
from email.parser import BytesParser
from email.policy import SMTP
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import gmail_smtp_transport as transport
from gmail_acknowledgments import GmailAcknowledgmentMailer

spec = importlib.util.spec_from_file_location("gmail_ack_test_fixtures",
    Path(__file__).with_name("test-gmail-acknowledgments.py"))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def message_for(form="elh-family"):
    payload = fixtures.letter()
    payload["headers"]["X-ELH-Form"] = form
    with patch("gmail_acknowledgments.subprocess.run",
               return_value=SimpleNamespace(returncode=0,stdout='{"ok":true,"message_id":"synthetic"}')) as run:
        GmailAcknowledgmentMailer().send(payload)
    request = json.loads(run.call_args.kwargs["input"])
    raw = request["raw"]
    return BytesParser(policy=SMTP).parsebytes(base64.urlsafe_b64decode(raw+"="*(-len(raw)%4)))


class GmailSmtpTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "GMAIL_ACK_APP_PASSWORD":"synthetic-info",
            "GMAIL_REFERRAL_APP_PASSWORD":"synthetic-referral"}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        smtp = patch.object(transport.smtplib, "SMTP")
        self.factory = smtp.start()
        self.addCleanup(smtp.stop)
        self.server = self.factory.return_value
        self.server.ehlo.return_value = (250,b"synthetic")
        self.server.send_message.return_value = {}

    def test_check_authenticates_each_mailbox_over_verified_tls_without_sending(self):
        for account, (mailbox, _) in transport.ACCOUNTS.items():
            with self.subTest(account=account):
                result = transport.check_login(account)
                self.assertTrue(result["authenticated"])
                self.server.login.assert_called_with(mailbox, "synthetic-"+account,
                                                      initial_response_ok=False)
                self.server.send_message.assert_not_called()
                self.server.close.assert_called()
                args, kwargs = self.factory.call_args
                self.assertEqual(args, ("smtp.gmail.com",587))
                context = self.server.starttls.call_args.kwargs["context"]
                self.assertTrue(context.check_hostname)
                self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_every_form_uses_matching_authentication_and_envelope_without_retries(self):
        for form, account in transport.FORM_ACCOUNTS.items():
            with self.subTest(form=form):
                self.server.reset_mock()
                message = message_for(form)
                result = transport.send_acknowledgment(message.as_bytes())
                self.assertTrue(result["ok"])
                self.server.login.assert_called_once_with(
                    transport.ACCOUNTS[account][0], "synthetic-"+account,
                    initial_response_ok=False)
                self.server.send_message.assert_called_once()
                self.assertEqual(self.server.send_message.call_args.kwargs,
                    {"from_addr":transport.ACCOUNTS[account][0],
                     "to_addrs":["synthetic@example.invalid"]})
                self.server.close.assert_called_once()

    def test_each_missing_credential_fails_closed_without_using_other_mailbox(self):
        for account, (_, secret) in transport.ACCOUNTS.items():
            with self.subTest(account=account), patch.dict(os.environ, {secret:""}):
                self.factory.reset_mock()
                with self.assertRaises(transport.GmailTransportError):
                    transport.check_login(account)
                self.factory.assert_not_called()

    def test_authentication_rejection_never_sends_and_never_uses_another_account(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(535,b"synthetic")
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            transport.send_acknowledgment(message_for("elh-physician").as_bytes())
        self.server.login.assert_called_once_with("referral@eternallifehospice.com","synthetic-referral",
                                                 initial_response_ok=False)
        self.server.send_message.assert_not_called()
        self.server.close.assert_called_once()

    def test_uncertain_send_or_refused_recipient_is_not_retried(self):
        for failure in (OSError("synthetic lost response"), {"synthetic@example.invalid":(550,b"synthetic")}):
            with self.subTest(failure=type(failure).__name__):
                self.server.reset_mock()
                self.server.send_message.side_effect = failure if isinstance(failure,Exception) else None
                self.server.send_message.return_value = failure
                with self.assertRaises((OSError,transport.GmailTransportError)):
                    transport.send_acknowledgment(message_for().as_bytes())
                self.server.send_message.assert_called_once()

    def test_cleanup_failure_after_acceptance_does_not_invalidate_success(self):
        self.server.close.side_effect = OSError("synthetic cleanup")
        self.assertTrue(transport.send_acknowledgment(message_for().as_bytes())["ok"])
        self.server.send_message.assert_called_once()

    def test_failed_tls_upgrade_never_authenticates_or_sends(self):
        self.server.starttls.side_effect = ssl.SSLError("synthetic")
        with self.assertRaises(ssl.SSLError):
            transport.check_login("info")
        self.server.login.assert_not_called()
        self.server.send_message.assert_not_called()

    def test_sender_spoofing_extra_recipients_and_unknown_forms_never_authenticate(self):
        for header, value in (("From","other@example.invalid"),
                              ("Reply-To","other@example.invalid"),
                              ("Cc","other@example.invalid"),
                              ("Bcc","other@example.invalid"),
                              ("To","one@example.invalid, two@example.invalid"),
                              ("X-ELH-Form","unknown-form")):
            with self.subTest(header=header):
                message = message_for()
                del message[header]
                message[header] = value
                with self.assertRaises((transport.GmailTransportError,KeyError)):
                    transport.send_acknowledgment(message.as_bytes())
        self.factory.assert_not_called()

    def test_pasted_password_spacing_is_accepted_without_logging(self):
        with patch.dict(os.environ,{"GMAIL_ACK_APP_PASSWORD":"synt hetic -info \n"}):
            transport.check_login("info")
        self.server.login.assert_called_once_with("info@eternallifehospice.com","synthetic-info",
                                                 initial_response_ok=False)

    def test_cli_errors_never_expose_credentials_or_provider_responses(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"SYNTHETIC-PRIVATE-PROVIDER-REPLY")
        output = io.StringIO()
        with patch("sys.argv", ["transport", "--check", "info"]), contextlib.redirect_stdout(output):
            self.assertEqual(transport.main(), 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["error"], "gmail_authentication_rejected")
        self.assertNotIn("SYNTHETIC-PRIVATE", output.getvalue())
        self.assertNotIn("synthetic-info", output.getvalue())
        self.server.send_message.assert_not_called()

    def test_auth_connection_close_is_reported_without_retrying(self):
        self.server.login.side_effect = smtplib.SMTPServerDisconnected("synthetic")
        with self.assertRaisesRegex(transport.GmailTransportError,
                                   "gmail_connection_closed_during_authentication"):
            transport.check_login("referral")
        self.server.login.assert_called_once()
        self.server.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
