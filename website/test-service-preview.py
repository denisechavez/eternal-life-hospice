"""Safety and scope checks for the review-only care-community page."""
import io
import os
import unittest
from unittest.mock import patch

import service_preview as preview


class Handler:
    def __init__(self, path, command="GET"):
        self.path, self.command = path, command
        self.wfile = io.BytesIO()
        self.headers = {}

    def send_error(self, status):
        self.status = status

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers[key] = value

    def end_headers(self):
        pass


class PreviewTests(unittest.TestCase):
    def test_production_never_serves_preview_or_assets(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            for path in (preview.ROUTE, preview.ROUTE + ".html",
                         preview.ASSET_PREFIX + "hero.webp"):
                handler = Handler(path)
                self.assertTrue(preview.serve(handler, lambda value: value))
                self.assertEqual(handler.status, 404)
                self.assertEqual(handler.wfile.getvalue(), b"")

    def test_production_navigation_is_unchanged(self):
        document = '<header><a href="/services">All Services</a></header>'
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            self.assertEqual(preview.decorate(document, "/services"), document)

    def test_header_link_only_and_service_listing_exception(self):
        document = ('<header><a href="/services">All Services</a></header>'
                    '<main><div class="rgrid">Existing content</div></main>'
                    '<footer><a href="/services">All Services</a></footer>')
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
            output = preview.decorate(document, "/")
            self.assertEqual(output.count(preview.ROUTE), 1)
            self.assertIn('<main><div class="rgrid">Existing content</div></main>', output)
            self.assertIn('<footer><a href="/services">All Services</a></footer>', output)
            listing = preview.decorate(document, "/services")
            self.assertEqual(listing.count(preview.ROUTE), 2)
            self.assertIn("Existing content", listing)

    def test_asset_allowlist_rejects_traversal(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
            handler = Handler(preview.ASSET_PREFIX + "../../devserver.py")
            self.assertTrue(preview.serve(handler, lambda value: value))
            self.assertEqual(handler.status, 404)
            handler = Handler("/unrelated-page")
            self.assertFalse(preview.serve(handler, lambda value: value))

    def test_preview_head_and_noindex(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
            handler = Handler(preview.ROUTE, "HEAD")
            self.assertTrue(preview.serve(handler, lambda value: value))
            self.assertEqual(handler.status, 200)
            self.assertEqual(handler.headers["X-Robots-Tag"], "noindex, nofollow")
            self.assertEqual(handler.headers["Cache-Control"], "no-store")
            self.assertEqual(handler.wfile.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
