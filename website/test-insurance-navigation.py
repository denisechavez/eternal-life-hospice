"""Shared navigation must expose insurance without modifying article content."""
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from fragments import HEADER_HTML
import service_preview

LINK = '<a href="/resources/medicare-hospice-benefit#insurance">Insurance &amp; Coverage</a>'


class InsuranceNavigationTests(unittest.TestCase):
    def test_old_and_new_headers_in_workspace_and_publishing(self):
        for deployment in ("0", "1"):
            for header in (HEADER_HTML, HEADER_HTML.replace(LINK, "")):
                with self.subTest(deployment=deployment, legacy=LINK not in header):
                    source = "<html><head></head><body>" + header + "<main><h1>Article</h1><p>Approved copy.</p></main></body></html>"
                    with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": deployment}):
                        rendered = service_preview.decorate(source, "/resources")
                        again = service_preview.decorate(rendered, "/resources")
                    group = re.search(r'data-section="resources".*?</div></div>', rendered, re.S).group()
                    self.assertEqual(group.count(LINK), 1)
                    self.assertEqual(again, rendered)
                    self.assertIn("<main><h1>Article</h1><p>Approved copy.</p></main>", rendered)

    def test_does_not_add_navigation_to_pages_without_header(self):
        source = "<html><head></head><body><p>Utility page</p></body></html>"
        self.assertEqual(service_preview.decorate(source, "/utility"), source)

    def test_destination_and_anchor_exist(self):
        path = Path(__file__).parent / "elh-preview/resources/medicare-hospice-benefit.html"
        self.assertIn('id="insurance"', path.read_text())


if __name__ == "__main__":
    unittest.main()
