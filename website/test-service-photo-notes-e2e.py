#!/usr/bin/env python3
"""Disposable service rebuild/HTTP/browser checks, independent of Journal.

Run: python3 website/test-service-photo-notes-e2e.py
Requires Chromium (CHROME_BIN / CHROMIUM_BIN overrides are supported).
"""
from contextlib import ExitStack, contextmanager
from email.parser import BytesParser
from email.utils import formatdate
import gzip
import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from PIL import Image
import devserver
import internal_links
import inline_links
import journal_photo_notes
import service_preview

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "service_photo_fixture_builder", ROOT / "build-service-previews.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
BROWSER_SPEC = importlib.util.spec_from_file_location(
    "service_photo_browser_tools", ROOT / "test-header-mobile.py")
browser_tools = importlib.util.module_from_spec(BROWSER_SPEC)
BROWSER_SPEC.loader.exec_module(browser_tools)

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
RELATED_ROUTE = "/services/fixture-care-guide"
RELATED_LABEL = "Fixture care guide"


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
        # Default cases retain the no-inventory path; contextual cases supply
        # only disposable service entries, never real publication state.
        self.inventory = self.stack.enter_context(patch.object(
            internal_links, "inventory", return_value={}))
        self.journal_releases = self.stack.enter_context(patch.object(
            devserver.PrettyURLHandler, "_released_journal",
            side_effect=AssertionError("Service requests must not read Journal releases")))
        self.transform = self.stack.enter_context(patch.object(
            journal_photo_notes, "public_html", wraps=journal_photo_notes.public_html))
        self.render_links = self.stack.enter_context(patch.object(
            internal_links, "render_links", wraps=internal_links.render_links))

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
        self.journal_releases.assert_not_called()

    @contextmanager
    def responsive_browser(self):
        # Reuse the project's dependency-free Chromium/CDP conventions.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix="elh-service-photo-chrome-") as profile:
            browser = subprocess.Popen([
                browser_tools.browser_binary(), "--headless=new", "--no-sandbox",
                "--disable-gpu", "--disable-background-networking",
                "--no-proxy-server",
                "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                "--remote-allow-origins=*", f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}", "about:blank",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            client = None
            try:
                client = browser_tools.DevTools(browser_tools.wait_for_page_debugger(port))
                client.call("Page.enable")
                client.call("Network.enable")
                client.call("Network.setCacheDisabled", {"cacheDisabled": True})
                yield client
            finally:
                if client is not None:
                    client.close()
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
                    browser.wait(timeout=5)

    def assert_responsive_loaded(self, client, origin, candidates):
        # Fresh documents avoid Chromium retaining a larger cached candidate
        # after shrinking the viewport. At DPR=1 the phone uses img's 1x;
        # desktop uses picture's width descriptors and sizes (half the viewport).
        for width, candidate, natural_width, decoded_width in (
                (390, "small", 640, 640), (1440, "large", 720, 1280),
                (1024, "small", 512, 640)):
            with self.subTest(browser_width=width, candidate=candidate):
                client.call("Page.navigate", {"url": "about:blank"})
                client.call("Emulation.setDeviceMetricsOverride", {
                    "width": width, "height": 900,
                    "deviceScaleFactor": 1, "mobile": width < 640})
                url = origin + ROUTE + f"?responsive-width={width}"
                navigation = client.call("Page.navigate", {"url": url})
                self.assertNotIn("errorText", navigation)
                state = None
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    result = client.call("Runtime.evaluate", {
                        "expression": """(() => {
                          const img=document.querySelector('#responsive-photo-fixture img');
                          if (!img) return null;
                          return {url:location.href, ready:document.readyState,
                            width:innerWidth, dpr:devicePixelRatio,
                            currentSrc:img.currentSrc, complete:img.complete,
                            naturalWidth:img.naturalWidth, naturalHeight:img.naturalHeight};
                        })()""", "returnByValue": True})
                    self.assertNotIn("exceptionDetails", result)
                    state = result["result"].get("value")
                    if (state and state["url"] == url and state["ready"] == "complete"
                            and state["complete"] and state["currentSrc"]):
                        break
                    time.sleep(.05)
                self.assertIsNotNone(state, "Responsive fixture never appeared")
                self.assertEqual(state["url"], url, state)
                self.assertEqual(state["ready"], "complete", state)
                self.assertEqual(state["width"], width, state)
                self.assertEqual(state["dpr"], 1, state)
                self.assertEqual(state["currentSrc"], origin + candidates[candidate], state)
                self.assertTrue(state["complete"], state)
                self.assertEqual(state["naturalWidth"], natural_width, state)
                self.assertEqual(state["naturalHeight"], natural_width * 5 // 8, state)
                decoded = client.call("Runtime.evaluate", {
                    "expression": """(async () => {
                      const img=document.querySelector('#responsive-photo-fixture img');
                      await img.decode();
                      const bitmap=await createImageBitmap(img);
                      const size=[bitmap.width, bitmap.height];
                      bitmap.close();
                      return size;
                    })()""",
                    "awaitPromise": True, "returnByValue": True})
                self.assertNotIn("exceptionDetails", decoded)
                self.assertEqual(decoded["result"].get("value"),
                                 [decoded_width, decoded_width * 5 // 8])

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

    def exercise(self, production, contextual=False):
        self.stack.enter_context(patch.dict(
            os.environ, {"REPLIT_DEPLOYMENT": "1" if production else "0"}))
        pages = {}
        if contextual:
            self.assertTrue(production, "Contextual checks must use static public HTML")
            related_path = self.public / (RELATED_ROUTE.lstrip("/") + ".html")
            related_html = "<main><h1>" + RELATED_LABEL + "</h1></main>"
            related_path.write_text(related_html)
            related_bytes = related_path.read_bytes()
            pages[RELATED_ROUTE] = (
                related_path, related_html, internal_links.PageParser(related_html))
            self.inventory.return_value = pages
            # _journal_pages normally overlays approved Journal snapshots.
            # Isolate that boundary, not the real contextual-link renderer.
            self.journal_pages = self.stack.enter_context(patch.object(
                devserver.PrettyURLHandler, "_journal_pages", return_value=pages))
            self.stack.enter_context(patch.object(internal_links, "config", return_value={
                "pages": {ROUTE: ["fixture"]},
                "topics": {"fixture": [RELATED_ROUTE, RELATED_LABEL]},
                "supportLinks": {}, "journalCategories": {}, "journalOwners": {},
            }))
            self.stack.enter_context(patch.object(
                internal_links, "journal_records", return_value={}))
            self.stack.enter_context(patch.object(
                inline_links, "editorial_map", return_value={}))

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
        responsive_fixture = ""
        if contextual:
            # Disposable markup only: exercise responsive images and embedded
            # provenance without editing public pages or Journal releases.
            candidates = {}
            candidate_bytes = {}
            for name, size, color in (
                    ("small", (640, 400), (190, 40, 40)),
                    ("large", (1280, 800), (40, 160, 70)),
                    ("fallback", (120, 75), (40, 70, 190))):
                filename = f"fixture-responsive-{name}.webp"
                path = self.public / "assets/service-pages" / filename
                Image.new("RGB", size, color).save(path)
                candidates[name] = prefix + filename
                candidate_bytes[path] = path.read_bytes()
            responsive_urls = tuple(candidates[name] for name in ("small", "large", "fallback"))
            self.assertEqual(len(set(candidate_bytes.values())), 3)
            client = self.stack.enter_context(self.responsive_browser())
            responsive_alt = "Fixture caregiver beside a sunlit window"
            provenance = {
                "@context": "https://schema.org",
                "@type": "ImageObject",
                "contentUrl": responsive_urls[2],
                "creator": {"@type": "Person", "name": "Fixture author"},
                "creditText": "Fixture image provenance",
                "acquireLicensePage": "https://example.org/service-photo",
                "license": "https://www.pexels.com/license/",
                "sha256": hashlib.sha256(
                    (self.public / candidates["fallback"].lstrip("/")).read_bytes()).hexdigest(),
            }
            provenance_json = json.dumps(provenance, indent=2)
            responsive_fixture = (
                '<figure id="responsive-photo-fixture">\n'
                '<picture data-provenance="fixture-service-photo">\n'
                f'<source type="image/webp" media="(min-width: 640px)" '
                f'srcset="{responsive_urls[0]} 640w, {responsive_urls[1]} 1280w" '
                'sizes="(min-width: 960px) 50vw, 100vw">\n'
                f'<img src="{responsive_urls[2]}" '
                f'srcset="{responsive_urls[0]} 1x, {responsive_urls[1]} 2x" '
                f'alt="{responsive_alt}" width="120" height="80">\n'
                '</picture>\n'
                '<figcaption><p class="service-photo-context">'
                'Keep this ordinary photo context paragraph.</p></figcaption>\n'
                '</figure>\n'
                '<script type="application/ld+json" id="fixture-image-provenance">\n'
                + provenance_json + '\n</script>\n'
            )
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
                if contextual:
                    self.assertEqual(generated.count("</main>"), 1)
                    generated = generated.replace("</main>", responsive_fixture + "</main>")
                self.assertGreater(generated.count(image_url), 0)
                # Simulate an older generated artifact on every rebuild. Neither
                # request-time path may rewrite this on-disk source.
                legacy = generated.replace("</main>", OLD_NOTE + OLD_NOTE + "</main>")
                target.write_text(legacy)
                before = target.read_bytes()
                self.assertEqual(legacy.count('class="journal-photo-credit"'), 2)
                if contextual:
                    pages[ROUTE] = (target, legacy, internal_links.PageParser(legacy))
                    self.assertNotIn(internal_links.START, legacy)
                clean_response = None
                modified = target.stat().st_mtime
                conditions = (
                    ("unconditional", None),
                    ("older", formatdate(modified - 86400, usegmt=True)),
                    ("matching", formatdate(modified, usegmt=True)),
                    ("newer", formatdate(modified + 86400, usegmt=True)),
                )
                requests = [(suffix, encoding)
                            for suffix in ("", ".html?refresh=1", "")
                            for encoding in (("identity", "gzip") if contextual
                                             else ("identity",))]
                for suffix, encoding in requests:
                    for condition, date in conditions:
                        with self.subTest(suffix=suffix, condition=condition,
                                          encoding=encoding):
                            headers = {"Cache-Control": "no-cache",
                                       "Accept-Encoding": encoding}
                            if date is not None:
                                headers["If-Modified-Since"] = date
                            calls = self.transform.call_count
                            render_calls = self.render_links.call_count
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
                                wire_body = response.read()
                                self.assertEqual(int(get_headers["Content-Length"]),
                                                 len(wire_body))
                                if contextual:
                                    self.assertEqual(get_headers["Vary"], "Accept-Encoding")
                                if encoding == "gzip":
                                    self.assertEqual(get_headers["Content-Encoding"], "gzip")
                                    body = gzip.decompress(wire_body)
                                else:
                                    self.assertIsNone(get_headers.get("Content-Encoding"))
                                    body = wire_body
                            self.assertGreater(self.transform.call_count, calls)
                            if not contextual:
                                self.assertLess(len(body), len(before))
                            document = body.decode()
                            self.assert_clean(document)
                            if contextual:
                                self.assertEqual(self.render_links.call_count, render_calls + 1)
                                self.assertEqual(self.render_links.call_args.args[0], legacy)
                                self.assertEqual(self.render_links.call_args.args[1], ROUTE)
                                self.assertIs(self.render_links.call_args.kwargs["pages"], pages)
                                self.journal_pages.assert_called()
                                self.assertEqual(document.count('class="elh-related"'), 1)
                                self.assertEqual(document.count(internal_links.START), 1)
                                self.assertIn(
                                    f'<a href="{RELATED_ROUTE}" data-reading-source="{ROUTE}"'
                                    f' data-reading-destination="{RELATED_ROUTE}"'
                                    f' data-reading-topic="fixture">{RELATED_LABEL}</a>',
                                    document)
                                self.assertEqual(related_path.read_bytes(), related_bytes)
                                # Both identity and decompressed gzip must retain
                                # the entire fixture verbatim, not just img tags.
                                self.assertEqual(document.count(responsive_fixture), 1)
                                for url in responsive_urls:
                                    self.assertEqual(document.count(url), generated.count(url))
                                self.assertEqual(
                                    document.count(f'alt="{responsive_alt}"'), 1)
                                metadata = re.findall(
                                    r'<script type="application/ld\+json" '
                                    r'id="fixture-image-provenance">\n(.*?)\n</script>',
                                    document, re.S)
                                self.assertEqual(metadata, [provenance_json])
                                self.assertEqual(json.loads(metadata[0]), provenance)
                            else:
                                self.assertEqual(self.render_links.call_count, render_calls)
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
                                         "X-Journal-Revision", "Content-Encoding", "Vary"):
                                self.assertEqual(head_headers.get(name), get_headers.get(name),
                                                 f"HEAD/GET {name} mismatch")
                            self.assertEqual(int(head_headers["Content-Length"]), len(wire_body))
                            self.assertEqual(target.read_bytes(), before)
                            self.assert_preserved()
                    with urlopen(origin + image_url, timeout=5) as response:
                        self.assertEqual(response.read(), self.image_bytes)
                    self.assert_preserved()
                if contextual:
                    self.assert_responsive_loaded(client, origin, candidates)
                    self.assertEqual(target.read_bytes(), before)
                    for path, original in candidate_bytes.items():
                        self.assertEqual(path.read_bytes(), original)
                    self.assert_preserved()

    def test_workspace_service_preview_after_rebuilds(self):
        self.exercise(production=False)

    def test_public_non_journal_html_after_rebuilds(self):
        self.exercise(production=True)

    def test_public_contextual_service_html_identity_and_gzip_after_rebuilds(self):
        self.exercise(production=True, contextual=True)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-service-photo-notes-e2e.py OK")
    raise SystemExit(not result.result.wasSuccessful())
