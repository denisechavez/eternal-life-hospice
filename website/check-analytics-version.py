#!/usr/bin/env python3
"""Reject immutable analytics URLs that no longer match the asset's bytes."""

import json
import re
import runpy
from pathlib import Path

from analytics_assets import ANALYTICS_FILE, analytics_url

BASE = Path(__file__).resolve().parent
REFERENCE = re.compile(r'<script\b[^>]*\bsrc=["\'](/assets/analytics\.js[^"\']*)["\']', re.I)


def mismatches(html: str, content: bytes) -> list[str]:
    expected = analytics_url(content)
    return [url for url in REFERENCE.findall(html) if url != expected]


def main() -> None:
    content = ANALYTICS_FILE.read_bytes()
    current = analytics_url(content)
    valid = f'<script defer src="{current}"></script>'
    # An asset-byte mutation must invalidate the old URL, regardless of its label.
    assert not mismatches(valid, content)
    assert mismatches(valid, content + b"\n// synthetic change\n") == [current]
    assert mismatches('<script src="/assets/analytics.js?v=old"></script>', content)
    assert mismatches('<script src="/assets/analytics.js"></script>', content)

    errors = []
    references = 0
    for page in sorted((BASE / "elh-preview").rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        references += len(REFERENCE.findall(html))
        errors.extend(f"{page.relative_to(BASE)}: {url}" for url in mismatches(html, content))
    assert references > 0, "No analytics references scanned"

    # Check the actual template output without regenerating or overwriting pages.
    generator = runpy.run_path(str(BASE / "build-cities.py"))
    for city in json.loads((BASE / "city-data.json").read_text(encoding="utf-8")):
        if city.get("publishStatus") != "published":
            continue
        # A legacy per-city version must not override the shared content hash.
        city = dict(city, analyticsVersion="old")
        html = generator["render_page"](city)
        urls = REFERENCE.findall(html)
        if urls != [current]:
            errors.append(f"generated {city['slug']}: {urls}")
    if errors:
        raise SystemExit("Analytics asset version check failed:\n" + "\n".join(errors))
    print(f"PASS: {references} authored references and city template output use {current}")
    print("SENTINEL: check-analytics-version.py self-test OK")


if __name__ == "__main__":
    main()
