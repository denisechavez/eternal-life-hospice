#!/usr/bin/env python3
"""Fixed editorial analytics metadata, including publication boundaries."""
import unittest
from urllib.parse import urlsplit

from internal_links import PageParser, config, inventory, recommendations, render_links


class RelatedReadingTests(unittest.TestCase):
    def test_fixed_metadata_for_every_curated_link(self):
        pages = inventory("2026-10-07")
        topics = set(config()["topics"]) | {"support"}
        for source, (_, text, _) in pages.items():
            rendered = render_links(text, source, "2026-10-07", pages)
            links = [attrs for _, _, attrs in PageParser(rendered).links
                     if "data-reading-source" in attrs]
            expected = recommendations(source, "2026-10-07", pages)
            self.assertEqual(len(links), len(expected), source)
            for attrs, (dest, _) in zip(links, expected):
                self.assertEqual(attrs["data-reading-source"], source)
                self.assertEqual(attrs["data-reading-destination"], urlsplit(dest).path)
                self.assertIn(attrs["data-reading-topic"], topics)
                self.assertNotIn("?", attrs["data-reading-destination"])
                self.assertNotIn("#", attrs["data-reading-destination"])

    def test_special_groups(self):
        for source, destination, topic in [
            ("/media-kit", "/refer", "referral"),
            ("/resources", "/resources/the-circle-around-you", "support"),
            ("/blog/hospice-at-home-in-thousand-oaks-what-families-can-expect",
             "/hospice-thousand-oaks-ca", "local"),
        ]:
            links = recommendations(source, "2026-10-07", with_topics=True)
            self.assertIn((destination, topic),
                          [(urlsplit(dest).path, group) for dest, _, group in links])

    def test_cached_metadata_cannot_expose_future_article(self):
        source = "/resources/medicare-hospice-benefit"
        future = "/blog/does-medicare-cover-hospice-care"
        text = render_links("<head></head><main></main>", source, "2026-09-25")
        self.assertIn(f'data-reading-destination="{future}"', text)
        self.assertNotIn(future, render_links(text, source, "2026-09-24"))


if __name__ == "__main__":
    unittest.main()
