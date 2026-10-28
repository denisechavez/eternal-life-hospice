#!/usr/bin/env python3
"""Website phone changes must not alter office contacts or acknowledgment mail."""
import io
import json
import unittest

import acknowledgments
import website_phone
from devserver import PrettyURLHandler
from fragments import FOOTER_HTML


class WebsitePhoneTests(unittest.TestCase):
    def test_phone_formats_and_click_to_call_stay_consistent(self):
        for old, new in (
            ("805.953.7273", "805.409.9262"),
            ("tel:18059537273", "tel:18054099262"),
            ("tel:+18059537273", "tel:+18054099262"),
            ("+1-805-953-7273", "+1-805-409-9262"),
            ("(805) 953-7273", "(805) 409-9262"),
        ):
            self.assertEqual(website_phone.public_text(old), new)
        original = '<a href="tel:18059537273">Call 805.953.7273</a>'
        updated = website_phone.public_html(original)
        self.assertEqual(updated, '<a href="tel:18054099262">Call 805.409.9262</a>')
        self.assertEqual(website_phone.public_html(updated), updated)

    def test_footer_office_links_and_employee_cards_are_preserved(self):
        office = '<a href="tel:18059537273"><span>Call Office &nbsp; 805.953.7273</span></a>'
        paragraph = '<p>Please contact our office at 805.953.7273.</p>'
        self.assertEqual(website_phone.public_html(FOOTER_HTML), FOOTER_HTML)
        self.assertEqual(website_phone.public_html(office + paragraph), office + paragraph)
        for route in website_phone.EMPLOYEE_CARD_ROUTES:
            card = '<script>{"telephone":"+18059537273"}</script>' + office
            self.assertEqual(website_phone.public_html(card, route), card)

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

    def test_public_api_projection_preserves_explicit_office_and_referral_fields(self):
        original = {"phone":"805.953.7273", "officePhone":"805.953.7273",
                    "referral_phone":"805.953.7273", "ok":False,
                    "nested":[{"message":"Please call 805.953.7273."}]}
        result = website_phone.public_payload(original)
        self.assertEqual(result["phone"], "805.409.9262")
        self.assertEqual(result["officePhone"], original["officePhone"])
        self.assertEqual(result["referral_phone"], original["referral_phone"])
        self.assertEqual(result["nested"][0]["message"], "Please call 805.409.9262.")
        self.assertEqual(original["phone"], "805.953.7273")

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
    unittest.main()
