#!/usr/bin/env python3
"""Validate Open Graph and Twitter metadata on every sitemap page."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys
import xml.etree.ElementTree as ET


BASE = Path(__file__).resolve().parent
SITE = BASE / "elh-preview"
SITEMAP = SITE / "sitemap.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

REQUIRED_OG = {
    "og:title",
    "og:description",
    "og:url",
    "og:type",
    "og:site_name",
    "og:image",
    "og:image:width",
    "og:image:height",
    "og:image:alt",
}
REQUIRED_TWITTER = {
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
}


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.properties = {}
        self.names = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        data = {key.lower(): value for key, value in attrs if key and value is not None}
        content = data.get("content", "").strip()
        if data.get("property"):
            self.properties[data["property"].lower()] = content
        if data.get("name"):
            self.names[data["name"].lower()] = content


def source_file(url):
    path = urlsplit(url).path
    if path == "/":
        return SITE / "index.html"
    candidates = [
        SITE / f"{path.lstrip('/')}.html",
        SITE / path.lstrip("/") / "index.html",
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def metadata_errors(html):
    parser = MetadataParser()
    parser.feed(html)
    errors = []
    for name in sorted(REQUIRED_OG):
        if not parser.properties.get(name):
            errors.append(f"missing {name}")
    for name in sorted(REQUIRED_TWITTER):
        if not parser.names.get(name):
            errors.append(f"missing {name}")
    return errors


def run_check():
    errors = []
    root = ET.parse(SITEMAP).getroot()
    urls = [node.text.strip() for node in root.findall(".//sm:loc", NS) if node.text]
    for url in urls:
        page = source_file(url)
        if page is None:
            errors.append(f"{url}: source file not found")
            continue
        for error in metadata_errors(page.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"{url}: {error}")
    return urls, errors


def self_test():
    broken = (
        '<meta property="og:title" content="Example">'
        '<meta name="twitter:card" content="summary_large_image">'
    )
    errors = metadata_errors(broken)
    if "missing og:image:alt" not in errors or "missing twitter:image" not in errors:
        raise AssertionError("metadata guard did not catch known-bad input")
    print("SENTINEL: check-og-metadata.py self-test OK")


def main():
    self_test()
    urls, errors = run_check()
    if errors:
        print("Open Graph/Twitter metadata check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Open Graph/Twitter metadata check passed for {len(urls)} sitemap pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())