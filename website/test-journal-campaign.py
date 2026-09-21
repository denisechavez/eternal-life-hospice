#!/usr/bin/env python3
"""Focused invariants for the Eternal Journal publication campaign."""
import importlib.util
import json
import os
import sys
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
        self.assertEqual(len(manifest["articles"]), 30)
        for article in self.articles:
            page = (ROOT / "elh-preview" / "blog" / f'{article["slug"]}.html').read_text()
            self.assertIn(f'<link rel="canonical" href="https://eternallifehospice.com/blog/{article["slug"]}">', page)
            self.assertIn(f'"datePublished":"{article["date"]}"', page.replace(" ", ""))


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-journal-campaign.py OK")
    raise SystemExit(not result.result.wasSuccessful())