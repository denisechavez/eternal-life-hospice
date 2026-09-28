#!/usr/bin/env python3
"""Regression check: workspace artifacts must not be served publicly."""

import contextlib
import http.server
import threading
import unittest
import urllib.error
import urllib.request

from devserver import PrettyURLHandler


class QuietHandler(PrettyURLHandler):
    def log_message(self, format, *args):
        pass


class PublicArtifactExposureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def status(self, path, method):
        request = urllib.request.Request(self.base + path, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                response.read()
                return response.status
        except urllib.error.HTTPError as error:
            with contextlib.closing(error):
                error.read()
                return error.code

    def test_work_files_are_not_public(self):
        for path in (
            "/FOOTER-SNIPPET.md",
            "/FOOTER-SNIPPET%2emd",
            "/FOOTER-SNIPPET.md/",
            "/AGENTS.md",
            "/assets/analytics-consent-test-results.md",
            "/assets/social/",
            "/assets/social/index.html",
            "/assets//social/index.html",
            "//assets/social/index.html",
            "/assets/social/elh-social-brand-brief.html",
            "/assets/social/elh-amethyst.png",
            "/assets/%73ocial/index.html",
            "/assets/img/amethyst-tmp/gallery.html",
            "/assets/img/amethyst-tmp/A_cathedral.jpg",
            "/assets/test-coverage-lookup.js",
            "/assets/build-search-index.js",
            "/assets/inject_breadcrumbs.py",
            "/fix-webp-heroes.py",
            "/assets/img/",
        ):
            with self.subTest(path=path):
                for method in ("GET", "HEAD"):
                    self.assertEqual(self.status(path, method), 404)

    def test_public_site_remains_available(self):
        for path in (
            "/",
            "/robots.txt",
            "/sitemap.xml",
            "/assets/header.js",
            "/.well-known/agent-card.json",
        ):
            with self.subTest(path=path):
                for method in ("GET", "HEAD"):
                    self.assertEqual(self.status(path, method), 200)


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PublicArtifactExposureTest)
    )
    if result.wasSuccessful():
        print("SENTINEL: test-public-artifact-exposure.py OK")
    else:
        raise SystemExit(1)