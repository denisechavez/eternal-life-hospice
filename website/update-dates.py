#!/usr/bin/env python3
"""
update-dates.py — set dateModified to today in all JSON-LD blocks across the site.

Run before deploying after any content change:
    python3 website/update-dates.py

Only updates lines that already contain "dateModified" — never inserts new entries.
"""

import os
import re
from datetime import date

TODAY = date.today().isoformat()          # e.g. "2026-08-06"
SITE_DIR = os.path.join(os.path.dirname(__file__), "elh-preview")
PATTERN = re.compile(r'("dateModified"\s*:\s*)"[\d-]+"')
EXTENSIONS = {".html", ".json"}

updated_files = []
unchanged_files = []

for root, dirs, files in os.walk(SITE_DIR):
    # Skip hidden dirs and asset dirs that don't contain JSON-LD
    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("assets", "fonts")]
    for fname in files:
        if not any(fname.endswith(ext) for ext in EXTENSIONS):
            continue
        path = os.path.join(root, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = PATTERN.sub(rf'\g<1>"{TODAY}"', content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_files.append(os.path.relpath(path, SITE_DIR))
        else:
            unchanged_files.append(os.path.relpath(path, SITE_DIR))

print(f"Updated {len(updated_files)} file(s) to dateModified = {TODAY}:")
for f in sorted(updated_files):
    print(f"  ✓ {f}")
if unchanged_files:
    print(f"\nNo dateModified found in {len(unchanged_files)} file(s) — skipped.")
