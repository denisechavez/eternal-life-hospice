#!/usr/bin/env python3
"""Contact changes must not rewrite editorial copy or telephone CTAs."""
import importlib.util
from pathlib import Path
import unittest

import footer_contact
from fragments import FOOTER_HTML
from website_phone import MAIN_DISPLAY, MAIN_TEL


class FooterContactTests(unittest.TestCase):
    def assert_contact(self, document):
        footer = footer_contact.FOOTER.search(document).group()
        self.assertEqual(footer.count('tel:' + MAIN_TEL), 1)
        self.assertIn(f'<span>{MAIN_DISPLAY} · Main</span>', footer)
        self.assertNotIn("805.410.1151", footer)
        self.assertNotIn("18054101151", footer)
        self.assertNotIn("805.953.7273", footer)
        self.assertIn(f'class="fc-line fc-direct no-swap" href="tel:{MAIN_TEL}"', footer)
        self.assertEqual(document, footer_contact.public_html(document))

    def assert_signup(self, document):
        from seo_page_parser import Page
        links = [link for link in Page(document).links
                 if "foot-signup" in link["attrs"].get("class", "").split()]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["href"], "/care-brief#signup")
        source = Path(__file__).with_name("elh-preview") / "care-brief.html"
        self.assertIn("signup", Page(source.read_text()).ids)

    def test_insurance_link_is_added_without_changing_article_or_repeating(self):
        source = ('<html><head></head><body><p>Approved article copy.</p>'
                  '<footer id="site-footer"><div class="foot-col"><h2>Resources</h2>'
                  '<a href="/family-guide">Family Guide</a></div></footer></body></html>')
        updated = footer_contact.public_html(source)
        self.assertIn('<p>Approved article copy.</p>', updated)
        self.assertEqual(updated.count(footer_contact.INSURANCE_LINK), 1)
        self.assertEqual(footer_contact.public_html(updated), updated)

    def test_insurance_link_is_in_canonical_and_all_existing_footer_variants(self):
        self.assertIn(footer_contact.INSURANCE_LINK, FOOTER_HTML)
        public = Path(__file__).with_name("elh-preview")
        checked = 0
        for source in public.rglob("*.html"):
            if "assets" in source.relative_to(public).parts:
                continue
            footer = footer_contact.FOOTER.search(source.read_text())
            if footer and "<h2>Resources</h2>" in footer.group():
                rendered = footer_contact.public_html(footer.group())
                self.assertEqual(rendered.count(footer_contact.INSURANCE_LINK), 1,
                                 str(source.relative_to(public)))
                checked += 1
        self.assertGreater(checked, 50)

    def test_canonical_and_city_generators(self):
        self.assert_contact(FOOTER_HTML)
        self.assert_signup(FOOTER_HTML)
        spec = importlib.util.spec_from_file_location(
            "city_builder", Path(__file__).with_name("build-cities.py"))
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        for county in ("Ventura County", "Los Angeles County"):
            self.assert_contact(builder.make_footer(county))
            # City footers link to the publication hub, without a signup CTA.
            self.assertIn('href="/care-brief"', builder.make_footer(county))

    def test_frozen_signup_link_is_preserved_by_contact_decoration(self):
        document = '<footer id="site-footer"><a class="foot-signup" href="/care-brief#signup">Share the Eternal Care Brief</a></footer>'
        self.assertEqual(footer_contact.public_html(document), document)
        self.assert_signup(footer_contact.public_html(document))

    def test_frozen_chrome_changes_without_rewriting_article_or_cta(self):
        old = (
            '<footer id="site-footer"><a class="fc-line no-swap" href="tel:18059537273">'
            '<span>805.953.7273</span></a><a class="fc-line fc-direct" href="tel:18054101151">'
            '<span>805.410.1151</span></a></footer>')
        content = '<article>Unchanged article text</article><a href="tel:18059537273">Call now</a>'
        updated = footer_contact.public_html(content + old)
        self.assertTrue(updated.startswith(content))
        self.assert_contact(updated)
        self.assertEqual(updated.count('· Main'), 1)

    def test_main_phone_emphasis_is_loaded_once_on_full_documents(self):
        source = "<html><head><title>Journal</title></head><body>" + FOOTER_HTML + "</body></html>"
        updated = footer_contact.public_html(source)
        self.assertEqual(updated.count(footer_contact.STYLESHEET), 1)
        self.assertIn(footer_contact.STYLESHEET + "\n</head>", updated)
        self.assert_contact(updated)
        self.assertEqual(footer_contact.public_html("<html><head></head><body>No footer</body></html>"),
                         "<html><head></head><body>No footer</body></html>")

    def test_phone_only_refresh_preserves_other_markup_and_numbers(self):
        prefix = '<head></head><article>Approved content</article><a href="tel:18059537273">Call 805.953.7273</a>'
        old = '<footer id="site-footer"><a class="fc-line fc-direct" href="tel:18054101151"><span>805.410.1151 · Main</span></a><span>805.953.8530 fax</span></footer>'
        updated = footer_contact.update_main_number(prefix + old)
        expected = old.replace("18054101151", MAIN_TEL).replace("805.410.1151", MAIN_DISPLAY)
        self.assertEqual(updated, prefix + expected)
        self.assertEqual(footer_contact.update_main_number(updated), updated)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    passed = result.wasSuccessful() and not result.skipped and result.testsRun > 0
    if passed:
        print("SENTINEL: test-footer-contact.py OK")
    raise SystemExit(0 if passed else 1)
