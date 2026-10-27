import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import journal_workspace_preview as preview


class WorkspacePreviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        cache = patch.object(preview, "CACHE", Path(self.directory.name) / "published.json")
        cache.start()
        self.addCleanup(cache.stop)
        env = patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"})
        env.start()
        self.addCleanup(env.stop)
        self.row = {"slug": "published-article", "revision": "a" * 64,
                    "date": "2026-10-27", "available": True}
        self.html = '<h1>Public copy</h1><img src="/api/journal-photo/' + "b" * 64 + '">'

    def fetch(self, origin, path):
        if path == "/api/journal-release-status":
            return json.dumps({"expected": [self.row, {
                **self.row, "slug": "not-yet-public", "available": False}]}), None
        self.assertEqual(path, "/blog/published-article.html")
        return self.html, self.row["revision"]

    def test_only_verified_available_articles_are_cached_and_shown(self):
        with patch.object(preview, "fetch", side_effect=self.fetch):
            self.assertEqual(preview.synchronize("https://published.example"), 1)
        original = {"older": {"html": "Existing released article"}}
        result = preview.overlay(original)
        self.assertNotIn("published-article", original)
        self.assertNotIn("not-yet-public", result)
        self.assertEqual(result["published-article"]["date"], "2026-10-27")
        self.assertIn('src="https://published.example/api/journal-photo/', result["published-article"]["html"])
        import devserver
        with patch.object(devserver.journal_release, "released", return_value=({}, True)):
            self.assertFalse(devserver.PrettyURLHandler._future_journal_path("/blog/published-article"))
            self.assertFalse(devserver.PrettyURLHandler._future_journal_path("/blog/published-article.html"))
            self.assertTrue(devserver.PrettyURLHandler._future_journal_path("/blog/not-yet-public"))

    def test_production_ignores_cache_and_cannot_refresh(self):
        preview.CACHE.write_text("Invalid cache must never be read in production")
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            self.assertEqual(preview.overlay({}), {})
            with self.assertRaises(RuntimeError):
                preview.synchronize("https://published.example")

    def test_mismatched_public_version_keeps_existing_cache(self):
        preview.CACHE.write_text("existing")
        def fetch(origin, path):
            if path.startswith("/api/"):
                return json.dumps({"expected": [self.row]}), None
            return self.html, "c" * 64
        with patch.object(preview, "fetch", side_effect=fetch):
            with self.assertRaises(ValueError):
                preview.synchronize("https://published.example")
        self.assertEqual(preview.CACHE.read_text(), "existing")

    def test_missing_cache_leaves_existing_records_unchanged(self):
        original = {"older": {"html": "Existing released article"}}
        self.assertIs(preview.overlay(original), original)

    def test_modified_cached_display_is_not_silently_accepted(self):
        document = "<h1>Published</h1>"
        preview.CACHE.write_text(json.dumps({
            "kind": "published-journal-display-only",
            "articles": {"article": {"html": document, "revision": "a" * 64,
                "date": "2026-10-27", "displayDigest": hashlib.sha256(b"changed").hexdigest()}}
        }))
        with self.assertRaises(ValueError):
            preview.overlay({})


if __name__ == "__main__":
    unittest.main()
