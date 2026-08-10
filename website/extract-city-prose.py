#!/usr/bin/env python3
"""
Eternal Life Hospice — City Prose Extractor
-------------------------------------------
Reads prose from existing city HTML pages (hospice-*-ca.html) and writes
the extracted text back into city-data.json as the canonical source.

Run this ONCE after hand-editing HTML files that have not yet been synced
back to city-data.json.  After the extraction, city-data.json is canonical
and build-cities.py can regenerate HTML deterministically.

Usage:
    python3 website/extract-city-prose.py            # update all cities
    python3 website/extract-city-prose.py --slug acton
    python3 website/extract-city-prose.py --dry-run  # print diffs, no writes

Fields extracted from each HTML file:
    atAGlanceSummary     — text of <p class="at-a-glance-summary">
    localIntroduction    — body paragraphs in the intro section (joined with
                           double-newline when there are multiple)
    localNearbyParagraph — the "We also serve…" paragraph (second-to-last in
                           the intro section; last is always the auto-generated
                           nearby-city links which this script skips)
"""

import argparse, json, os, re, sys

BASE     = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE, "city-data.json")
HTML_DIR  = os.path.join(BASE, "elh-preview")


def _strip_tags(html: str) -> str:
    """Remove HTML tags and decode a small set of common entities."""
    text = re.sub(r"<[^>]+>", "", html)
    entities = {
        "&mdash;": "—", "&ndash;": "–", "&rsquo;": "\u2019",
        "&lsquo;": "\u2018", "&rdquo;": "\u201d", "&ldquo;": "\u201c",
        "&amp;": "&", "&nbsp;": " ", "&#8594;": "→",
        "&rsquo;": "'",
    }
    for ent, char in entities.items():
        text = text.replace(ent, char)
    return text.strip()


def extract_prose(html: str) -> dict:
    """
    Extract the three prose fields from a city page.

    Returns a dict with keys:
        atAGlanceSummary, localIntroduction, localNearbyParagraph
    Any field that cannot be found is returned as an empty string.
    """
    result = {}

    # ── at-a-glance summary ───────────────────────────────────────────────────
    m = re.search(
        r'<p class="at-a-glance-summary">(.*?)</p>',
        html, re.S
    )
    result["atAGlanceSummary"] = _strip_tags(m.group(1)) if m else ""

    # ── intro section: all <p> tags inside the "Hospice care at home" section ─
    # The section always has:
    #   P[0..n-3]  — intro paragraphs (1 or 3 paragraphs depending on the city)
    #   P[n-2]     — "We also serve …" localNearbyParagraph
    #   P[n-1]     — "Explore hospice care in …" links (auto-generated; skip)
    m = re.search(
        r'<section class="sec wrap">.*?<h2>Hospice care at home in [^<]+</h2>'
        r'(.*?)</section>',
        html, re.S
    )
    if m:
        paras = re.findall(r'<p>(.*?)</p>', m.group(1), re.S)
        if len(paras) >= 3:
            intro_paras  = paras[:-2]
            nearby_para  = paras[-2]
        elif len(paras) == 2:
            intro_paras  = paras[:1]
            nearby_para  = paras[1]
        else:
            intro_paras  = paras
            nearby_para  = ""

        result["localIntroduction"]    = "\n\n".join(
            _strip_tags(p) for p in intro_paras if p.strip()
        )
        result["localNearbyParagraph"] = _strip_tags(nearby_para)
    else:
        result["localIntroduction"]    = ""
        result["localNearbyParagraph"] = ""

    return result


def slug_from_filename(filename: str) -> str:
    """hospice-thousand-oaks-ca.html  →  thousand-oaks"""
    return re.sub(r"^hospice-|-ca\.html$", "", filename)


def main():
    parser = argparse.ArgumentParser(
        description="Extract city prose from HTML and write back to city-data.json."
    )
    parser.add_argument("--slug", help="Process only this city slug")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would change without writing city-data.json"
    )
    args = parser.parse_args()

    with open(DATA_FILE, encoding="utf-8") as f:
        cities = json.load(f)

    city_index = {c["slug"]: i for i, c in enumerate(cities)}

    updated  = []
    skipped  = []
    no_html  = []

    html_files = [
        fn for fn in os.listdir(HTML_DIR)
        if fn.startswith("hospice-") and fn.endswith("-ca.html")
    ]

    for fn in sorted(html_files):
        slug = slug_from_filename(fn)
        if args.slug and slug != args.slug:
            continue
        if slug not in city_index:
            skipped.append(slug)
            continue

        html_path = os.path.join(HTML_DIR, fn)
        html = open(html_path, encoding="utf-8").read()

        prose = extract_prose(html)
        idx   = city_index[slug]
        city  = cities[idx]

        # Detect which fields actually changed
        changed = {}
        for key, new_val in prose.items():
            if new_val and city.get(key) != new_val:
                changed[key] = (city.get(key, ""), new_val)

        if not changed:
            continue

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"City: {city['city']} ({slug})")
            for key, (old, new) in changed.items():
                print(f"\n  [{key}]")
                print(f"  OLD: {old[:120]}{'…' if len(old)>120 else ''}")
                print(f"  NEW: {new[:120]}{'…' if len(new)>120 else ''}")
        else:
            for key, (_, new_val) in changed.items():
                cities[idx][key] = new_val
            updated.append(slug)
            print(f"  ✓ {slug} — updated {', '.join(changed.keys())}")

    if not args.dry_run and updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cities, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nUpdated city-data.json with prose from {len(updated)} cities.")
    elif args.dry_run:
        print(f"\n[DRY RUN] {len(updated) if not args.dry_run else 'N'} cities would be updated.")
        # Re-count in dry-run mode
        dry_count = 0
        for fn in sorted(html_files):
            slug = slug_from_filename(fn)
            if args.slug and slug != args.slug:
                continue
            if slug not in city_index:
                continue
            html = open(os.path.join(HTML_DIR, fn), encoding="utf-8").read()
            prose = extract_prose(html)
            idx   = city_index[slug]
            city  = cities[idx]
            if any(prose.get(k) and city.get(k) != prose[k] for k in prose):
                dry_count += 1
        print(f"[DRY RUN] {dry_count} cities have prose that differs from city-data.json.")

    if skipped:
        print(f"Skipped (no JSON entry): {', '.join(skipped)}")
    if no_html:
        print(f"Skipped (no HTML file):  {', '.join(no_html)}")


if __name__ == "__main__":
    main()
