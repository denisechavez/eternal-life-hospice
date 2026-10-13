#!/usr/bin/env python3
"""Passage-preservation, publication, seven-link cap and regeneration checks."""
import html
import re
import unittest
import sys
from unittest.mock import patch

from inline_links import ProseParser, apply_inline_links, signature
from internal_links import inventory


class InlineLinksTests(unittest.TestCase):
    def fixture(self):
        copy = "Clear answers on when hospice begins, what it covers, how to choose a provider, and what to expect from the very first day."
        text = "<main><p>" + copy + "</p></main><footer><p>" + copy + "</p></footer>"
        data = {"/hospice-care": [
            {"paragraph": signature(copy), "phrase": "what it covers", "href": "/resources/medicare-hospice-benefit"},
            {"paragraph": signature(copy), "phrase": "how to choose a provider", "href": "/resources/how-to-choose-a-hospice"}]}
        eligible = {"/resources/medicare-hospice-benefit": None,
                    "/resources/how-to-choose-a-hospice": None}
        return text, data, eligible

    def test_exact_paragraph_only_and_idempotence(self):
        text, data, eligible = self.fixture()
        with patch("inline_links.editorial_map", return_value=data):
            result = apply_inline_links(text, "/hospice-care", eligible)
            self.assertEqual(result.count('class="elh-inline-link"'), 2)
            self.assertEqual(text.split("<footer>")[1], result.split("<footer>")[1])
            self.assertEqual(re.sub("<[^>]+>", "", text), re.sub("<[^>]+>", "", result))
            self.assertEqual(result, apply_inline_links(result, "/hospice-care", eligible))

    def test_changed_paragraph_is_not_keyword_replaced(self):
        text, data, eligible = self.fixture()
        with patch("inline_links.editorial_map", return_value=data):
            changed = text.replace("Clear answers", "Different wording")
            self.assertEqual(changed, apply_inline_links(changed, "/hospice-care", eligible))

    def test_future_and_self_targets_not_linked(self):
        text, data, eligible = self.fixture()
        with patch("inline_links.editorial_map", return_value=data):
            self.assertEqual(text, apply_inline_links(text, "/hospice-care", {}))
            data["/hospice-care"][0]["href"] = "/hospice-care"
            result = apply_inline_links(text, "/hospice-care", eligible)
            self.assertEqual(result.count('class="elh-inline-link"'), 1)

    def test_existing_links_count_and_cap_preserves_words(self):
        copy = "We discuss practical questions about " + ", ".join(
            f'<a href="/guide-{i}">care question {i}</a>' for i in range(9)) + " together."
        text = "<main><p>" + copy + "</p></main>"
        with patch("inline_links.editorial_map", return_value={}):
            result = apply_inline_links(text, "/services", {f"/guide-{i}": None for i in range(9)})
        self.assertEqual(result.count('class="elh-inline-link"'), 7)
        self.assertEqual(re.sub("<[^>]+>", "", text), re.sub("<[^>]+>", "", result))

    def test_cards_buttons_and_city_directory_are_not_prose(self):
        text = ('<main><div class="blog-featured"><p>Read hospice care stories and learn about the next useful answer here.</p></div>'
                '<section class="cta"><p>Discover our hospice care and speak with the team about your needs.</p></section>'
                '<p>Explore hospice care in <a href="/hospice-a-ca">City A</a> and '
                '<a href="/hospice-b-ca">City B</a> to find a community guide.</p></main>')
        self.assertEqual(ProseParser(text, "/services").blocks, [])

    def test_all_informational_pages_have_two_to_seven_and_safe_destinations(self):
        current = inventory()
        pages = inventory("9999-12-31")
        utilities = {"/privacy-policy", "/terms", "/sitemap", "/referral-card"}
        for route, (_, text, _) in pages.items():
            if route in utilities:
                continue
            parser = ProseParser(text, route)
            links = [a for b in parser.blocks for a in b["links"]]
            self.assertGreaterEqual(len(links), 2, route)
            # The approved nine-item modality directory is an explicit exception,
            # not a higher content-link budget for other informational pages.
            jumps = [a for a in links if route == "/resources/comfort-therapies"
                     and a["href"].startswith("/#therapy-")]
            if route == "/resources/comfort-therapies":
                self.assertEqual(len(jumps), 9)
                self.assertEqual(len({a["href"] for a in jumps}), 9)
            self.assertLessEqual(len(links) - len(jumps), 7, route)
            for anchor in links:
                self.assertIn(anchor["target"], current, (route, anchor["href"]))
                self.assertIn("elh-inline-link", anchor["open"], (route, anchor["text"]))
            self.assertEqual(text, apply_inline_links(text, route, current), route)

    def test_regeneration_reapplies_annotations(self):
        from inline_links import editorial_map
        pages = inventory("9999-12-31")
        for route in editorial_map():
            original = pages[route][1]
            stripped = re.sub(r'<a\b[^>]*class="elh-inline-link"[^>]*>(.*?)</a>',
                              r"\1", original, flags=re.S)
            reapplied = apply_inline_links(stripped, route, inventory())
            for annotation in editorial_map()[route]:
                self.assertIn(f'>{annotation["phrase"]}</a>', reapplied, (route, annotation["phrase"]))


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    if not result.wasSuccessful():
        sys.exit(1)
    print("SENTINEL: test-inline-links.py contextual links OK")
