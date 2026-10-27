"""Real guard/HTTP/PostgreSQL tests; synthetic mailer, no real submissions."""
import concurrent.futures
import io
import json
import os
import threading
import unittest
import uuid
from http.server import ThreadingHTTPServer
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg
from psycopg.rows import dict_row
import devserver
import form_antispam as guard
import form_intake


class OriginChecksTests(unittest.TestCase):
    def test_browser_get_metadata_is_scoped_to_challenge_get_only(self):
        handler = object.__new__(devserver.PrettyURLHandler)
        handler.command = "GET"
        handler.headers = {"Host": "eternallifehospice.com",
                           "Sec-Fetch-Site": "same-origin",
                           "Referer": "https://eternallifehospice.com/refer"}
        self.assertTrue(handler._is_same_origin(allow_same_origin_get=True))
        self.assertFalse(handler._is_same_origin())
        handler.command = "POST"
        self.assertFalse(handler._is_same_origin(allow_same_origin_get=True))
        handler.command = "GET"
        handler.headers.pop("Referer")
        self.assertTrue(handler._is_same_origin(allow_same_origin_get=True))
        for metadata in ("cross-site", "same-site", "none", ""):
            handler.headers["Sec-Fetch-Site"] = metadata
            self.assertFalse(handler._is_same_origin(allow_same_origin_get=True))

    def test_explicit_bad_origin_and_mismatched_referrer_remain_rejected(self):
        handler = object.__new__(devserver.PrettyURLHandler)
        handler.command = "GET"
        handler.headers = {"Host": "eternallifehospice.com",
                           "Sec-Fetch-Site": "same-origin",
                           "Referer": "https://other.invalid/refer"}
        self.assertFalse(handler._is_same_origin(allow_same_origin_get=True))
        handler.headers["Referer"] = "https://eternallifehospice.com/refer"
        for origin in ("https://other.invalid", "null", "file://eternallifehospice.com"):
            handler.headers["Origin"] = origin
            self.assertFalse(handler._is_same_origin(allow_same_origin_get=True))
        handler.headers["Origin"] = "https://eternallifehospice.com"
        self.assertTrue(handler._is_same_origin())


