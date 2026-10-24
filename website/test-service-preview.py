"""Safety, content and metadata checks for the review-only service suite."""
import hashlib
import html
import io
import json
import os
import re
import runpy
import unittest
from unittest.mock import patch

import service_preview as preview


def plain(markup):
    return html.unescape(re.sub(r"<[^>]+>", "", markup)).strip()


class Handler:
    def __init__(self, path, command="GET"):
        self.path, self.command = path, command
        self.wfile = io.BytesIO()
        self.headers = {}

    def send_error(self, status):
        self.status = status

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers[key] = value

    def end_headers(self):
        pass


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.pages = preview.catalog()

    def source(self, slug):
        return (preview.PREVIEWS / (slug + ".html")).read_text()

    def test_catalog_has_exact_ten_approved_pages(self):
        self.assertEqual(len(self.pages), 10)
        self.assertEqual(set(self.pages), set(preview.SLUGS))
        for slug, record in self.pages.items():
            source = self.source(slug)
            self.assertEqual(plain(re.search(r"<h1[^>]*>(.*?)</h1>", source, re.S)[1]),
                             record["title"])
            self.assertIn(record["summary"], plain(source))

    def test_production_never_serves_preview_or_assets(self):
        paths = [preview.ASSET_PREFIX + name
                 for name in preview.IMAGE_NAMES | set(preview.PRESENTATION_ASSETS)]
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            for path in paths:
                handler = Handler(path)
                self.assertTrue(preview.serve(handler, lambda value: value), path)
                self.assertEqual(handler.status, 404, path)
                self.assertEqual(handler.wfile.getvalue(), b"")

    def test_existing_production_services_page_falls_through_unchanged(self):
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            for route in ("/services", *("/services/" + slug for slug in preview.SLUGS)):
              for path in (route, route + "/", route + ".html"):
                self.assertFalse(preview.serve(Handler(path), lambda value: value))

    def test_production_navigation_uses_approved_public_assets(self):
        source = (preview.BASE / "elh-preview/services.html").read_text()
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            rendered = preview.decorate(source, "/services")
            self.assertIn('id="sp-services-menu"', rendered)
            self.assertIn(preview.PUBLIC_ASSET_PREFIX + "navigation.css", rendered)
            self.assertNotIn(preview.ASSET_PREFIX, rendered)
            for tag in ("main", "footer"):
                pattern = rf"<{tag}\b.*?</{tag}>"
                self.assertEqual(re.search(pattern, source, re.S)[0],
                                 re.search(pattern, rendered, re.S)[0])

    def test_preview_changes_header_only_not_body_or_footer(self):
        source = (preview.BASE / "elh-preview/services.html").read_text()
        output = preview.decorate(source, "/")
        for tag in ("main", "footer"):
            pattern = rf"<{tag}\b.*?</{tag}>"
            self.assertEqual(re.search(pattern, source, re.S)[0],
                             re.search(pattern, output, re.S)[0])
        header = re.search(r"<header\b.*?</header>", output, re.S)[0]
        for slug in preview.SLUGS:
            self.assertEqual(header.count('href="/services/' + slug + '"'), 1)
        self.assertEqual(header.count('class="sp-group-toggle"'), 4)
        self.assertNotIn("/services/medical-aid-in-dying-california", header)
        self.assertIn("View All Services", header)
        self.assertIn('href="tel:8059537273"', header)

    def test_navigation_decoration_is_idempotent(self):
        source = (preview.BASE / "elh-preview/services.html").read_text()
        once = preview.decorate(source, "/services")
        self.assertEqual(preview.decorate(once, "/services"), once)
        self.assertEqual(once.count('id="sp-services-menu"'), 1)
        self.assertIn('aria-current="page"', once)

    def test_edge_treatment_is_loaded_on_every_service_preview_only(self):
        stylesheet = preview.ASSET_PREFIX + "service-hero-edge.css"
        overview = (preview.PREVIEWS / "services-directory.html").read_text()
        for route, source in [
            ("/services", overview),
            *(("/services/" + slug, self.source(slug)) for slug in preview.SLUGS),
        ]:
            rendered = preview.decorate(source, route)
            self.assertEqual(rendered.count(f'href="{stylesheet}"'), 1, route)
            self.assertEqual(preview.decorate(rendered, route), rendered, route)
        self.assertNotIn(stylesheet, preview.decorate(overview, "/"))
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            self.assertNotIn(stylesheet, preview.decorate(overview, "/services"))

    def test_directory_grouping_and_unique_service_cards(self):
        source = (preview.PREVIEWS / "services-directory.html").read_text()
        main = re.search(r"<main\b.*?</main>", source, re.S)[0]
        for heading, _ in preview.GROUPS:
            self.assertIn(html.escape(heading), main)
        for slug in preview.SLUGS:
            self.assertEqual(main.count('href="/services/' + slug + '"'), 1)
        self.assertNotIn("/services/medical-aid-in-dying-california", main)
        headings = re.findall(r'<section class="directory-group[^"]*"><h2>(.*?)</h2>', main)
        self.assertEqual(headings[0], "Getting Started")
        self.assertEqual(preview.GROUPS[0][0], "Getting Started")
        self.assertIn('class="directory-group directory-group--getting-started"', main)

    def test_faq_schema_matches_every_visible_answer(self):
        for slug in preview.SLUGS:
            source = self.source(slug)
            scripts = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
            data = [json.loads(script) for script in scripts]
            faq = next(item for item in data if item["@type"] == "FAQPage")
            visible = [(plain(q), plain(a)) for q, a in re.findall(
                r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", source, re.S)]
            structured = [(item["name"], item["acceptedAnswer"]["text"])
                          for item in faq["mainEntity"]]
            self.assertTrue(visible, slug)
            self.assertEqual(visible, structured, slug)
            breadcrumb = next(item for item in data if item["@type"] == "BreadcrumbList")
            self.assertEqual(len(breadcrumb["itemListElement"]), 3)
            self.assertEqual(breadcrumb["itemListElement"][-1]["item"],
                             "https://eternallifehospice.com/services/" + slug)

    def test_every_service_page_opens_without_breadcrumb_or_preview_strip(self):
        directory = (preview.PREVIEWS / "services-directory.html").read_text()
        self.assertNotIn('class="cc-breadcrumb"', directory)
        for slug in preview.SLUGS:
            source = self.source(slug)
            self.assertNotIn('class="cc-breadcrumb"', source)
            self.assertNotIn('class="cc-wrap cc-preview-note"', source)

    def test_in_home_grid_has_a_decorative_visual_not_an_invented_service(self):
        source = self.source("in-home-hospice-care")
        self.assertEqual(source.count('class="cc-tile cc-tile--visual"'), 1)
        self.assertIn('class="cc-tile cc-tile--visual" aria-hidden="true"', source)
        self.assertIn('class="cc-home-visual"', source)
        for slug in preview.SLUGS:
            if slug != "in-home-hospice-care":
                self.assertNotIn("cc-home-visual", self.source(slug))

    def test_bereavement_uses_four_real_items_in_a_balanced_grid(self):
        source = self.source("bereavement-support")
        self.assertIn('id="service-page" class="bereavement-service-page"', source)
        self.assertEqual(source.count('data-layout="balanced-pairs"'), 1)
        self.assertEqual(source.count('class="cc-tile"'), 4)
        self.assertNotIn("cc-tile--visual", source)
        for slug in preview.SLUGS:
            if slug not in ("bereavement-support", "hospice-care-for-heart-failure"):
                self.assertNotIn('data-layout="balanced-pairs"', self.source(slug))
            if slug != "bereavement-support":
                self.assertNotIn('class="bereavement-service-page"', self.source(slug))

    def test_heart_failure_uses_four_unchanged_items_in_a_balanced_grid(self):
        source = self.source("hospice-care-for-heart-failure")
        self.assertEqual(source.count('data-layout="balanced-pairs"'), 1)
        self.assertEqual(source.count('class="cc-tile"'), 4)
        self.assertNotIn("cc-tile--visual", source)
        for text in (
            "Relief for breathlessness at rest and during activity",
            "Guidance on swelling, fluid and comfortable positioning",
            "Review of heart medications, keeping those that support comfort",
            "Warning signs to watch and when to call the nurse",
        ):
            self.assertIn(text, source)

    def test_editorial_approvals_and_preview_metadata(self):
        for slug in preview.SLUGS:
            source = self.source(slug)
            self.assertRegex(source, r'<meta name="robots" content="noindex,\s*nofollow">')
            self.assertIn('<meta name="description" content="', source)
            self.assertIn('href="tel:8059537273"', source)
            self.assertIn('href="/refer#referral-form"', source)
            self.assertNotIn(
                "Phone access does not mean a nurse stays continuously at the bedside.",
                source)
            self.assertNotIn("Same-day admission is available", source)
            self.assertNotIn("Each one is temporary", source)
            self.assertNotIn("Kaiser Permanente", source)
            self.assertNotIn("thirteen months", source)
            self.assertIn("Families deserve calm direction and clear answers.", source)
        source = self.source("24-7-nurse-access")
        self.assertIn("arranges a visit when clinically needed under the plan of care.", source)
        self.assertIn("Who should we call when symptoms change?", source)
        self.assertNotIn("Should we call 911?", source)
        source = self.source("bereavement-support")
        self.assertIn("Understanding bereavement support", source)
        self.assertNotIn("Covered under Medicare and Medi-Cal", source)

    def test_related_service_links_are_real_destinations(self):
        public = preview.BASE / "elh-preview"
        for slug in preview.SLUGS:
            source = self.source(slug)
            section = re.search(r'<section class="cc-related">.*?</section>', source, re.S)[0]
            for url in re.findall(r'href="([^"]+)"', section):
                if url.startswith("/services/"):
                    self.assertIn(url.rsplit("/", 1)[1], preview.SLUGS)
                else:
                    self.assertTrue((public / (url.lstrip("/") + ".html")).is_file(), url)

    def test_contextual_links_are_in_content_not_only_bottom(self):
        public = preview.BASE / "elh-preview"
        for slug in preview.SLUGS:
            source = self.source(slug)
            links = re.findall(r'<a class="cc-context-link" href="([^"]+)">([^<]+)</a>',
                               source)
            self.assertEqual(len(links), 2, slug)
            for url, text in links:
                self.assertTrue(text.strip())
                if url.startswith("/services/"):
                    self.assertIn(url.rsplit("/", 1)[1], preview.SLUGS)
                    self.assertNotEqual(url, "/services/" + slug)
                else:
                    self.assertTrue((public / (url.lstrip("/") + ".html")).is_file(), url)
                self.assertLess(source.index('class="cc-context-link"'),
                                source.index('<section class="cc-related">'))

    def test_service_photos_have_no_visible_footnote_overlays(self):
        sources = [self.source(slug) for slug in preview.SLUGS]
        sources.append((preview.PREVIEWS / "services-directory.html").read_text())
        for source in sources:
            self.assertNotIn("<figcaption", source)
            self.assertNotIn("not an actual patient encounter", source)
            self.assertIn("Illustrative", source)  # Alt text remains truthful.

    def test_tiles_and_timelines_appear_once_in_correct_section(self):
        pages = runpy.run_path(str(preview.BASE / "build-service-previews.py"))["PAGES"]
        second_tile_slugs = {
            "hospice-in-assisted-living-and-skilled-nursing", "hospice-care-for-dementia"}
        for page in pages:
            source = self.source(page["slug"])
            self.assertEqual(source.count('class="cc-tile"'), len(page.get("tiles", [])),
                             page["slug"])
            self.assertEqual(source.count('class="cc-timeline"'),
                             int(bool(page.get("timeline"))), page["slug"])
            if page.get("tiles"):
                tile_position = source.index('class="cc-tiles"')
                photo_position = source.index('<section class="cc-communication">')
                self.assertEqual(tile_position > photo_position,
                                 page["slug"] in second_tile_slugs, page["slug"])

    def test_asset_allowlist_rejects_arbitrary_workspace_files(self):
        for name in ("../../devserver.py", "catalog.json", "care-community.html",
                     "qa-contact-sheet.jpg", "%2e%2e/devserver.py"):
            handler = Handler(preview.ASSET_PREFIX + name)
            self.assertTrue(preview.serve(handler, lambda value: value))
            self.assertEqual(handler.status, 404)
        self.assertFalse(preview.serve(Handler("/unrelated-page"), lambda value: value))

    def test_all_photos_exist_and_are_unique(self):
        root = preview.BASE.parent / "generated-artifacts/service-community-preview"
        hashes = {hashlib.sha256((root / name).read_bytes()).hexdigest()
                  for name in preview.IMAGE_NAMES}
        self.assertEqual(len(hashes), 20)

    def test_preview_get_head_and_noindex(self):
        for route in ("/services", *("/services/" + slug for slug in preview.SLUGS)):
            for command in ("GET", "HEAD"):
                handler = Handler(route, command)
                self.assertTrue(preview.serve(handler, lambda value: value))
                self.assertEqual(handler.status, 200, route)
                self.assertEqual(handler.headers["X-Robots-Tag"], "noindex, nofollow")
                self.assertEqual(handler.headers["Cache-Control"], "no-store")
                if command == "HEAD":
                    self.assertEqual(handler.wfile.getvalue(), b"")
                else:
                    self.assertTrue(handler.wfile.getvalue().startswith(b"<!doctype"))


if __name__ == "__main__":
    unittest.main()
