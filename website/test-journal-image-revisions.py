#!/usr/bin/env python3
"""Read-only checks for the four replacement Journal photographs."""
import hashlib
import json
import re
import unittest
from pathlib import Path

import journal_release
from journal_image_revisions import apply_image_revision, image_revisions

PUBLIC = Path(__file__).resolve().parent / "elh-preview"


class JournalPhotoReviewTests(unittest.TestCase):
    def test_replacements_preserve_everything_except_photos_and_dimensions(self):
        drafts = json.loads((PUBLIC.parent / "content/seo-journal-review.json").read_text())["articles"]
        photos = image_revisions()
        self.assertEqual({p["date"] for p in photos.values()}, {
            "2026-10-14", "2026-10-16", "2026-10-19", "2026-10-21",
        })
        records = journal_release.candidates()
        for slug, photo in photos.items():
            with self.subTest(slug=slug):
                original = (PUBLIC / "blog" / (slug + ".html")).read_text()
                before = drafts.get(slug, {}).get("reviewHtml") or original
                after = apply_image_revision(slug, before)
                strip_dimensions = lambda text: re.sub(
                    r'<meta\s+property="og:image:(?:width|height)"[^>]*>', "", text)
                self.assertEqual(
                    strip_dimensions(before),
                    strip_dimensions(after.replace(photo["heroImage"], photo["originalImage"])),
                )
                self.assertEqual(records[slug]["html"], after)
                self.assertEqual(records[slug]["date"], photo["date"])
                self.assertNotEqual(journal_release.revision(before), records[slug]["revision"])
                self.assertEqual(records[slug]["revision"], journal_release.revision(after))
                self.assertEqual(
                    hashlib.sha256((PUBLIC / photo["heroImage"].lstrip("/")).read_bytes()).hexdigest(),
                    photo["sha256"],
                )
                self.assertEqual(apply_image_revision(slug, after), after)
                self.assertIn(photo["originalImage"], original)
                self.assertNotIn(photo["heroImage"], original)

    def test_unrelated_articles_are_untouched(self):
        text = '<section>Original article</section>'
        self.assertEqual(apply_image_revision("unrelated-article", text), text)

    def test_stale_source_does_not_silently_override_a_different_image(self):
        slug = next(iter(image_revisions()))
        with self.assertRaises(ValueError):
            apply_image_revision(slug, '<section>No matching photograph</section>')


if __name__ == "__main__":
    unittest.main()
