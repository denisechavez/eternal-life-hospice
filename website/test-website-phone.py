#!/usr/bin/env python3
"""Website phone changes must not alter office contacts or acknowledgment mail."""
import gzip
import io
import json
import re
import tempfile
import unittest
from email.message import Message
from email.parser import BytesParser
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import acknowledgments
import chat_api
import coverage_api
import form_intake
import website_phone
from devserver import PrettyURLHandler
from fragments import FOOTER_HTML


class NetworkFreePhoneTests(unittest.TestCase):
    def setUp(self):
        # No HTTP requests, form submissions, email deliveries or AI calls.
        for target in ("socket.socket.connect", "socket.socket.connect_ex",
                       "socket.create_connection", "urllib.request.urlopen"):
            blocker = patch(target, side_effect=AssertionError("External transport forbidden"))
            blocker.start()
            self.addCleanup(blocker.stop)


class WebsitePhoneTests(NetworkFreePhoneTests):
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


class StaticWebsitePhoneTests(NetworkFreePhoneTests):
    """Exercise real send_head branches without a socket or approved documents."""

    OFFICE = '<a href="tel:18059537273">Office 805.953.7273</a>'
    OFFICE_PARAGRAPH = '<p>Our office phone is 805.953.7273.</p>'
    OLD_CALL = '<a href="tel:18059537273">Call 805.953.7273</a>'
    MAIN_CALL = '<a href="tel:18054099262">Call 805.409.9262</a>'
    RELATED_CALL = '<a href="tel:18054101151">Referral 805.410.1151</a>'
    MAIN_RELATED_CALL = '<a href="tel:18054099262">Referral 805.409.9262</a>'

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="unsigned-phone-responses-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.approved_cta = acknowledgments.CTA_HTML
        self.approved_templates = dict(acknowledgments.TEMPLATES)
        self.source = (
            '<!doctype html><html><head><meta charset="utf-8">'
            '<script type="application/ld+json">'
            '{"@type":"Organization","telephone":"+18059537273"}'
            '</script></head><body><main><h1>Synthetic café — care</h1>'
            + self.OLD_CALL + self.OFFICE + self.OFFICE_PARAGRAPH
            + '<p>Fax 805.953.8530; Medicare 1-800-633-4227.</p>'
            + '<p>Unsigned test content.</p>' * 40
            + '</main></body></html>'
        ).encode("utf-8")
        for name in ("synthetic.html", "index.html"):
            (self.root / name).write_bytes(self.source)

        def replace(target, **kwargs):
            mocked = patch(target, **kwargs)
            result = mocked.start()
            self.addCleanup(mocked.stop)
            return result

        replace("devserver.ROOT", new=str(self.root))
        # Inventory normally scans approved source pages. Supply unsigned entries
        # instead; never allow a release snapshot or a provider to be consulted.
        self.inventory = replace("internal_links.inventory", return_value={})
        self.render_links = replace(
            "internal_links.render_links",
            side_effect=lambda text, *args, **kwargs: text.replace(
                "</main>", self.RELATED_CALL + "</main>"))
        replace("devserver.PrettyURLHandler._journal_today", return_value="2026-01-01")
        replace("devserver.PrettyURLHandler._journal_pages", return_value={})
        replace("devserver.PrettyURLHandler._hide_unreleased_links",
                side_effect=lambda text, route: text)
        for target in ("devserver.PrettyURLHandler._released_journal",
                       "devserver.journal_release.released",
                       "devserver.process_submission", "devserver.process_chat",
                       "devserver.get_reviews", "devserver.notify_delivery_failure"):
            replace(target, side_effect=AssertionError("Journal/provider access forbidden"))

    def tearDown(self):
        self.assertEqual(acknowledgments.CTA_HTML, self.approved_cta)
        self.assertEqual(acknowledgments.TEMPLATES, self.approved_templates)
        super().tearDown()

    def static_response(self, route, method="GET", accept_gzip=False):
        """Use stdlib body handling, real headers and our real send_head.

        Deliberately bypass GET/HEAD routing for APIs and Journal publication:
        this test owns only static response serving, with an isolated directory.
        """
        handler = object.__new__(PrettyURLHandler)
        handler.path = route
        handler.directory = str(self.root)
        handler.command = method
        handler.request_version = "HTTP/1.1"
        handler.requestline = f"{method} {route} HTTP/1.1"
        handler.headers = Message()
        if accept_gzip:
            handler.headers["Accept-Encoding"] = "gzip"
        handler.wfile = io.BytesIO()
        handler.log_message = lambda *args: None
        with patch.object(handler, "send_head", wraps=handler.send_head) as send_head:
            if method == "HEAD":
                SimpleHTTPRequestHandler.do_HEAD(handler)
            else:
                SimpleHTTPRequestHandler.do_GET(handler)
            send_head.assert_called_once_with()
        raw_headers, body = handler.wfile.getvalue().split(b"\r\n\r\n", 1)
        status, raw_headers = raw_headers.split(b"\r\n", 1)
        self.assertRegex(status, rb"^HTTP/\d\.\d 200 ")
        headers = BytesParser().parsebytes(raw_headers + b"\r\n\r\n")
        self.assertEqual(len(headers.get_all("Content-Length", [])), 1)
        if method == "HEAD":
            self.assertEqual(body, b"", "HEAD must never write response bytes")
        else:
            self.assertEqual(int(headers["Content-Length"]), len(body))
        return headers, body

    def response_matrix(self, route, expected_gzip, media_type, expected_headers=None):
        """Check decoded GET parity and HEAD lengths for both encodings."""
        decoded = []
        for accept_gzip in (False, True):
            with self.subTest(route=route, gzip=accept_gzip):
                headers, body = self.static_response(route, accept_gzip=accept_gzip)
                head, _ = self.static_response(route, "HEAD", accept_gzip)
                compressed = accept_gzip and expected_gzip
                self.assertEqual(headers.get("Content-Encoding"),
                                 "gzip" if compressed else None)
                self.assertEqual(headers.get_content_type(), media_type)
                for name in ("Content-Length", "Content-Type", "Content-Encoding",
                             "Vary", "Cache-Control", "Last-Modified"):
                    self.assertEqual(head.get(name), headers.get(name), name)
                for name, value in (expected_headers or {}).items():
                    self.assertEqual(headers.get(name), value)
                    self.assertEqual(head.get(name), value)
                if compressed:
                    self.assertIn("Accept-Encoding", headers.get("Vary", ""))
                decoded.append(gzip.decompress(body) if compressed else body)
        self.assertEqual(decoded[0], decoded[1], "Encoding must not change public content")
        return decoded[0]

    def test_html_with_and_without_contextual_inventory(self):
        for contextual in (False, True):
            self.inventory.return_value = (
                {"/synthetic": None, "/": None} if contextual else {})
            for route in ("/synthetic?unsigned=1", "/synthetic.html", "/"):
                with self.subTest(contextual=contextual, route=route):
                    self.render_links.reset_mock()
                    document = self.response_matrix(
                        route, expected_gzip=contextual, media_type="text/html").decode("utf-8")
                    self.assertIn(self.MAIN_CALL, document)
                    self.assertNotIn(self.OLD_CALL, document)
                    self.assertIn('"telephone":"+18054099262"', document)
                    self.assertIn(self.OFFICE, document)
                    self.assertIn(self.OFFICE_PARAGRAPH, document)
                    self.assertIn("Fax 805.953.8530; Medicare 1-800-633-4227.", document)
                    self.assertIn("Synthetic café — care", document)
                    if contextual:
                        self.assertEqual(self.render_links.call_count, 4)
                        self.assertIn(self.MAIN_RELATED_CALL, document)
                        self.assertNotIn(self.RELATED_CALL, document)
                    else:
                        self.render_links.assert_not_called()
                    self.assertEqual((self.root / "synthetic.html").read_bytes(), self.source)
                    self.assertEqual((self.root / "index.html").read_bytes(), self.source)

    def test_journal_response_uses_only_an_unsigned_in_memory_snapshot(self):
        directory = self.root / "blog"
        directory.mkdir()
        path = directory / "synthetic.html"
        path.write_bytes(b"<article>Unsigned disk fixture, not the snapshot.</article>")
        record = {"html": self.source.decode("utf-8"), "revision": "unsigned-fixture"}
        # Exercise the snapshot response branch without reading a real approval,
        # manifest or Journal document. The underlying release loader stays blocked.
        with patch.object(PrettyURLHandler, "_released_journal",
                          return_value={"synthetic": record}) as released:
            document = self.response_matrix(
                "/blog/synthetic", False, "text/html",
                {"X-Journal-Revision": "unsigned-fixture"}).decode("utf-8")
            self.assertEqual(released.call_count, 4)
        self.inventory.assert_not_called()
        self.render_links.assert_not_called()
        self.assertIn(self.MAIN_CALL, document)
        self.assertNotIn(self.OLD_CALL, document)
        self.assertIn('"telephone":"+18054099262"', document)
        self.assertIn(self.OFFICE, document)
        self.assertIn(self.OFFICE_PARAGRAPH, document)
        self.assertEqual(record["html"].encode("utf-8"), self.source)
        self.assertEqual(path.read_bytes(),
                         b"<article>Unsigned disk fixture, not the snapshot.</article>")

    def test_llms_discovery_projects_phone_even_when_gzip_is_requested(self):
        source = ("# Synthetic café — discovery\n"
                  "Call 805.953.7273; tel:+18059537273\n"
                  "Referral +1-805-410-1151\n"
                  "Fax 805.953.8530; Medicare 1-800-633-4227\n"
                  + "Unsigned discovery information.\n" * 40).encode("utf-8")
        (self.root / "llms.txt").write_bytes(source)
        # This dynamic text branch intentionally serves identity, even to gzip clients.
        body = self.response_matrix("/llms.txt?unsigned=1", False, "text/plain")
        self.assertEqual(body, source.decode("utf-8").replace(
            "805.953.7273", "805.409.9262").replace(
            "+18059537273", "+18054099262").replace(
            "+1-805-410-1151", "+1-805-409-9262").encode("utf-8"))
        self.assertEqual((self.root / "llms.txt").read_bytes(), source)

    def test_public_metadata_preserves_canonical_main_and_explicit_office(self):
        directory = self.root / ".well-known"
        directory.mkdir()
        # Metadata is authored with Main, not HTML-projected at runtime. Office
        # fields must not be swept up by a future blanket static rewrite.
        for large in (False, True):
            with self.subTest(large=large):
                metadata = {
                    "openapi": "3.1.0",
                    "info": {"title": "Synthetic café", "version": "1",
                             "contact": {"phone": "805.409.9262",
                                         "url": "tel:18054099262"}},
                    "officePhone": "805.953.7273",
                    "description": "Unsigned metadata. " * (80 if large else 1),
                }
                source = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
                self.assertEqual(len(source) >= 512, large)
                path = directory / "openapi.json"
                path.write_bytes(source)
                body = self.response_matrix(
                    "/.well-known/openapi.json?unsigned=1", large, "application/json")
                self.assertEqual(body, source)
                self.assertEqual(json.loads(body), metadata)
                self.assertEqual(path.read_bytes(), source)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    passed = result.wasSuccessful() and not result.skipped and result.testsRun > 0
    if passed:
        print("SENTINEL: test-website-phone.py OK")
    raise SystemExit(0 if passed else 1)
