#!/usr/bin/env python3
"""Focused checks for the five-city editorial pilot; never writes site files."""
import html
import importlib.util
import itertools
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
PILOTS = ("thousand-oaks", "westlake-village", "simi-valley", "calabasas", "ventura")
spec = importlib.util.spec_from_file_location("city_builder", ROOT / "build-cities.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def plain(markup):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


class CityContentPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_cities = json.loads((ROOT / "city-data.json").read_text())
        cls.cities = {c["slug"]: c for c in cls.all_cities if c["slug"] in PILOTS}
        cls.pages = {
            slug: (PUBLIC / f"hospice-{slug}-ca.html").read_text()
            for slug in PILOTS
        }

    def test_source_and_generated_pilots_match(self):
        self.assertEqual(set(self.cities), set(PILOTS))
        for slug, city in self.cities.items():
            with self.subTest(slug=slug):
                self.assertEqual(builder._normalise(self.pages[slug]),
                                 builder._normalise(builder.render_page(city)))

    def test_search_and_opening_copy_are_distinct(self):
        for field in ("title", "h1", "heroIntroduction", "searchMetaDescription"):
            normalized = []
            for slug, city in self.cities.items():
                with self.subTest(slug=slug, field=field):
                    value = city.get(field, "")
                    self.assertTrue(value.strip())
                    self.assertIn(city["city"], value)
                    normalized.append(value.replace(city["city"], "[CITY]").lower())
            self.assertEqual(len(set(normalized)), len(PILOTS),
                             f"{field} must not be city-name substitutions")
        for slug, city in self.cities.items():
            self.assertEqual(city["metaDescription"], city["searchMetaDescription"])
            self.assertIn(f'<h1>{city["h1"]}</h1>', self.pages[slug])
            self.assertIn(f'<title>{city["title"]}</title>', self.pages[slug])

    def test_faq_schema_matches_visible_local_questions(self):
        for slug, page in self.pages.items():
            with self.subTest(slug=slug):
                self.assertEqual(self.cities[slug]["faqItems"], self.cities[slug]["displayFaqItems"])
                visible = [
                    (plain(q), plain(a))
                    for q, a in re.findall(
                        r'<details class="faq-item"[^>]*><summary>(.*?)</summary><p>(.*?)</p>',
                        page, re.S,
                    )
                ]
                schemas = [
                    json.loads(value) for value in re.findall(
                        r'<script type="application/ld\+json">(.*?)</script>', page, re.S
                    )
                ]
                faq = [s for s in schemas if s.get("@type") == "FAQPage"]
                self.assertEqual(len(faq), 1)
                self.assertGreaterEqual(len(visible), 3)
                expected = [
                    (plain(f["name"]), plain(f["acceptedAnswer"]["text"]))
                    for f in faq[0]["mainEntity"]
                ]
                self.assertEqual(visible, expected)

    def test_main_has_real_local_links_and_beginning_care_guidance(self):
        for slug, page in self.pages.items():
            with self.subTest(slug=slug):
                main = re.search(r'<main\b[^>]*>(.*?)</main>', page, re.S).group(1)
                city = self.cities[slug]
                self.assertTrue(city.get("beginningCareHtml", "").strip())
                self.assertIn(f'<h2>{city["beginningCareHeading"]}</h2>', main)
                self.assertIn(city["beginningCareHtml"], main)
                self.assertIn("hospice-ventura-and-los-angeles-county-ca", main)
                self.assertIn("tel:18059537273", main)
                self.assertIn("/refer#referral-form", main)
                resource_links = set()
                for href in re.findall(r'href="([^"]+)"', main):
                    parsed = urlsplit(html.unescape(href))
                    if parsed.scheme or not parsed.path:
                        continue
                    path = PUBLIC / parsed.path.lstrip("/")
                    self.assertTrue(
                        path.is_file() or Path(str(path) + ".html").is_file()
                        or path.is_dir(), f"Broken internal link: {slug}: {href}",
                    )
                    if parsed.path.startswith(("/resources/", "/services/", "/blog/")):
                        resource_links.add(parsed.path)
                self.assertGreaterEqual(len(resource_links), 3)
                self.assertIn('href="/services"', main)

    def test_long_informational_paragraphs_are_not_swapped_between_pilots(self):
        paragraphs = {}
        names = sorted((c["city"] for c in self.all_cities), key=len, reverse=True)
        for slug, page in self.pages.items():
            main = re.search(r'<main\b[^>]*>(.*?)</main>', page, re.S).group(1)
            paragraphs[slug] = set()
            for paragraph in re.findall(r'<p\b[^>]*>(.*?)</p>', main, re.S):
                text = plain(paragraph).lower()
                for name in names:
                    text = re.sub(r"\b" + re.escape(name.lower()) + r"\b", "[city]", text)
                if len(text.split()) >= 35:
                    paragraphs[slug].add(text)
        for left, right in itertools.combinations(PILOTS, 2):
            self.assertFalse(paragraphs[left] & paragraphs[right],
                             f"Long copy duplicated between {left} and {right}")


if __name__ == "__main__":
    unittest.main()