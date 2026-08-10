#!/usr/bin/env python3
"""
Eternal Life Hospice — City Prose Extractor
--------------------------------------------
One-time sync utility: reads each hospice-*-ca.html file, extracts the
hand-authored prose paragraphs, and writes them back into city-data.json
so both sources tell the same story.

Fields extracted from each HTML file:
  atAGlanceSummary      — <p class="at-a-glance-summary">...</p>
  localIntroduction     — one or more plain <p> tags in the "Hospice care
                          at home" section (multi-paragraph text joined
                          with \\n\\n, exactly as build-cities.py expects)
  localNearbyParagraph  — the "We also serve …" / "We serve …" paragraph
                          that immediately precedes the auto-generated
                          "Explore hospice care in …" links paragraph

The script never modifies any HTML file.
The auto-generated "Explore hospice care in …" paragraph (produced by
build-cities.py from nearbyCityPages) is skipped — it is not stored in
city-data.json.

Usage:
    python3 website/extract-city-prose.py            # dry-run (shows diff)
    python3 website/extract-city-prose.py --write    # apply changes
    python3 website/extract-city-prose.py --slug thousand-oaks --write
"""

import argparse
import json
import os
import re
import sys

BASE     = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE, "city-data.json")
HTML_DIR  = os.path.join(BASE, "elh-preview")


# ── HTML paragraph extractor ──────────────────────────────────────────────────

def extract_prose(html: str, slug: str, city: str,
                   existing_nearby_para: str = "") -> dict:
    """Return a dict with the three prose fields extracted from the HTML.

    existing_nearby_para: the current localNearbyParagraph value from JSON,
    used as a fallback to recognise nearby paragraphs that don't begin with
    the standard "We [also] serve …" pattern.

    Returns an empty dict if the expected sections are not found.
    """
    result = {}

    # 1. at-a-glance summary
    m = re.search(r'<p class="at-a-glance-summary">(.*?)</p>', html, re.DOTALL)
    if m:
        result["atAGlanceSummary"] = m.group(1).strip()

    # 2. Intro section — everything between the "Hospice care at home" <h2>
    #    and the closing </section> tag that follows it.
    section_pat = (
        r'<h2>Hospice care at home in [^<]+</h2>'   # section heading
        r'(.*?)'                                      # content
        r'</section>'
    )
    m2 = re.search(section_pat, html, re.DOTALL)
    if not m2:
        return result

    section = m2.group(1)

    # Collect every <p> block inside the section.
    # We want full inner HTML (may contain <a> tags for the links paragraph).
    raw_paras = re.findall(r'<p>(.*?)</p>', section, re.DOTALL)
    paras = [p.strip() for p in raw_paras if p.strip()]

    if not paras:
        return result

    # 3. Drop the auto-generated "Explore hospice care in …" paragraph
    #    (it starts with "Explore hospice care in" and contains <a> tags).
    if paras and paras[-1].startswith("Explore hospice care in"):
        paras = paras[:-1]

    if not paras:
        return result

    # 4. Identify the localNearbyParagraph.
    #    It is always the paragraph immediately before the "Explore" links
    #    paragraph.  Two detection strategies (applied in order):
    #      a) Classic pattern: starts with "We [also] serve …"
    #      b) The paragraph already exists verbatim as localNearbyParagraph
    #         in the JSON entry passed via existing_nearby_para — meaning a
    #         hand-authored nearby sentence that doesn't use the standard
    #         "We serve …" opener should still be recognised and excluded
    #         from localIntroduction to avoid duplication.
    nearby_para = ""
    existing_nearby = existing_nearby_para or ""
    if paras:
        last = paras[-1]
        if re.match(r'^We (?:also )?serve\b', last):
            nearby_para = last
            paras = paras[:-1]
        elif existing_nearby and last == existing_nearby:
            # The last paragraph IS the known nearby paragraph — don't fold
            # it into localIntroduction.
            nearby_para = last
            paras = paras[:-1]

    if nearby_para:
        result["localNearbyParagraph"] = nearby_para

    # 5. Everything remaining is localIntroduction (joined with double-newline).
    if paras:
        result["localIntroduction"] = "\n\n".join(paras)

    return result


# ── Diff helper ───────────────────────────────────────────────────────────────

def _short(text: str, n: int = 100) -> str:
    return text[:n] + "…" if len(text) > n else text


def main():
    parser = argparse.ArgumentParser(
        description="Extract hand-authored HTML prose back into city-data.json."
    )
    parser.add_argument("--write", action="store_true",
                        help="Apply changes to city-data.json (default: dry-run)")
    parser.add_argument("--slug", help="Process only this city slug")
    args = parser.parse_args()

    with open(DATA_FILE, encoding="utf-8") as f:
        cities = json.load(f)

    city_map = {c["slug"]: i for i, c in enumerate(cities)}

    changed = 0
    skipped_no_html = 0
    skipped_no_match = 0

    for slug, idx in sorted(city_map.items()):
        if args.slug and slug != args.slug:
            continue

        c = cities[idx]
        html_path = os.path.join(HTML_DIR, f"hospice-{slug}-ca.html")

        if not os.path.exists(html_path):
            skipped_no_html += 1
            continue

        with open(html_path, encoding="utf-8") as f:
            html = f.read()

        extracted = extract_prose(html, slug, c.get("city", slug),
                                   existing_nearby_para=c.get("localNearbyParagraph", ""))
        if not extracted:
            print(f"  WARN: no prose extracted for {slug}")
            skipped_no_match += 1
            continue

        # Compare extracted values against JSON
        fields = ["atAGlanceSummary", "localIntroduction", "localNearbyParagraph"]
        city_changed = False

        for field in fields:
            html_val = extracted.get(field)
            json_val = c.get(field, "")

            if html_val is None:
                # Field not found in HTML — leave JSON as-is
                continue

            if html_val != json_val:
                city_changed = True
                print(f"\n  {slug}  [{field}]")
                print(f"    JSON: {_short(json_val)}")
                print(f"    HTML: {_short(html_val)}")

                if args.write:
                    cities[idx][field] = html_val

        if city_changed:
            changed += 1

    print(f"\n{'─'*60}")
    print(f"Cities with prose differences: {changed}")
    print(f"Cities with no HTML file:      {skipped_no_html}")
    if skipped_no_match:
        print(f"Cities with extraction errors: {skipped_no_match}")

    if changed == 0:
        print("All city entries already match their HTML files. Nothing to do.")
        return

    if not args.write:
        print("\nDry-run — no files written. Re-run with --write to apply changes.")
        return

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nWrote updated city-data.json ({changed} city entries updated).")


if __name__ == "__main__":
    main()
