#!/usr/bin/env python3
"""
Regression guard: city-page generator must not emit render-blocking scripts
===========================================================================
Renders ALL published city pages in-memory and runs four groups of checks:

  [1] No external <script src=…> in <head> without defer or async
  [2] Third-party CDN URLs (UserWay, WhatConverts) are NOT static bare src=
       attributes — they must only appear inside the dynamic loaders
  [3] Both deferred-loader patterns are present somewhere in the HTML
  [4] Mutation self-tests: guard correctly rejects three known-bad templates

Run from repo root:
    python3 website/check-city-scripts.py

Exits 0 on success, 1 on any failure.
Wire this into CI / deploy validation so a future template edit that
accidentally re-introduces blocking scripts is caught before it ships.
"""

import importlib.util
import json
import os
import re
import sys

# ── Load build-cities as a module (handles the hyphenated filename) ────────────

_spec = importlib.util.spec_from_file_location(
    "build_cities",
    os.path.join(os.path.dirname(__file__), "build-cities.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# ── HTML-inspection helpers ───────────────────────────────────────────────────

def extract_head(html):
    """Return the raw content of the first <head>…</head> block."""
    m = re.search(r'<head\b[^>]*>(.*?)</head>', html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ''


def iter_script_attrs(html_fragment):
    """Yield the attribute string for every <script …> opening tag."""
    yield from (m.group(1) for m in
                re.finditer(r'<script\b([^>]*)>', html_fragment, re.IGNORECASE))


def is_ld_json(attrs):
    return bool(re.search(
        r'type\s*=\s*["\']application/ld\+json["\']', attrs, re.IGNORECASE))


def has_src(attrs):
    return bool(re.search(r'\bsrc\s*=', attrs, re.IGNORECASE))


def has_defer_or_async(attrs):
    return bool(re.search(r'\b(defer|async)\b', attrs, re.IGNORECASE))


def src_value(attrs):
    m = re.search(r'src\s*=\s*["\']([^"\']+)["\']', attrs, re.IGNORECASE)
    return m.group(1) if m else ''


def find_city_hero_preload(head_html, slug):
    """Return the first <link> tag that is rel=preload as=image for *slug*'s city hero.

    Searches each <link> tag as a unit so all required attributes must appear
    on the same element — a decoy WebP link elsewhere in <head> cannot satisfy
    the assertions that use this helper.
    """
    for tag in re.findall(r'<link\b[^>]*>', head_html, re.IGNORECASE):
        if (re.search(r'\brel\s*=\s*["\']preload["\']', tag, re.IGNORECASE) and
                re.search(r'\bas\s*=\s*["\']image["\']', tag, re.IGNORECASE) and
                re.search(
                    r'href\s*=\s*["\']assets/img/city/' + re.escape(slug),
                    tag, re.IGNORECASE)):
            return tag
    return None


# CDN substrings that must ONLY appear dynamically inside deferred loaders,
# never as a static bare <script src=…> attribute.
FORBIDDEN_BARE_SRC_SUBSTRINGS = [
    'cdn.userway.org/widget.js',
    'ksrndkehqnwntyxlhgto.com',   # WhatConverts CDN domain
]

# Patterns that MUST appear somewhere in the full rendered HTML
# (belt-and-suspenders: ensures the deferred loaders are actually present).
REQUIRED_PATTERNS = [
    ("requestIdleCallback",
     "UserWay widget deferred via requestIdleCallback — must never revert to "
     "inline/DOMContentLoaded"),
    ("window.addEventListener('load'",
     "WhatConverts tracker deferred via window load event — must never revert "
     "to inline async"),
]


# ── Core check logic (reused by both the live check and mutation self-tests) ──

def collect_errors(html):
    """
    Run all checks against *html* and return a list of error strings.
    Empty list → all checks passed.
    """
    errs = []
    head = extract_head(html)

    # [1] External scripts in <head> must carry defer or async
    for attrs in iter_script_attrs(head):
        if is_ld_json(attrs):
            continue          # structured-data scripts are exempt
        if not has_src(attrs):
            continue          # inline scripts have no network request to defer
        src = src_value(attrs)
        if not has_defer_or_async(attrs):
            errs.append(
                f"blocking-external-script: src={src!r} in <head> has neither "
                f"defer nor async"
            )

    # [2] CDN loader URLs must not appear as bare static src= attributes
    for substring in FORBIDDEN_BARE_SRC_SUBSTRINGS:
        pat = re.compile(
            r'<script\b[^>]*\bsrc\s*=\s*["\'][^"\']*' + re.escape(substring),
            re.IGNORECASE,
        )
        if pat.search(head):
            errs.append(
                f"bare-cdn-src: {substring!r} appears as a static <script src= "
                f"in <head> — must be dynamically injected inside a deferred loader"
            )

    # [3] Deferred-loader patterns must be present in the full HTML
    for pattern, label in REQUIRED_PATTERNS:
        if pattern not in html:
            errs.append(f"missing-deferred-pattern: {pattern!r} — {label}")

    return errs


# ── Load all published cities ─────────────────────────────────────────────────

_data_file = os.path.join(os.path.dirname(__file__), "city-data.json")
with open(_data_file, encoding='utf-8') as _f:
    _cities = json.load(_f)

_published = [c for c in _cities if c.get('publishStatus') == 'published']

if not _published:
    print("ERROR: no published city found in city-data.json — cannot render test pages")
    sys.exit(1)

print(f"\nCity-script regression check — {len(_published)} published city page(s)\n")

# ── [1–3] Check every published city page ────────────────────────────────────

print(f"[ 1–3 ] Scanning all {len(_published)} published cities …")

all_errors = []   # list of (slug, error_string) pairs
pass_count = 0

for city_data in _published:
    slug = city_data['slug']
    html = _mod.render_page(city_data)
    city_errs = collect_errors(html)
    if city_errs:
        for e in city_errs:
            all_errors.append((slug, e))
            print(f"  ✗  [{slug}] {e}")
    else:
        pass_count += 1

if not all_errors:
    print(f"  ✓  all {pass_count} cities clean  "
          f"(no blocking scripts · no bare CDN srcs · deferred-loader patterns present)")

# ── [4] Mutation self-tests (run once on the first published city's HTML) ─────

print("\n[ 4 ] Mutation self-tests (guard must catch known-bad templates) …")

# Use first published city as the mutation base
_base_html = _mod.render_page(_published[0])
_base_slug  = _published[0]['slug']

mutation_errors = []

# Helper: inject a snippet into <head> just before the first <link>
def inject_into_head(base_html, snippet):
    return base_html.replace('<link rel="stylesheet"', snippet + '\n<link rel="stylesheet"', 1)

# Mutation A — blocking external script with no defer/async
_mutant_a = inject_into_head(_base_html, '<script src="/assets/bad-blocking.js"></script>')
_errs_a = collect_errors(_mutant_a)
if any('blocking-external-script' in e for e in _errs_a):
    print("  ✓  Mutation A: blocking external <script src> in <head> is caught")
else:
    msg = "Mutation A FAILED: guard did not catch a blocking external script in <head>"
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)

# Mutation B — CDN loader URL as a bare static src
_mutant_b = inject_into_head(
    _base_html, '<script src="https://cdn.userway.org/widget.js"></script>')
_errs_b = collect_errors(_mutant_b)
if any('bare-cdn-src' in e for e in _errs_b):
    print("  ✓  Mutation B: bare CDN static src in <head> is caught")
else:
    msg = "Mutation B FAILED: guard did not catch a bare CDN <script src= in <head>"
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)

# Mutation C — deferred-loader pattern stripped from HEAD_SCRIPTS
_mutant_c = _base_html.replace("requestIdleCallback", "REMOVED_PATTERN")
_errs_c = collect_errors(_mutant_c)
if any('missing-deferred-pattern' in e for e in _errs_c):
    print("  ✓  Mutation C: removed requestIdleCallback is caught")
else:
    msg = "Mutation C FAILED: guard did not catch removal of requestIdleCallback"
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)

