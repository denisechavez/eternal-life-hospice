#!/usr/bin/env python3
"""
ELH Header Parity Audit
========================
Scans every HTML page in elh-preview and classifies its header against
the canonical homepage implementation.

Usage:
    python3 website/check-header-parity.py

Exit code 0 = all standard pages pass.  Non-zero = failures found.
"""

import os, sys

ROOT = os.path.join(os.path.dirname(__file__), "elh-preview")

# ── Approved six-item navigation labels ────────────────────────────────────
NAV_LABELS = [
    "Hospice Care", "Services", "Resources",
    "Locations", "For Professionals", "About",
]

# ── Pages that intentionally omit the standard header ─────────────────────
INTENTIONAL_EXCEPTIONS = {
    # Digital contact / vCard pages — minimal by design
    "card-aleksandra-dubina.html": "digital contact card — no nav intentional",
    "card-denise-chavez.html":     "digital contact card — no nav intentional",
    # Referral tool — stripped header (logo + phone only), no full nav
    "referral-card.html":          "referral tool — stripped header intentional",
    # Full-page interactive booklet — own toolbar with Back to site
    "family-guide.html":           "flipbook UI — own toolbar, no standard nav",
    "media-kit.html":              "flipbook UI — own toolbar, no standard nav",
    # Redirect stubs — noindex, meta-refresh, no UI needed
    "resources/index.html":        "redirect stub → /resources.html",
    "blog/index.html":             "redirect stub → /blog.html",
    "care-brief/index.html":       "redirect stub → /care-brief.html",
    # Care brief article — has header HTML but hides it for clean reader mode
    "care-brief/hospice-is-part-of-life-a-continuation-of-care.html":
        "reader view — #hdr hidden via CSS intentionally",
    # Homepage — IS the canonical; uses inline JS not header.js file
    "index.html":                  "canonical homepage — inline header JS, not file include",
    # Internal / utility pages not in public nav
    "sitemap.html":                "utility page",
    "assets/img/amethyst-tmp/gallery.html": "internal asset gallery",
    # Social graphics — not public pages
    "assets/social/index.html":             "social graphic — not a public page",
    "assets/social/amethyst-duotone.html":  "social graphic",
    "assets/social/bowl-wash.html":         "social graphic",
    "assets/social/elh-social-brand-brief.html": "social graphic",
    "assets/social/eye-split.html":         "social graphic",
    "assets/social/mosaic-m1.html":         "social graphic",
    "assets/social/mosaic-m3.html":         "social graphic",
    "assets/social/mosaic-m5.html":         "social graphic",
    "assets/social/mosaic-m7.html":         "social graphic",
    "assets/social/mosaic-m9.html":         "social graphic",
    "assets/social/mosaic-pinterest.html":  "social graphic",
    "assets/social/pen-graphic-pop.html":   "social graphic",
    "assets/social/stillness-card.html":    "social graphic",
}

# ── Canonical checks ───────────────────────────────────────────────────────
REQUIRED = {
    "header_id":   ('id="hdr"',          "header element uses id=hdr"),
    "menu_btn":    ('class="menu-btn"',   "hamburger button present"),
    "search_btn":  ('class="search-btn"', "search button present"),
    "request_care":('Request Care',       "Request Care CTA present"),
    "logo_cream":  ('elh-logo-h2-cream',  "cream logo present"),
    "header_js":   ('header.js',          "header.js included"),
    "no_stale_url":('/aleksandradubina',  "stale /aleksandradubina URL"),  # must NOT appear
}

results = {"pass": [], "fail": [], "exception": []}
failures = []
stale_exceptions = []   # exception keys whose file is missing from disk
redundant_exceptions = []  # exception keys whose file now passes all parity checks

