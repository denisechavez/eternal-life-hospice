#!/usr/bin/env python3
"""
ELH Footer Parity Check
------------------------
Two-tier check:

  STATIC pages (non-city)  — exact equality against FOOTER_HTML in fragments.py.
  CITY pages (hospice-*-ca.html) — column-heading + key-token check, because
      their Locations column is county-contextual (managed by build-cities.py ->
      make_footer()) and legitimately differs between pages.

Usage:
    python3 website/check-footer-parity.py

Exit 0 = all standard pages pass.  Non-zero = failures found.

WORKFLOW -- when the footer changes:
  1. Edit website/fragments.py -> FOOTER_HTML
  2. python3 website/sync-footer.py           (patches static pages)
  3. python3 website/build-cities.py --force  (regenerates city pages)
  4. This script runs in the pre-deploy chain -- blocks deploy on any divergence.
"""

import os, re, sys

# -- Import canonical footer ---------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fragments import FOOTER_HTML

CANONICAL = FOOTER_HTML.strip()

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elh-preview")

FOOTER_RE    = re.compile(r'<footer id="site-footer">.*?</footer>', re.DOTALL)
CITY_PAGE_RE = re.compile(r'^hospice-.+-ca\.html$')
COUNTY_HUB = "hospice-ventura-and-los-angeles-county-ca.html"
STALE_HEADING_SELECTOR_RE = re.compile(r'(?:#site-footer\s+)?\.foot-col\s+h4\b')

# -- Required tokens present in EVERY footer (static and city) ----------------
# These headings and links are invariant across all page types.
CITY_TOKENS = [
    ('<h2>Hospice Care</h2>',      "Hospice Care column heading"),
    ('<h2>Services</h2>',          "Services column heading"),
    ('<h2>Resources</h2>',         "Resources column heading"),
    ('<h2>Service Areas</h2>',     "Service Areas column heading"),
    ('<h2>About</h2>',             "About column heading"),
    ('<h2>Contact</h2>',           "Contact column heading"),
    ('When Is It Time?',           "Hospice Care -- When Is It Time? link"),
    ('County Coverage',            "Service Areas -- County Coverage link"),
    ('fc-direct',                  "Contact -- Direct phone line (fc-direct)"),
    ('foot-disclaimer',            "foot-disclaimer block present"),
]

# -- Pages whose footer intentionally deviates from canonical -----------------
INTENTIONAL_EXCEPTIONS = {
    "sitemap.html":                              "custom layout -- not a standard foot-col footer",
    "card-aleksandra-dubina.html":               "digital contact card -- no standard footer",
    "card-denise-chavez.html":                   "digital contact card -- no standard footer",
    "family-guide.html":                         "flipbook UI -- own chrome, no standard footer",
    "media-kit.html":                            "flipbook UI -- own chrome, no standard footer",
    "referral-card.html":                        "referral tool -- stripped UI, no standard footer",
    "blog/index.html":                           "redirect stub -- no UI needed",
    "care-brief/index.html":                     "redirect stub -- no UI needed",
    # Social graphics and internal asset pages (not public pages)
    "assets/img/amethyst-tmp/gallery.html":      "internal asset gallery",
    "assets/social/index.html":                  "social graphic -- not a public page",
    "assets/social/amethyst-duotone.html":       "social graphic",
    "assets/social/bowl-wash.html":              "social graphic",
    "assets/social/elh-social-brand-brief.html": "social graphic",
    "assets/social/eye-split.html":              "social graphic",
    "assets/social/mosaic-m1.html":              "social graphic",
    "assets/social/mosaic-m3.html":              "social graphic",
    "assets/social/mosaic-m5.html":              "social graphic",
    "assets/social/mosaic-m7.html":              "social graphic",
    "assets/social/mosaic-m9.html":              "social graphic",
    "assets/social/mosaic-pinterest.html":       "social graphic",
    "assets/social/pen-graphic-pop.html":        "social graphic",
    "assets/social/stillness-card.html":         "social graphic",
}

# -- Sentinel self-test -------------------------------------------------------
# Build a fake footer by corrupting a link label guaranteed to be in CANONICAL.
# The exact-equality check on a static page must catch this; if it doesn't,
# the guard is broken and the sentinel exits 1 rather than silently passing.
assert 'When Is It Time?' in CANONICAL, "Sentinel anchor text missing from CANONICAL"
_bad = CANONICAL.replace('When Is It Time?', 'When Is It Time -- stale', 1)
assert _bad != CANONICAL, "Sentinel mutation had no effect"
assert STALE_HEADING_SELECTOR_RE.search(
    "<style>#site-footer .foot-col h4{font-size:12px}</style>"
), "Sentinel stale-heading selector was not detected"
_html = f'<html><body>{_bad}</body></html>'
_m = FOOTER_RE.search(_html)
if _m and _m.group(0).strip() == CANONICAL:
    print("SELF-TEST FAILED: exact-equality guard did not detect a mutated footer")
    sys.exit(1)
print("SENTINEL: check-footer-parity.py self-test OK")

