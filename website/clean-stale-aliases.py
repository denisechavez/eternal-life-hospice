#!/usr/bin/env python3
"""
clean-stale-aliases.py
----------------------
Removes aliases from city-aliases.json whose target city no longer appears
in the published index of city-data.json.

Also warns about *redundant* aliases — entries whose key already resolves to
the correct city via coverage.js exact-match logic (city name or slug) without
needing the alias entry.  Redundant aliases are printed as warnings but are
NOT removed automatically; an editor must decide whether to keep or drop them.

Usage (from repo root):
    python3 website/clean-stale-aliases.py [--dry-run]

Options:
    --dry-run   Print what would be removed without writing any changes.

Exits 0 when the file is clean (or was successfully cleaned).
Exits 1 if a file cannot be read or parsed.
"""

import json
import os
import re
import sys
import unicodedata

DRY_RUN = "--dry-run" in sys.argv


# ── Normalisation (mirrors coverage.js — keep in sync) ────────────────────────

def normalise(s):
    """Strip diacritics, lowercase, remove punctuation, collapse whitespace."""
    nfd = unicodedata.normalize("NFD", str(s or ""))
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    lower = stripped.lower()
    clean = re.sub(r"[^a-z0-9\s]", "", lower)
    return re.sub(r"\s+", " ", clean).strip()


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

published = [c for c in city_data if c.get("publishStatus") == "published"]
published_cities = {c["city"] for c in published}

# ── Load city-aliases.json ─────────────────────────────────────────────────────

try:
    with open(_alias_file_path, encoding="utf-8") as f:
        alias_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    print(f"ERROR: could not load city-aliases.json — {exc}", file=sys.stderr)
    sys.exit(1)

aliases = alias_data.get("aliases", {})

# ── Find stale aliases ─────────────────────────────────────────────────────────
# A stale alias points to a city that is no longer in the published index.

stale = {key: target for key, target in aliases.items() if target not in published_cities}

# ── Find redundant aliases ─────────────────────────────────────────────────────
# A redundant alias has a key that already resolves to the correct city via
# coverage.js step-1 exact-match logic (city name OR slug), so the alias entry
# adds nothing.  coverage.js matches:
#   (a) normalise(c.city)          — diacritic-stripped city name
#   (b) c.slug.replace(/-/g, " ") — slug-derived name (already ASCII)

redundant = []
for key, target in aliases.items():
    if key in stale:
        continue  # stale aliases are a separate problem; skip overlap
    norm_key = normalise(key)
    by_name = any(normalise(c["city"]) == norm_key and c["city"] == target
                  for c in published)
    by_slug = any(c.get("slug", "").replace("-", " ") == norm_key and c["city"] == target
                  for c in published)
    if by_name or by_slug:
        via = "city name" if by_name else "slug"
        redundant.append((key, target, via))

# ── Report stale aliases ───────────────────────────────────────────────────────

if stale:
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Found {len(stale)} stale alias(es):\n")
    for key, target in stale.items():
        print(f'  "{key}" → "{target}"  (target not in published city-data.json)')

# ── Report redundant aliases (always, before any write) ───────────────────────

if redundant:
    print(f"\n⚠️   Found {len(redundant)} redundant alias(es) "
          f"(key already resolves via exact match — alias not needed):\n")
    for key, target, via in redundant:
        print(f'  ⚠  "{key}" → "{target}"  (resolves via {via} without alias)')
    print(
        "\n    These aliases are harmless but add noise to city-aliases.json.\n"
        "    Remove them manually if the city-data.json entry will not be renamed."
    )

# ── Early exit for dry-run or nothing-to-remove ───────────────────────────────

if not stale:
    if not redundant:
        print(f"✅  city-aliases.json is clean — all {len(aliases)} alias(es) point to "
              f"published cities and none are redundant.")
    sys.exit(0)

if DRY_RUN:
    print(f"\nDry run complete — no changes written.")
    print(f"Run without --dry-run to remove the {len(stale)} stale alias(es).")
    sys.exit(0)

# ── Remove stale entries and rewrite the file ──────────────────────────────────

clean_aliases = {k: v for k, v in aliases.items() if k not in stale}
alias_data["aliases"] = clean_aliases

with open(_alias_file_path, "w", encoding="utf-8") as f:
    json.dump(alias_data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\n✅  Removed {len(stale)} stale alias(es) from city-aliases.json.")
print(f"    Remaining: {len(clean_aliases)} alias(es).")
sys.exit(0)
