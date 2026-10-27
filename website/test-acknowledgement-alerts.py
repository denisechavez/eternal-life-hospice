#!/usr/bin/env python3
"""Receipt-failure regressions with synthetic intake and intercepted transports."""
import concurrent.futures
import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import devserver
import form_intake as intake


FIELDS = {
    "form-name": "elh-family",
    "first_name": "Synthetic", "last_name": "Visitor",
    "phone": "2025550190", "email": "synthetic@example.com",
    "message": "SYNTHETIC-PRIVATE-CONTENT",
}


class AcknowledgementAlertTests(unittest.TestCase):
    def setUp(self):
        self.configured_alerter = intake.FORM_ACKNOWLEDGEMENT_ALERTER
        self.alerter = intake.DeliveryFailureAlerter(
            webhook_url="https://synthetic.invalid/private-channel",
            environment="synthetic-test", failure_threshold=1,
            processor_status="acknowledgement_unavailable",
        )
        self.patchers = [
            patch.object(intake, "FORM_ACKNOWLEDGEMENT_ALERTER", self.alerter),
            patch.object(intake.urllib.request, "urlopen",
                         side_effect=AssertionError("Unexpected external transport")),
            patch("sys.stderr", new_callable=io.StringIO),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def mailer(self, failure=2):
        # Internal acceptance is always retained; only the second send fails.
        return Mock(send=Mock(side_effect=[
            intake.DeliveryError("synthetic private provider response")
            if failure == 1 else "synthetic-internal-record",
            intake.DeliveryError("synthetic private provider response")
            if failure == 2 else "synthetic-receipt-record",
        ]))

    def test_default_acknowledgement_policy_is_distinct_and_immediate(self):
        self.assertEqual(self.configured_alerter.processor_status,
                         "acknowledgement_unavailable")
        self.assertEqual(self.configured_alerter.failure_threshold, 1)
        self.assertEqual(self.configured_alerter.cooldown_seconds, 900)
        self.assertEqual(self.configured_alerter.window_seconds, 300)
        self.assertIsNot(self.configured_alerter, intake.FORM_DELIVERY_ALERTER)

    def test_webhook_transport_is_bounded_and_rejects_non_success(self):
        for status in (204, 503):
            with self.subTest(status=status):
                response = Mock(status=status)
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                alerter = intake.DeliveryFailureAlerter(
                    webhook_url="https://synthetic.invalid/private-channel",
                    environment="synthetic-test", failure_threshold=1,
                    processor_status="acknowledgement_unavailable")
                logs = io.StringIO()
                with patch.object(
                    intake.urllib.request, "urlopen", return_value=response
                ) as transport, patch("sys.stderr", logs):
                    self.assertTrue(alerter.record_failure())
                    self.assertFalse(alerter.record_failure())
                transport.assert_called_once()
                request = transport.call_args.args[0]
                self.assertEqual(request.method, "POST")
                self.assertEqual(transport.call_args.kwargs["timeout"], 5)
                self.assertEqual(json.loads(request.data)["processor_status"],
                                 "acknowledgement_unavailable")
                self.assertEqual("FORM_ALERT_FAILED" in logs.getvalue(), status == 503)
                self.assertNotIn("private-channel", logs.getvalue())

    def assert_accepted(self, result, mailer):
        self.assertTrue(result["ok"])
        self.assertTrue(result["accepted"])
        self.assertFalse(result["acknowledgement_sent"])
        self.assertTrue(result["acknowledgement_error"])
        self.assertEqual(result["provider_message_id"], "synthetic-internal-record")
        self.assertEqual(mailer.send.call_count, 2)
        internal, receipt = [call.args[0] for call in mailer.send.call_args_list]
        self.assertEqual(internal["to"][0]["email"], intake.REFERRAL_EMAIL)
        self.assertEqual(receipt["to"][0]["email"], FIELDS["email"])
        self.assertIn(FIELDS["message"], internal["textContent"])

    def test_isolated_failure_alert_has_only_allowlisted_metadata(self):
        mailer = self.mailer()
        with patch.object(self.alerter, "_send") as send:
            result = intake.process_submission(FIELDS, {}, mailer)
        self.assert_accepted(result, mailer)
        send.assert_called_once()
        payload = send.call_args.args[0]
        self.assertEqual(set(payload), {
            "timestamp", "environment", "processor_status", "failure_count"})
        self.assertEqual(payload["processor_status"], "acknowledgement_unavailable")
        self.assertEqual(payload["failure_count"], 1)
        self.assertEqual(payload["environment"], "synthetic-test")
        encoded = json.dumps(payload)
        for value in [*FIELDS.values(), result["receipt_id"],
                      result["provider_message_id"], "private provider response"]:
            self.assertNotIn(value, encoded)

    def test_no_alert_for_success_no_email_honeypot_or_internal_failure(self):
        with patch.object(self.alerter, "_send") as send:
            intake.process_submission(FIELDS, {}, self.mailer(failure=0))
            no_email = self.mailer()
            intake.process_submission(dict(FIELDS, email=""), {}, no_email)
            self.assertEqual(no_email.send.call_count, 1)
            honeypot = self.mailer()
            intake.process_submission(dict(FIELDS, **{"bot-field": "synthetic"}), {}, honeypot)
            honeypot.send.assert_not_called()
            internal_failure = self.mailer(failure=1)
            with self.assertRaises(intake.DeliveryError):
                intake.process_submission(FIELDS, {}, internal_failure)
            self.assertEqual(internal_failure.send.call_count, 1)
        send.assert_not_called()

    def test_window_cooldown_and_bounded_counter(self):
        with patch.object(self.alerter, "_send") as send, patch.object(
            intake.time, "monotonic"
        ) as clock:
            clock.return_value = 0
            self.assertTrue(intake.notify_acknowledgement_failure())
            clock.return_value = 1
            for _ in range(1100):
                self.assertFalse(intake.notify_acknowledgement_failure())
            self.assertEqual(len(self.alerter._failures), 1000)
            clock.return_value = 899
            self.assertFalse(intake.notify_acknowledgement_failure())
            clock.return_value = 900
            self.assertTrue(intake.notify_acknowledgement_failure())
            self.assertEqual(send.call_count, 2)
            self.assertEqual(send.call_args.args[0]["failure_count"], 2)

    def test_concurrent_failures_attempt_one_alert(self):
        with patch.object(self.alerter, "_send") as send:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                attempts = list(pool.map(
                    lambda _: intake.notify_acknowledgement_failure(), range(100)))
        self.assertEqual(sum(attempts), 1)
        send.assert_called_once()

    def test_alert_channel_errors_keep_success_and_cooldown_and_safe_logs(self):
        for error in [TimeoutError, OSError, ValueError]:
            with self.subTest(error=error.__name__):
                alerter = intake.DeliveryFailureAlerter(
                    webhook_url="https://synthetic.invalid/private-channel",
                    failure_threshold=1, processor_status="acknowledgement_unavailable")
                logs = io.StringIO()
                with patch.object(intake, "FORM_ACKNOWLEDGEMENT_ALERTER", alerter), patch.object(
                    alerter, "_send", side_effect=error("SYNTHETIC-PRIVATE-CONTENT")
                ) as send, patch("sys.stderr", logs):
                    for _ in range(2):
                        mailer = self.mailer()
                        result = intake.process_submission(FIELDS, {}, mailer)
                        self.assert_accepted(result, mailer)
                send.assert_called_once()
                self.assertIn("FORM_ALERT_FAILED channel=webhook error=" + error.__name__,
                              logs.getvalue())
                for private in ["private-channel", "SYNTHETIC-PRIVATE-CONTENT",
                                FIELDS["email"], "private provider response"]:
                    self.assertNotIn(private, logs.getvalue())

    def test_unconfigured_channel_preserves_success(self):
        with patch.object(self.alerter, "webhook_url", ""), patch.object(
            self.alerter, "_send"
        ) as send:
            mailer = self.mailer()
            result = intake.process_submission(FIELDS, {}, mailer)
        self.assert_accepted(result, mailer)
        send.assert_not_called()

    def test_acknowledgement_and_other_outages_have_independent_cooldowns(self):
        others = [intake.FORM_DELIVERY_ALERTER, *intake.FORM_SECURITY_ALERTERS.values()]
        before = [(list(item._failures), item._last_alert_at) for item in others]
        with patch.object(self.alerter, "_send") as send:
            intake.process_submission(FIELDS, {}, self.mailer())
            intake.process_submission(FIELDS, {}, self.mailer())
        send.assert_called_once()
        self.assertEqual(before, [
            (list(item._failures), item._last_alert_at) for item in others])

    def test_http_success_even_when_receipt_and_alert_fail(self):
        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(app.server_close)
        self.addCleanup(app.shutdown)
        intake.FORM_CLIENT_RATE_LIMITER.reset()
        intake.FORM_GLOBAL_RATE_LIMITER.reset()
        self.addCleanup(intake.FORM_CLIENT_RATE_LIMITER.reset)
        self.addCleanup(intake.FORM_GLOBAL_RATE_LIMITER.reset)
        origin = f"http://127.0.0.1:{app.server_address[1]}"
        request = Request(
            origin + "/api/form-submit", data=urlencode(FIELDS).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": origin})
        mailer = self.mailer()
        with patch.object(devserver.form_antispam, "reserve", return_value=None), patch.object(
            devserver, "process_submission",
            side_effect=lambda fields, files: intake.process_submission(fields, files, mailer)
        ), patch.object(self.alerter, "_send", side_effect=OSError("private alert response")), patch.object(
            devserver.form_antispam, "release_failed"
        ) as release:
            # This pre-bound urlopen reaches only our loopback HTTP server;
            # provider transports remain blocked by setUp's patch.
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                result = json.loads(response.read())
        self.assert_accepted(result, mailer)
        release.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
