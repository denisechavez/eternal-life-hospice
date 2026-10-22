#!/usr/bin/env python3
"""Offline scheduler/receipt regression tests. Never send to real recipients."""
import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.request import Request

spec = spec_from_file_location("freshness", Path(__file__).with_name("check-journal-monitor-freshness.py"))
watchdog = module_from_spec(spec)
spec.loader.exec_module(watchdog)
monitor = watchdog.monitor


class FreshnessTests(unittest.TestCase):
    now = datetime(2026, 10, 22, 15, 17, tzinfo=timezone.utc)

    def actions(self, status="healthy", alert="not-needed", message_id=None,
                conclusion="success", cron="45 13 * * *"):
        self.result = {
            "schema": 1, "checkedAt": "2026-10-22T13:47:00+00:00",
            "scheduledCron": cron, "status": status,
            "alert": alert, "messageId": message_id,
        }
        self.run = {"id": 1, "event": "schedule", "status": "completed", "conclusion": conclusion}
        self.artifact = {"id": 2, "name": "journal-monitor-result", "expired": False}
        self.runs = [self.run]

        def get(path, binary=False):
            if path.endswith("journal-release.yml"):
                return {"state": "active"}
            if "/runs?" in path:
                self.assertIn("event=schedule", path)
                return {"workflow_runs": self.runs}
            if "/artifacts?" in path:
                return {"artifacts": [self.artifact]}
            if path.endswith("/zip"):
                archive = io.BytesIO()
                with zipfile.ZipFile(archive, "w") as target:
                    target.writestr("journal-monitor-result.json", json.dumps(self.result))
                return archive.getvalue()
            raise AssertionError(path)
        return Mock(get=Mock(side_effect=get))

    def test_healthy_run(self):
        self.assertEqual(watchdog.check(self.actions(), self.now), [])

    def test_article_gap_with_accepted_email_is_not_missing_run(self):
        actions = self.actions("missed", "accepted", "<provider-id>", "failure")
        self.assertEqual(watchdog.check(actions, self.now), [])

    def test_monitor_unavailable_with_accepted_email_is_already_reported(self):
        actions = self.actions("unavailable", "accepted", "<provider-id>", "failure")
        self.assertEqual(watchdog.check(actions, self.now), [])

    def test_disabled_scheduler(self):
        actions = Mock()
        actions.get.return_value = {"state": "disabled_inactivity"}
        self.assertIn("disabled", watchdog.check(actions, self.now)[0])

    def test_missing_cancelled_running_manual_skipped_and_wrong_offset_runs(self):
        for change in ("missing", "cancelled", "running", "manual", "skipped", "offset", "expired", "old", "future"):
            with self.subTest(change=change):
                actions = self.actions()
                if change == "missing":
                    self.runs.clear()
                elif change == "cancelled":
                    self.run["conclusion"] = "cancelled"
                elif change == "running":
                    self.run["status"] = "in_progress"
                elif change == "manual":
                    self.run["event"] = "workflow_dispatch"
                elif change == "skipped":
                    self.result["status"] = "skipped"
                elif change == "offset":
                    self.result["scheduledCron"] = "45 14 * * *"
                elif change == "expired":
                    self.artifact["expired"] = True
                elif change == "old":
                    self.result["checkedAt"] = "2026-10-21T13:47:00+00:00"
                else:
                    self.result["checkedAt"] = "2026-10-23T13:47:00+00:00"
                self.assertTrue(watchdog.check(actions, self.now))

    def test_failed_or_suppressed_email_and_missing_receipt_are_unverified(self):
        for alert, receipt in (("failed", None), ("suppressed", None), ("accepted", None), ("accepted", "")):
            with self.subTest(alert=alert, receipt=receipt):
                actions = self.actions("missed", alert, receipt, "failure")
                self.assertIn("provider acceptance", watchdog.check(actions, self.now)[0])

    def test_crash_after_healthy_result_is_unverified(self):
        self.assertTrue(watchdog.check(self.actions(conclusion="failure"), self.now))

    def test_dst_offsets_and_grace_period(self):
        for day, hour in (("2026-03-08", 13), ("2026-11-01", 14),
                          ("2026-03-07", 14), ("2026-10-31", 13)):
            local = datetime.fromisoformat(day).replace(tzinfo=watchdog.PACIFIC)
            check_time = local.replace(hour=8, minute=17).astimezone(timezone.utc)
            self.assertEqual(watchdog.expected_run(check_time).hour, hour)
            self.assertEqual(watchdog.expected_run(check_time).astimezone(watchdog.PACIFIC).date(), local.date())
            self.assertTrue(watchdog.scheduled_today(f"17 {hour+2} * * *", check_time))
            self.assertFalse(watchdog.scheduled_today(f"17 {29-hour} * * *", check_time))
            before = local.replace(hour=8, minute=14).astimezone(timezone.utc)
            self.assertEqual(watchdog.expected_run(before).astimezone(watchdog.PACIFIC).date(),
                             local.date() - timedelta(days=1))

    def test_api_failure_is_monitoring_warning_without_sending_in_no_email_mode(self):
        with patch.object(watchdog, "Actions", side_effect=OSError("offline")), \
             patch.object(monitor, "notify") as notify, \
             patch.object(watchdog.sys, "argv", ["watchdog", "--repository", "owner/repo", "--no-email"]):
            self.assertEqual(watchdog.main(), 1)
            notify.assert_not_called()

    def test_artifact_redirect_does_not_forward_actions_token_to_storage(self):
        request = Request("https://api.github.com/repos/owner/repo/actions/artifacts/1/zip",
                          headers={"Authorization": "Bearer fake", "Accept": "application/json"})
        redirected = watchdog.SafeRedirect().redirect_request(
            request, None, 302, "", {}, "https://storage.example.invalid/artifact.zip")
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(redirected.get_header("Accept"), "application/json")

    def test_watchdog_alert_failure_is_visible(self):
        with patch.object(watchdog, "Actions", side_effect=OSError("offline")), \
             patch.object(monitor, "notify", side_effect=OSError("rejected")) as notify, \
             patch.object(watchdog.sys, "argv", ["watchdog", "--repository", "owner/repo"]):
            self.assertEqual(watchdog.main(), 2)
            self.assertTrue(notify.call_args.kwargs["missing_run"])

    def test_missing_run_subject_is_distinct_and_cannot_authorize_drafts(self):
        with patch.dict(os.environ, {"BREVO_API": "fake-test-key"}), \
             patch.object(monitor.email, "send_alert", return_value="<fake-id>") as send:
            self.assertEqual(monitor.notify(["Run missing"], monitoring_unavailable=True, missing_run=True), "<fake-id>")
            message = send.call_args.args[1]
            self.assertIn("monitor run missing", message["subject"])
            self.assertNotIn("publication gap", message["subject"])
            self.assertIn("not evidence that a held draft should publish", message["textContent"])
            self.assertTrue(send.call_args.kwargs["require_message_id"])

    def test_primary_receipt_for_healthy_skipped_unavailable_and_provider_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "receipt.json"
            for status, no_email, fail in (("healthy", False, False), ("missed", False, False),
                                           ("unavailable", True, False), ("missed", False, True),
                                           ("not-installed", True, False)):
                with self.subTest(status=status, fail=fail), \
                     patch.object(monitor, "check", return_value=(status, ["test"])), \
                     patch.object(monitor, "notify", return_value="<fake-id>",
                                  side_effect=OSError("rejected") if fail else None) as notify, \
                     patch.object(monitor.sys, "argv", ["monitor", "--site", "https://invalid.example",
                                      "--result-file", str(output)] + (["--no-email"] if no_email else [])):
                    code = monitor.main()
                    result = json.loads(output.read_text())
                    self.assertEqual(result["status"], "unavailable" if status == "not-installed" else status)
                    self.assertEqual(result["alert"], "not-needed" if status == "healthy" else
                                     "suppressed" if no_email else "failed" if fail else "accepted")
                    self.assertEqual(code, 0 if status == "healthy" else 2 if fail else 1)
                    if no_email or status == "healthy":
                        notify.assert_not_called()
            with patch.object(monitor, "scheduled_today", return_value=False), \
                 patch.object(monitor, "check") as check, \
                 patch.object(monitor.sys, "argv", ["monitor", "--site", "https://invalid.example",
                                 "--result-file", str(output)]):
                self.assertEqual(monitor.main(), 0)
                self.assertEqual(json.loads(output.read_text())["status"], "skipped")
                check.assert_not_called()


class ProviderAcceptanceTests(unittest.TestCase):
    def test_real_http_acceptance_and_rejection_against_local_fake_provider_only(self):
        class Handler(BaseHTTPRequestHandler):
            status = 201
            body = b'{"messageId":"<local-fake-id>"}'

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(self.status)
                self.end_headers()
                self.wfile.write(self.body)

            def log_message(self, *_):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}/email"
            for code, body, accepted in ((201, b'{"messageId":"<local-fake-id>"}', True),
                                          (201, b'{}', False), (201, b'not json', False),
                                          (202, b'{"messageId":""}', False), (401, b'{}', False),
                                          (429, b'{}', False), (500, b'{}', False)):
                Handler.status, Handler.body = code, body
                with self.subTest(code=code, body=body):
                    if accepted:
                        self.assertEqual(monitor.email.send_alert("fake", {"to": [{"email": "test@example.invalid"}]},
                            endpoint, require_message_id=True), "<local-fake-id>")
                    else:
                        with self.assertRaises((OSError, ValueError)):
                            monitor.email.send_alert("fake", {}, endpoint, require_message_id=True)
        finally:
            server.shutdown()
            worker.join()
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
