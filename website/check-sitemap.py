#!/usr/bin/env python3
"""Validate sitemap source, canonicals, indexability, and route resolution."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys
import tempfile
import xml.etree.ElementTree as ET

from devserver import CANONICAL_HTML_ROUTES, LEGACY_PAGE_REDIRECTS


BASE = Path(__file__).resolve().parent
SITE = BASE / "elh-preview"
SITEMAP = SITE / "sitemap.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
CANONICAL_ORIGIN = "https://eternallifehospice.com"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = ""
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        data = {key.lower(): value for key, value in attrs if key and value is not None}
        if tag.lower() == "link" and data.get("rel", "").lower() == "canonical":
            self.canonical = data.get("href", "").strip()
        if (
            tag.lower() == "meta"
            and data.get("name", "").lower() == "robots"
            and "noindex" in data.get("content", "").lower()
        ):
            self.noindex = True


def source_file(path):
    if path == "/":
        return SITE / "index.html"
    candidates = [
        SITE / f"{path.lstrip('/')}.html",
        SITE / path.lstrip("/") / "index.html",
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def route_resolution_error(path, site=SITE, canonical_routes=CANONICAL_HTML_ROUTES):
    if path == "/":
        return None if (site / "index.html").is_file() else "homepage source is missing"
    if path.rstrip("/") in canonical_routes:
        target = site / f"{path.strip('/')}.html"
        return None if target.is_file() else f"canonical route target is missing: {target}"
    directory = site / path.lstrip("/")
    if directory.is_dir():
        return (
            "route resolves to a directory redirect instead of a final HTML response; "
            "add it to CANONICAL_HTML_ROUTES or use a trailing-slash canonical"
        )
    direct = site / f"{path.lstrip('/')}.html"
    if direct.is_file():
        return None
    if (directory / "index.html").is_file():
        return None
    return "route has no source file"


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "loop").mkdir()
        (root / "loop" / "index.html").write_text("directory", encoding="utf-8")
        (root / "loop.html").write_text("final", encoding="utf-8")
        if route_resolution_error("/loop", root, set()) is None:
            raise AssertionError("directory-conflict guard did not catch known-bad input")
        if route_resolution_error("/loop", root, {"/loop"}) is not None:
            raise AssertionError("canonical route declaration did not resolve conflict")
    print("SENTINEL: check-sitemap.py self-test OK")


def main():
    self_test()
    errors = []
    root = ET.parse(SITEMAP).getroot()
    urls = [node.text.strip() for node in root.findall(".//sm:loc", NS) if node.text]

    if len(urls) != len(set(urls)):
        errors.append("sitemap contains duplicate URLs")

    for url in urls:
        parsed = urlsplit(url)
        if f"{parsed.scheme}://{parsed.netloc}" != CANONICAL_ORIGIN:
            errors.append(f"{url}: URL is not on the canonical HTTPS origin")
            continue
        if parsed.query or parsed.fragment:
            errors.append(f"{url}: sitemap URL contains a query string or fragment")
        if parsed.path in LEGACY_PAGE_REDIRECTS:
            errors.append(f"{url}: sitemap URL is configured as a redirect")
        route_error = route_resolution_error(parsed.path)
        if route_error:
            errors.append(f"{url}: {route_error}")
            continue
        page = source_file(parsed.path)
        if page is None:
            errors.append(f"{url}: source file not found")
            continue
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        if parser.noindex:
            errors.append(f"{url}: sitemap page is marked noindex")
        if parser.canonical != url:
            errors.append(
                f"{url}: canonical mismatch ({parser.canonical or 'missing canonical'})"
            )

    if errors:
        print("Sitemap/canonical route check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Sitemap/canonical route check passed for {len(urls)} URLs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())