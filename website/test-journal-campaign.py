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
        self.assertEqual(len(self.articles), 30)
        self.assertEqual(
            [a["date"] for a in self.articles],
            [(date(2026, 9, 21) + timedelta(days=i)).isoformat() for i in range(30)],
        )
        self.assertEqual(len({a["slug"] for a in self.articles}), 30)

    def test_archived_source_is_not_in_publication_schedule(self):
        archived_slug = "can-a-family-request-a-hospice-evaluation"
        archived = [a for a in self.articles if a["slug"] == archived_slug]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].get("publicationStatus"), "archived")
        active = [a for a in self.articles if a.get("publicationStatus") != "archived"]
        self.assertEqual(len(active), 29)
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
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_generated_metadata_and_schedule(self):
        manifest = json.loads((ROOT / "content" / "30-day-journal-manifest.json").read_text())
        self.assertEqual(len(manifest["articles"]), 29)
        archive = (ROOT / "elh-preview" / "blog.html").read_text()
        for article in self.articles:
            if article.get("publicationStatus") == "archived":
                continue
            page = (ROOT / "elh-preview" / "blog" / f'{article["slug"]}.html').read_text()
            self.assertIn(f'<link rel="canonical" href="https://eternallifehospice.com/blog/{article["slug"]}">', page)
            self.assertIn(f'"datePublished":"{article["date"]}"', page.replace(" ", ""))
            self.assertIn(f"background-image:url('..{article['heroImage']}')", page)
            self.assertIn(f"https://eternallifehospice.com{article['heroImage']}", page)
            self.assertNotIn('property="og:image:width"', page)
            self.assertNotIn('property="og:image:height"', page)
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
            "date": "2026-10-21",
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
                    ("2026-10-20", "how-physicians-and-facilities-refer-a-patient-to-hospice"),
                    ("2026-10-21", "new-journal-story"),
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
                        self.assertEqual(featured, [(today, f"blog/{expected_slug}")])
                        self.assertNotIn(
                            f'class="rc" data-publish-date="{today}" href="blog/{expected_slug}"',
                            archive,
                        )
                        if today == "2026-10-20":
                            self.assertNotIn('href="blog/new-journal-story"', archive)
                        else:
                            self.assertIn(
                                'class="rc" data-publish-date="2026-10-20" '
                                'href="blog/how-physicians-and-facilities-refer-a-patient-to-hospice"',
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


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-journal-campaign.py OK")
    raise SystemExit(not result.result.wasSuccessful())