class SecurityAlertTests(unittest.TestCase):
    def test_threshold_window_cooldown_and_bounded_memory(self):
        alerter = form_intake.DeliveryFailureAlerter(
            webhook_url="https://synthetic.invalid/alert", environment="test",
            failure_threshold=3, window_seconds=300, cooldown_seconds=900,
            processor_status="guard_storage_unavailable")
        with patch.object(alerter, "_send") as send, patch.object(form_intake.time, "monotonic") as clock:
            # Old isolated failures must not combine with a later incident.
            for timestamp in [0, 301, 302]:
                clock.return_value = timestamp
                self.assertFalse(alerter.record_failure())
            clock.return_value = 303
            self.assertTrue(alerter.record_failure())
            for timestamp in range(304, 1500):
                clock.return_value = timestamp
                alerter.record_failure()
            self.assertEqual(send.call_count, 2)
            self.assertLessEqual(len(alerter._failures), 1000)
            payload = send.call_args.args[0]
            self.assertEqual(set(payload), {
                "timestamp", "environment", "processor_status", "failure_count"})
            self.assertEqual(payload["processor_status"], "guard_storage_unavailable")

    def test_no_channel_and_alert_failure_are_safe(self):
        self.assertFalse(form_intake.DeliveryFailureAlerter(
            webhook_url="", failure_threshold=1).record_failure())
        alerter = form_intake.DeliveryFailureAlerter(
            webhook_url="https://synthetic.invalid/private", failure_threshold=1)
        with patch.object(alerter, "_send", side_effect=OSError("secret response")), patch(
            "sys.stderr", new_callable=io.StringIO
        ) as log:
            self.assertTrue(alerter.record_failure())
            self.assertFalse(alerter.record_failure())
            self.assertNotIn("secret response", log.getvalue())
            self.assertNotIn("private", log.getvalue())

    def test_concurrent_failures_only_send_one_alert(self):
        alerter = form_intake.DeliveryFailureAlerter(
            webhook_url="https://synthetic.invalid/alert")
        with patch.object(alerter, "_send") as send:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: alerter.record_failure(), range(100)))
            self.assertEqual(send.call_count, 1)

    def test_webhook_receives_only_operational_payload(self):
        alerter = form_intake.DeliveryFailureAlerter(
            webhook_url="https://synthetic.invalid/alert", environment="test",
            failure_threshold=1, processor_status="turnstile_unavailable")
        response = Mock(status=204)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(form_intake.urllib.request, "urlopen", return_value=response) as send:
            self.assertTrue(alerter.record_failure())
        request = send.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(set(payload), {
            "timestamp", "environment", "processor_status", "failure_count"})
        self.assertEqual(payload["processor_status"], "turnstile_unavailable")
        self.assertEqual(send.call_args.kwargs["timeout"], 5)


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("REPLIT_DEPLOYMENT") == "1":
            raise RuntimeError("Do not run tests against production")
        cls.real_connect = guard.connect
        cls.schema = "intake_test_" + uuid.uuid4().hex
        with cls.real_connect() as db:
            db.execute(f'CREATE SCHEMA "{cls.schema}"')
        cls.connection = patch.object(guard, "connect", lambda: psycopg.connect(
            os.environ["DATABASE_URL"], options=f"-c search_path={cls.schema}", row_factory=dict_row))
        cls.environment = patch.dict(os.environ, {
            "SESSION_SECRET": "synthetic-intake-key-not-a-real-secret-123456",
            "TURNSTILE_SITE_KEY": "", "TURNSTILE_SECRET_KEY": ""})
        cls.connection.start()
        cls.environment.start()
        guard.initialize()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.connection.stop()
        cls.environment.stop()
        with cls.real_connect() as db:
            db.execute(f'DROP SCHEMA "{cls.schema}" CASCADE')

    def setUp(self):
        with guard.connect() as db:
            db.execute("TRUNCATE intake_abuse_guard")
        form_intake.FORM_CLIENT_RATE_LIMITER.reset()
        form_intake.FORM_GLOBAL_RATE_LIMITER.reset()
        self.age = patch.object(guard, "MIN_AGE_SECONDS", 0)
        self.age.start()
        self.addCleanup(self.age.stop)
        mail_patch = patch.object(devserver, "process_submission", return_value={
            "ok": True, "accepted": True, "receipt_id": "SYNTHETIC",
            "acknowledgement_sent": False})
        self.mail = mail_patch.start()
        self.addCleanup(mail_patch.stop)
        # Never use the real operations channel during synthetic outages.
        self.alerters = {
            status: form_intake.DeliveryFailureAlerter(
                webhook_url="https://synthetic.invalid/alert", environment="test",
                processor_status=status)
            for status in form_intake.FORM_SECURITY_ALERTERS
        }
        alerts = patch.object(form_intake, "FORM_SECURITY_ALERTERS", self.alerters)
        alerts.start()
        self.addCleanup(alerts.stop)
        for alerter in self.alerters.values():
            send = patch.object(alerter, "_send")
            send.start()
            self.addCleanup(send.stop)
        self.fields = {"form-name": "elh-family", "first_name": "Synthetic",
                       "last_name": "Family", "phone": "2025550190", "message": "Please call."}

    def request(self, path, data=None, origin=None):
        headers = {"Origin": origin or self.origin, "Content-Type": "application/x-www-form-urlencoded"}
        request = Request(self.origin + path, headers=headers,
                          data=urlencode(data).encode() if data is not None else None)
        try:
            with urlopen(request, timeout=8) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def protected(self, fields=None):
        fields = dict(fields or self.fields)
        status, response = self.request("/api/form-security?form=" + fields["form-name"])
        self.assertEqual(status, 200)
        fields["_elh_security"] = response["token"]
        return fields

    def test_real_browser_style_challenge_get_and_synthetic_referral(self):
        # Same-origin GET fetches carry Fetch Metadata, not normally Origin.
        request = Request(self.origin + "/api/form-security?form=elh-physician",
                          headers={"Sec-Fetch-Site": "same-origin",
                                   "Referer": self.origin + "/refer",
                                   "Accept": "application/json"})
        with urlopen(request, timeout=8) as response:
            self.assertEqual(response.status, 200)
            security = json.loads(response.read())
        self.mail.assert_not_called()
        fields = {"form-name": "elh-physician", "referrer_name": "Synthetic Professional",
                  "phone": "2025550190",
                  "message": "Synthetic regression only.",
                  "_elh_security": security["token"]}
        self.assertEqual(self.request("/api/form-submit", fields)[0], 200)
        self.mail.assert_called_once()

    def test_cross_site_challenge_get_without_origin_is_rejected(self):
        request = Request(self.origin + "/api/form-security?form=elh-physician",
                          headers={"Sec-Fetch-Site": "cross-site",
                                   "Referer": "https://other.invalid/"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=8)
        self.assertEqual(caught.exception.code, 403)
        self.mail.assert_not_called()

    def test_direct_bot_and_tampered_token_cannot_deliver(self):
        self.assertEqual(self.request("/api/form-submit", self.fields)[0], 403)
        fields = self.protected()
        fields["_elh_security"] += "tampered"
        self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
        self.mail.assert_not_called()

    def test_legitimate_202_number_is_allowed_and_replay_is_blocked(self):
        fields = self.protected()
        self.assertEqual(self.request("/api/form-submit", fields)[0], 200)
        self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
        self.assertEqual(self.mail.call_count, 1)

    def test_duplicate_with_new_token_is_not_delivered_twice(self):
        self.assertEqual(self.request("/api/form-submit", self.protected())[0], 200)
        status, response = self.request("/api/form-submit", self.protected())
        self.assertEqual(status, 429)
        self.assertEqual(response["error"], "duplicate_submission")
        self.assertEqual(self.mail.call_count, 1)

    def test_contact_burst_limit_does_not_block_all_202_numbers(self):
        for index in range(4):
            fields = self.protected({**self.fields, "message": f"Request {index}"})
            self.assertEqual(self.request("/api/form-submit", fields)[0], 200 if index < 3 else 429)
        other = self.protected({**self.fields, "phone": "2025550191"})
        self.assertEqual(self.request("/api/form-submit", other)[0], 200)

    def test_rotating_numbers_cannot_bypass_email_burst_limit(self):
        for index in range(4):
            fields = self.protected({**self.fields, "phone": f"202555019{index}",
                                     "email": "synthetic@example.com"})
            self.assertEqual(self.request("/api/form-submit", fields)[0], 200 if index < 3 else 429)

    def test_professional_office_can_send_multiple_referrals(self):
        for index in range(4):
            fields = self.protected({"form-name": "elh-physician", "referrer_name": "Synthetic Physician",
                                     "phone": "2025550190", "situation": f"General request {index}"})
            self.assertEqual(self.request("/api/form-submit", fields)[0], 200)

    def test_minimum_age_and_expiration_enforced(self):
        with patch.object(guard, "MIN_AGE_SECONDS", 1.8):
            self.assertEqual(self.request("/api/form-submit", self.protected())[0], 403)
        fields = self.protected()
        import time
        with patch.object(guard.time, "time", return_value=time.time()+1900):
            self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
        self.mail.assert_not_called()

    def test_cross_form_and_cross_origin_tokens_cannot_deliver(self):
        fields = self.protected()
        fields.update({"form-name": "elh-chat-callback", "name": "Synthetic Caller"})
        self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
        self.assertEqual(self.request("/api/form-submit", self.protected(), "https://attacker.invalid")[0], 403)
        self.mail.assert_not_called()

    def test_concurrent_replay_only_delivers_once(self):
        fields = self.protected()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: self.request("/api/form-submit", fields)[0], range(2)))
        self.assertEqual(sorted(statuses), [200, 403])
        self.assertEqual(self.mail.call_count, 1)

    def test_delivery_failure_allows_fresh_token_retry(self):
        self.mail.side_effect = [form_intake.DeliveryError("Synthetic outage"), self.mail.return_value]
        with patch.object(devserver, "notify_delivery_failure"):
            self.assertEqual(self.request("/api/form-submit", self.protected())[0], 502)
        self.assertEqual(self.request("/api/form-submit", self.protected())[0], 200)

    def test_turnstile_checks_server_response_hostname_and_action(self):
        with patch.dict(os.environ, {"TURNSTILE_SITE_KEY": "synthetic-public", "TURNSTILE_SECRET_KEY": "synthetic-private"}):
            for result in [
                {"success": False},
                {"success": True, "hostname": "attacker.invalid", "action": "intake"},
                {"success": True, "hostname": "127.0.0.1", "action": "other"},
            ]:
                response = Mock()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                response.read.return_value = json.dumps(result).encode()
                with patch.object(guard, "urlopen", return_value=response):
                    fields = {**self.protected(), "cf-turnstile-response": "synthetic-response"}
                    self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
            self.mail.assert_not_called()
            with patch.object(guard, "urlopen", side_effect=TimeoutError):
                self.assertEqual(self.request("/api/form-submit", {**self.protected(), "cf-turnstile-response": "synthetic"})[0], 503)
            response.read.return_value = json.dumps({"success": True, "hostname": "127.0.0.1", "action": "intake"}).encode()
            with patch.object(guard, "urlopen", return_value=response):
                self.assertEqual(self.request("/api/form-submit", {**self.protected(), "cf-turnstile-response": "synthetic"})[0], 200)
            self.assertEqual(self.mail.call_count, 1)

    def test_chat_cache_busted_without_changing_editorial_source(self):
        original = '<script defer src="/assets/chat.js?v=20260805"></script>'
        updated = guard.refresh_assets(original)
        self.assertIn("v=" + guard.CHAT_VERSION, updated)
        self.assertNotIn("20260805", updated)

    def test_guard_storage_outage_fails_closed_with_phone_fallback(self):
        fields = self.protected()
        with patch.object(guard, "connect", side_effect=OSError("Synthetic outage")):
            status, response = self.request("/api/form-submit", fields)
        self.assertEqual(status, 503)
        self.assertIn("805.953.7273", response["message"])
        self.mail.assert_not_called()

    def test_sustained_storage_outage_alerts_without_request_data(self):
        fields = self.protected()
        with patch.object(guard, "connect", side_effect=OSError(
            "private database error 2025550190 synthetic@example.com"
        )):
            for _ in range(4):
                status, response = self.request("/api/form-submit", fields)
                self.assertEqual(status, 503)
                self.assertIn("805.953.7273", response["message"])
        send = self.alerters["guard_storage_unavailable"]._send
        send.assert_called_once()
        payload = send.call_args.args[0]
        self.assertEqual(payload["failure_count"], 3)
        self.assertEqual(payload["processor_status"], "guard_storage_unavailable")
        for value in list(fields.values()) + ["127.0.0.1", "private database error"]:
            self.assertNotIn(value, json.dumps(payload))
        self.alerters["turnstile_unavailable"]._send.assert_not_called()
        self.mail.assert_not_called()

    def test_turnstile_outages_are_distinct_from_rejections(self):
        with patch.dict(os.environ, {
            "TURNSTILE_SITE_KEY": "synthetic-public",
            "TURNSTILE_SECRET_KEY": "synthetic-private",
        }):
            fields = {**self.protected(), "cf-turnstile-response": "synthetic-token"}
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            for result in [
                {"success": False, "error-codes": ["invalid-input-response"]},
                {"success": False, "error-codes": ["timeout-or-duplicate"]},
                {"success": True, "hostname": "wrong.invalid", "action": "intake"},
                {"success": True, "hostname": "127.0.0.1", "action": "other"},
            ]:
                response.read.return_value = json.dumps(result).encode()
                with patch.object(guard, "urlopen", return_value=response):
                    self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
            self.assertEqual(len(self.alerters["turnstile_unavailable"]._failures), 0)
            for result in [
                {"success": False, "error-codes": ["internal-error"]},
                {"success": False, "error-codes": ["invalid-input-secret"]},
                [], {"unexpected": "response"},
                {"success": True, "hostname": None, "action": "intake"},
            ]:
                form_intake.FORM_CLIENT_RATE_LIMITER.reset()
                response.read.return_value = json.dumps(result).encode()
                with patch.object(guard, "urlopen", return_value=response):
                    status, public = self.request("/api/form-submit", fields)
                    self.assertEqual(status, 503)
                    self.assertIn("805.953.7273", public["message"])
            for error in [TimeoutError("private token"), OSError("private URL")]:
                form_intake.FORM_CLIENT_RATE_LIMITER.reset()
                with patch.object(guard, "urlopen", side_effect=error):
                    self.assertEqual(self.request("/api/form-submit", fields)[0], 503)
            response.read.return_value = b"not JSON"
            form_intake.FORM_CLIENT_RATE_LIMITER.reset()
            with patch.object(guard, "urlopen", return_value=response):
                self.assertEqual(self.request("/api/form-submit", fields)[0], 503)
            self.alerters["turnstile_unavailable"]._send.assert_called_once()
            self.alerters["guard_storage_unavailable"]._send.assert_not_called()
            self.mail.assert_not_called()

    def test_configuration_outage_alerts_on_token_endpoint(self):
        with patch.dict(os.environ, {"TURNSTILE_SITE_KEY": "synthetic-public",
                                     "TURNSTILE_SECRET_KEY": ""}):
            for _ in range(4):
                status, public = self.request("/api/form-security?form=elh-family")
                self.assertEqual(status, 503)
                self.assertIn("805.953.7273", public["message"])
        self.alerters["turnstile_unavailable"]._send.assert_called_once()

    def test_ordinary_rejections_do_not_alert(self):
        self.assertEqual(self.request("/api/form-submit", self.fields)[0], 403)
        fields = self.protected()
        self.assertEqual(self.request("/api/form-submit", fields)[0], 200)
        self.assertEqual(self.request("/api/form-submit", fields)[0], 403)
        self.assertEqual(self.request("/api/form-submit", self.protected())[0], 429)
        for alerter in self.alerters.values():
            self.assertEqual(len(alerter._failures), 0)
            alerter._send.assert_not_called()

    def test_query_and_commit_outages_are_storage_failures(self):
        for commit in [False, True]:
            with self.subTest(commit=commit):
                db = Mock()
                db.__enter__ = Mock(return_value=db)
                db.__exit__ = Mock(return_value=False, side_effect=OSError("private database error") if commit else None)
                db.execute.side_effect = None if commit else OSError("private query")
                with patch.object(guard, "connect", return_value=db):
                    status, public = self.request("/api/form-submit", self.protected())
                    self.assertEqual(status, 503)
                    self.assertIn("805.953.7273", public["message"])
        self.assertEqual(len(self.alerters["guard_storage_unavailable"]._failures), 2)
        self.mail.assert_not_called()

    def test_alert_channel_outage_does_not_change_public_fallback(self):
        fields = self.protected()
        alerter = self.alerters["guard_storage_unavailable"]
        alerter._send.side_effect = OSError("private webhook response")
        with patch.object(guard, "connect", side_effect=OSError("private database")):
            for _ in range(4):
                status, public = self.request("/api/form-submit", fields)
                self.assertEqual(status, 503)
                self.assertEqual(public["error"], "security_unavailable")
                self.assertIn("805.953.7273", public["message"])
        alerter._send.assert_called_once()
        self.mail.assert_not_called()

    def test_retry_cleanup_storage_outage_keeps_delivery_fallback(self):
        self.mail.side_effect = form_intake.DeliveryError("synthetic delivery failure")
        real_connect = guard.connect
        fields = self.protected()
        # Reservations succeed; only releasing the failed-delivery slot fails.
        calls = [real_connect(), OSError("private cleanup error")]
        with patch.object(guard, "connect", side_effect=calls), patch.object(
            devserver, "notify_delivery_failure"
        ):
            status, public = self.request("/api/form-submit", fields)
        self.assertEqual(status, 502)
        self.assertIn("805.953.7273", public["message"])
        self.assertEqual(len(self.alerters["guard_storage_unavailable"]._failures), 1)

    def test_missing_signing_configuration_alerts_without_logging_secret(self):
        with patch.dict(os.environ, {"SESSION_SECRET": ""}):
            for _ in range(3):
                status, public = self.request("/api/form-security?form=elh-family")
                self.assertEqual(status, 503)
                self.assertIn("805.953.7273", public["message"])
        self.alerters["guard_configuration_unavailable"]._send.assert_called_once()
        self.alerters["turnstile_unavailable"]._send.assert_not_called()

    def test_no_contact_details_are_persisted(self):
        self.assertEqual(self.request("/api/form-submit", self.protected())[0], 200)
        with guard.connect() as db:
            records = str(db.execute("SELECT * FROM intake_abuse_guard").fetchall())
        for value in ["2025550190", "Synthetic", "Please call.", "127.0.0.1"]:
            self.assertNotIn(value, records)


if __name__ == "__main__":
    unittest.main(verbosity=2)
