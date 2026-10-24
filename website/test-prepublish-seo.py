"""Regression tests for read-only checks, shared breadcrumbs and build behavior."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import prepublish_seo as seo
import site_breadcrumbs as crumbs
from seo_page_parser import Page


def document(heading, route, body="", breadcrumb=True, title=None, description=None):
    trail = crumbs.expected_path(route, heading)
    nav, schema = "", ""
    if trail and breadcrumb:
        nav = '<nav aria-label="Breadcrumb"><ol>' + "".join(
            "<li>" + (f'<a href="{url}">{label}</a>' if i < len(trail) - 1
                      else f'<span aria-current="page">{label}</span>') + "</li>"
            for i, (label, url) in enumerate(trail)) + "</ol></nav>"
        schema = '<script type="application/ld+json">' + json.dumps({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                 "name": label, "item": seo.ORIGIN + url}
                                for i, (label, url) in enumerate(trail)]}) + "</script>"
    return (f'<html><head><title>{title or heading}</title>'
            f'<meta name="description" content="{description or heading + " description"}">'
            f'<link rel="canonical" href="{seo.ORIGIN + route}">{schema}</head>'
            f'<body><main><section class="hero"><h1>{heading}</h1></section>'
            + nav + body + "</main></body></html>")


def record(text):
    return {"file": None, "source": text, "page": Page(text)}


class AuditTests(unittest.TestCase):
    def baseline(self):
        return {"/": record(document("Welcome", "/")),
                "/services": record(document("Services", "/services")),
                "/services/example": record(document("Example", "/services/example"))}

    def test_good_pages_and_home_exception(self):
        self.assertEqual(seo.audit(self.baseline(), {}), [])

    def test_all_requested_content_and_link_errors_are_reported(self):
        pages = self.baseline()
        pages["/services/example"] = record(document(
            "Example", "/services/example", '<h1>Second H1</h1><img src="/photo.jpg">'
            '<a href="/missing">Missing</a><a href="/old">Old</a>'
            '<a href="/services#absent">Absent section</a>',
            breadcrumb=False, title="Services", description="Services description"))
        issues = seo.audit(pages, {"/old": "/services"})
        checks = {item["check"] for item in issues}
        self.assertTrue({"Duplicate page identity", "Main heading", "Image description",
                         "Internal link", "Breadcrumb", "Breadcrumb structured data"} <= checks)
        self.assertTrue(any("redirects" in item["problem"] for item in issues))
        self.assertTrue(any("section" in item["problem"] for item in issues))
        self.assertTrue(all(item["url"].startswith(seo.ORIGIN) and item["fix"] for item in issues))

    def test_leaf_is_plain_text_and_path_and_menu_labels_are_exact(self):
        pages = self.baseline()
        text = document("Example", "/services/example").replace(
            '<span aria-current="page">Example</span>', '<a href="/services/example">Wrong</a>')
        text = text.replace('<a href="/services">Services</a>', '<a href="/">Services</a>')
        pages["/services/example"] = record(text)
        pages["/"]["page"] = Page(document("Welcome", "/", body="").replace(
            "<body>", '<body><header><a href="/services/example">Different menu label</a></header>'))
        checks = {item["check"] for item in seo.audit(pages, {})}
        self.assertTrue({"Breadcrumb current page", "Breadcrumb label", "Breadcrumb path", "Menu label"} <= checks)

    def test_invalid_schema_positions_types_urls_and_json(self):
        for bad in ('"position": "1"', '"position": 0', '"position": true'):
            pages = self.baseline()
            pages["/services"]["page"] = Page(document("Services", "/services").replace(
                '"position": 1', bad))
            self.assertTrue(any("invalid types" in item["problem"] for item in seo.audit(pages, {})))
        pages = self.baseline()
        pages["/services"]["page"] = Page(document("Services", "/services").replace(
            '"item": "https://eternallifehospice.com/"', '"item": "/missing"'))
        self.assertTrue(any("structured data" in item["check"] for item in seo.audit(pages, {})))
        self.assertTrue(Page('<script type="application/ld+json">{bad}</script>').schema_errors)

    def test_decorative_alt_requires_explicit_marking(self):
        pages = self.baseline()
        pages["/"]["page"] = Page(document("Welcome", "/", '<img src="/art.svg" alt="" role="presentation">'))
        self.assertFalse(any(item["check"] == "Image description" for item in seo.audit(pages, {})))
        pages["/"]["page"] = Page(document("Welcome", "/", '<img src="/art.svg" alt="">'))
        self.assertTrue(any(item["check"] == "Image description" for item in seo.audit(pages, {})))

    def test_graph_schema_and_entities_and_nested_heading(self):
        page = Page('<h1>Care &amp; <em>Comfort</em></h1><script type="application/ld+json">'
                    '{"@graph":[{"@type":null},{"@type":"BreadcrumbList","itemListElement":[]}]}'
                    '</script>')
        self.assertEqual(page.headings, ["Care & Comfort"])
        self.assertEqual(len(page.breadcrumb_schemas), 1)
        self.assertTrue(seo.schema_context_valid(page.schema_contexts[id(page.breadcrumb_schemas[0])])
                        is False)
        page = Page('<script type="application/ld+json">{"@context":"https://schema.org",'
                    '"@graph":[{"@type":["BreadcrumbList"]}]}</script>')
        self.assertTrue(seo.schema_context_valid(page.schema_contexts[id(page.breadcrumb_schemas[0])]))

    def test_external_links_are_not_called_and_files_are_resolved(self):
        self.assertEqual(seo.local_target("/", "https://eternallifehospice.com"), ("/", ""))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "guide.pdf").write_bytes(b"test")
            pages = {"/": record(document("Welcome", "/",
                     '<a href="/guide.pdf#page=1">Guide</a>'
                     '<a href="https://external.invalid">External</a>'))}
            self.assertEqual(seo.audit(pages, {}, root), [])


class BreadcrumbTests(unittest.TestCase):
    def test_missing_blog_resource_and_city_breadcrumbs_are_added_after_hero(self):
        for route in ("/blog/example", "/resources/example", "/hospice-example-ca"):
            with self.subTest(route=route):
                original = document("Example", route, breadcrumb=False)
                result = crumbs.decorate(original, route)
                parsed = Page(result)
                self.assertEqual(len(parsed.breadcrumbs), 1)
                self.assertEqual(parsed.breadcrumbs[0][-1]["label"], "Example")
                self.assertFalse(parsed.breadcrumbs[0][-1]["links"])
                self.assertEqual(len(parsed.breadcrumb_schemas), 1)
                self.assertLess(result.index("</section>"), result.index('<nav class="content-breadcrumbs"'))
                self.assertEqual(crumbs.decorate(result, route), result)

    def test_existing_breadcrumbs_and_service_heroes_stay_unchanged(self):
        for route in ("/services/example", "/", "/resources/example"):
            original = document("Example", route)
            self.assertEqual(crumbs.decorate(original, route), original)

    def test_blogposting_dates_and_article_copy_are_not_changed(self):
        original = document("Example", "/blog/example", "<p>Approved article copy.</p>", False)
        metadata = {"@context": "https://schema.org", "@graph": [
            {"@type": "BlogPosting", "datePublished": "2026-10-01", "headline": "Example"},
            {"@type": "BreadcrumbList", "itemListElement": []}]}
        original = original.replace("</head>", '<script type="application/ld+json">'
                                    + json.dumps(metadata) + "</script></head>")
        result = crumbs.decorate(original, "/blog/example")
        parsed = Page(result)
        article = next(node for node in parsed.schemas if node.get("@type") == "BlogPosting")
        self.assertEqual(article, metadata["@graph"][0])
        self.assertEqual(len(parsed.breadcrumb_schemas), 1)
        stripped = re.sub(r'<nav class="content-breadcrumbs".*?</nav>', "", result)
        self.assertEqual(re.search("<main>.*</main>", stripped)[0],
                         re.search("<main>.*</main>", original)[0])
        standalone = '<script type="application/ld+json">' + json.dumps(metadata["@graph"][0]) + "</script>"
        original = original.replace("</head>", standalone + "</head>")
        self.assertIn(standalone, crumbs.decorate(original, "/blog/example"))

    def test_nested_hero_and_main_fallback(self):
        original = document("Example", "/resources/example", breadcrumb=False).replace(
            "</h1>", "</h1><section>Inner section</section>")
        result = crumbs.decorate(original, "/resources/example")
        self.assertIn('Inner section</section></section><nav', result)
        original = document("Example", "/resources/example", breadcrumb=False).replace(
            '<section class="hero">', "").replace("</section>", "")
        self.assertIn('<main><nav', crumbs.decorate(original, "/resources/example"))


class AdvisoryTests(unittest.TestCase):
    def test_real_audit_does_not_change_any_site_html(self):
        before = {file: hashlib.sha256(file.read_bytes()).hexdigest()
                  for file in seo.SITE.rglob("*.html")}
        report = seo.run()
        self.assertGreater(report["pages_checked"], 0)
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in before})

    def test_cli_reports_issues_but_always_returns_success_and_does_not_edit_sources(self):
        module = runpy.run_path(str(seo.BASE / "check-prepublish-seo.py"))
        before = {file: hashlib.sha256(file.read_bytes()).hexdigest()
                  for file in seo.SITE.rglob("*.html")}
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            with patch.object(sys, "argv", ["check-prepublish-seo.py", "--report-dir", folder]), \
                 patch.dict(module["main"].__globals__, {"run": lambda: {
                     "generated_at": "test", "pages_checked": 1,
                     "issues": [{"url": seo.ORIGIN + "/example", "check": "Breadcrumb",
                                 "problem": "Missing breadcrumb", "fix": "Add a breadcrumb."}]}}):
                self.assertEqual(module["main"](), 0)
                self.assertIn("Fix: Add a breadcrumb.", (Path(folder) / "prepublish-seo-report.txt").read_text())
            with patch.object(sys, "argv", ["check-prepublish-seo.py"]), \
                 patch.dict(module["main"].__globals__, {"run": lambda: 1 / 0}), \
                 contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(module["main"](), 0)
                self.assertIn("NOT blocked", errors.getvalue())
        self.assertEqual(before, {file: hashlib.sha256(file.read_bytes()).hexdigest() for file in before})

    def test_build_continues_even_if_checker_process_fails(self):
        build = (seo.BASE / "build-published-site.sh").read_text()
        self.assertLess(build.index("check-prepublish-seo.py"), build.index("npm ci"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "website").mkdir()
            (root / "website/check-prepublish-seo.py").write_text("raise SystemExit(17)\n")
            simulation = re.sub(r"^(?:npm|node|bash) .*$", "echo BUILD_CONTINUED", build, flags=re.M)
            result = subprocess.run(["bash", "-c", simulation], cwd=root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("BUILD_CONTINUED", result.stdout)
            self.assertIn("continuing", result.stderr)


if __name__ == "__main__":
    unittest.main()
