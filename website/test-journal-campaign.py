#!/usr/bin/env python3
"""Focused invariants for the Eternal Journal publication campaign."""
import importlib.util
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("journal_builder", ROOT / "build-journal-campaign.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
from devserver import PrettyURLHandler
import journal_release
import journal_workspace_preview
import analytics_assets
from photo_note_test_fixtures import NOTE_VARIANTS, PRESERVED_HTML


class JournalCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = builder.load_articles()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "timezone": "America/Los_Angeles",
            "articles": [a for a in self.articles if a.get("publicationStatus") != "archived"],
        }))
        # Layout fixtures explicitly release staged copies, never owner approvals
        # or frozen production history. A workspace's verified-public overlay is
        # intentionally NOT rewound by ELH_JOURNAL_DATE, so isolate its cache too.
        for fixture in (
            patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0", "ELH_JOURNAL_DATE": "2026-09-21"}),
            patch("devserver.JOURNAL_MANIFEST", str(manifest)),
            patch.object(journal_workspace_preview, "CACHE", root / "absent-preview.json"),
            patch.object(journal_release, "released", side_effect=self.synthetic_releases),
            patch.object(journal_release, "connect",
                         side_effect=AssertionError("Campaign tests must not access approval storage")),
        ):
            fixture.start()
            self.addCleanup(fixture.stop)

    def synthetic_releases(self):
        """Explicit synthetic approval of the campaign/legacy layout fixtures.

        Date-only eligibility here sets up archive tests; it is not an imitation
        of the authoritative 06:30 release clock (covered independently below).
        """
        today = PrettyURLHandler._journal_today()
        import devserver
        records = {}
        for article in self.articles + builder.LEGACY_POSTS:
            if article.get("publicationStatus") == "archived" or article["date"] > (today or ""):
                continue
            path = Path(devserver.ROOT) / "blog" / (article["slug"] + ".html")
            document = path.read_text()
            records[article["slug"]] = {
                "date": article["date"], "html": document,
                "revision": hashlib.sha256(document.encode()).hexdigest(),
            }
        return records, True

    def test_inline_editorial_links_are_safe_and_contextual(self):
        self.assertEqual(
            builder.render_inline('Use the [Family Guide](/family-guide) & ask <questions>.'),
            'Use the <a href="/family-guide">Family Guide</a> &amp; ask &lt;questions&gt;.',
        )
        with self.assertRaises(ValueError):
            builder.render_inline('[Unsafe](javascript:alert)')
        with self.assertRaises(ValueError):
            builder.render_inline('[Unsafe](//example.com)')

    def test_optional_photo_notes_are_not_rendered(self):
        for license_url in (
            "https://www.pexels.com/license/",
            "https://creativecommons.org/publicdomain/mark/1.0/",
            "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
        ):
            self.assertEqual(builder.render_photo_credit({"licenseUrl": license_url}), "")
        self.assertEqual(builder.render_photo_credit(None), "")

    def test_legacy_photo_note_refresh_variants_preserve_other_bytes(self):
        for note_html in NOTE_VARIANTS:
            with self.subTest(note=note_html), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                article = {
                    "slug": "legacy",
                    "photoCredit": {"author": "Original author",
                                    "sourceUrl": "https://example.org/source",
                                    "licenseUrl": "https://creativecommons.org/licenses/by/4.0/"},
                }
                original = PRESERVED_HTML + note_html + PRESERVED_HTML + note_html
                expected = PRESERVED_HTML * 2
                page = root / "legacy.html"
                page.write_text(original)
                review = root / "review.json"
                draft = {"reviewHtml": original, "revision": "old",
                         "photoCredit": article["photoCredit"], "date": "2020-01-01",
                         "title": "Unchanged article", "heroImage": "/assets/original.jpg"}
                document = {"articles": {"legacy": draft, "unmatched": dict(draft)},
                            "metadata": {"source": "unchanged"}}
                review.write_text(json.dumps(document))
                frozen = root / "frozen-approval.json"
                frozen.write_text(json.dumps({"html": original, "revision": "approved",
                                              "approval": {"action": "approve"},
                                              "photoCredit": article["photoCredit"]}))
                frozen_bytes = frozen.read_bytes()
                source = json.dumps(article)
                with patch.object(builder, "OUT", root):
                    self.assertEqual(builder.refresh_photo_credits([article]), 1)
                    self.assertEqual(builder.refresh_review_photo_credits([article], review), 1)
                    self.assertEqual(page.read_text(), expected)
                    updated = json.loads(review.read_text())
                    self.assertEqual(updated["articles"]["legacy"], {
                        **draft, "reviewHtml": expected,
                        "revision": hashlib.sha256(expected.encode()).hexdigest()[:12],
                    })
                    self.assertEqual(updated["articles"]["unmatched"], draft)
                    self.assertEqual(updated["metadata"], document["metadata"])
                    page_bytes, review_bytes = page.read_bytes(), review.read_bytes()
                    self.assertEqual(builder.refresh_photo_credits([article]), 0)
                    self.assertEqual(builder.refresh_review_photo_credits([article], review), 0)
                    self.assertEqual(page.read_bytes(), page_bytes)
                    self.assertEqual(review.read_bytes(), review_bytes)
                self.assertEqual(frozen.read_bytes(), frozen_bytes)
                self.assertEqual(json.dumps(article), source)

    def test_photo_source_metadata_is_preserved_but_not_rendered(self):
        credit = {
            "author": "Author & Photographer",
            "sourceUrl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
            "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0",
            "license": "CC BY-SA 4.0",
        }
        original = dict(credit)
        self.assertEqual(builder.render_photo_credit(credit), "")
        self.assertEqual(credit, original)

    def test_photo_note_refresh_only_changes_credit_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            posts = Path(directory)
            page = posts / "example.html"
            original = ('<h1>Approved title</h1>\n'
                        '<p class="journal-photo-credit"><small>Old note</small></p>\n'
                        '<p>Approved article copy.</p>\n')
            page.write_text(original)
            articles = [{"slug": "example", "photoCredit": {
                "licenseUrl": "https://www.pexels.com/license/",
            }}]
            with patch.object(builder, "OUT", posts):
                self.assertEqual(builder.refresh_photo_credits(articles), 1)
                self.assertEqual(page.read_text(),
                                 '<h1>Approved title</h1>\n<p>Approved article copy.</p>\n')
                self.assertEqual(builder.refresh_photo_credits(articles), 0)

    def test_review_photo_refresh_preserves_copy_and_changes_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            original = ('<h1>Approved title</h1>\n'
                        '<p class="journal-photo-credit">Old note</p>\n'
                        '<p>Article copy.</p>')
            path.write_text(json.dumps({"articles": {"example": {
                "reviewHtml": original, "revision": "old", "date": "2026-10-28",
            }}}))
            articles = [{"slug": "example", "photoCredit": {
                "licenseUrl": "https://www.pexels.com/license/",
            }}]
            self.assertEqual(builder.refresh_review_photo_credits(articles, path), 1)
            saved = json.loads(path.read_text())["articles"]["example"]
            self.assertEqual(saved["reviewHtml"],
                             '<h1>Approved title</h1>\n<p>Article copy.</p>')
            self.assertNotEqual(saved["revision"], "old")
            self.assertEqual(saved["date"], "2026-10-28")
            self.assertEqual(builder.refresh_review_photo_credits(articles, path), 0)

    @contextmanager
    def archive_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory) / "elh-preview"
            posts = public / "blog"
            posts.mkdir(parents=True)
            for source in (ROOT / "elh-preview" / "blog").glob("*.html"):
                (posts / source.name).write_bytes(source.read_bytes())
            for name in ("blog.html", "sitemap.xml"):
                (public / name).write_bytes((ROOT / "elh-preview" / name).read_bytes())
            (public / "assets").symlink_to(ROOT / "elh-preview" / "assets", target_is_directory=True)
            with patch.object(builder, "PUBLIC", public), patch.object(builder, "OUT", posts), \
                 patch.object(builder, "MANIFEST", Path(directory) / "manifest.json"):
                yield public, posts

    @contextmanager
    def metadata_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory) / "elh-preview"
            posts = public / "blog"
            posts.mkdir(parents=True)
            # No campaign JSON: discovery must cover legacy and staged HTML.
            schema = {"@type": "BlogPosting", "headline": "Care & connection",
                      "description": "A calm summary for families."}
            page = (
                "<html><head><title>Intentional SEO title | Eternal Life Hospice</title>"
                "<meta content='A calm summary for families.' name='description'>"
                "<meta content='A calm summary for families.' property='og:description'>"
                "<meta content='A calm summary for families.' name='twitter:description'>"
                "<meta property='og:title' content='Different share title'>"
                "<meta name='twitter:title' content='Another share title'>"
                f"<script type='application/ld+json'>{json.dumps(schema)}</script>"
                "</head><body><section class='hero--photo hero'>"
                "<h1>Care &amp; <em>connection</em></h1>"
                "<p>A calm summary<br> for families.</p></section></body></html>"
            )
            path = posts / "edited-story.html"
            path.write_text(page)
            (public / "blog.html").write_text("Archive must remain untouched")
            with patch.object(builder, "OUT", posts):
                yield public, path, page, schema

    def test_metadata_check_allows_seo_titles_and_normalizes_visible_copy(self):
        with self.metadata_fixture() as (public, path, page, schema):
            schema["headline"] = " Care &amp; connection "
            schema["description"] = "A calm\n  summary for families."
            # Also accept schema type arrays and @graph, ignoring archive nodes.
            schema["@type"] = ["Article", "BlogPosting"]
            graph = {"@graph": [schema, {"@type": "Blog", "blogPost": [
                {"@type": "BlogPosting", "headline": "Unrelated card"}]}]}
            path.write_text(page.replace(json.dumps({
                "@type": "BlogPosting", "headline": "Care & connection",
                "description": "A calm summary for families."}), json.dumps(graph)))
            before = {p: p.read_bytes() for p in public.rglob("*") if p.is_file()}
            self.assertEqual(builder.check_metadata(), [])
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_metadata_check_reports_each_stale_field_without_writing(self):
        with self.metadata_fixture() as (public, path, page, schema):
            for field in ("headline", "description", "og:description", "twitter:description",
                          "meta description"):
                with self.subTest(field=field):
                    if field in ("headline", "description"):
                        changed = dict(schema, **{field: "Earlier editorial copy"})
                        stale = page.replace(json.dumps(schema), json.dumps(changed))
                        label = f"BlogPosting[1].{field}"
                    else:
                        attribute = {"og:description": "property='og:description'",
                                     "twitter:description": "name='twitter:description'",
                                     "meta description": "name='description'"}[field]
                        stale = page.replace(
                            f"content='A calm summary for families.' {attribute}",
                            f"content='Earlier editorial copy' {attribute}")
                        label = "description" if field == "meta description" else field
                    path.write_text(stale)
                    before = {p: p.read_bytes() for p in public.rglob("*") if p.is_file()}
                    issues = builder.check_metadata()
                    self.assertEqual(len(issues), 1)
                    self.assertIn(f"{path}: {label}:", issues[0])
                    self.assertIn("Earlier editorial copy", issues[0])
                    self.assertIn("hero=", issues[0])
                    self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_metadata_check_detects_missing_duplicate_and_broken_metadata(self):
        with self.metadata_fixture() as (_, path, page, schema):
            tag = "<meta content='A calm summary for families.' name='description'>"
            for broken, label in (
                (page.replace(tag, ""), "description"),
                (page.replace(tag, tag * 2), "description"),
                (page.replace(tag, "<meta name='description' content=' '>"), "description"),
                (page.replace(json.dumps(schema), "{broken"), "JSON-LD"),
                (page.replace(json.dumps(schema), json.dumps({"@type": "WebPage"})), "BlogPosting"),
                (page.replace(json.dumps(schema), json.dumps([schema, schema])), "BlogPosting"),
                (page.replace(json.dumps(schema), json.dumps(dict(schema, headline=None))), "headline"),
                (page.replace(json.dumps(schema), json.dumps({"@type": "BlogPosting"})), "description"),
                (page.replace("<h1>Care &amp; <em>connection</em></h1>", ""), "hero"),
            ):
                with self.subTest(label=label, broken=broken):
                    path.write_text(broken)
                    issues = builder.check_metadata()
                    self.assertTrue(issues)
                    self.assertTrue(any(label in issue for issue in issues))
                    self.assertTrue(all(str(path) in issue for issue in issues))
                    self.assertEqual(path.read_text(), broken)

    def test_metadata_check_scans_all_pages_and_continues_after_invalid_hero(self):
        with self.metadata_fixture() as (_, path, page, schema):
            legacy = path.with_name("legacy-story.html")
            staged = path.with_name("staged-story.html")
            legacy.write_text(page.replace("Care &amp;", "Edited &amp;"))
            staged.write_text(page.replace("<p>A calm summary<br> for families.</p>", ""))
            issues = builder.check_metadata()
            self.assertEqual(len(issues), 2)
            self.assertTrue(any(str(legacy) in issue and "headline" in issue for issue in issues))
            self.assertTrue(any(str(staged) in issue and "hero" in issue for issue in issues))
            for article in path.parent.glob("*.html"):
                article.unlink()
            self.assertIn("no Journal article HTML", builder.check_metadata()[0])

    def test_metadata_cli_is_read_only_and_returns_failure_for_stale_copy(self):
        with self.metadata_fixture() as (public, path, page, _):
            root = public.parent
            for name in ("build-journal-campaign.py", "journal_metadata.py",
                         "journal_photo_notes.py"):
                (root / name).write_bytes((ROOT / name).read_bytes())
            command = [sys.executable, str(root / "build-journal-campaign.py"), "--check-metadata"]
            for text, expected_code in ((page, 0), (page.replace("Care &amp;", "Edited &amp;"), 1)):
                path.write_text(text)
                before = {p: p.read_bytes() for p in public.rglob("*") if p.is_file()}
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
                self.assertIn("no files changed", result.stdout)
                if expected_code:
                    self.assertIn(str(path), result.stdout)
                    self.assertIn("BlogPosting[1].headline", result.stdout)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                self.assertFalse((root / "content").exists())

    def test_archive_sync_uses_visible_copy_and_preserves_pages(self):
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        originals = json.dumps(self.articles + builder.LEGACY_POSTS, sort_keys=True)
        with self.archive_fixture() as (public, posts):
            expected = {}
            # Cover an ordinary card, the staged feature and a legacy card.
            for article in (active[0], active[-1], builder.LEGACY_POSTS[0]):
                path = posts / f'{article["slug"]}.html'
                title = 'Edited & "quoted" <title> ' + article["slug"]
                summary = r'A fresh summary with \1, café & family support.'
                hero = ("<section data-note='editorial' class='hero--photo hero'>"
                        f"<h1>Edited &amp; <em>&quot;quoted&quot;</em> &lt;title&gt; {article['slug']}</h1>"
                        "<p>A fresh <strong>summary</strong> with \\1,<br>café &amp; family support.</p></section>")
                page = re.sub(r'<section class="hero hero--photo"[\s\S]*?</section>',
                              lambda _: hero, path.read_text(), count=1)
                path.write_text(page + "\n<!-- Keep this editorial note -->")
                expected[article["slug"]] = dict(article, title=title, description=summary)
            before = {p.name: p.read_bytes() for p in posts.glob("*.html")}
            sitemap = (public / "sitemap.xml").read_bytes()
            builder.write_archive(active, self.articles)
            archive = (public / "blog.html").read_text()
            entries = next(json.loads(text)["blogPost"] for text in re.findall(
                r'<script type="application/ld\+json">([\s\S]*?)</script>', archive)
                if json.loads(text).get("@type") == "Blog")
            for slug, article in expected.items():
                with self.subTest(slug=slug):
                    self.assertIn(builder.card(article), archive)
                    self.assertIn(builder.esc(builder.card(article, True)), archive)
                    entry = next(e for e in entries if e["url"] == builder.BASE_URL + slug)
                    self.assertEqual(entry["headline"], article["title"])
                    self.assertEqual(entry["description"], article["description"])
                    self.assertEqual(entry["datePublished"], article["date"])
            self.assertIn(builder.card(expected[active[-1]["slug"]], True), archive)
            self.assertNotIn("can-a-family-request-a-hospice-evaluation", archive)
            # Runtime promotion must use edited copy, without leaking future
            # stories through either the featured payload or Blog schema.
            with patch.dict(os.environ, {"ELH_JOURNAL_DATE": active[0]["date"]}), \
                 patch("devserver.ROOT", str(public)):
                handler = PrettyURLHandler.__new__(PrettyURLHandler)
                handler.command = "GET"
                handler.wfile = io.BytesIO()
                handler.send_response = lambda *_: None
                handler.send_header = lambda *_: None
                handler.end_headers = lambda: None
                self.assertTrue(handler._send_journal_artifact(str(public / "blog.html")))
                served = handler.wfile.getvalue().decode()
                self.assertIn(builder.card(expected[active[0]["slug"]], True), served)
                self.assertNotIn(active[-1]["slug"], served)
                self.assertIn('"headline": ' + json.dumps(expected[active[0]["slug"]]["title"]), served)
            builder.write_archive(active, self.articles)
            self.assertEqual(archive, (public / "blog.html").read_text())
            self.assertEqual(before, {p.name: p.read_bytes() for p in posts.glob("*.html")})
            self.assertEqual(sitemap, (public / "sitemap.xml").read_bytes())
            self.assertFalse(builder.MANIFEST.exists())
        self.assertEqual(originals, json.dumps(self.articles + builder.LEGACY_POSTS, sort_keys=True))

    def test_archive_sync_rejects_missing_or_ambiguous_copy_without_writing(self):
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        with self.archive_fixture() as (public, posts):
            path = posts / f'{active[0]["slug"]}.html'
            before = (public / "blog.html").read_bytes()
            for hero in (
                "<section class='hero'><h1>Title</h1></section>",
                "<section class='hero'><h1> </h1><p>Summary</p></section>",
                "<section class='hero'><h1>Title</h1><p>Summary</p><p>Other</p></section>",
                "<section class='hero'><h1>Title</h1><h1>Other</h1><p>Summary</p></section>",
                "<section class='hero'><h1>Title</h1><p>Summary</p></section>" * 2,
                "<h1>Outside hero</h1><p>Outside hero summary</p>",
            ):
                with self.subTest(hero=hero):
                    path.write_text(hero)
                    with self.assertRaisesRegex(ValueError, active[0]["slug"]):
                        builder.write_archive(active, self.articles)
                    self.assertEqual(before, (public / "blog.html").read_bytes())
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                builder.write_archive(active, self.articles)
            self.assertEqual(before, (public / "blog.html").read_bytes())

    def test_archive_sync_rejects_broken_schema_without_writing(self):
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        with self.archive_fixture() as (public, posts):
            path = public / "blog.html"
            source = path.read_text()
            for replacement in ('"@type": "WebPage"', '"@type": '):
                broken = re.sub(r'"@type"\s*:\s*"Blog"', lambda _: replacement, source)
                path.write_text(broken)
                with self.assertRaisesRegex(ValueError, "valid Blog schema"):
                    builder.write_archive(active, self.articles)
                self.assertEqual(broken, path.read_text())

    def test_full_build_and_image_refresh_sync_copy_without_overwriting_edits(self):
        with self.archive_fixture() as (public, posts):
            article = self.articles[0]
            path = posts / f'{article["slug"]}.html'
            page = re.sub(r'<h1>[\s\S]*?</h1>', '<h1>Published edited heading</h1>',
                          path.read_text(), count=1)
            page = re.sub(r'(<h1>Published edited heading</h1>)<p>[\s\S]*?</p>',
                          r'\1<p>Published edited summary.</p>', page, count=1)
            # Build refreshes analytics-asset URLs by design. Start with a current
            # URL so this assertion isolates preservation of editorial bytes.
            page = analytics_assets.refresh_html(page)
            path.write_text(page)
            with patch.object(builder.subprocess, "run"):
                for sync in (builder.build, builder.refresh_images):
                    with self.subTest(mode=sync.__name__):
                        sync(self.articles)
                        self.assertEqual(page, path.read_text())
                        archive = (public / "blog.html").read_text()
                        self.assertIn(builder.card(dict(article, title="Published edited heading",
                                                       description="Published edited summary.")), archive)
                        self.assertIn('"headline": "Published edited heading"', archive)
                        self.assertIn('"description": "Published edited summary."', archive)

    def test_all_batches_are_consecutive_and_unique(self):
        self.assertGreater(len(self.articles), 30)
        self.assertEqual(
            [a["date"] for a in self.articles[:30]],
            [(date(2026, 9, 21) + timedelta(days=i)).isoformat() for i in range(30)],
        )
        self.assertTrue(all(a["date"] > "2026-10-20" for a in self.articles[30:]))
        self.assertEqual(len({a["slug"] for a in self.articles}), len(self.articles))

    def test_archived_source_is_not_in_publication_schedule(self):
        archived_slug = "can-a-family-request-a-hospice-evaluation"
        archived = [a for a in self.articles if a["slug"] == archived_slug]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].get("publicationStatus"), "archived")
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        self.assertEqual(len(active), len(self.articles) - 1)
        manifest = json.loads((ROOT / "content" / "30-day-journal-manifest.json").read_text())
        self.assertNotIn(archived_slug, {a["slug"] for a in manifest["articles"]})
        self.assertFalse((ROOT / "elh-preview" / "blog" / f"{archived_slug}.html").exists())

    def test_publication_gating_uses_local_date(self):
        old = os.environ.get("ELH_JOURNAL_DATE")
        try:
            os.environ["ELH_JOURNAL_DATE"] = "2026-09-21"
            self.assertFalse(PrettyURLHandler._future_journal_path(
                "/blog/what-happens-during-a-hospice-evaluation"
            ))
            self.assertTrue(PrettyURLHandler._future_journal_path(
                "/blog/dementia-and-hospice-eligibility"
            ))
            for variant in (
                "/blog/dementia-and-hospice-eligibility.html",
                "/blog/dementia%2Dand%2Dhospice%2Deligibility",
                "/blog/dementia-and-hospice-eligibility/",
            ):
                self.assertTrue(PrettyURLHandler._future_journal_path(variant))
            self.assertTrue(PrettyURLHandler._future_journal_path(
                "/blog/preparing-for-a-hospice-care-plan-conversation"
            ))
            os.environ["ELH_JOURNAL_DATE"] = "2026-10-21"
            self.assertFalse(PrettyURLHandler._future_journal_path(
                "/blog/preparing-for-a-hospice-care-plan-conversation.html"
            ))
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_generated_metadata_and_schedule(self):
        manifest = json.loads((ROOT / "content" / "30-day-journal-manifest.json").read_text())
        self.assertEqual(len(manifest["articles"]), len(self.articles) - 1)
        self.assertEqual(manifest["end"], max(a["date"] for a in self.articles))
        archive = (ROOT / "elh-preview" / "blog.html").read_text()
        for article in self.articles:
            if article.get("publicationStatus") == "archived":
                continue
            page = (ROOT / "elh-preview" / "blog" / f'{article["slug"]}.html').read_text()
            self.assertIn(f'<link rel="canonical" href="https://eternallifehospice.com/blog/{article["slug"]}">', page)
            self.assertIn(f'"datePublished":"{article["date"]}"', page.replace(" ", ""))
            self.assertIn(f"background-image:url('..{article['heroImage']}')", page)
            self.assertIn(f"https://eternallifehospice.com{article['heroImage']}", page)
            self.assertRegex(page, r'property="og:image:width" content="\d+"')
            self.assertRegex(page, r'property="og:image:height" content="\d+"')
            self.assertIn(article["heroImage"], archive)

    def test_every_public_journal_post_has_its_own_image(self):
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        posts = active + builder.LEGACY_POSTS
        self.assertEqual(len({a["heroImage"] for a in posts}), len(posts))
        for article in posts:
            with self.subTest(slug=article["slug"]):
                self.assertTrue(
                    (ROOT / "elh-preview" / article["heroImage"].lstrip("/")).is_file()
                )

    def test_newest_published_article_is_the_only_featured_story(self):
        old = os.environ.get("ELH_JOURNAL_DATE")
        try:
            cases = (
                ("2026-09-20", "2026-08-13", "the-caregiver-who-needs-care"),
                ("2026-09-21", "2026-09-21", "what-happens-during-a-hospice-evaluation"),
                ("2026-09-28", "2026-09-28", "hospice-care-for-advanced-cancer"),
                ("2026-09-29", "2026-09-29", "hospice-and-advanced-heart-failure"),
                ("2026-10-19", "2026-10-19", "grief-support-before-and-after-a-loss"),
                ("2026-10-20", "2026-10-20", "how-physicians-and-facilities-refer-a-patient-to-hospice"),
                ("2026-10-21", "2026-10-21", "preparing-for-a-hospice-care-plan-conversation"),
                ("2027-01-01", self.articles[-1]["date"], self.articles[-1]["slug"]),
            )
            for today, expected_date, slug in cases:
                with self.subTest(today=today):
                    os.environ["ELH_JOURNAL_DATE"] = today
                    handler = PrettyURLHandler.__new__(PrettyURLHandler)
                    handler.command = "GET"
                    handler.wfile = io.BytesIO()
                    statuses = []
                    handler.send_response = statuses.append
                    handler.send_header = lambda *_: None
                    handler.end_headers = lambda: None
                    self.assertTrue(handler._send_journal_artifact(
                        str(ROOT / "elh-preview" / "blog.html")
                    ))
                    self.assertEqual(statuses, [200])
                    archive = handler.wfile.getvalue().decode()
                    featured = re.findall(
                        r'<div class="blog-featured" data-publish-date="([^"]+)">'
                        r'<a class="bf-img" href="([^"]+)" '
                        r'style="background-image:url\(\'([^\']+)\'\)"',
                        archive,
                    )
                    image = next(a["heroImage"] for a in
                                 self.articles + builder.LEGACY_POSTS if a["slug"] == slug)
                    self.assertEqual(featured, [(expected_date, f"/blog/{slug}", image)])
                    self.assertNotIn(f'class="rc" data-publish-date="{expected_date}" href="/blog/{slug}"', archive)
                    self.assertNotIn("can-a-family-request-a-hospice-evaluation", archive)
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_new_post_after_staged_lead_takes_featured_position(self):
        article = {
            "date": "2027-01-02",
            "slug": "new-journal-story",
            "title": "A New Journal Story",
            "description": "A new story added after the original campaign.",
            "category": "Family Support",
            "readMinutes": 4,
            "heroImage": "/assets/img/journal/referral.jpg",
        }
        source = (ROOT / "elh-preview" / "blog.html").read_text()
        source = source.replace('<div class="rgrid">', '<div class="rgrid">' + builder.card(article), 1)
        old = os.environ.get("ELH_JOURNAL_DATE")
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "blog.html"
                path.write_text(source)
                for today, expected_slug in (
                    ("2027-01-01", self.articles[-1]["slug"]),
                    ("2027-01-02", "new-journal-story"),
                ):
                    with self.subTest(today=today):
                        os.environ["ELH_JOURNAL_DATE"] = today
                        handler = PrettyURLHandler.__new__(PrettyURLHandler)
                        handler.command = "GET"
                        handler.wfile = io.BytesIO()
                        records, healthy = self.synthetic_releases()
                        if article["date"] <= today:
                            records[article["slug"]] = {"date":article["date"],
                                "revision":"explicitly-approved-new-story-fixture","html":""}
                        handler._journal_snapshot = (records, healthy)
                        statuses = []
                        handler.send_response = statuses.append
                        handler.send_header = lambda *_: None
                        handler.end_headers = lambda: None
                        self.assertTrue(handler._send_journal_artifact(str(path)))
                        self.assertEqual(statuses, [200])
                        archive = handler.wfile.getvalue().decode()
                        featured = re.findall(
                            r'<div class="blog-featured" data-publish-date="([^"]+)">'
                            r'<a class="bf-img" href="([^"]+)"',
                            archive,
                        )
                        expected_date = self.articles[-1]["date"] if today == "2027-01-01" else today
                        self.assertEqual(featured, [(expected_date, f"/blog/{expected_slug}")])
                        self.assertNotIn(
                            f'class="rc" data-publish-date="{expected_date}" href="/blog/{expected_slug}"',
                            archive,
                        )
                        if today == "2027-01-01":
                            self.assertNotIn('href="/blog/new-journal-story"', archive)
                        else:
                            self.assertIn(
                                f'class="rc" data-publish-date="{self.articles[-1]["date"]}" '
                                f'href="/blog/{self.articles[-1]["slug"]}"',
                                archive,
                            )
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_old_featured_card_is_replaced_by_current_post(self):
        source = (ROOT / "elh-preview" / "blog.html").read_text()
        old_featured = builder.card(self.articles[0], featured=True)
        source = re.sub(
            r'<div class="blog-featured"[^>]*>[\s\S]*?</div>\s*</div>',
            lambda _: old_featured,
            source,
            count=1,
        )
        old = os.environ.get("ELH_JOURNAL_DATE")
        try:
            os.environ["ELH_JOURNAL_DATE"] = "2026-09-29"
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "blog.html"
                path.write_text(source)
                handler = PrettyURLHandler.__new__(PrettyURLHandler)
                handler.command = "GET"
                handler.wfile = io.BytesIO()
                statuses = []
                handler.send_response = statuses.append
                handler.send_header = lambda *_: None
                handler.end_headers = lambda: None
                self.assertTrue(handler._send_journal_artifact(str(path)))
                self.assertEqual(statuses, [200])
                archive = handler.wfile.getvalue().decode()
                self.assertIn(
                    '<div class="blog-featured" data-publish-date="2026-09-29">'
                    '<a class="bf-img" href="/blog/hospice-and-advanced-heart-failure"',
                    archive,
                )
                self.assertIn(
                    'class="rc" data-publish-date="2026-09-21" '
                    'href="/blog/what-happens-during-a-hospice-evaluation"',
                    archive,
                )
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_build_is_additive_and_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory) / "elh-preview"
            posts = public / "blog"
            posts.mkdir(parents=True)
            (public / "assets").symlink_to(ROOT / "elh-preview" / "assets", target_is_directory=True)
            (public / "blog.html").write_bytes((ROOT / "elh-preview" / "blog.html").read_bytes())
            (public / "sitemap.xml").write_bytes((ROOT / "elh-preview" / "sitemap.xml").read_bytes())
            existing = posts / "what-happens-during-a-hospice-evaluation.html"
            existing.write_text((ROOT / "elh-preview" / "blog" / existing.name).read_text() + "\nEDITORIAL EDIT")
            for legacy in builder.LEGACY_POSTS:
                name = f'{legacy["slug"]}.html'
                (posts / name).write_bytes((ROOT / "elh-preview" / "blog" / name).read_bytes())
            with patch.object(builder, "PUBLIC", public), patch.object(builder, "OUT", posts), \
                 patch.object(builder, "MANIFEST", Path(directory) / "manifest.json"), \
                 patch.object(builder.subprocess, "run") as search_build:
                builder.build(self.articles)
                self.assertTrue((posts / "preparing-for-a-hospice-care-plan-conversation.html").exists())
                self.assertTrue(existing.read_text().endswith("EDITORIAL EDIT"))
                first = {p.name: p.read_bytes() for p in posts.glob("*.html")}
                builder.build(self.articles)
                self.assertEqual(first, {p.name: p.read_bytes() for p in posts.glob("*.html")})
                self.assertTrue(existing.read_text().endswith("EDITORIAL EDIT"))
                self.assertIn("preparing-for-a-hospice-care-plan-conversation",
                              (public / "sitemap.xml").read_text())
                self.assertEqual(search_build.call_count, 2)

    def test_future_story_is_hidden_from_search_and_sitemap(self):
        old = os.environ.get("ELH_JOURNAL_DATE")
        slug = "preparing-for-a-hospice-care-plan-conversation"
        try:
            for today, visible in (("2026-10-20", False), ("2026-10-21", True)):
                os.environ["ELH_JOURNAL_DATE"] = today
                for relative in ("assets/search-index.json", "sitemap.xml"):
                    with self.subTest(today=today, artifact=relative):
                        handler = PrettyURLHandler.__new__(PrettyURLHandler)
                        handler.command = "GET"
                        handler.wfile = io.BytesIO()
                        handler.send_response = lambda *_: None
                        handler.send_header = lambda *_: None
                        handler.end_headers = lambda: None
                        handler.guess_type = lambda *_: "application/json"
                        self.assertTrue(handler._send_journal_artifact(
                            str(ROOT / "elh-preview" / relative)
                        ))
                        self.assertEqual(slug in handler.wfile.getvalue().decode(), visible)
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_continuation_dates_need_not_be_consecutive(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(builder, "CONTENT", Path(directory)):
                for source in (ROOT / "content" / "30-day-journal").glob("batch-*.json"):
                    (Path(directory) / source.name).write_bytes(source.read_bytes())
                new = dict(self.articles[-1], date="2027-01-02", slug="another-story",
                           heroImage="/assets/img/inline-f9dec1d865.jpg")
                (Path(directory) / "additional-next.json").write_text(json.dumps([new]))
                self.assertEqual(builder.load_articles()[-1]["date"], "2027-01-02")
                new["date"] = "2026-10-20"
                (Path(directory) / "additional-next.json").write_text(json.dumps([new]))
                with self.assertRaisesRegex(ValueError, "after 2026-10-20"):
                    builder.load_articles()

    def test_manifest_accepts_later_years_and_gates_their_pages(self):
        old = os.environ.get("ELH_JOURNAL_DATE")
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(json.dumps({
                "timezone": "America/Los_Angeles",
                "articles": [{"slug": "later-story", "date": "2027-01-02",
                              "url": "/blog/later-story"}],
            }))
            try:
                row = {"date": "2027-01-02", "revision": "a" * 64,
                       "html": "<h1>Synthetic later story</h1>"}
                def later_release():
                    return ({"later-story": row} if
                            PrettyURLHandler._journal_today() >= row["date"] else {}), True
                with patch("devserver.JOURNAL_MANIFEST", str(manifest_path)), \
                     patch.object(journal_release, "released", side_effect=later_release):
                    os.environ["ELH_JOURNAL_DATE"] = "2027-01-01"
                    self.assertTrue(PrettyURLHandler._future_journal_path("/blog/later-story"))
                    os.environ["ELH_JOURNAL_DATE"] = "2027-01-02"
                    self.assertFalse(PrettyURLHandler._future_journal_path("/blog/later-story"))
            finally:
                if old is None:
                    os.environ.pop("ELH_JOURNAL_DATE", None)
                else:
                    os.environ["ELH_JOURNAL_DATE"] = old

    def test_synthetic_archive_and_discovery_use_released_copy_not_due_drafts(self):
        """Release membership, not today's date or staged copy, grants visibility."""
        def article(slug, title, day="2026-11-01"):
            return {"slug": slug, "title": title, "date": day,
                    "description": title + " summary.", "category": "Family Support",
                    "readMinutes": 4, "heroImage": "/assets/img/synthetic.jpg"}

        approved = article("synthetic-approved", "Frozen approved heading")
        pending = dict(approved, title="UNAPPROVED_REPLACEMENT",
                       description="UNAPPROVED_SUMMARY")
        draft = article("synthetic-draft", "UNAPPROVED_DUE_STORY")
        future = article("synthetic-future", "UNRELEASED_FUTURE_STORY", "2026-11-02")
        archived = article("synthetic-archived", "ARCHIVED_SOURCE")
        archived["publicationStatus"] = "archived"
        active = [pending, draft, future]
        all_articles = active + [archived]
        schema = {"@type": "Blog", "blogPost": [
            {"url": builder.BASE_URL + a["slug"], "headline": a["title"]}
            for a in all_articles]}
        # The staged archive deliberately contains both unapproved and archived
        # entries so filtering assertions cannot pass because inputs are absent.
        staged = ('<html><head><script type="application/ld+json">' +
                  json.dumps(schema) + '</script></head><body>' +
                  builder.card(future, True) + '<section><div class="rgrid">' +
                  "".join(builder.card(a) for a in all_articles) +
                  '</div></section></body></html>')
        document = ('<section class="hero"><h1>' + approved["title"] +
                    '</h1><p>' + approved["description"] + '</p></section>')
        released = {approved["slug"]: {"date": approved["date"], "html": document,
                                     "revision": hashlib.sha256(document.encode()).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            (public / "assets").mkdir()
            (public / "blog.html").write_text(staged)
            search = [{"url": "/blog/" + a["slug"], "title": a["title"]} for a in all_articles]
            search.append({"url": "/family-guide", "title": "Family Guide"})
            (public / "assets/search-index.json").write_text(json.dumps(search))
            (public / "sitemap.xml").write_text('<urlset>' + "".join(
                f'<url><loc>{builder.BASE_URL}{a["slug"]}</loc></url>' for a in all_articles
            ) + '<url><loc>https://eternallifehospice.com/family-guide</loc></url></urlset>')
            manifest = public / "manifest.json"
            manifest.write_text(json.dumps({"timezone": "America/Los_Angeles",
                                           "articles": all_articles}))
            before = {p: p.read_bytes() for p in public.rglob("*") if p.is_file()}
            with patch("devserver.ROOT", str(public)), \
                 patch("devserver.JOURNAL_MANIFEST", str(manifest)), \
                 patch.dict(os.environ, {"ELH_JOURNAL_DATE": "2026-11-01"}), \
                 patch.object(journal_release, "released", return_value=(released, True)):
                self.assertFalse(PrettyURLHandler._future_journal_path("/blog/synthetic-approved"))
                for a in (draft, future, archived):
                    self.assertTrue(PrettyURLHandler._future_journal_path("/blog/" + a["slug"]))
                for relative in ("blog.html", "assets/search-index.json", "sitemap.xml"):
                    with self.subTest(artifact=relative):
                        handler = PrettyURLHandler.__new__(PrettyURLHandler)
                        handler.command = "GET"
                        handler.wfile = io.BytesIO()
                        statuses = []
                        handler.send_response = statuses.append
                        handler.send_header = lambda *_: None
                        handler.end_headers = lambda: None
                        self.assertTrue(handler._send_journal_artifact(str(public / relative)))
                        self.assertEqual(statuses, [200])
                        body = handler.wfile.getvalue().decode()
                        self.assertIn("/blog/synthetic-approved", body)
                        for hidden in (draft["slug"], future["slug"], archived["slug"],
                                       pending["title"], pending["description"]):
                            self.assertNotIn(hidden, body)
                        if relative != "sitemap.xml":
                            self.assertIn(approved["title"], body)
                            self.assertIn(approved["description"], body)
                        if relative != "blog.html":
                            self.assertIn("/family-guide", body)
                        else:
                            self.assertEqual(body.count('<div class="blog-featured"'), 1)
                            self.assertNotIn('class="rc" data-publish-date=', body)
            self.assertEqual(before, {p: p.read_bytes() for p in before})


class PublicationClockTests(unittest.TestCase):
    """Clock checks do not use the date-only layout-release fixture."""

    def test_local_date_uses_pacific_day_not_utc_day(self):
        for instant, expected in (
            (datetime(2026, 9, 22, 6, 59, tzinfo=timezone.utc), "2026-09-21"),
            (datetime(2026, 9, 22, 7, 0, tzinfo=timezone.utc), "2026-09-22"),
            (datetime(2026, 11, 2, 7, 59, tzinfo=timezone.utc), "2026-11-01"),
            (datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc), "2026-11-02"),
        ):
            with self.subTest(instant=instant), \
                 patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0", "ELH_JOURNAL_DATE": ""}), \
                 patch("devserver.datetime") as clock:
                clock.now.side_effect = lambda zone: instant.astimezone(zone)
                self.assertEqual(PrettyURLHandler._journal_today(), expected)

    def test_date_override_is_workspace_only_and_invalid_dates_fail_closed(self):
        instant = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0", "ELH_JOURNAL_DATE": "2027-01-02"}):
            self.assertEqual(PrettyURLHandler._journal_today(), "2027-01-02")
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0", "ELH_JOURNAL_DATE": "2026-02-30"}):
            self.assertIsNone(PrettyURLHandler._journal_today())
            self.assertTrue(PrettyURLHandler._future_journal_path("/blog/synthetic-approved"))
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1", "ELH_JOURNAL_DATE": "2027-01-02"}), \
             patch("devserver.datetime") as clock:
            clock.now.side_effect = lambda zone: instant.astimezone(zone)
            self.assertEqual(PrettyURLHandler._journal_today(), "2026-11-02")


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-journal-campaign.py OK")
    raise SystemExit(not result.result.wasSuccessful())
