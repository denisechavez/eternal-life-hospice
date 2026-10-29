#!/usr/bin/env python3
"""Every public page must receive the current header script, not a cached copy."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analytics_assets


class HeaderAssetTests(unittest.TestCase):
    def test_header_urls_refresh_on_all_page_depths(self):
        for old in (
            "/assets/header.js?v=old", "../assets/header.js?v=old",
            "../../assets/header.js", "assets/header.js",
        ):
            source = f'<script src="{old}" defer></script>'
            output = analytics_assets.refresh_html(source)
            self.assertEqual(
                output, f'<script src="{analytics_assets.header_url()}" defer></script>')
            self.assertEqual(analytics_assets.refresh_html(output), output)

    def test_script_changes_get_a_new_url(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "header.js"
            with patch.object(analytics_assets, "HEADER_FILE", script):
                script.write_bytes(b"first version")
                before = analytics_assets.header_url()
                script.write_bytes(b"second version")
                after = analytics_assets.header_url()
                self.assertNotEqual(before, after)
                self.assertIn(hashlib.sha256(b"second version").hexdigest()[:12], after)

    def test_other_markup_and_scripts_are_unchanged(self):
        source = '<h1>Page title</h1><script src="/assets/share.js" defer></script>'
        self.assertEqual(analytics_assets.refresh_html(source), source)


if __name__ == "__main__":
    unittest.main()
