#!/usr/bin/env python3
"""Focused invariants for the Eternal Journal publication campaign."""
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("journal_builder", ROOT / "build-journal-campaign.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
from devserver import PrettyURLHandler


class JournalCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = builder.load_articles()

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
        self.assertEqual(manifest["end"], "2026-10-21")
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
                ("2027-01-01", "2026-10-21", "preparing-for-a-hospice-care-plan-conversation"),
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
                    self.assertEqual(featured, [(expected_date, f"blog/{slug}", image)])
                    self.assertNotIn(f'class="rc" data-publish-date="{expected_date}" href="blog/{slug}"', archive)
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
                    ("2027-01-01", "preparing-for-a-hospice-care-plan-conversation"),
                    ("2027-01-02", "new-journal-story"),
                ):
                    with self.subTest(today=today):
                        os.environ["ELH_JOURNAL_DATE"] = today
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
                        featured = re.findall(
                            r'<div class="blog-featured" data-publish-date="([^"]+)">'
                            r'<a class="bf-img" href="([^"]+)"',
                            archive,
                        )
                        expected_date = "2026-10-21" if today == "2027-01-01" else today
                        self.assertEqual(featured, [(expected_date, f"blog/{expected_slug}")])
                        self.assertNotIn(
                            f'class="rc" data-publish-date="{expected_date}" href="blog/{expected_slug}"',
                            archive,
                        )
                        if today == "2027-01-01":
                            self.assertNotIn('href="blog/new-journal-story"', archive)
                        else:
                            self.assertIn(
                                'class="rc" data-publish-date="2026-10-21" '
                                'href="blog/preparing-for-a-hospice-care-plan-conversation"',
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
                    '<a class="bf-img" href="blog/hospice-and-advanced-heart-failure"',
                    archive,
                )
                self.assertIn(
                    'class="rc" data-publish-date="2026-09-21" '
                    'href="blog/what-happens-during-a-hospice-evaluation"',
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
                with patch("devserver.JOURNAL_MANIFEST", str(manifest_path)):
                    os.environ["ELH_JOURNAL_DATE"] = "2027-01-01"
                    self.assertTrue(PrettyURLHandler._future_journal_path("/blog/later-story"))
                    os.environ["ELH_JOURNAL_DATE"] = "2027-01-02"
                    self.assertFalse(PrettyURLHandler._future_journal_path("/blog/later-story"))
            finally:
                if old is None:
                    os.environ.pop("ELH_JOURNAL_DATE", None)
                else:
                    os.environ["ELH_JOURNAL_DATE"] = old


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-journal-campaign.py OK")
    raise SystemExit(not result.result.wasSuccessful())