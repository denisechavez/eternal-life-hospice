#!/usr/bin/env python3
"""Rebuild/refresh/HTTP regression; no database, workspace cache or approvals.

Run: python3 website/test-journal-photo-notes-e2e.py
Only the release-storage boundary is synthetic. The builder, photo-note
transform and public request handler run unchanged against temporary files.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from PIL import Image
import devserver
import internal_links

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "photo_note_builder_fixture", ROOT / "build-journal-campaign.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

OLD_NOTE = (
    '<p class="journal-photo-credit"><small>Illustrative photograph: Fixture author / '
    '<a href="https://example.org/source">Source</a> &middot; '
    '<a href="https://creativecommons.org/licenses/by-sa/4.0/">License</a>. '
    'Resized for display. The photograph does not depict an Eternal patient '
    'or service encounter.</small></p>\n'
)
# Keep the expected removal independent of the production recognizer.
LEGACY_NOTES = (
    OLD_NOTE.replace('class="journal-photo-credit"', "class='journal-photo-credit'"),
    OLD_NOTE.replace('class="journal-photo-credit"',
                     'id="photo-note" class="muted journal-photo-credit compact"'),
    OLD_NOTE.replace('class="journal-photo-credit"',
                     "data-source='photo'\n class \t= ' muted\tjournal-photo-credit\ncompact '")
            .replace("</p>", "</p \t>"),
)


class RebuiltPhotoNoteTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.base = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.public = self.base / "elh-preview"
        self.posts = self.public / "blog"
        self.posts.mkdir(parents=True)
        self.content = self.base / "content"
        self.content.mkdir()
        self.assets = self.public / "assets"
        (self.assets / "img").mkdir(parents=True)
        # Exercise the real search rebuild too, but only inside this fixture.
        shutil.copyfile(ROOT / "elh-preview/assets/build-search-index.js",
                        self.assets / "build-search-index.js")
        for name in ("website-phone.cjs", "website-contact.json"):
            shutil.copyfile(ROOT / name, self.base / name)
        shutil.copyfile(ROOT / "content/internal-links.json",
                        self.content / "internal-links.json")
        shutil.copyfile(ROOT / "elh-preview/blog.html", self.public / "blog.html")
        (self.public / "sitemap.xml").write_text("<urlset></urlset>")
        self.image = self.assets / "img/fixture-photo.jpg"
        Image.new("RGB", (120, 80), (70, 90, 110)).save(self.image)
        self.image_bytes = self.image.read_bytes()
        self.image_url = "/assets/img/fixture-photo.jpg"
        self.digest = hashlib.sha256(self.image_bytes).hexdigest()
        self.frozen_url = "/api/journal-photo/" + self.digest
        # A small template deliberately includes an old visible block.
        template = (
            '<!doctype html><html><head><title>Fixture</title>'
            '<meta name="description" content="Fixture">'
            '<meta property="og:image" content="https://eternallifehospice.com'
            + self.image_url + '">'
            '<script type="application/ld+json">{"@type":"BlogPosting"}</script>'
            '</head><body><section class="hero hero--photo"></section>'
            '<article><h1>Old title</h1>' + OLD_NOTE + '</article>'
            '<section class="cta"></section></body></html>'
        )
        (self.posts / "template.html").write_text(template)
        self.articles = []
        for slug, license_url in (
            ("generated-photo-fixture", "https://www.pexels.com/license/"),
            ("staged-photo-fixture", "https://creativecommons.org/publicdomain/zero/1.0/"),
            ("frozen-photo-fixture", "https://creativecommons.org/licenses/by-sa/4.0/"),
        ):
            self.articles.append({
                "slug": slug, "title": "Fixture care guidance", "seoTitle": "Fixture care guidance",
                "description": "Fixture summary.", "date": "2020-01-01",
                "category": "Family Support", "readMinutes": 3,
                "heroImage": self.image_url, "heroImageAlt": "Unchanged fixture photograph",
                "lede": "Fixture introduction.",
                "sections": [{"heading": "Fixture guidance", "paragraphs": ["Keep this copy."]}],
                "ctaHeading": "Ask about care", "ctaCopy": "Fixture contact guidance.",
                "photoCredit": {
                    "author": "Fixture author", "sourceUrl": "https://example.org/source",
                    "license": "Fixture source license", "licenseUrl": license_url,
                },
            })
        self.source = self.content / "photo-sources.json"
        self.source.write_text(json.dumps(self.articles, indent=2))
        self.source_bytes = self.source.read_bytes()
        self.manifest = self.content / "30-day-journal-manifest.json"
        self.manifest.write_text(json.dumps({"articles": [
            {"slug": article["slug"], "date": article["date"]} for article in self.articles
        ]}))
        for module, values in (
            (builder, dict(ROOT=self.base, PUBLIC=self.public, OUT=self.posts,
                           MANIFEST=self.manifest, LEGACY_POSTS=[])),
            (internal_links, dict(BASE=self.base, PUBLIC=self.public)),
            (devserver, dict(ROOT=str(self.public), JOURNAL_MANIFEST=str(self.manifest))),
        ):
            for name, value in values.items():
                self.stack.enter_context(patch.object(module, name, value))
        # Avoid the real workspace display cache; do not bypass the HTTP handler.
        self.stack.enter_context(patch.dict("os.environ", {"REPLIT_DEPLOYMENT": "1"}))
        self.review = self.content / "seo-journal-review.json"
        self.snapshot = self.content / "frozen-approval.json"
        self.records = {}
        self.stack.enter_context(patch.object(
            devserver.journal_release, "released", side_effect=lambda: (deepcopy(self.records), True)))
        self.stack.enter_context(patch.object(
            devserver.journal_release, "photo",
            side_effect=lambda digest: {"body": self.image_bytes, "media_type": "image/jpeg"}
            if digest == self.digest else None))

    def rebuild(self):
        builder.build(json.loads(self.source.read_text()))

    def assert_no_notes(self, document):
        self.assertNotIn("journal-photo-credit", document)
        self.assertNotIn("Illustrative photograph:", document)
        self.assertNotIn("does not depict an Eternal patient", document)
        self.assertNotIn("Resized for display.", document)

    def publish_fixture_records(self):
        """Synthetic storage adapter: never grant approval or connect to a DB."""
        generated = (self.posts / (self.articles[0]["slug"] + ".html")).read_text()
        staged = json.loads(self.review.read_text())["articles"][self.articles[1]["slug"]]
        frozen = json.loads(self.snapshot.read_text())
        self.records = {
            self.articles[0]["slug"]: {
                "html": generated, "date": "2020-01-01",
                "revision": hashlib.sha256(generated.encode()).hexdigest(),
            },
            self.articles[1]["slug"]: {
                "html": staged["reviewHtml"], "date": staged["date"],
                "revision": staged["revision"],
            },
            self.articles[2]["slug"]: frozen,
        }

    def test_rebuild_refresh_and_public_responses_preserve_photos_and_approvals(self):
        self.rebuild()
        generated = (self.posts / (self.articles[0]["slug"] + ".html")).read_text()
        self.assert_no_notes(generated)
        # Seed an older generated article, a review copy and a frozen approval
        # with varied legacy blocks. A fresh build must not replace their copy.
        old_documents = {}
        for article, old_note in zip(self.articles, LEGACY_NOTES):
            path = self.posts / (article["slug"] + ".html")
            old_documents[article["slug"]] = path.read_text().replace(
                "</article>", old_note + "</article>")
            path.write_text(old_documents[article["slug"]])
        staged_slug = self.articles[1]["slug"]
        self.review.write_text(json.dumps({"articles": {staged_slug: {
            "reviewHtml": old_documents[staged_slug], "revision": "old-review-revision",
            "date": "2020-01-01", "photoCredit": self.articles[1]["photoCredit"],
        }}}))
        frozen_html = old_documents[self.articles[2]["slug"]].replace(
            self.image_url, self.frozen_url)
        frozen = {"html": frozen_html, "date": "2020-01-01",
                  "revision": hashlib.sha256(frozen_html.encode()).hexdigest(),
                  "approval": {"reviewer": "synthetic-fixture-only", "action": "approve"},
                  "photoCredit": self.articles[2]["photoCredit"]}
        self.snapshot.write_text(json.dumps(frozen, indent=2))
        snapshot_bytes = self.snapshot.read_bytes()
        article_values = deepcopy(self.articles)

        class QuietHandler(devserver.PrettyURLHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = "http://127.0.0.1:" + str(server.server_port)
            # Initial request, rebuild+refresh, then repeat to catch reintroduced
            # notes and prove idempotence. Every request uses a fresh handler.
            clean_review_bytes = None
            for cycle in range(3):
                with self.subTest(cycle=cycle):
                    if cycle:
                        self.rebuild()
                        changed = builder.refresh_review_photo_credits(self.articles, self.review)
                        self.assertEqual(changed, 1 if cycle == 1 else 0)
                        if clean_review_bytes is not None:
                            self.assertEqual(self.review.read_bytes(), clean_review_bytes)
                        clean_review_bytes = self.review.read_bytes()
                        staged = json.loads(clean_review_bytes)["articles"][staged_slug]
                        self.assertEqual(staged["reviewHtml"],
                                         old_documents[staged_slug].replace(LEGACY_NOTES[1], ""))
                        self.assertEqual(staged["photoCredit"], self.articles[1]["photoCredit"])
                        self.assertEqual(staged["date"], "2020-01-01")
                        self.assertEqual(staged["revision"], hashlib.sha256(
                            staged["reviewHtml"].encode()).hexdigest()[:12])
                        for article, old_note in zip(self.articles, LEGACY_NOTES):
                            self.assertEqual(
                                (self.posts / (article["slug"] + ".html")).read_text(),
                                old_documents[article["slug"]].replace(old_note, ""))
                    self.publish_fixture_records()
                    records_before = deepcopy(self.records)
                    for slug, row in self.records.items():
                        for suffix in ("", ".html?refresh=1"):
                            with self.subTest(slug=slug, suffix=suffix):
                                request = Request(origin + "/blog/" + slug + suffix,
                                                  headers={"Cache-Control": "no-cache"})
                                with urlopen(request, timeout=5) as response:
                                    self.assertEqual(response.status, 200)
                                    self.assertEqual(response.headers["X-Journal-Revision"],
                                                     row["revision"])
                                    self.assertIn("must-revalidate", response.headers["Cache-Control"])
                                    document = response.read().decode()
                                self.assert_no_notes(document)
                                self.assertIn("Keep this copy.", document)
                                expected_url = self.frozen_url if slug == self.articles[2]["slug"] else self.image_url
                                # Preserve every occurrence, including hero and social/schema metadata.
                                self.assertEqual(document.count(expected_url),
                                                 row["html"].count(expected_url))
                                self.assertGreater(document.count(expected_url), 0)
                    for url in (self.image_url, self.frozen_url):
                        with urlopen(origin + url, timeout=5) as response:
                            self.assertEqual(response.read(), self.image_bytes)
                    self.assertEqual(self.records, records_before)
                    self.assertEqual(self.snapshot.read_bytes(), snapshot_bytes)
                    self.assertEqual(self.source.read_bytes(), self.source_bytes)
                    self.assertEqual(self.articles, article_values)
                    self.assertEqual(self.image.read_bytes(), self.image_bytes)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), "Fixture server did not stop")


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-journal-photo-notes-e2e.py OK")
    raise SystemExit(not result.result.wasSuccessful())
