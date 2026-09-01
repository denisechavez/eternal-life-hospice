#!/usr/bin/env python3
"""
website/sync-footer.py  —  Eternal Life Hospice
================================================
Patches the canonical footer into every standard STATIC HTML page in
elh-preview/.  City pages (hospice-*-ca.html) are excluded because they carry
a county-contextual Locations column managed by build-cities.py → make_footer().

Usage (from repo root):
    python3 website/sync-footer.py           # patch all eligible pages
    python3 website/sync-footer.py --dry-run # show what would change without writing

WORKFLOW — when the footer changes:
  1. Edit website/fragments.py → FOOTER_HTML
  2. python3 website/sync-footer.py               (patches static/non-city pages)
  3. python3 website/build-cities.py --force      (regenerates city pages via make_footer())
  4. python3 website/check-footer-parity.py       (CI gate — fails if anything diverges)

Exit 0 on success, 1 if any file could not be patched due to a regex mismatch.
"""

import os, re, sys, argparse

# ── Import canonical footer ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fragments import FOOTER_HTML

# ── Configuration ─────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elh-preview")

# City pages are managed by build-cities.py → make_footer(); never patch here.
CITY_PAGE_RE = re.compile(r'^hospice-.+-ca\.html$')
COUNTY_HUB = "hospice-ventura-and-los-angeles-county-ca.html"

# Pages whose footer intentionally differs from the canonical — do not patch.
EXCEPTIONS = {
    # Digital contact / vCard — minimal pages, no standard footer
    "card-aleksandra-dubina.html",
    "card-denise-chavez.html",
    # Redirect stubs — noindex, meta-refresh only, no UI
    "resources/index.html",
    "blog/index.html",
}

# Public custom-layout pages that should receive the canonical footer even when
# they did not previously contain a footer element.
INSERT_IF_MISSING = {"family-guide.html"}

# Sub-directories whose files are never standard pages
SKIP_DIRS = {"assets"}

# ── Regex ─────────────────────────────────────────────────────────────────────
FOOTER_RE = re.compile(r'<footer id="site-footer">.*?</footer>', re.DOTALL)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be changed without writing files")
    args = parser.parse_args()

    updated, already_ok, skipped, no_footer, errors = [], [], [], [], []

    for dirpath, dirs, files in os.walk(OUT_DIR):
        # Prune excluded subdirectory trees
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)

        for fn in sorted(files):
            if not fn.endswith(".html"):
                continue

            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, OUT_DIR).replace("\\", "/")

            # Skip city pages — managed by build-cities.py → make_footer()
            if CITY_PAGE_RE.match(fn) and fn != COUNTY_HUB:
                skipped.append(rel)
                continue

            if rel in EXCEPTIONS:
                skipped.append(rel)
                continue

            try:
                html = open(abs_path, encoding="utf-8").read()
            except OSError as e:
                errors.append((rel, str(e)))
                continue

            if not FOOTER_RE.search(html):
                if rel in INSERT_IF_MISSING and "</body>" in html:
                    new_html = html.replace("</body>", FOOTER_HTML + "\n</body>", 1)
                else:
                    no_footer.append(rel)
                    continue
            else:
                new_html = FOOTER_RE.sub(FOOTER_HTML, html, count=1)

            if new_html == html:
                already_ok.append(rel)
            else:
                if not args.dry_run:
                    open(abs_path, "w", encoding="utf-8").write(new_html)
                updated.append(rel)

    # ── Report ────────────────────────────────────────────────────────────────
    tag = "[DRY-RUN] " if args.dry_run else ""
    verb = "Would update" if args.dry_run else "Updated"

    print(f"\n{tag}sync-footer.py results")
    print("─" * 56)
    if updated:
        print(f"  {verb}: {len(updated)} file(s)")
        for f in updated:
            print(f"    ✓  {f}")
    if already_ok:
        print(f"  Already canonical: {len(already_ok)} file(s)")
    if skipped:
        print(f"  Skipped (city pages + exceptions): {len(skipped)} file(s)")
    if no_footer:
        print(f"  No <footer> block found (skipped): {len(no_footer)} file(s)")
        for f in no_footer:
            print(f"    ⚠  {f}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for f, e in errors:
            print(f"    ✗  {f}: {e}")
    print("─" * 56)

    if errors:
        sys.exit(1)

    total = len(updated) + len(already_ok) + len(skipped)
    print(f"  Done. {total} pages processed; {len(updated)} {'would be ' if args.dry_run else ''}updated.\n")


if __name__ == "__main__":
    main()
