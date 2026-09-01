#!/usr/bin/env python3
"""Synchronize the canonical ELH header across standard static pages."""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fragments import HEADER_HTML

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elh-preview")
HEADER_RE = re.compile(r'<header id="hdr">.*?</header>', re.DOTALL)
HEADER_CSS_RE = re.compile(
    r'\s*<link[^>]+href=["\']/assets/header-nav\.css\?v=[^"\']+["\'][^>]*>',
    re.IGNORECASE,
)
HEADER_JS_RE = re.compile(r'(?P<prefix>(?:/|assets/)?assets/header\.js\?v=)[A-Za-z0-9._-]+')
CSS_LINK = '<link rel="stylesheet" href="/assets/header-nav.css?v=20260901u">'
JS_VERSION = "20260901d"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    updated = []
    unchanged = []
    skipped = []
    errors = []

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d != "assets")
        for filename in sorted(files):
            if not filename.endswith(".html"):
                continue
            path = os.path.join(dirpath, filename)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            html = open(path, encoding="utf-8", errors="replace").read()
            match = HEADER_RE.search(html)
            if not match or 'aria-label="Main navigation"' not in match.group(0):
                skipped.append(rel)
                continue

            new_html = HEADER_RE.sub(HEADER_HTML, html, count=1)
            new_html = HEADER_CSS_RE.sub("", new_html)
            if "</head>" not in new_html:
                errors.append((rel, "missing </head>"))
                continue
            new_html = new_html.replace("</head>", f"{CSS_LINK}\n</head>", 1)
            new_html = HEADER_JS_RE.sub(
                lambda m: m.group("prefix") + JS_VERSION,
                new_html,
            )

            if new_html == html:
                unchanged.append(rel)
            else:
                updated.append(rel)
                if not args.dry_run:
                    open(path, "w", encoding="utf-8").write(new_html)

    verb = "Would update" if args.dry_run else "Updated"
    print(f"{verb}: {len(updated)}")
    print(f"Already canonical: {len(unchanged)}")
    print(f"Skipped nonstandard/no-header pages: {len(skipped)}")
    if errors:
        for rel, error in errors:
            print(f"ERROR {rel}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())