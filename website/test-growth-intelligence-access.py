#!/usr/bin/env python3
"""Production must never expose workspace Growth Intelligence UI or reports."""
import http.client
import http.server
import json
import os
import subprocess
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from devserver import CANVAS_HUB, PrettyURLHandler


REPORTS = {
    "/canvas-hub/dashboard/api/elh-reporting": "google",
    "/canvas-hub/dashboard/api/whatconverts-reporting": "whatconverts",
    "/canvas-hub/dashboard/api/brevo-reporting": "brevo",
}


class QuietHandler(PrettyURLHandler):
    def log_message(self, *args):
        pass


class GrowthIntelligenceAccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_production_blocks_dashboard_and_all_static_dependencies(self):
        dashboard = Path(CANVAS_HUB) / "dashboard"
        paths = ["/growth-intelligence", "/growth-intelligence/",
                 "/growth-intelligence?period=ytd", "/canvas-hub/dashboard",
                 "/canvas-hub/dashboard/"]
        paths += ["/canvas-hub/dashboard/" + str(path.relative_to(dashboard))
                  for path in dashboard.rglob("*") if path.is_file()]
        paths += [
            "/canvas-hub/%64ashboard/index.html",
            "/canvas-hub/dashboard/../dashboard/index.html",
            "/canvas-hub//dashboard/index.html",
            "/canvas-hub%2fdashboard/index.html",
            "/%67rowth-intelligence",
        ]
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            for path in paths:
                for method in ("GET", "HEAD"):
                    with self.subTest(path=path, method=method):
                        status, headers, body = self.request(path, method)
                        self.assertEqual(status, 404)
                        self.assertEqual(headers["Cache-Control"], "no-store")
                        if method == "HEAD":
                            self.assertEqual(body, b"")

    def test_production_blocks_reports_before_spawning_provider(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}), \
                patch("devserver.subprocess.run") as reporter:
            for path in REPORTS:
                for method in ("GET", "HEAD"):
                    for headers in ({}, {"Origin": "https://example.invalid"},
                                    {"Cookie": "__session=invalid",
                                     "Origin": "https://eternallifehospice.com"}):
                        with self.subTest(path=path, method=method, headers=headers):
                            status, response_headers, body = self.request(
                                path + "?period=ytd", method, headers)
                            self.assertEqual(status, 404)
                            self.assertEqual(response_headers["Cache-Control"], "no-store")
                            self.assertNotIn(b'"live"', body)
            reporter.assert_not_called()

    def test_workspace_dashboard_and_reports_remain_available(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
            for path in ("/growth-intelligence", "/canvas-hub/dashboard/index.html",
                         "/canvas-hub/dashboard/favicon.svg"):
                for method in ("GET", "HEAD"):
                    with self.subTest(path=path, method=method):
                        self.assertEqual(self.request(path, method)[0], 200)
            for path, source in REPORTS.items():
                result = subprocess.CompletedProcess([], 0, '{"live":true}', "")
                with patch("devserver.subprocess.run", return_value=result) as reporter:
                    status, _, body = self.request(path + "?period=ytd")
                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(body), {"live": True})
                    self.assertEqual(reporter.call_args.args[0][-2:], [source, "ytd"])

    def test_public_health_unaffected_in_production(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            for method in ("GET", "HEAD"):
                self.assertEqual(self.request("/healthz", method)[0], 200)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("SENTINEL: test-growth-intelligence-access.py OK")
