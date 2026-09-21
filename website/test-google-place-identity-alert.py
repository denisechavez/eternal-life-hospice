#!/usr/bin/env python3
"""Regression test for the Google Place identity failure notification path."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "identity_alert", HERE / "notify-google-place-identity.py"
)
identity_alert = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity_alert)


class CaptureHandler(BaseHTTPRequestHandler):
    payload = None
    api_key = None

    def do_POST(self):
        length = int(self.headers["content-length"])
        CaptureHandler.payload = json.loads(self.rfile.read(length))
        CaptureHandler.api_key = self.headers["api-key"]
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args):
        pass


class IdentityAlertTests(unittest.TestCase):
    def test_synthetic_checker_failure_notifies_owner_without_credentials(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "check-google-place-identity.py"), "--test-failure"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Synthetic Google Place identity failure test", result.stdout)

        server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        google_key = "AIza" + ("A" * 32)
        endpoint = f"http://127.0.0.1:{server.server_address[1]}/email"
        brevo_key = "synthetic-brevo-api-key"
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8") as output:
                output.write(result.stdout + f"\naccidental secret: {google_key}")
                output.flush()
                with mock.patch.dict(
                    os.environ,
                    {
                        "BREVO_API": brevo_key,
                        "GOOGLE_API_KEY": google_key,
                        "IDENTITY_ALERT_BREVO_ENDPOINT": endpoint,
                        "IDENTITY_CHECK_OUTPUT_FILE": output.name,
                        "IDENTITY_CHECK_RUN_URL": "https://github.example/actions/runs/123",
                    },
                    clear=False,
                ):
                    self.assertEqual(identity_alert.main(), 0)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        message = CaptureHandler.payload
        self.assertEqual(message["to"][0]["email"], identity_alert.ALERT_EMAIL)
        self.assertIn(identity_alert.ALERT_OWNER, message["textContent"])
        self.assertIn("Synthetic Google Place", message["textContent"])
        self.assertIn("https://github.example/actions/runs/123", message["textContent"])
        self.assertEqual(CaptureHandler.api_key, brevo_key)
        serialized = json.dumps(message)
        self.assertNotIn(google_key, serialized)
        self.assertNotIn(brevo_key, serialized)
        self.assertIn("[REDACTED]", serialized)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    if result.result.wasSuccessful():
        print("SENTINEL: test-google-place-identity-alert.py OK")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)