"""Real guard/HTTP/PostgreSQL tests; synthetic mailer, no real submissions."""
import concurrent.futures
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

    def test_no_contact_details_are_persisted(self):
        self.assertEqual(self.request("/api/form-submit", self.protected())[0], 200)
        with guard.connect() as db:
            records = str(db.execute("SELECT * FROM intake_abuse_guard").fetchall())
        for value in ["2025550190", "Synthetic", "Please call.", "127.0.0.1"]:
            self.assertNotIn(value, records)


if __name__ == "__main__":
    unittest.main(verbosity=2)
