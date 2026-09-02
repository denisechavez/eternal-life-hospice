#!/usr/bin/env python3
"""Require an alt attribute on every image used by a sitemap page."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys
import xml.etree.ElementTree as ET


BASE = Path(__file__).resolve().parent
SITE = BASE / "elh-preview"
SITEMAP = SITE / "sitemap.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            self.images.append({key.lower(): value for key, value in attrs if key})


def source_file(url):
    path = urlsplit(url).path
    if path == "/":
        return SITE / "index.html"
    candidates = [
        SITE / f"{path.lstrip('/')}.html",
        SITE / path.lstrip("/") / "index.html",
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def missing_alt_images(html):
    parser = ImageParser()
    parser.feed(html)
    return [image.get("src", "(missing src)") for image in parser.images if "alt" not in image]


def self_test():
    broken = '<img src="missing.jpg"><img src="decorative.jpg" alt="">'
    missing = missing_alt_images(broken)
    if missing != ["missing.jpg"]:
        raise AssertionError("image-alt guard did not catch known-bad input")
    print("SENTINEL: check-img-alt.py self-test OK")


def main():
    self_test()
    errors = []
    root = ET.parse(SITEMAP).getroot()
    urls = [node.text.strip() for node in root.findall(".//sm:loc", NS) if node.text]
    for url in urls:
        page = source_file(url)
        if page is None:
            errors.append(f"{url}: source file not found")
            continue
        for src in missing_alt_images(page.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"{url}: image missing alt attribute: {src}")
    if errors:
        print("Image alt check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Image alt check passed for {len(urls)} sitemap pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())