#!/usr/bin/env python3
"""Block Westlake Village Hospice identifiers from Eternal public files."""

from pathlib import Path
import sys
from footer_contact import public_html as update_footer_contact


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
FORBIDDEN = {
    "5753774355151396017": "Westlake Google Maps CID",
    "ChIJrRDxvAsl6IARsRyNjEqD2U8": "Westlake Google place ID",
    "westlakevillagehospiceinc.com": "Westlake website",
    "818-791-0611": "Westlake phone",
    "818.791.0611": "Westlake phone",
    "(818) 791-0611": "Westlake phone",
    "805-870-0103": "Westlake phone",
    "805.870.0103": "Westlake phone",
    "(805) 870-0103": "Westlake phone",
}
TEXT_SUFFIXES = {".html", ".js", ".json", ".xml", ".txt"}
WESTLAKE_MAPS_URL = "https://maps.google.com/?cid=5753774355151396017"
ETERNAL_MAPS_URL = "https://maps.google.com/?cid=9771388271577679785"
RETIRED_ETERNAL_PLACE_URL = (
    "https://www.google.com/maps/place/?q=place_id:ChIJ8TnEjG4l6IARTsNF_xMDyyI"
)
PRIMARY_FOOTER_PHONE = (
    '<a class="fc-line no-swap" href="tel:18059537273">'
)
TRACKED_FOOTER_PHONE = (
    '<a class="fc-line fc-direct" href="tel:18054101151">'
)


def fix_public_files() -> None:
    """Remove known Westlake links and restore the verified Eternal target."""
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        updated = text.replace(WESTLAKE_MAPS_URL, "#")
        updated = updated.replace(RETIRED_ETERNAL_PLACE_URL, ETERNAL_MAPS_URL)
        updated = updated.replace(
            '<a hidden class="review-trust-link" data-review-link href="#"',
            f'<a class="review-trust-link" data-review-link href="{ETERNAL_MAPS_URL}"',
        )
        updated = updated.replace(
            '<a hidden class="map-hq" href="#"',
            f'<a class="map-hq" href="{ETERNAL_MAPS_URL}"',
        )
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def main() -> int:
    if "--fix" in sys.argv[1:]:
        fix_public_files()

    findings = []
    for path in sorted(PUBLIC.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".html" and path.parent == PUBLIC / "blog":
            text = update_footer_contact(text)
        if path.suffix.lower() == ".html" and 'id="site-footer"' in text:
            if PRIMARY_FOOTER_PHONE not in text or "<span>805.953.7273</span>" not in text:
                findings.append(
                    f"{path.relative_to(ROOT)}: protected primary footer phone missing"
                )
            if TRACKED_FOOTER_PHONE not in text or "<span>805.410.1151 · Main</span>" not in text:
                findings.append(
                    f"{path.relative_to(ROOT)}: WhatConverts footer phone missing"
                )
            if PRIMARY_FOOTER_PHONE in text and TRACKED_FOOTER_PHONE in text:
                if text.index(TRACKED_FOOTER_PHONE) > text.index(PRIMARY_FOOTER_PHONE):
                    findings.append(f"{path.relative_to(ROOT)}: Main tracking number must be first")
        for token, label in FORBIDDEN.items():
            if token.lower() in text.lower():
                findings.append(f"{path.relative_to(ROOT)}: {label} ({token})")

    if findings:
        print("Agency-separation check failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("SENTINEL: check-agency-separation.py OK")
    print("No Westlake GBP identifiers found in Eternal public files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())