#!/usr/bin/env python3
"""Regression and synthetic end-to-end tests for public form intake."""

from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import devserver
import form_intake


class CaptureHandler(BaseHTTPRequestHandler):
    payloads = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        self.__class__.payloads.append(json.loads(body.decode("utf-8")))
        response = json.dumps(
            {"messageId": f"synthetic-{len(self.__class__.payloads)}"}
        ).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        return


class AlertCaptureHandler(BaseHTTPRequestHandler):
    payloads = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        self.__class__.payloads.append(json.loads(body.decode("utf-8")))
        response = b'{"accepted":true}'
        self.send_response(204)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

    def log_message(self, _format, *_args):
        return


class FakeMailer:
    def __init__(self, fail_at=None):
        self.payloads = []
        self.fail_at = fail_at

    def send(self, payload):
        self.payloads.append(payload)
        if self.fail_at == len(self.payloads):
            raise form_intake.DeliveryError("synthetic failure")
        return f"fake-{len(self.payloads)}"


class FormIntakeTests(unittest.TestCase):
    def test_refer_page_routes_to_referral_inbox_and_acknowledges(self):
        fields = {
            "form-name": "elh-physician",
            "referrer_name": "Synthetic Referrer",
            "phone": "805.555.0101",
            "email": "synthetic@example.com",
            "county": "Ventura County",
            "situation": "Synthetic non-PHI routing test only.",
            "bot-field": "",
        }
        mailer = FakeMailer()
        result = form_intake.process_submission(fields, {}, mailer)

        self.assertTrue(result["accepted"])
        self.assertTrue(result["acknowledgement_sent"])
        self.assertEqual(len(mailer.payloads), 2)
        internal, acknowledgement = mailer.payloads
        self.assertEqual(
            internal["to"][0]["email"], "referral@eternallifehospice.com"
        )
        self.assertIn("Synthetic non-PHI routing test only.", internal["textContent"])
        self.assertNotIn(
            "Synthetic non-PHI routing test only.", acknowledgement["textContent"]
        )
        self.assertEqual(
            acknowledgement["to"][0]["email"], "synthetic@example.com"
        )

    def test_homepage_physician_variant_needs_no_email(self):
        fields = {
            "form-name": "elh-physician",
            "provider_first_name": "Synthetic",
            "provider_last_name": "Provider",
            "phone": "805-555-0102",
        }
        mailer = FakeMailer()
        result = form_intake.process_submission(fields, {}, mailer)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["acknowledgement_sent"])
        self.assertEqual(len(mailer.payloads), 1)

    def test_chat_callback_routes_internally_without_acknowledgement(self):
        fields = {
            "form-name": "elh-chat-callback",
            "name": "Synthetic Caller",
            "phone": "(805) 555-0103",
            "email": "synthetic@example.com",
        }
        mailer = FakeMailer()
        result = form_intake.process_submission(fields, {}, mailer)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["acknowledgement_sent"])
        self.assertEqual(len(mailer.payloads), 1)
        self.assertEqual(
            mailer.payloads[0]["to"][0]["email"],
            "referral@eternallifehospice.com",
        )

    def test_delivery_failure_never_reports_acceptance(self):
        fields = {
            "form-name": "elh-family",
            "first_name": "Synthetic",
            "last_name": "Family",
            "phone": "805.555.0104",
        }
        with self.assertRaises(form_intake.DeliveryError):
            form_intake.process_submission(fields, {}, FakeMailer(fail_at=1))

    def test_invalid_or_unknown_submissions_are_rejected(self):
        with self.assertRaises(form_intake.IntakeError):
            form_intake.validate_submission(
                {"form-name": "unknown", "phone": "805.555.0105"}, {}
            )
        with self.assertRaises(form_intake.IntakeError):
            form_intake.validate_submission(
                {
                    "form-name": "elh-family",
                    "first_name": "Synthetic",
                    "last_name": "Family",
                    "phone": "123",
                },
                {},
            )

    def test_common_identifiers_are_rejected_before_delivery(self):
        mailer = FakeMailer()
        with self.assertRaises(form_intake.IntakeError) as context:
            form_intake.process_submission(
                {
                    "form-name": "elh-physician",
                    "referrer_name": "Synthetic Referrer",
                    "phone": "805.555.0106",
                    "situation": "Patient name is Example Person, DOB 01/02/1940.",
                },
                {},
                mailer,
            )
        self.assertEqual(context.exception.code, "possible_phi")
        self.assertEqual(mailer.payloads, [])

    def test_honeypot_is_not_delivered(self):
        mailer = FakeMailer()
        result = form_intake.process_submission(
            {"form-name": "elh-family", "bot-field": "spam"}, {}, mailer
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(mailer.payloads, [])

    def test_static_browser_paths_use_replit_processor(self):
        root = Path(__file__).resolve().parent / "elh-preview"
        index = (root / "index.html").read_text(encoding="utf-8")
        refer = (root / "refer.html").read_text(encoding="utf-8")
        chat = (root / "assets" / "chat.js").read_text(encoding="utf-8")
        careers = (root / "careers.html").read_text(encoding="utf-8")
        brief = (root / "care-brief.html").read_text(encoding="utf-8")

        for content in (index, refer, chat, careers, brief):
            self.assertIn("/api/form-submit", content)
        self.assertNotIn(
            "fetch('/',{method:'POST'", index + refer + careers + brief
        )
        self.assertNotIn('fetch("/", {\n      method: "POST"', chat)
        self.assertIn('.then(function (result)', chat)
        self.assertIn('data.name.split(" ")', chat)
        self.assertIn('result.receipt_id', chat)
        self.assertIn("LEGACY NETLIFY COPY ONLY", (
            root / "netlify" / "functions" / "submission-created.js"
        ).read_text(encoding="utf-8"))


class SyntheticEndToEndTest(unittest.TestCase):
    def test_http_to_internal_and_acknowledgement_then_cleanup(self):
        """POST through the app, capture both Brevo messages, then erase them."""
        CaptureHandler.payloads = []
        brevo = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
        brevo_thread = threading.Thread(target=brevo.serve_forever, daemon=True)
        brevo_thread.start()

        mailer = form_intake.BrevoMailer(
            api_key="synthetic-test-key",
            endpoint=f"http://127.0.0.1:{brevo.server_address[1]}/v3/smtp/email",
        )
        real_process = form_intake.process_submission

        def process_with_capture(fields, files):
            return real_process(fields, files, mailer=mailer)

        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        app_thread = threading.Thread(target=app.serve_forever, daemon=True)
        app_thread.start()

        body = urllib.parse.urlencode(
            {
                "form-name": "elh-physician",
                "referrer_name": "Synthetic E2E",
                "phone": "805.555.0199",
                "email": "synthetic-e2e@example.com",
                "county": "Ventura County",
                "situation": "Synthetic non-PHI end-to-end routing check.",
                "bot-field": "",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{app.server_address[1]}/api/form-submit",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Origin": f"http://127.0.0.1:{app.server_address[1]}",
            },
        )

        try:
            with mock.patch.object(
                devserver, "process_submission", side_effect=process_with_capture
            ):
                with urllib.request.urlopen(request, timeout=5) as response:
                    result = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 200)
            self.assertTrue(result["ok"])
            self.assertTrue(result["accepted"])
            self.assertTrue(result["acknowledgement_sent"])
            self.assertEqual(len(CaptureHandler.payloads), 2)

            internal, acknowledgement = CaptureHandler.payloads
            self.assertEqual(
                internal["to"][0]["email"],
                "referral@eternallifehospice.com",
            )
            self.assertEqual(
                acknowledgement["to"][0]["email"],
                "synthetic-e2e@example.com",
            )
            self.assertIn(
                "Synthetic non-PHI end-to-end routing check.",
                internal["textContent"],
            )
            self.assertNotIn(
                "Synthetic non-PHI end-to-end routing check.",
                acknowledgement["textContent"],
            )
        finally:
            # The production processor stores no submissions. The local Brevo
            # capture is the only test record, and it is explicitly erased here.
            CaptureHandler.payloads.clear()
            app.shutdown()
            app.server_close()
            brevo.shutdown()
            brevo.server_close()

        self.assertEqual(CaptureHandler.payloads, [])

    def test_cross_origin_request_is_rejected_without_delivery(self):
        CaptureHandler.payloads = []
        form_intake.FORM_CLIENT_RATE_LIMITER.reset()
        form_intake.FORM_GLOBAL_RATE_LIMITER.reset()
        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        app_thread = threading.Thread(target=app.serve_forever, daemon=True)
        app_thread.start()
        body = urllib.parse.urlencode(
            {
                "form-name": "elh-chat-callback",
                "name": "Synthetic Caller",
                "phone": "805.555.0198",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{app.server_address[1]}/api/form-submit",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://attacker.example",
            },
        )
        try:
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(context.exception.code, 403)
            payload = json.loads(context.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"], "invalid_origin")
            self.assertEqual(CaptureHandler.payloads, [])
        finally:
            app.shutdown()
            app.server_close()

    def test_rate_limiter_stops_repeated_attempts(self):
        limiter = form_intake.SlidingWindowRateLimiter(2, 60)
        self.assertTrue(limiter.allow("synthetic-client"))
        self.assertTrue(limiter.allow("synthetic-client"))
        self.assertFalse(limiter.allow("synthetic-client"))

    def test_delivery_outage_alerts_and_preserves_phone_fallback(self):
        """Synthetic provider outage sends only safe alert data and 502 fallback."""
        AlertCaptureHandler.payloads = []
        form_intake.FORM_CLIENT_RATE_LIMITER.reset()
        form_intake.FORM_GLOBAL_RATE_LIMITER.reset()
        alert_server = ThreadingHTTPServer(("127.0.0.1", 0), AlertCaptureHandler)
        alert_thread = threading.Thread(
            target=alert_server.serve_forever, daemon=True
        )
        alert_thread.start()
        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        app_thread = threading.Thread(target=app.serve_forever, daemon=True)
        app_thread.start()
        original_alerter = form_intake.FORM_DELIVERY_ALERTER
        form_intake.FORM_DELIVERY_ALERTER = form_intake.DeliveryFailureAlerter(
            webhook_url=(
                f"http://127.0.0.1:{alert_server.server_address[1]}/alert"
            ),
            environment="synthetic-test",
            failure_threshold=3,
            window_seconds=60,
            cooldown_seconds=60,
        )
        body = urllib.parse.urlencode(
            {
                "form-name": "elh-family",
                "first_name": "Synthetic",
                "last_name": "Outage",
                "phone": "805.555.0196",
            }
        ).encode("utf-8")
        origin = f"http://127.0.0.1:{app.server_address[1]}"
        try:
            with mock.patch.object(
                devserver,
                "process_submission",
                side_effect=form_intake.DeliveryError("synthetic provider outage"),
            ):
                statuses = []
                response_bodies = []
                for _ in range(4):
                    request = urllib.request.Request(
                        origin + "/api/form-submit",
                        data=body,
                        method="POST",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Origin": origin,
                        },
                    )
                    try:
                        urllib.request.urlopen(request, timeout=5)
                    except urllib.error.HTTPError as exc:
                        statuses.append(exc.code)
                        response_bodies.append(
                            json.loads(exc.read().decode("utf-8"))
                        )

            self.assertEqual(statuses, [502, 502, 502, 502])
            self.assertTrue(
                all("805.953.7273" in result["message"] for result in response_bodies)
            )
            self.assertEqual(len(AlertCaptureHandler.payloads), 1)
            alert = AlertCaptureHandler.payloads[0]
            self.assertEqual(
                set(alert),
                {"timestamp", "environment", "processor_status", "failure_count"},
            )
            self.assertEqual(alert["environment"], "synthetic-test")
            self.assertEqual(alert["processor_status"], "delivery_unavailable")
            self.assertEqual(alert["failure_count"], 3)
            self.assertNotIn("Synthetic", json.dumps(alert))
            self.assertNotIn("805.555.0196", json.dumps(alert))
        finally:
            form_intake.FORM_DELIVERY_ALERTER = original_alerter
            form_intake.FORM_CLIENT_RATE_LIMITER.reset()
            form_intake.FORM_GLOBAL_RATE_LIMITER.reset()
            app.shutdown()
            app.server_close()
            alert_server.shutdown()
            alert_server.server_close()
            AlertCaptureHandler.payloads.clear()

    def test_spoofed_leading_forwarded_ips_cannot_bypass_endpoint_limit(self):
        form_intake.FORM_CLIENT_RATE_LIMITER.reset()
        form_intake.FORM_GLOBAL_RATE_LIMITER.reset()
        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        app_thread = threading.Thread(target=app.serve_forever, daemon=True)
        app_thread.start()
        body = urllib.parse.urlencode(
            {
                "form-name": "elh-chat-callback",
                "name": "Synthetic Caller",
                "phone": "805.555.0197",
            }
        ).encode("utf-8")
        accepted = {
            "ok": True,
            "accepted": True,
            "receipt_id": "SYNTHETIC",
            "acknowledgement_sent": False,
        }
        origin = f"http://127.0.0.1:{app.server_address[1]}"
        statuses = []
        try:
            with mock.patch.object(
                devserver, "process_submission", return_value=accepted
            ):
                for index in range(form_intake.RATE_LIMIT_ATTEMPTS + 1):
                    request = urllib.request.Request(
                        origin + "/api/form-submit",
                        data=body,
                        method="POST",
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Origin": origin,
                            # The attacker-controlled left edge rotates, while
                            # the proxy-observed right edge remains stable.
                            "X-Forwarded-For": (
                                f"203.0.113.{index}, 198.51.100.42"
                            ),
                        },
                    )
                    try:
                        with urllib.request.urlopen(request, timeout=5) as response:
                            statuses.append(response.status)
                    except urllib.error.HTTPError as exc:
                        statuses.append(exc.code)
            self.assertEqual(
                statuses[: form_intake.RATE_LIMIT_ATTEMPTS],
                [200] * form_intake.RATE_LIMIT_ATTEMPTS,
            )
            self.assertEqual(statuses[-1], 429)
        finally:
            app.shutdown()
            app.server_close()
            form_intake.FORM_CLIENT_RATE_LIMITER.reset()
            form_intake.FORM_GLOBAL_RATE_LIMITER.reset()


if __name__ == "__main__":
    unittest.main(verbosity=2)
