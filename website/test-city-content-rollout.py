#!/usr/bin/env python3
"""Content, preservation and measurement checks for the approved wider rollout."""
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
PILOTS = {"thousand-oaks", "westlake-village", "simi-valley", "calabasas", "ventura"}
spec = importlib.util.spec_from_file_location("city_audit", ROOT / "audit-city-redundancy.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class RolloutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cities = json.loads((ROOT / "city-data.json").read_text())
        cls.rewritten = [c for c in cls.cities if c["slug"] not in PILOTS]
        cls.index = {p["url"]: p for p in json.loads(
            (PUBLIC / "assets/search-index.json").read_text())}
        cls.sitemap = ET.parse(PUBLIC / "sitemap.xml")
        cls.ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def test_all_remaining_pages_have_complete_editorial_sections(self):
        self.assertEqual(len(self.rewritten), 140)
        for city in self.rewritten:
            with self.subTest(city=city["slug"]):
                page = (PUBLIC / f"hospice-{city['slug']}-ca.html").read_text()
                for field in ("heroIntroduction", "beginningCareHtml", "coverageHtml",
                              "resourcesHtml", "providerContext", "familyContext"):
                    self.assertTrue(city[field].strip())
                    self.assertIn(city[field], page)
                self.assertIn(city["city"], city["title"])
                self.assertIn(city["city"], city["h1"])
                self.assertEqual(city["metaDescription"], city["searchMetaDescription"])
                self.assertEqual(city["faqItems"], city["displayFaqItems"])
                self.assertGreaterEqual(len(city["localIntroduction"].split("\n\n")), 2)

    def test_visible_faq_matches_schema_on_every_rewritten_page(self):
        def plain(value):
            return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())
        for city in self.rewritten:
            page = (PUBLIC / f"hospice-{city['slug']}-ca.html").read_text()
            visible = [(plain(q), plain(a)) for q, a in re.findall(
                r'<details class="faq-item"[^>]*><summary>(.*?)</summary><p>(.*?)</p>',
                page, re.S)]
            schemas = [json.loads(s) for s in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
            faq = next(s for s in schemas if s.get("@type") == "FAQPage")
            self.assertEqual(visible, [(plain(q["name"]), plain(q["acceptedAnswer"]["text"]))
                                       for q in faq["mainEntity"]], city["slug"])

    def test_pilot_pages_and_county_hub_remain_byte_identical(self):
        hashes = json.loads((ROOT.parent /
                             "exports/seo/city-rewrite-preservation.json").read_text())
        self.assertEqual(len(hashes), 6)
        for filename, digest in hashes.items():
            self.assertEqual(hashlib.sha256((PUBLIC / filename).read_bytes()).hexdigest(),
                             digest, filename)

    def test_city_search_metadata_matches_sources(self):
        for city in self.cities:
            entry = self.index[urlsplit(city["canonicalUrl"]).path]
            title = re.sub(r"\s*[|–—]\s*Eternal Life Hospice.*$", "",
                           city["title"]).strip()
            self.assertEqual(entry["title"], title)
            self.assertEqual(entry["desc"], city["metaDescription"])

    def test_rewritten_sitemap_dates_match_material_updates(self):
        dates = {u.find("s:loc", self.ns).text: u.find("s:lastmod", self.ns).text
                 for u in self.sitemap.findall("s:url", self.ns)}
        for city in self.rewritten:
            self.assertEqual(dates[city["canonicalUrl"]], city["lastMaterialUpdate"])

    def test_island_and_regional_guidance_is_not_a_blanket_service_promise(self):
        by_slug = {c["slug"]: c for c in self.rewritten}
        avalon = by_slug["avalon"]
        self.assertIn("an inquiry does not confirm availability", avalon["heroIntroduction"])
        self.assertIn("not a substitute", avalon["faqItems"][2]["a"])
        self.assertIn("Ventura and Los Angeles", by_slug["conejo-valley"]["localIntroduction"])
        self.assertIn("not automatically unrelated", by_slug["point-mugu"]["faqItems"][2]["a"])

    def test_copy_does_not_claim_equipment_or_supply_copayments(self):
        for city in self.rewritten:
            self.assertNotRegex(
                city["coverageHtml"].lower(),
                r"(?:copayments.{0,55}(?:equipment|supplies)|"
                r"(?:equipment|supplies) may require copayments)",
                city["slug"],
            )


class MeasurementTests(unittest.TestCase):
    def test_shared_chrome_excluded_from_primary_measure(self):
        markup = ('<head><title>ignore</title></head><body><header>header shared</header>'
                  '<main><nav>breadcrumb shared</nav><p>unique care guidance</p>'
                  '<div class="hero-btns">call shared</div><script>ignore</script></main>'
                  '<footer>footer shared</footer></body>')
        pattern = re.compile("never-match")
        self.assertEqual(audit.tokens(markup, True, pattern),
                         ["unique", "care", "guidance"])
        self.assertIn("header", audit.tokens(markup, False, pattern))
        self.assertNotIn("ignore", audit.tokens(markup, False, pattern))

    def test_city_name_swaps_do_not_create_artificial_uniqueness(self):
        pattern = re.compile(r"\b(?:acton|agoura hills)\b", re.I)
        left = audit.tokens("<main><p>Guidance in Acton for families</p></main>", True, pattern)
        right = audit.tokens("<main><p>Guidance in Agoura Hills for families</p></main>", True, pattern)
        self.assertEqual(left, right)

    def test_repeated_word_positions_are_counted_once(self):
        shared = "one two three four five six seven eight nine ten".split()
        stats = audit.summarize({"left": shared + ["left"], "right": shared + ["right"]})
        self.assertEqual(stats["total_repeated_words"], 20)
        self.assertEqual(stats["word_weighted_redundancy_percent"], 90.91)

    def test_repetition_within_one_page_is_not_cross_page_duplication(self):
        words = "one two three four five six seven eight".split()
        stats = audit.summarize({"left": words * 2, "right": ["different"] * 8})
        self.assertEqual(stats["total_repeated_words"], 0)

    def test_both_snapshots_use_identical_scope_and_method(self):
        before = json.loads((ROOT.parent / "exports/seo/city-redundancy-before.json").read_text())
        after = json.loads((ROOT.parent / "exports/seo/city-redundancy-after.json").read_text())
        self.assertEqual(before["page_count"], 145)
        self.assertEqual(before["page_count"], after["page_count"])
        self.assertEqual(before["method"], after["method"])
        self.assertEqual(set(before["main_content"]["per_page"]),
                         set(after["main_content"]["per_page"]))
        self.assertLess(after["main_content"]["word_weighted_redundancy_percent"],
                        before["main_content"]["word_weighted_redundancy_percent"])


if __name__ == "__main__":
    unittest.main()