for dirpath, dirs, files in os.walk(ROOT):
    dirs.sort()
    for fn in sorted(files):
        if not fn.endswith(".html"):
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        rel = rel.replace("\\", "/")

        if rel in INTENTIONAL_EXCEPTIONS:
            results["exception"].append((rel, INTENTIONAL_EXCEPTIONS[rel]))
            continue

        html = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
        page_fails = []

        # Standard presence checks
        for key, (token, label) in REQUIRED.items():
            if key == "no_stale_url":
                if token in html:
                    page_fails.append(f"STALE URL: {token} found")
            else:
                if token not in html:
                    page_fails.append(f"MISSING: {label}")

        # All six nav labels must appear
        for label in NAV_LABELS:
            if label not in html:
                page_fails.append(f"MISSING NAV: {label}")

        if page_fails:
            results["fail"].append(rel)
            failures.append((rel, page_fails))
        else:
            results["pass"].append(rel)

# ── Staleness scan: verify every exception entry is still valid ────────────
for exc_rel, exc_reason in INTENTIONAL_EXCEPTIONS.items():
    exc_path = os.path.join(ROOT, exc_rel.replace("/", os.sep))
    if not os.path.exists(exc_path):
        stale_exceptions.append((exc_rel, exc_reason))
        continue
    # File exists — check whether it now passes all parity checks
    html = open(exc_path, encoding="utf-8", errors="replace").read()
    page_fails = []
    for key, (token, label) in REQUIRED.items():
        if key == "no_stale_url":
            if token in html:
                page_fails.append(f"STALE URL: {token} found")
        else:
            if token not in html:
                page_fails.append(f"MISSING: {label}")
    for nav_label in NAV_LABELS:
        if nav_label not in html:
            page_fails.append(f"MISSING NAV: {nav_label}")
    if not page_fails:
        redundant_exceptions.append((exc_rel, exc_reason))

# ── Report ─────────────────────────────────────────────────────────────────
total = len(results["pass"]) + len(results["fail"]) + len(results["exception"])
print(f"\nELH Header Parity Audit — {total} pages scanned")
print(f"  ✅  Pass:       {len(results['pass'])}")
print(f"  ❌  Fail:       {len(results['fail'])}")
print(f"  ⚠️   Exceptions: {len(results['exception'])}")
if stale_exceptions:
    print(f"  🚨  Stale exceptions (file missing):   {len(stale_exceptions)}")
if redundant_exceptions:
    print(f"  🔔  Redundant exceptions (now passes): {len(redundant_exceptions)}")
print()

if failures:
    print("── FAILURES ─────────────────────────────────────────────────────")
    for rel, errs in failures:
        print(f"\n  {rel}")
        for e in errs:
            print(f"    • {e}")
    print()

if stale_exceptions:
    print("── STALE EXCEPTIONS (file no longer exists on disk) ─────────────")
    for rel, reason in stale_exceptions:
        print(f"  🚨  {rel}")
        print(f"       was: {reason}")
    print()

if redundant_exceptions:
    print("── REDUNDANT EXCEPTIONS (file now passes all parity checks) ─────")
    for rel, reason in redundant_exceptions:
        print(f"  🔔  {rel}")
        print(f"       was: {reason}")
        print(f"       → consider removing this entry from INTENTIONAL_EXCEPTIONS")
    print()

print("── INTENTIONAL EXCEPTIONS ───────────────────────────────────────────")
for rel, reason in results["exception"]:
    print(f"  ⚠️  {rel}")
    print(f"       {reason}")

exit_code = 0
if failures:
    print(f"\n❌  {len(failures)} page(s) failed — fix before deploying.\n")
    exit_code = 1
if stale_exceptions:
    print(f"\n🚨  {len(stale_exceptions)} stale exception(s) — remove or update INTENTIONAL_EXCEPTIONS.\n")
    exit_code = 1
if not failures and not stale_exceptions:
    print(f"\n✅  All standard pages pass header parity check.\n")
if redundant_exceptions:
    print(f"🔔  {len(redundant_exceptions)} exception(s) may be redundant — review INTENTIONAL_EXCEPTIONS.\n")
sys.exit(exit_code)
