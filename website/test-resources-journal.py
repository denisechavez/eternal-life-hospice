#!/usr/bin/env python3
"""Resources Journal picks follow the same publication boundary as the archive."""
import http.client
import io
import json
import re
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import devserver
from journal_preview import recent_journal_cards

ROOT = Path(devserver.ROOT)
MANIFEST = json.loads(Path(devserver.JOURNAL_MANIFEST).read_text())["articles"]


class ResourcesJournalTests(unittest.TestCase):
    def render(self, today, command="GET"):
        handler = devserver.PrettyURLHandler.__new__(devserver.PrettyURLHandler)
        handler.command = command
        handler.wfile = io.BytesIO()
        statuses, headers = [], {}
        handler.send_response = statuses.append
        handler.send_error = lambda status, *_: statuses.append(status)
        handler.send_header = lambda key, value: headers.update({key: value})
        handler.end_headers = lambda: None
        with patch.dict("os.environ", {"ELH_JOURNAL_DATE": today}):
            self.assertTrue(handler._send_journal_artifact(str(ROOT / "resources.html")))
        return statuses, headers, handler.wfile.getvalue().decode()

    def test_latest_three_before_during_and_after_campaign(self):
        cases = {
            "2026-09-20": ["the-caregiver-who-needs-care",
                           "sound-baths-ancient-comfort-for-body-and-spirit",
                           "the-quiet-work-of-hospice-volunteers"],
            "2026-09-21": ["what-happens-during-a-hospice-evaluation",
                           "the-caregiver-who-needs-care",
                           "sound-baths-ancient-comfort-for-body-and-spirit"],
            "2026-10-02": ["the-first-48-hours-of-hospice-care",
                           "hospice-support-for-advanced-copd",
                           "hospice-and-advanced-heart-failure"],
            "2026-10-21": ["preparing-for-a-hospice-care-plan-conversation",
                           "how-physicians-and-facilities-refer-a-patient-to-hospice",
                           "grief-support-before-and-after-a-loss"],
            "2027-01-01": ["preparing-for-a-hospice-care-plan-conversation",
                           "how-physicians-and-facilities-refer-a-patient-to-hospice",
                           "grief-support-before-and-after-a-loss"],
        }
        source = (ROOT / "resources.html").read_text()
        before, rest = source.split("<!-- JOURNAL_PICKS_START -->")
        _, after = rest.split("<!-- JOURNAL_PICKS_END -->")
        for today, expected in cases.items():
            with self.subTest(today=today):
                statuses, headers, page = self.render(today)
                self.assertEqual(statuses, [200])
                self.assertEqual(headers["Cache-Control"], "public, max-age=0, must-revalidate")
                self.assertTrue(page.startswith(before))
                self.assertTrue(page.endswith(after))
                self.assertEqual(
                    re.findall(r'class="rc"[^>]*href="blog/([^"]+)"', page), expected
                )
                self.assertNotIn("data-featured", page)
                self.assertNotIn("can-a-family-request-a-hospice-evaluation", page)
                self.assertEqual(page.count('href="/care-brief"'), source.count('href="/care-brief"'))
                self.assertTrue(all(d <= today for d in
                                    re.findall(r'<time datetime="([^"]+)"', page)))
                for item in MANIFEST:
                    if item["date"] > today:
                        self.assertNotIn(item["slug"], page)

    def test_manifest_date_overrides_archive_date_and_display(self):
        archive = (ROOT / "blog.html").read_text()
        changed = [dict(a) for a in MANIFEST]
        changed[0]["date"] = "2027-02-03"
        cards = recent_journal_cards(archive, changed, "2026-09-21")
        self.assertNotIn(changed[0]["slug"], cards)
        cards = recent_journal_cards(archive, changed, "2027-02-03")
        self.assertIn(changed[0]["slug"], cards)
        self.assertIn('<time datetime="2027-02-03">February 3, 2027</time>', cards)

    def test_next_story_is_selected_without_resources_edit(self):
        archive = (ROOT / "blog.html").read_text()
        new = (
            '<a class="rc" data-publish-date="2027-01-02" href="blog/new-story">'
            '<div class="rc-img"></div><div class="rc-body"><h3 class="rc-title">'
            'New story</h3><p class="rc-ex">New summary</p>'
            '<div class="rc-meta">January 2, 2027</div></div></a>'
        )
        archive += new
        manifest = MANIFEST + [{"slug": "new-story", "date": "2027-01-02"}]
        self.assertNotIn("new-story", recent_journal_cards(archive, manifest, "2027-01-01"))
        picks = recent_journal_cards(archive, manifest, "2027-01-02")
        self.assertEqual(re.findall(r'href="blog/([^"]+)"', picks)[0], "new-story")
        self.assertEqual(picks.count('href="blog/new-story"'), 1)

    def test_unavailable_schedule_archive_or_slot_fails_closed(self):
        self.assertEqual(self.render("invalid")[0], [503])
        with patch.object(devserver.PrettyURLHandler, "_journal_manifest", return_value=None):
            self.assertEqual(self.render("2026-10-02")[0], [503])
        with patch.object(devserver, "ROOT", "/missing-journal-root"):
            self.assertEqual(self.render("2026-10-02")[0], [503])
        with patch("devserver.render_resources_journal", side_effect=ValueError("Missing slot")):
            self.assertEqual(self.render("2026-10-02")[0], [503])

    def test_routes_queries_and_head_use_filtered_response(self):
        with patch.dict("os.environ", {"ELH_JOURNAL_DATE": "2026-10-02"}):
            server = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for route in ("/resources", "/resources/", "/resources.html",
                              "/resources?source=journal"):
                    with self.subTest(route=route):
                        connection = http.client.HTTPConnection(*server.server_address)
                        connection.request("GET", route)
                        response = connection.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, 200)
                        self.assertIn(b'blog/the-first-48-hours-of-hospice-care', body)
                        self.assertNotIn(b'blog/hospice-care-in-simi-valley', body)
                        self.assertEqual(response.getheader("Cache-Control"),
                                         "public, max-age=0, must-revalidate")
                        connection.request("HEAD", route)
                        head = connection.getresponse()
                        self.assertEqual(head.status, 200)
                        self.assertEqual(int(head.getheader("Content-Length")), len(body))
                        self.assertEqual(head.read(), b"")
                        connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()