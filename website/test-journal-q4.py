#!/usr/bin/env python3
"""Checks the full Q4 editorial package, not just the article generator."""
import importlib.util
import json
import os
import re
import unittest
from datetime import date, timedelta
from pathlib import Path
from PIL import Image
from devserver import PrettyURLHandler

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
spec = importlib.util.spec_from_file_location("journal_builder", ROOT / "build-journal-campaign.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
spec2 = importlib.util.spec_from_file_location("q4_authoring", ROOT / "author-journal-q4.py")
authoring = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(authoring)


class Q4EditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = json.loads((ROOT / "content/30-day-journal/additional-2026-q4.json").read_text())
        cls.photos = json.loads((ROOT / "content/journal-q4-photo-sources.json").read_text())

    def test_daily_dates_and_unique_titles(self):
        self.assertEqual(len(self.articles), 71)
        self.assertEqual([a["date"] for a in self.articles],
                         [(date(2026, 10, 22) + timedelta(days=i)).isoformat() for i in range(71)])
        for key in ("title", "slug", "heroImage"):
            self.assertEqual(len({a[key] for a in self.articles}), 71)

    def test_first_and_last_articles_obey_publication_dates(self):
        old = os.environ.get("ELH_JOURNAL_DATE")
        try:
            for today in ("2026-10-21", "2026-10-22", "2026-12-30", "2026-12-31"):
                os.environ["ELH_JOURNAL_DATE"] = today
                for a in (self.articles[0], self.articles[-1]):
                    for suffix in ("", ".html", "/"):
                        self.assertEqual(
                            PrettyURLHandler._future_journal_path("/blog/" + a["slug"] + suffix),
                            a["date"] > today,
                        )
        finally:
            if old is None:
                os.environ.pop("ELH_JOURNAL_DATE", None)
            else:
                os.environ["ELH_JOURNAL_DATE"] = old

    def test_varied_lengths_and_original_paragraphs(self):
        lengths, paragraphs = [], set()
        for a in self.articles:
            lengths.append(authoring.words(a))
            self.assertGreaterEqual(len(a["sections"]), 3)
            for section in a["sections"]:
                for text in section["paragraphs"]:
                    normalized = re.sub(r"\W+", " ", text.lower()).strip()
                    self.assertNotIn(normalized, paragraphs, a["slug"])
                    paragraphs.add(normalized)
            self.assertNotRegex(json.dumps(a), r"(?i)overwhelm")
        self.assertGreaterEqual(min(lengths), 350)
        self.assertLess(min(lengths), 550)
        self.assertGreater(max(lengths), 900)
        self.assertLessEqual(max(lengths), 1400)
        self.assertGreaterEqual(len({a["format"] for a in self.articles}), 5)

    def test_contextual_links_exist_in_every_article(self):
        for a in self.articles:
            with self.subTest(slug=a["slug"]):
                text = a["lede"] + "\n" + "\n".join(
                    p for section in a["sections"] for p in section["paragraphs"])
                paths = {m.group(2) for m in builder.INLINE_LINK.finditer(text)}
                self.assertGreaterEqual(len(paths), 3)
                for path in paths:
                    self.assertTrue(path.startswith("/") and not path.startswith("//"))
                    route = path.split("#")[0].split("?")[0].lstrip("/")
                    self.assertTrue((PUBLIC / (route + ".html")).exists() or
                                    (PUBLIC / route / "index.html").exists(), path)
                page = (PUBLIC / "blog" / (a["slug"] + ".html")).read_text()
                self.assertIn("The Eternal Life Hospice Team", page)
                self.assertNotRegex(page, r"\[[^\]]+\]\(/")
                self.assertIn('class="journal-photo-credit"', page)

    def test_local_and_national_mix(self):
        counts = {}
        for a in self.articles:
            counts[a["location"]] = counts.get(a["location"], 0) + 1
        self.assertEqual(counts["national"], 48)
        for city in authoring.CITY_ROUTES:
            self.assertGreaterEqual(counts.get(city, 0), 2, city)

    def test_distinct_photographs_and_credits(self):
        self.assertEqual(len(self.photos), 71)
        self.assertEqual(len({r["sourceUrl"] for r in self.photos}), 71)
        self.assertEqual(len({r["sha256"] for r in self.photos}), 71)
        hashes = []
        for a in self.articles:
            credit = a["photoCredit"]
            self.assertTrue(credit["sourceUrl"].startswith("https://"))
            self.assertTrue(credit["licenseUrl"].startswith("https://"))
            self.assertIn(credit["sourceName"], ("Wikimedia Commons", "Pexels"))
            with Image.open(PUBLIC / a["heroImage"].lstrip("/")) as im:
                h = authoring.dhash(im)
            for old in hashes:
                self.assertGreater((h ^ old).bit_count(), 6, a["slug"])
            hashes.append(h)


if __name__ == "__main__":
    unittest.main()
