#!/usr/bin/env python3
"""Reject immutable analytics URLs that no longer match the asset's bytes."""

import json
import re
import runpy
import sys
from pathlib import Path

from analytics_assets import ANALYTICS_FILE, analytics_url, refresh_html

BASE = Path(__file__).resolve().parent
REFERENCE = re.compile(r'<script\b[^>]*\bsrc=["\'](/assets/analytics\.js[^"\']*)["\']', re.I)


def mismatches(html: str, content: bytes) -> list[str]:
    expected = analytics_url(content)
    return [url for url in REFERENCE.findall(html) if url != expected]


def main() -> None:
    content = ANALYTICS_FILE.read_bytes()
    current = analytics_url(content)
    if "--sync" in sys.argv:
        # Explicit maintenance mode: refresh immutable URLs without regenerating
        # page copy. Normal pre-publish checks remain read-only.
        sources = list((BASE / "elh-preview").rglob("*.html"))
        sources += list((BASE / "previews").rglob("*.html"))
        sources.append(BASE / "build-service-previews.py")
        for page in sources:
            # Journal source bytes are signed by approval. Refresh their served
            # HTML instead of invalidating approvals for a tracking-asset update.
            if page.is_relative_to(BASE / "elh-preview" / "blog"):
                continue
            html = page.read_text(encoding="utf-8")
            updated = REFERENCE.sub(
                lambda match: match[0].replace(match[1], current), html
            )
            if updated != html:
                page.write_text(updated, encoding="utf-8")
    valid = f'<script defer src="{current}"></script>'
    # An asset-byte mutation must invalidate the old URL, regardless of its label.
    assert not mismatches(valid, content)
    assert mismatches(valid, content + b"\n// synthetic change\n") == [current]
    assert mismatches('<script src="/assets/analytics.js?v=old"></script>', content)
    assert mismatches('<script src="/assets/analytics.js"></script>', content)
    # Check the real response pipeline, not just the URL-rewriting helper.
    from devserver import PrettyURLHandler
    handler = object.__new__(PrettyURLHandler)
    handler.path = "/blog/synthetic-tracking-check"
    legacy = '<html><head><script defer src="/assets/analytics.js?v=old"></script></head><body></body></html>'
    assert REFERENCE.findall(handler._preview_chrome(legacy)) == [current]

    errors = []
    references = 0
    for page in sorted((BASE / "elh-preview").rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        if page.is_relative_to(BASE / "elh-preview" / "blog"):
            html = refresh_html(html, content)
        references += len(REFERENCE.findall(html))
        errors.extend(f"{page.relative_to(BASE)}: {url}" for url in mismatches(html, content))
    assert references > 0, "No analytics references scanned"

    # Check the actual template output without regenerating or overwriting pages.
    if "--static-only" not in sys.argv:
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
    scope = "authored/served references" if "--static-only" in sys.argv else "authored/served references and city template output"
    print(f"PASS: {references} {scope} use {current}")
    print("SENTINEL: check-analytics-version.py self-test OK")


if __name__ == "__main__":
    main()
