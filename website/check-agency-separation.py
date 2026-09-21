#!/usr/bin/env python3
"""Block Westlake Village Hospice profile identifiers from Eternal public files."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
FORBIDDEN = {
    "9771388271577679785": "former Google Maps CID now assigned to Westlake",
    "ChIJteBBU6vdfEcRqUfOqdzxmoc": "former Google place ID",
    "westlakevillagehospiceinc.com": "Westlake website",
    "805-870-0103": "Westlake phone",
    "805.870.0103": "Westlake phone",
    "(805) 870-0103": "Westlake phone",
}
TEXT_SUFFIXES = {".html", ".js", ".json", ".xml", ".txt"}
FORMER_MAPS_URL = "https://maps.google.com/?cid=9771388271577679785"


def fix_public_files() -> None:
    """Remove known cross-agency links while the Eternal profile is unverified."""
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        updated = text.replace(FORMER_MAPS_URL, "#")
        updated = updated.replace(
            '<a class="review-trust-link"',
            '<a hidden class="review-trust-link"',
        )
        updated = updated.replace(
            '<a class="map-hq"',
            '<a hidden class="map-hq"',
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