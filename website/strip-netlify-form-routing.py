#!/usr/bin/env python3
"""Disable Netlify Forms in the separately deployed static copy.

The production form API exists only in the Replit deployment. Netlify builds
run this script against their ephemeral publish workspace so legacy form
attributes cannot silently reactivate Netlify as a second intake destination.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


FORM_FILES = ("index.html", "refer.html", "careers.html", "care-brief.html")


def strip_form_tag(match: re.Match[str]) -> str:
    tag = match.group(0)
    tag = re.sub(r'\s+data-netlify="true"', "", tag)
    tag = re.sub(r'\s+netlify-honeypot="[^"]*"', "", tag)
    if re.search(r'\saction="(?:/|/care-brief)"', tag):
        tag = re.sub(
            r'\saction="(?:/|/care-brief)"',
            ' action="/api/form-submit"',
            tag,
        )
    return tag


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "website/elh-preview")
    changed = 0
    for name in FORM_FILES:
        path = root / name
        text = path.read_text(encoding="utf-8")
        updated = re.sub(r"<form\b[^>]*>", strip_form_tag, text, flags=re.I)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    remaining = []
    for name in FORM_FILES:
        path = root / name
        text = path.read_text(encoding="utf-8")
        if 'data-netlify="true"' in text or 'netlify-honeypot=' in text:
            remaining.append(name)
    if remaining:
        print("ERROR: Netlify form attributes remain in " + ", ".join(remaining))
        return 1

    print(
        f"Netlify form routing disabled in {changed} file(s); "
        "all forms target /api/form-submit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
