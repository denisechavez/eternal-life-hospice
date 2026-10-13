#!/usr/bin/env python3
"""Read-only checks for reversible recruitment withdrawal and clinical preservation."""
import json
import http.server
from pathlib import Path
import threading
import urllib.error
import urllib.request
import unittest
from unittest.mock import patch

import recruitment_policy as policy

ROOT = Path(__file__).parent / "elh-preview"


class RecruitmentTests(unittest.TestCase):
    def test_route_aliases(self):
        for route in policy.WITHDRAWN_ROUTES:
            for suffix in ("", "/", ".html", ".html?x=1", "/index.html"):
                self.assertTrue(policy.withdrawn(route + suffix), route + suffix)
        self.assertTrue(policy.withdrawn("/%76olunteer"))
        self.assertTrue(policy.withdrawn("/resources/../careers"))
        self.assertFalse(policy.withdrawn("/services"))
        self.assertFalse(policy.withdrawn("https://example.com/volunteer"))

    def test_every_site_html_has_no_retired_links(self):
        checked = 0
        for path in ROOT.rglob("*.html"):
            if policy.withdrawn("/" + str(path.relative_to(ROOT))):
                continue
            source = path.read_text()
            transformed = policy.public_html(source)
            parser = policy._Elements(transformed)
            for node in parser.nodes:
                if node["tag"] == "a":
                    self.assertFalse(policy.withdrawn(node["attrs"].get("href", "")), str(path))
            self.assertEqual(transformed, policy.public_html(transformed), str(path))
            checked += 1
        self.assertGreater(checked, 100)

    def test_home_and_resources_recruitment_sections_removed(self):
        for filename in ("index.html", "resources.html", "referral-card.html"):
            result = policy.public_html((ROOT / filename).read_text())
            self.assertNotIn('id="join"', result)
            self.assertNotIn("Here to join our team or volunteer?", result)
            self.assertNotIn("Give time, give presence", result)
            self.assertNotIn("Learn about volunteering", result)
        original = (ROOT / "index.html").read_text()
        self.assertIn('id="join"', original)  # Retained, not deleted.

    def test_clinical_volunteer_text_and_inline_text_retained(self):
        source = ('<p>Trained volunteers provide companionship.</p>'
                  '<p>Ask about <a href="/resources/volunteer" class="elh-inline-link">'
                  'hospice volunteers</a> in the care plan.</p>')
        self.assertEqual(policy.public_html(source),
                         '<p>Trained volunteers provide companionship.</p>'
                         '<p>Ask about hospice volunteers in the care plan.</p>')

    def test_discovery(self):
        sitemap = policy.public_discovery((ROOT / "sitemap.xml").read_text(), "sitemap")
        for route in policy.WITHDRAWN_ROUTES:
            self.assertNotIn("https://eternallifehospice.com" + route + "</loc>", sitemap)
        search = policy.public_discovery(json.dumps([
            {"url": "/careers"}, {"url": "/volunteer.html"}, {"url": "/services"}
        ]), "search")
        self.assertEqual(json.loads(search), [{"url": "/services"}])
        llms = policy.public_discovery((ROOT / "llms.txt").read_text(), "llms")
        self.assertNotIn("Volunteer with us", llms)
        self.assertIn("Volunteer companionship and respite services", llms)

    def test_one_switch_restores_original_content(self):
        original = (ROOT / "index.html").read_text()
        with patch.object(policy, "RECRUITMENT_PAUSED", False):
            self.assertFalse(policy.withdrawn("/careers"))
            self.assertEqual(original, policy.public_html(original))
            self.assertEqual('[]', policy.public_discovery('[]', "search"))

    def test_http_routes_and_old_application_form(self):
        import devserver
        manifest = json.loads((ROOT.parent / "content" / "30-day-journal-manifest.json").read_text())
        fixtures = {
            item["slug"]: {
                "html": (ROOT / "blog" / (item["slug"] + ".html")).read_text(),
                "date": item["date"], "revision": "test-only",
            }
            for item in manifest["articles"][:4]
        }
        # Isolate this takedown test from approval databases and email delivery.
        class Handler(devserver.PrettyURLHandler):
            def _released_journal(self):
                return fixtures

            def _is_same_origin(self):
                return True

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        try:
            for path in ("/", "/index.html", "/referral-card", "/resources",
                         "/sitemap.xml", "/assets/search-index.json", "/llms.txt"):
                with urllib.request.urlopen(base + path, timeout=30) as response:
                    text = response.read().decode()
                    self.assertEqual(response.status, 200)
                if path.endswith(".xml"):
                    self.assertEqual(text, policy.public_discovery(text, "sitemap"))
                elif path.endswith(".json"):
                    self.assertTrue(all(not policy.withdrawn(entry["url"])
                                        for entry in json.loads(text)))
                else:
                    self.assertEqual(text, policy.public_html(text))
                    self.assertNotIn('id="join"', text)
            for route in policy.WITHDRAWN_ROUTES:
                for method in ("GET", "HEAD"):
                    request = urllib.request.Request(base + route + ".html", method=method)
                    with self.assertRaises(urllib.error.HTTPError) as failure:
                        urllib.request.urlopen(request, timeout=5)
                    self.assertEqual(failure.exception.code, 404)
                    self.assertIn("noindex", failure.exception.headers["X-Robots-Tag"])
            request = urllib.request.Request(
                base + "/api/form-submit", data=b"form-name=elh-careers",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with self.assertRaises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(failure.exception.code, 410)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
