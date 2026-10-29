#!/usr/bin/env python3
"""Public naming changes must not alter article paths or approval snapshots."""
import json
from pathlib import Path
import unittest

from journal_branding import DISPLAY_NAME, public_html


class JournalBrandingTests(unittest.TestCase):
    def test_labels_and_metadata_use_the_approved_name(self):
        source = (
            '<title>Family guidance | The Eternal Journal</title>'
            '<meta property="og:title" content="The Eternal Journal">'
            '<a href="/blog">Journal</a><a href="../blog">Eternal Journal</a>'
            '<div class="kicker">Journal &middot; Family support</div>'
            '<script type="application/ld+json">'
            '{"@type":"Blog","name":"The Eternal Journal","url":"/blog"}'
            '</script>'
        )
        output = public_html(source)
        self.assertEqual(output.count(DISPLAY_NAME), 6)
        self.assertIn('"url":"/blog"', output)
        self.assertIn('href="../blog"', output)
        schema = output.split('application/ld+json">')[1].split("</script>")[0]
        self.assertEqual(json.loads(schema)["name"], DISPLAY_NAME)
        self.assertEqual(public_html(output), output)

    def test_article_content_and_other_publications_are_unchanged(self):
        source = (
            '<a href="/blog/family-support">Article title</a>'
            '<h1>Understanding hospice care</h1><p>Your care team can help.</p>'
            '<a href="/care-brief">The Eternal Care Brief</a>'
        )
        self.assertEqual(public_html(source), source)

    def test_existing_pages_get_the_name_without_source_rewrites(self):
        public = Path(__file__).with_name("elh-preview")
        for filename in ("index.html", "resources.html", "blog.html"):
            path = public / filename
            before = path.read_bytes()
            rendered = public_html(before.decode())
            self.assertIn(f'href="/blog">{DISPLAY_NAME}</a>', rendered)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