# -- Scan ---------------------------------------------------------------------
static_pass = []
static_fail = []
city_pass   = []
city_fail   = []
exceptions  = []
stale_exceptions  = []
static_failures   = []   # (rel, [diff lines])
city_failures     = []   # (rel, [missing tokens])
semantic_failures = []   # public/custom footers that still use h4 headings

for dirpath, dirs, files in os.walk(ROOT):
    dirs.sort()
    for fn in sorted(files):
        if not fn.endswith(".html"):
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace("\\", "/")
        html = open(os.path.join(dirpath, fn), encoding="utf-8",
                    errors="replace").read()
        footer_match = FOOTER_RE.search(html)
        if footer_match and "<h4" in footer_match.group(0).lower():
            semantic_failures.append(
                (rel, "Footer category headings must use h2, not h4")
            )
        if STALE_HEADING_SELECTOR_RE.search(html):
            semantic_failures.append(
                (rel, "Stale .foot-col h4 CSS selector; footer headings are h2")
            )

        if rel in INTENTIONAL_EXCEPTIONS:
            exceptions.append((rel, INTENTIONAL_EXCEPTIONS[rel]))
            continue

        m = FOOTER_RE.search(html)

        is_city = bool(CITY_PAGE_RE.match(fn) and fn != COUNTY_HUB)

        if is_city:
            # City pages: token check only (Locations column varies by county)
            if not m:
                city_fail.append(rel)
                city_failures.append((rel, ['MISSING: <footer id="site-footer"> element not found']))
                continue
            footer = m.group(0)
            missing = [label for tok, label in CITY_TOKENS if tok not in footer]
            if missing:
                city_fail.append(rel)
                city_failures.append((rel, [f"Missing: {t}" for t in missing]))
            else:
                city_pass.append(rel)
        else:
            # Static pages: exact equality against FOOTER_HTML
            if not m:
                static_fail.append(rel)
                static_failures.append((rel, ['MISSING: <footer id="site-footer"> element not found']))
                continue
            page_footer = m.group(0).strip()
            if page_footer != CANONICAL:
                c_lines = CANONICAL.splitlines()
                p_lines = page_footer.splitlines()
                diffs = []
                for i, (cl, pl) in enumerate(zip(c_lines, p_lines)):
                    if cl != pl:
                        diffs.append(
                            f"line {i+1} differs:\n"
                            f"    canonical: {cl[:120]!r}\n"
                            f"    page:      {pl[:120]!r}"
                        )
                        if len(diffs) >= 3:
                            break
                if len(c_lines) != len(p_lines):
                    diffs.append(
                        f"length mismatch: canonical {len(c_lines)} lines, "
                        f"page {len(p_lines)} lines"
                    )
                static_fail.append(rel)
                static_failures.append((rel, diffs or ["footer content differs from canonical"]))
            else:
                static_pass.append(rel)

# -- Stale exception entries --------------------------------------------------
for rel in INTENTIONAL_EXCEPTIONS:
    if not os.path.exists(os.path.join(ROOT, rel)):
        stale_exceptions.append(rel)

# -- Report -------------------------------------------------------------------
total_pass = len(static_pass) + len(city_pass)
total_fail = len(static_fail) + len(city_fail)
total_exc  = len(exceptions)

print(
    f"\nELH Footer Parity -- "
    f"{len(static_pass)} static pass, {len(static_fail)} static fail | "
    f"{len(city_pass)} city pass, {len(city_fail)} city fail | "
    f"{total_exc} exception"
)
print("-" * 64)

if static_failures:
    print("\nSTATIC PAGE FAILURES (exact equality vs FOOTER_HTML):")
    for rel, page_fails in static_failures:
        print(f"  x  {rel}")
        for f in page_fails:
            print(f"       {f}")

if city_failures:
    print("\nCITY PAGE FAILURES (missing required tokens):")
    for rel, page_fails in city_failures:
        print(f"  x  {rel}")
        for f in page_fails:
            print(f"       {f}")

if semantic_failures:
    print("\nFOOTER SEMANTIC FAILURES:")
    for rel, failure in semantic_failures:
        print(f"  x  {rel}: {failure}")

if stale_exceptions:
    print("\nSTALE EXCEPTIONS (file deleted but still listed):")
    for rel in stale_exceptions:
        print(f"  !  {rel}")

print()

if total_fail or semantic_failures:
    print("=" * 64)
    print("FAILED -- footer parity check did not pass.")
    if static_fail:
        print("  Static pages diverge from FOOTER_HTML in fragments.py.")
        print("  Fix:  python3 website/sync-footer.py")
    if city_fail:
        print("  City pages are missing required footer tokens.")
        print("  Fix:  python3 website/build-cities.py --force")
    if semantic_failures:
        print("  Footer category markup/styles still reference h4.")
    print("=" * 64)
    sys.exit(1)

if stale_exceptions:
    print("! Stale exception entries -- remove from INTENTIONAL_EXCEPTIONS.")
    sys.exit(1)

print("=" * 64)
print(f"OK  All {total_pass} standard pages pass footer parity check.")
print("=" * 64)
sys.exit(0)
