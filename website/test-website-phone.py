#!/usr/bin/env python3
"""Website phone changes must not alter office contacts or acknowledgment mail."""
import io
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import acknowledgments
import chat_api
import coverage_api
import form_intake
import website_phone
from devserver import PrettyURLHandler
from fragments import FOOTER_HTML


class WebsitePhoneTests(unittest.TestCase):
    def assert_public_call_links(self, document):
        links = re.findall(r'<a\b[^>]*href=["\']tel:([^"\']+)["\'][^>]*>(.*?)</a>',
                           document, re.S | re.I)
        self.assertTrue(links, "No public click-to-call links checked")
        for target, label in links:
            digits = re.sub(r"\D", "", target)
            if len(digits) == 10:
                digits = "1" + digits
            if digits == "18006334227":  # Medicare, not an Eternal contact.
                continue
            visible = re.sub(r"<[^>]+>", "", label).strip()
            self.assertEqual(digits, "18054099262", f"Wrong public call target: {target}")
            if re.search(r"\d{3}[. -]\d{3}[. -]\d{4}", visible):
                self.assertIn("805.409.9262", visible, f"Wrong call label: {visible}")

    def setUp(self):
        # No HTTP requests, form submissions, email deliveries or AI calls.
        for target in ("socket.socket.connect", "socket.socket.connect_ex",
                       "socket.create_connection", "urllib.request.urlopen"):
            blocker = patch(target, side_effect=AssertionError("External transport forbidden"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def boundary(self, route, body, status=200):
        handler = object.__new__(PrettyURLHandler)
        handler.path = route
        handler.command = "POST"
        handler.wfile = io.BytesIO()
        headers = {}
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda key, value: headers.update({key: value})
        handler.end_headers = lambda: None
        handler._send_json(status, body)
        raw = handler.wfile.getvalue()
        self.assertEqual(statuses, [status])
        self.assertEqual(int(headers["Content-Length"]), len(raw))
        return json.loads(raw)

    def test_final_header_decoration_cannot_reintroduce_old_phone_pills(self):
        handler = object.__new__(PrettyURLHandler)
        handler.path = "/"
        source = (Path(__file__).parent / "elh-preview" / "index.html").read_text()
        rendered = handler._preview_chrome(source)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(rendered))
        self.assertIn("805.409.9262", rendered)

    def test_phone_formats_and_click_to_call_stay_consistent(self):
        for old, new in (
            ("805.953.7273", "805.409.9262"),
            ("tel:18059537273", "tel:18054099262"),
            ("tel:+18059537273", "tel:+18054099262"),
            ("+1-805-953-7273", "+1-805-409-9262"),
            ("(805) 953-7273", "(805) 409-9262"),
            ("805.410.1151", "805.409.9262"),
            ("tel:18054101151", "tel:18054099262"),
            ("+1-805-410-1151", "+1-805-409-9262"),
        ):
            self.assertEqual(website_phone.public_text(old), new)
        original = '<a href="tel:18059537273">Call 805.953.7273</a>'
        updated = website_phone.public_html(original)
        self.assertEqual(updated, '<a href="tel:18054099262">Call 805.409.9262</a>')
        self.assertEqual(website_phone.public_html(updated), updated)

    def test_public_calls_change_but_explicit_office_contacts_are_retained(self):
        office = '<a href="tel:18059537273"><span>Call Office &nbsp; 805.953.7273</span></a>'
        paragraph = '<p>Please contact our office at 805.953.7273.</p>'
        footer = website_phone.public_html(FOOTER_HTML)
        self.assertIn('href="tel:18054099262"', footer)
        self.assertIn("805.409.9262", footer)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(footer))
        self.assertEqual(website_phone.public_html(footer), footer)
        self.assertEqual(website_phone.public_html(office + paragraph),
                         office + paragraph)
        for route in ("/card-aleksandra-dubina", "/card-denise-chavez"):
            card = '<script>{"telephone":"+18059537273"}</script>' + office
            rendered = website_phone.public_html(card, route)
            self.assertIn('"telephone":"+18054099262"', rendered)
            self.assertIn(office, rendered)
        mixed = '<a href="tel:18059537273">Call 805.953.7273</a>' + office
        self.assertEqual(website_phone.public_html(mixed),
                         '<a href="tel:18054099262">Call 805.409.9262</a>' + office)

    def test_office_paragraph_cannot_exempt_surrounding_public_links(self):
        public = '<a href="tel:18059537273">Call 805.953.7273</a>'
        office = '<p>Our office phone is 805.953.7273.</p>'
        main = '<a href="tel:18054099262">Call 805.409.9262</a>'
        for document, expected in (
            (public + office + public, main + office + main),
            ('<p>' + public + '</p>' + office + public,
             '<p>' + main + '</p>' + office + main),
            ('<p>Contact our office. ' + public + '</p>' + public,
             '<p>Contact our office. ' + main + '</p>' + main),
            (public + '<a href="tel:18059537273">Office 805.953.7273</a>' + public,
             main + '<a href="tel:18059537273">Office 805.953.7273</a>' + main),
        ):
            with self.subTest(document=document):
                self.assertEqual(website_phone.public_html(document), expected)

    def test_fax_external_numbers_and_other_contact_numbers_are_not_rewritten(self):
        unrelated = "Fax 805.953.8530; Medicare 1-800-633-4227; visitor 202.555.0190"
        self.assertEqual(website_phone.public_text(unrelated), unrelated)

    def test_email_copy_stays_approved_while_web_confirmation_uses_main_number(self):
        approved = acknowledgments.CTA_HTML
        self.assertIn("Call 805.953.7273", approved)
        response = website_phone.public_payload({"care_cta_html": approved, "accepted":True})
        self.assertIn("Call 805.409.9262", response["care_cta_html"])
        self.assertIn("tel:18054099262", response["care_cta_html"])
        self.assertTrue(response["accepted"])
        self.assertEqual(acknowledgments.CTA_HTML, approved)
        for key in acknowledgments.TEMPLATES:
            _, text, html = acknowledgments.render(key, "Synthetic", "SYNTHETIC", "info@eternallifehospice.com")
            self.assertNotIn("805.409.9262", text + html)
            if key in acknowledgments.CARE_TEMPLATES:
                self.assertIn("805.953.7273", text + html)
                self.assertIn('href="tel:18059537273"', html)

    def test_public_api_projection_preserves_explicit_office_fields(self):
        original = {"phone":"805.953.7273", "officePhone":"805.953.7273",
                    "referral_phone":"805.953.7273", "ok":False,
                    "nested":[{"message":"Please call 805.953.7273."}]}
        result = website_phone.public_payload(original)
        self.assertEqual(result["phone"], "805.409.9262")
        self.assertEqual(result["officePhone"], "805.953.7273")
        self.assertEqual(result["referral_phone"], "805.409.9262")
        self.assertEqual(result["nested"][0]["message"], "Please call 805.409.9262.")
        self.assertEqual(original["phone"], "805.953.7273")
        self.assertEqual(website_phone.public_payload(
            {"nested": [{"office_phone": "805.953.7273", "office": "805.953.7273"}]}),
            {"nested": [{"office_phone": "805.953.7273", "office": "805.953.7273"}]})

    def test_form_confirmation_and_error_links_at_public_boundary(self):
        for status, ok in ((200, True), (400, False), (429, False), (503, False)):
            with self.subTest(status=status):
                source = form_intake.json_response_payload(
                    ok, accepted=ok, error=None if ok else "synthetic",
                    message="Please call 805.953.7273.",
                    care_cta_html=acknowledgments.CTA_HTML)
                result = self.boundary("/api/form-submit?synthetic=1", source, status)
                self.assertEqual(result["phone"], "805.409.9262")
                self.assertEqual(result["ok"], ok)
                self.assertEqual(result["accepted"], ok)
                self.assertIn("805.409.9262", result["message"])
                self.assertIn('href="tel:18054099262"', result["care_cta_html"])
                self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(json.dumps(result)))
                self.assertIn(b"805.953.7273", source)

    def test_chat_defaults_and_guarded_public_response(self):
        source = (Path(__file__).parent / "elh-preview/assets/chat.js").read_text()
        for name, value in (("PHONE_DISPLAY", "805.409.9262"),
                            ("PHONE_TEL", "18054099262")):
            self.assertRegex(source, rf'var {name}\s*=\s*"{re.escape(value)}"')
        self.assertIn('phone.href = "tel:" + PHONE_TEL', source)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(source))
        body = json.dumps({"messages": [{"role": "user", "content": "call 911"}]}).encode()
        status, payload = chat_api.process_chat(body, environ={})
        result = self.boundary("/api/chat", payload, status)
        self.assertTrue(result["guarded"])
        self.assertIn("911", result["reply"])
        self.assertIn("805.409.9262", result["reply"])
        fallback = self.boundary("/api/chat", {"reply": chat_api.FALLBACK}, 503)
        self.assertIn("805.409.9262", fallback["reply"])

    def test_public_coverage_responses_keep_main_phone(self):
        for params in ({"city": ["Pasadena"]}, {"city": ["San Francisco"]},
                       {"city": ["West"]}, {"list": ["true"]}, {}):
            with self.subTest(params=params):
                status, payload, _ = coverage_api.lookup_coverage(params)
                original = json.dumps(payload)
                result = self.boundary("/api/coverage?synthetic=1", payload, status)
                self.assertEqual(json.dumps(payload), original)
                self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(json.dumps(result)))
                if "phone" in payload:
                    self.assertEqual(result["phone"], "805.409.9262")
                self.assertEqual(result, website_phone.public_payload(payload))

    def test_website_metadata_and_public_html_without_editing_signed_sources(self):
        root = Path(__file__).parent / "elh-preview"
        handler = object.__new__(PrettyURLHandler)
        for name, route in (("index.html", "/"), ("refer.html", "/refer"),
                            ("resources.html", "/resources")):
            with self.subTest(page=name):
                handler.path = route
                source = (root / name).read_text()
                rendered = handler._preview_chrome(source)
                self.assert_public_call_links(rendered)
                self.assertRegex(rendered, r'href=["\']tel:\+?18054099262["\']')
                if name == "index.html":
                    phones = re.findall(r'"telephone"\s*:\s*"([^"]+)"', rendered)
                    self.assertTrue(phones)
                    self.assertEqual([re.sub(r"\D", "", phone) for phone in phones],
                                     ["18054099262"] * len(phones))
                self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(rendered))
        metadata = (root / ".well-known/openapi.json").read_text()
        json.loads(metadata)
        self.assertIn("805.409.9262", metadata)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(metadata))
        discovery = website_phone.public_text((root / "llms.txt").read_text())
        self.assertIn("805.409.9262", discovery)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(discovery))
        # A synthetic signed-document boundary: never load or rewrite Journal files.
        signed = '<article>Approved article</article><a href="tel:18059537273">805.953.7273</a>'
        self.assertIn('href="tel:18054099262"',
                      handler._preview_chrome(signed, "/blog/synthetic"))
        self.assertIn('href="tel:18059537273"', signed)

    def test_call_guard_rejects_wrong_targets_and_labels(self):
        for link in ('<a href="tel:18054099263">805.409.9262</a>',
                     '<a href="tel:18054099262">805.409.9263</a>'):
            with self.subTest(link=link), self.assertRaises(AssertionError):
                self.assert_public_call_links(link)

    def test_shared_form_error_links_use_main_phone(self):
        source = (Path(__file__).parent / "elh-preview/assets/intake-security.js").read_text()
        self.assertIn("805.409.9262", source)
        self.assertIn("tel:18054099262", source)
        self.assertFalse(website_phone.OLD_PUBLIC_PHONE.search(source))

    def test_http_boundary_changes_only_public_api_responses(self):
        original = {"phone":"805.953.7273", "care_cta_html":acknowledgments.CTA_HTML}
        for route in (*website_phone.PUBLIC_API_ROUTES, "/api/studio/email-review"):
            for serialized in (False, True):
                with self.subTest(route=route, serialized=serialized):
                    handler = object.__new__(PrettyURLHandler)
                    handler.path = route + "?synthetic=1"
                    handler.command = "GET"
                    handler.wfile = io.BytesIO()
                    handler.send_response = lambda *args: None
                    handler.send_header = lambda *args: None
                    handler.end_headers = lambda: None
                    body = json.dumps(original).encode() if serialized else original
                    handler._send_json(200, body)
                    actual = json.loads(handler.wfile.getvalue())
                    expected = website_phone.public_payload(original) if route in website_phone.PUBLIC_API_ROUTES else original
                    self.assertEqual(actual, expected)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    passed = result.wasSuccessful() and not result.skipped and result.testsRun > 0
    if passed:
        print("SENTINEL: test-website-phone.py OK")
    raise SystemExit(0 if passed else 1)
