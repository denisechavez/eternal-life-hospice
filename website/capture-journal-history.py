#!/usr/bin/env python3
"""One-time, explicit capture of published originals from the live sitemap."""
import argparse
import base64
import json
import re
import zlib
from urllib.request import urlopen
from pathlib import Path
from journal_release import HISTORY, revision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--published-site", required=True)
    parser.add_argument("--output", type=Path, default=HISTORY)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("History already exists; do not regenerate from dates.")
    with urlopen(args.published_site.rstrip("/") + "/sitemap.xml", timeout=30) as response:
        sitemap = response.read().decode()
    articles = {}
    for slug in sorted(set(re.findall(r"<loc>https://eternallifehospice\.com/blog/([^<]+)</loc>", sitemap))):
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise SystemExit("Unexpected published Journal URL")
        # The live response, not a potentially changed workspace file, is
        # authoritative for previously published copy.
        with urlopen(args.published_site.rstrip("/") + "/blog/" + slug, timeout=30) as response:
            document = response.read().decode()
        day = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', document)
        if not day or "<h1" not in document or 'http-equiv="refresh"' in document:
            raise SystemExit("Published Journal document could not be verified")
        articles[slug] = {"revision": revision(document), "date": day.group(1),
                          "document": base64.b64encode(zlib.compress(document.encode(), 9)).decode()}
    args.output.write_text(json.dumps({"source": args.published_site, "articles": articles}, indent=2) + "\n")
    print(f"Captured {len(articles)} published originals, {args.output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
