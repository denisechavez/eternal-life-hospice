"""Exercise approved pages through the real production HTTP handler."""
import html
import http.client
import json
import os
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import devserver
import service_preview


class PublicationHandler(devserver.PrettyURLHandler):
    def log_message(self, *_):
        pass

    def _journal_pages(self):
        return {}

    def _released_journal(self):
        return {}


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"})
        cls.environment.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), PublicationHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.environment.stop()

    def request(self, path, method="GET"):
        client = http.client.HTTPConnection(*self.server.server_address, timeout=15)
        try:
            client.request(method, path)
            response = client.getresponse()
            return response.status, {key.title(): value for key, value in response.getheaders()}, response.read()
        finally:
            client.close()

    def test_all_eleven_pages_are_public_indexable_and_use_public_assets(self):
        for route in ("/services", *("/services/" + s for s in service_preview.SLUGS)):
            for method in ("GET", "HEAD"):
                status, headers, body = self.request(route, method)
                self.assertEqual(status, 200, (route, method))
                self.assertNotIn("noindex", headers.get("X-Robots-Tag", ""))
                self.assertIn("must-revalidate", headers["Cache-Control"])
                if method == "HEAD":
                    self.assertEqual(body, b"")
                    continue
                document = body.decode()
                self.assertIn('content="index,follow"', document)
                self.assertNotRegex(document, r'<meta name="robots" content="[^"]*noindex')
                self.assertNotIn(service_preview.ASSET_PREFIX, document)
                self.assertEqual(document.count('rel="canonical"'), 1)
                self.assertIn('href="https://eternallifehospice.com' + route + '"', document)
                self.assertIn('/assets/service-pages/service-hero-edge.css', document)
                self.assertEqual(document.count('id="sp-services-menu"'), 1)
                for asset in re.findall(r'(?:src|href)="(/assets/service-pages/[^"]+)"', document):
                    self.assertEqual(self.request(html.unescape(asset))[0], 200, asset)

    def test_all_approved_photographs_are_included_in_public_bundle(self):
        for name in service_preview.IMAGE_NAMES:
            status, headers, body = self.request(service_preview.PUBLIC_ASSET_PREFIX + name)
            self.assertEqual(status, 200, name)
            self.assertEqual(headers["Content-Type"], "image/webp")
            self.assertEqual(body[:4], b"RIFF")
            self.assertEqual(body[8:12], b"WEBP")

    def test_navigation_is_available_from_existing_homepage(self):
        status, _, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b'id="sp-services-menu"', body)
        for slug in service_preview.SLUGS:
            self.assertIn(('href="/services/' + slug + '"').encode(), body)

    def test_private_preview_bundle_remains_unavailable(self):
        for asset in ("hero.webp", "navigation.css", "catalog.json", "../previews/catalog.json"):
            for method in ("GET", "HEAD"):
                self.assertEqual(self.request(service_preview.ASSET_PREFIX + asset, method)[0], 404)

    def test_search_and_sitemap_include_all_services(self):
        site = service_preview.BASE / "elh-preview"
        entries = json.loads((site / "assets/search-index.json").read_text())
        urls = [entry["url"] for entry in entries]
        sitemap = (site / "sitemap.xml").read_text()
        for route in ("/services", *("/services/" + s for s in service_preview.SLUGS)):
            self.assertEqual(urls.count(route), 1, route)
            self.assertEqual(sitemap.count("<loc>https://eternallifehospice.com" + route + "</loc>"), 1)

    def test_directory_guard_catches_missing_or_changed_service_links(self):
        source = (service_preview.BASE / "elh-preview/services.html").read_text()
        self.assertEqual(service_preview.directory_issues(source), [])
        self.assertTrue(service_preview.directory_issues(source.replace(
            'href="/services/hospice-evaluation"', 'href="/missing-service"', 1)))
        self.assertTrue(service_preview.directory_issues(source.replace(
            'class="directory-item"', 'class="missing-item"', 1)))


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-service-publication.py OK")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)
