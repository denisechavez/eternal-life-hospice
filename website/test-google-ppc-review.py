"""Keep the Google PPC review accessible in preview, not in production."""
import io
import os
import unittest
from unittest.mock import patch

import devserver


ROUTE = "/__reviews-mockup/elh-realtop-thank-you-review.html"


class Handler:
    def __init__(self, path=ROUTE, command="GET"):
        self.path = path
        self.command = command
        self.wfile = io.BytesIO()
        self.headers = {}

    def send_error(self, status, *_):
        self.status = status

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers[key] = value

    def end_headers(self):
        pass


class ReviewTests(unittest.TestCase):
    def serve(self, handler, production="0"):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": production}):
            return devserver.PrettyURLHandler._google_ppc_review(handler)

    def test_get_serves_review_with_no_tracking(self):
        handler = Handler(ROUTE + "?review=1")
        self.assertTrue(self.serve(handler))
        self.assertEqual(handler.status, 200)
        body = handler.wfile.getvalue()
        self.assertIn(b"Not connected to the live form", body)
        self.assertIn(b"tel:+18054099262", body)
        self.assertNotIn(b"<script", body.lower())
        self.assertEqual(int(handler.headers["Content-Length"]), len(body))
        self.assertEqual(handler.headers["Cache-Control"], "no-store")
        self.assertEqual(handler.headers["X-Robots-Tag"], "noindex, nofollow")

    def test_head_matches_get_without_body(self):
        handler = Handler(command="HEAD")
        self.serve(handler)
        self.assertEqual(handler.status, 200)
        self.assertGreater(int(handler.headers["Content-Length"]), 0)
        self.assertEqual(handler.wfile.getvalue(), b"")

    def test_production_never_opens_review_source(self):
        for command in ("GET", "HEAD"):
            with self.subTest(command=command), patch("builtins.open") as opened:
                handler = Handler(command=command)
                self.assertTrue(self.serve(handler, production="1"))
                self.assertEqual(handler.status, 404)
                opened.assert_not_called()

    def test_unknown_and_traversal_paths_are_not_exposed(self):
        for suffix in ("", "other.html", "../.replit", "%2e%2e/.replit",
                       "elh-realtop-thank-you-review.html/extra"):
            handler = Handler("/__reviews-mockup/" + suffix)
            self.assertTrue(self.serve(handler))
            self.assertEqual(handler.status, 404)

    def test_other_routes_are_unchanged(self):
        self.assertFalse(self.serve(Handler("/")))
        self.assertFalse(self.serve(Handler("/services/in-home-hospice-care")))

    def test_missing_source_reports_unavailable(self):
        with patch.object(devserver, "GOOGLE_PPC_REVIEW_SOURCE", "/nonexistent/review"):
            handler = Handler()
            self.serve(handler)
            self.assertEqual(handler.status, 503)


if __name__ == "__main__":
    unittest.main()
