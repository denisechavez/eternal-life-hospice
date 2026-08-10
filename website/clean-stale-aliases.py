#!/usr/bin/env python3
"""
clean-stale-aliases.py
----------------------
Removes aliases from city-aliases.json whose target city no longer appears
in the published index of city-data.json.

Usage (from repo root):
    python3 website/clean-stale-aliases.py [--dry-run]

Options:
    --dry-run   Print what would be removed without writing any changes.

Exits 0 when the file is clean (or was successfully cleaned).
Exits 1 if a file cannot be read or parsed.
"""

import json
import os
import sys

DRY_RUN = "--dry-run" in sys.argv

_dir = os.path.dirname(__file__)
_city_data_path  = os.path.join(_dir, "city-data.json")
_alias_file_path = os.path.join(_dir, "city-aliases.json")

# ── Load city-data.json ────────────────────────────────────────────────────────

try:
    with open(_city_data_path, encoding="utf-8") as f:
        city_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    print(f"ERROR: could not load city-data.json — {exc}", file=sys.stderr)
    sys.exit(1)

published_cities = {c["city"] for c in city_data if c.get("publishStatus") == "published"}

# ── Load city-aliases.json ─────────────────────────────────────────────────────

try:
    with open(_alias_file_path, encoding="utf-8") as f:
        alias_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    print(f"ERROR: could not load city-aliases.json — {exc}", file=sys.stderr)
    sys.exit(1)

aliases = alias_data.get("aliases", {})

# ── Find stale aliases ─────────────────────────────────────────────────────────

stale = {key: target for key, target in aliases.items() if target not in published_cities}

if not stale:
    print(f"✅  city-aliases.json is clean — all {len(aliases)} alias(es) point to "
          f"published cities.")
    sys.exit(0)

# ── Report and (optionally) remove ────────────────────────────────────────────

print(f"{'[DRY RUN] ' if DRY_RUN else ''}Found {len(stale)} stale alias(es):\n")
for key, target in stale.items():
    print(f'  "{key}" → "{target}"  (target not in published city-data.json)')

if DRY_RUN:
    print(f"\nDry run complete — no changes written.")
    print(f"Run without --dry-run to remove these aliases.")
    sys.exit(0)

# Remove stale entries and rewrite the file
clean_aliases = {k: v for k, v in aliases.items() if k not in stale}
alias_data["aliases"] = clean_aliases

with open(_alias_file_path, "w", encoding="utf-8") as f:
    json.dump(alias_data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\n✅  Removed {len(stale)} stale alias(es) from city-aliases.json.")
print(f"    Remaining: {len(clean_aliases)} alias(es).")
sys.exit(0)
