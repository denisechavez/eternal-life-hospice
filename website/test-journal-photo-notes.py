#!/usr/bin/env python3
"""Photo presentation must honor licenses and preserve approval snapshots."""
import json
from pathlib import Path
import re
import unittest

from journal_photo_notes import public_html

PREFIX = '<p class="journal-photo-credit"><small>Illustrative photograph: Photographer / '
DISCLAIMER = (
    "Resized for display. The photograph does not depict an Eternal patient or service encounter."
)


def note(license_url):
    return (PREFIX + '<a href="https://example.org/photo">Source</a> &middot; '
            f'<a href="{license_url}">License</a>. {DISCLAIMER}</small></p>\n')


class PhotoNoteTests(unittest.TestCase):
    def test_pexels_and_public_domain_notes_are_removed(self):
        for url in (
            "https://www.pexels.com/license/",
            "https://creativecommons.org/publicdomain/mark/1.0/",
            "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
        ):
            self.assertEqual(public_html("<h1>Title</h1>" + note(url) + "<p>Body.</p>"),
                             "<h1>Title</h1><p>Body.</p>")

    def test_required_and_unknown_credits_remain(self):
        for url in (
            "https://creativecommons.org/licenses/by-sa/4.0",
            "https://creativecommons.org/licenses/by/2.0/",
            "https://example.org/custom-license",
        ):
            output = public_html(note(url))
            self.assertIn("Photo: Photographer", output)
            self.assertIn('href="https://example.org/photo"', output)
            self.assertIn(url, output)
            self.assertIn("Resized for display.", output)
            self.assertNotIn("Illustrative photograph", output)
            self.assertNotIn("does not depict", output)
            self.assertEqual(public_html(output), output)

    def test_unrelated_copy_is_not_removed(self):
        content = "<p>Illustrative photograph: explain this term.</p>"
        self.assertEqual(public_html(content), content)

    def test_frozen_preview_snapshots_are_cleaned_without_being_rewritten(self):
        path = Path(__file__).resolve().parents[1] / ".local/journal-preview/published.json"
        if not path.exists():
            self.skipTest("Workspace snapshot cache is not present")
        original = path.read_bytes()
        records = json.loads(original)["articles"]
        pattern = re.compile(r'<p class="journal-photo-credit">.*?</p>\n?', re.S)
        for slug, row in records.items():
            source = row["html"]
            rendered = public_html(source)
            self.assertNotIn("Illustrative photograph:", rendered, slug)
            self.assertNotIn("does not depict an Eternal patient", rendered, slug)
            self.assertEqual(pattern.sub("", rendered), pattern.sub("", source), slug)
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