# ── [ 5 ] WebP hero-preload sentinel test ────────────────────────────────────
print("\n[ 5 ] WebP hero preload — sentinel .webp triggers correct <link> tag …")

_img_dir       = os.path.join(_mod.OUT_DIR, "assets", "img", "city")
_sentinel_path = os.path.join(_img_dir, f"{_base_slug}.webp")
_sentinel_created = False
_webp_checks = 0

try:
    if not os.path.isfile(_sentinel_path):
        # Create a zero-byte sentinel so _hero_preload_tag detects a WebP file.
        os.makedirs(_img_dir, exist_ok=True)
        open(_sentinel_path, 'wb').close()
        _sentinel_created = True

    # --- 5a: all three required attributes on the SAME <link> tag ---------------
    # find_city_hero_preload returns only a tag with rel=preload + as=image +
    # the slug's href, so a decoy WebP link elsewhere in <head> cannot pass.
    _webp_html = _mod.render_page(_published[0])
    _webp_head = extract_head(_webp_html)

    _preload_tag = find_city_hero_preload(_webp_head, _base_slug)

    if _preload_tag is not None:
        print(f"  ✓  <link rel=preload as=image> found for {_base_slug}")
    else:
        msg = (f'webp-preload: no <link rel="preload" as="image"> found '
               f'for slug {_base_slug!r} when .webp file is present')
        print(f"  ✗  {msg}")
        mutation_errors.append(msg)
    _webp_checks += 1

    if _preload_tag is not None:
        _has_webp_href = bool(re.search(
            r'href\s*=\s*["\']assets/img/city/' + re.escape(_base_slug) + r'\.webp["\']',
            _preload_tag, re.IGNORECASE))
        _has_webp_type = bool(re.search(
            r'type\s*=\s*["\']image/webp["\']', _preload_tag, re.IGNORECASE))

        if _has_webp_href:
            print(f"  ✓  preload href is assets/img/city/{_base_slug}.webp (same tag)")
        else:
            msg = (f'webp-preload: preload href does not end in .webp '
                   f'for slug {_base_slug!r}')
            print(f"  ✗  {msg}")
            mutation_errors.append(msg)
        _webp_checks += 1

        if _has_webp_type:
            print(f'  ✓  type="image/webp" present on the same preload tag')
        else:
            msg = (f'webp-preload: type="image/webp" missing from the '
                   f'<link rel=preload as=image> tag for {_base_slug!r}')
            print(f"  ✗  {msg}")
            mutation_errors.append(msg)
        _webp_checks += 1
    else:
        _webp_checks += 2  # count sub-checks as run (already failed above)

    # --- 5b: mutation — decoy WebP link must not fool the guard -----------------
    # Replace the real preload's .webp href with .jpg (simulating a forgotten
    # update), then inject a decoy <link> that carries type="image/webp" and a
    # .webp href but is NOT a preload.  The guard must still reject this page.
    _decoy = (f'<link rel="prefetch" as="image" '
              f'href="assets/img/city/{_base_slug}.webp" type="image/webp">')
    _mutant_d = re.sub(
        r'(<link\b[^>]*\brel\s*=\s*["\']preload["\'][^>]*)'
        + re.escape(_base_slug) + r'\.webp',
        r'\g<1>' + _base_slug + '.jpg',
        _webp_html, count=1, flags=re.IGNORECASE,
    )
    # Inject decoy just before the stylesheet so it lands in <head>
    _mutant_d = _mutant_d.replace('<link rel="stylesheet"',
                                  _decoy + '\n  <link rel="stylesheet"', 1)
    _mutant_d_head = extract_head(_mutant_d)
    _mutant_preload = find_city_hero_preload(_mutant_d_head, _base_slug)
    _mutant_webp = (_mutant_preload is not None and
                    bool(re.search(r'\.webp["\']', _mutant_preload, re.IGNORECASE)) and
                    bool(re.search(r'type\s*=\s*["\']image/webp["\']',
                                   _mutant_preload, re.IGNORECASE)))
    if not _mutant_webp:
        print("  ✓  Mutation 5b: decoy WebP link does not satisfy preload guard "
              "(wrong preload is caught)")
    else:
        msg = ("webp-preload-mutation: guard passed despite preload pointing to "
               ".jpg while a decoy WebP link was present — assertions are too loose")
        print(f"  ✗  {msg}")
        mutation_errors.append(msg)
    _webp_checks += 1

finally:
    # Always clean up the sentinel if we created it.
    if _sentinel_created and os.path.isfile(_sentinel_path):
        os.remove(_sentinel_path)

# ── Summary ───────────────────────────────────────────────────────────────────

print()

combined_errors = all_errors + [(f"mutation/{_base_slug}", e) for e in mutation_errors]

if combined_errors:
    print("❌  FAIL — city-script regression check found issues:")
    for slug, e in combined_errors:
        print(f"     [{slug}] {e}")
    print()
    if all_errors:
        print("    Blocking scripts in <head> slow page load and hurt PageSpeed scores.")
        print("    Fix HEAD_SCRIPTS in website/build-cities.py before deploying.")
    sys.exit(1)

checks_per_city = len(REQUIRED_PATTERNS) + len(FORBIDDEN_BARE_SRC_SUBSTRINGS) + 1  # +1 for blocking-script scan
total_city_checks = checks_per_city * len(_published)
print(f"✅  OK — all checks pass across {len(_published)} published cities "
      f"({total_city_checks} total city checks · 3 mutations caught · "
      f"{_webp_checks} WebP preload checks).")
sys.exit(0)
