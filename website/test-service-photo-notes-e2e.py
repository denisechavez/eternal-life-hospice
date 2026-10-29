#!/usr/bin/env python3
"""Disposable service rebuild/HTTP checks, independent of Journal and layout tests.

Run: python3 website/test-service-photo-notes-e2e.py
"""
from contextlib import ExitStack
from email.parser import BytesParser
from email.utils import formatdate
import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from PIL import Image
import devserver
import internal_links
import journal_photo_notes
import service_preview

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "service_photo_fixture_builder", ROOT / "build-service-previews.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

OLD_NOTE = (
    '<p class="journal-photo-credit"><small>Illustrative photograph: Fixture author / '
    '<a href="https://example.org/service-photo">Source</a> &middot; '
    '<a href="https://www.pexels.com/license/">License</a>. '
    'Resized for display. The photograph does not depict an Eternal patient '
    'or service encounter.</small></p>\n'
)
SLUG = "in-home-hospice-care"
ROUTE = "/services/" + SLUG
IMAGE_NAME = SLUG + "-hero.webp"


class ServicePhotoNoteTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.base = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.website = self.base / "website"
        self.previews = self.website / "previews"
        self.public = self.website / "elh-preview"
        self.previews.mkdir(parents=True)
        (self.public / "services").mkdir(parents=True)
        self.seed = self.previews / "seed.html"
        self.seed.write_text(
            '<header id="hdr"><p>Fixture navigation</p></header>'
            '<footer id="site-footer"><p>Fixture footer</p></footer>')
        self.seed_bytes = self.seed.read_bytes()
        images = self.base / "generated-artifacts/service-community-preview"
        images.mkdir(parents=True)
        self.image = images / IMAGE_NAME
        Image.new("RGB", (120, 80), (70, 90, 110)).save(self.image)
        self.image_bytes = self.image.read_bytes()
        self.digest = hashlib.sha256(self.image_bytes).hexdigest()
        public_images = self.public / "assets/service-pages"
        public_images.mkdir(parents=True)
        self.public_image = public_images / IMAGE_NAME
        self.public_image.write_bytes(self.image_bytes)
        # Internal provenance is deliberately outside both served directories.
        self.source = self.website / "content/service-photo-sources.json"
        self.source.parent.mkdir()
        self.source.write_text(json.dumps({
            "slug": SLUG, "image": IMAGE_NAME, "sha256": self.digest,
            "author": "Fixture author",
            "sourceUrl": "https://example.org/service-photo",
            "license": "Pexels License", "licenseUrl": "https://www.pexels.com/license/",
        }, indent=2))
        self.source_bytes = self.source.read_bytes()
        for module, values in (
            (builder, dict(OUT=self.previews, SEED=self.seed)),
            (service_preview, dict(BASE=self.website, PREVIEWS=self.previews)),
            (devserver, dict(ROOT=str(self.public))),
        ):
            for key, value in values.items():
                self.stack.enter_context(patch.object(module, key, value))
        # This fixture has no contextual-link inventory or publication state.
        self.stack.enter_context(patch.object(internal_links, "inventory", return_value={}))
        self.stack.enter_context(patch.object(
            devserver.PrettyURLHandler, "_released_journal",
            side_effect=AssertionError("Service requests must not read Journal releases")))
        self.transform = self.stack.enter_context(patch.object(
            journal_photo_notes, "public_html", wraps=journal_photo_notes.public_html))

    def assert_clean(self, document):
        for text in ("journal-photo-credit", "Illustrative photograph:",
                     "Resized for display.", "does not depict an Eternal patient"):
            self.assertNotIn(text, document)
        self.assertIn("In-Home Hospice Care", document)
        self.assertIn("Fixture navigation", document)
        self.assertIn("Fixture footer", document)

    def assert_preserved(self):
        self.assertEqual(self.seed.read_bytes(), self.seed_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        for path in (self.image, self.public_image):
            self.assertEqual(path.read_bytes(), self.image_bytes)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.digest)

    def read_head(self, port, path, headers):
        # HTTP clients normally discard HEAD bodies, hiding server regressions.
        # Read through connection close to assert the actual wire body is empty.
        request = (
            f"HEAD {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Connection: close\r\n"
            + "".join(f"{key}: {value}\r\n" for key, value in headers.items())
            + "\r\n"
        )
        with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
            connection.sendall(request.encode("ascii"))
            chunks = []
            while chunk := connection.recv(65536):
                chunks.append(chunk)
        head, body = b"".join(chunks).split(b"\r\n\r\n", 1)
        status, fields = head.split(b"\r\n", 1)
        self.assertEqual(status.split()[1], b"200")
        self.assertEqual(body, b"", "HEAD must not send any body bytes")
        return BytesParser().parsebytes(fields + b"\r\n\r\n")

    def exercise(self, production):
        self.stack.enter_context(patch.dict(
            os.environ, {"REPLIT_DEPLOYMENT": "1" if production else "0"}))

        class QuietHandler(devserver.PrettyURLHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.addCleanup(server.server_close)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        origin = "http://127.0.0.1:" + str(server.server_port)
        prefix = (service_preview.PUBLIC_ASSET_PREFIX if production
                  else service_preview.ASSET_PREFIX)
        image_url = prefix + IMAGE_NAME
        target = (self.public / "services" if production else self.previews) / (SLUG + ".html")
        clean_build = None
        for cycle in range(3):
            with self.subTest(cycle=cycle, production=production):
                builder.main()
                generated = (self.previews / (SLUG + ".html")).read_text()
                self.assert_clean(generated)
                if clean_build is not None:
                    self.assertEqual(generated, clean_build)
                clean_build = generated
                generated = generated.replace(service_preview.ASSET_PREFIX, prefix)
                self.assertGreater(generated.count(image_url), 0)
                # Simulate an older generated artifact on every rebuild. Neither
                # request-time path may rewrite this on-disk source.
                legacy = generated.replace("</main>", OLD_NOTE + OLD_NOTE + "</main>")
                target.write_text(legacy)
                before = target.read_bytes()
                self.assertEqual(legacy.count('class="journal-photo-credit"'), 2)
                clean_response = None
                modified = target.stat().st_mtime
                conditions = (
                    ("unconditional", None),
                    ("older", formatdate(modified - 86400, usegmt=True)),
                    ("matching", formatdate(modified, usegmt=True)),
                    ("newer", formatdate(modified + 86400, usegmt=True)),
                )
                for suffix in ("", ".html?refresh=1", ""):
                    for condition, date in conditions:
                        with self.subTest(suffix=suffix, condition=condition):
                            headers = {"Cache-Control": "no-cache"}
                            if date is not None:
                                headers["If-Modified-Since"] = date
                            calls = self.transform.call_count
                            request = Request(origin + ROUTE + suffix, headers=headers)
                            # Presentation-filtered pages deliberately return a
                            # fresh 200 even when the source mtime matches.
                            with urlopen(request, timeout=5) as response:
                                self.assertEqual(response.status, 200)
                                get_headers = response.headers
                                self.assertIn("text/html", get_headers["Content-Type"])
                                self.assertIsNone(get_headers.get("X-Journal-Revision"))
                                if production:
                                    self.assertIn("must-revalidate", get_headers["Cache-Control"])
                                else:
                                    self.assertEqual(get_headers["Cache-Control"], "no-store")
                                body = response.read()
                                self.assertEqual(int(get_headers["Content-Length"]), len(body))
                            self.assertGreater(self.transform.call_count, calls)
                            self.assertLess(len(body), len(before))
                            document = body.decode()
                            self.assert_clean(document)
                            self.assertEqual(document.count(image_url), generated.count(image_url))
                            self.assertEqual(re.findall(r"<img\b[^>]*>", document),
                                             re.findall(r"<img\b[^>]*>", generated))
                            if clean_response is not None:
                                self.assertEqual(document, clean_response)
                            clean_response = document
                            self.assertEqual(target.read_bytes(), before)

                            calls = self.transform.call_count
                            head_headers = self.read_head(
                                server.server_port, ROUTE + suffix, headers)
                            self.assertGreater(self.transform.call_count, calls)
                            for name in ("Content-Length", "Content-Type", "Cache-Control",
                                         "X-Journal-Revision"):
                                self.assertEqual(head_headers.get(name), get_headers.get(name),
                                                 f"HEAD/GET {name} mismatch")
                            self.assertEqual(int(head_headers["Content-Length"]), len(body))
                            self.assertEqual(target.read_bytes(), before)
                            self.assert_preserved()
                    with urlopen(origin + image_url, timeout=5) as response:
                        self.assertEqual(response.read(), self.image_bytes)
                    self.assert_preserved()

    def test_workspace_service_preview_after_rebuilds(self):
        self.exercise(production=False)

    def test_public_non_journal_html_after_rebuilds(self):
        self.exercise(production=True)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-service-photo-notes-e2e.py OK")
    raise SystemExit(not result.result.wasSuccessful())
