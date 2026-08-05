#!/usr/bin/env python3
"""
Regression guard: city-page generator must not emit render-blocking scripts
---------------------------------------------------------------------------
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

    # [4] Hero image — every page must contain <img class="hero-bg">
    if not re.search(r'<img\b[^>]*\bclass=["\'][^"\']*hero-bg', html, re.IGNORECASE):
        errs.append(
            'missing-hero-img: no <img class="hero-bg"> found — '
            'hero section will render as a plain dark background'
        )

    # [5] WebP preload — <link rel="preload" as="image" …webp> must be in <head>
    if not re.search(
        r'<link\b[^>]*\brel\s*=\s*["\']preload["\'][^>]*\.webp',
        head, re.IGNORECASE,
    ):
        errs.append(
            'missing-webp-preload: no <link rel="preload" as="image" …webp> '
            'in <head> — hero image will not be eagerly preloaded'
        )

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

# ── [ 5 ] Hero image + WebP preload — attribute checks and mutation tests ──────
print("\n[ 5 ] Hero image and WebP preload — attribute checks and mutations …")

# collect_errors already checks every published city (groups [4] and [5] inside
# collect_errors).  This section verifies the exact tag attributes on a single
# rendered page and runs two extra mutation tests.

_base_head = extract_head(_base_html)

# 5a — all three required attributes on the SAME <link> tag --------------------
_preload_tag = find_city_hero_preload(_base_head, _base_slug)

if _preload_tag is not None:
    print(f"  ✓  <link rel=preload as=image> found for {_base_slug}")
else:
    msg = (f'webp-preload: no <link rel="preload" as="image"> found '
           f'for slug {_base_slug!r}')
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)

_hero_checks = 1

if _preload_tag is not None:
    _has_webp_href = bool(re.search(
        r'href\s*=\s*["\']assets/img/city/' + re.escape(_base_slug) + r'\.webp["\']',
        _preload_tag, re.IGNORECASE))
    _has_webp_type = bool(re.search(
        r'type\s*=\s*["\']image/webp["\']', _preload_tag, re.IGNORECASE))

    if _has_webp_href:
        print(f"  ✓  preload href is assets/img/city/{_base_slug}.webp (same tag)")
    else:
        msg = f'webp-preload: href does not end in .webp for slug {_base_slug!r}'
        print(f"  ✗  {msg}")
        mutation_errors.append(msg)
    _hero_checks += 1

    if _has_webp_type:
        print(f'  ✓  type="image/webp" present on the preload tag')
    else:
        msg = (f'webp-preload: type="image/webp" missing from '
               f'<link rel=preload as=image> for {_base_slug!r}')
        print(f"  ✗  {msg}")
        mutation_errors.append(msg)
    _hero_checks += 1
else:
    _hero_checks += 2  # count sub-checks as run (already failed above)

# 5b — img.hero-bg present in the rendered hero section -----------------------
if re.search(r'<img\b[^>]*\bclass=["\'][^"\']*hero-bg', _base_html, re.IGNORECASE):
    print(f"  ✓  <img class=\"hero-bg\"> found in rendered page for {_base_slug}")
else:
    msg = f'missing-hero-img: no <img class="hero-bg"> in rendered page for {_base_slug!r}'
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)
_hero_checks += 1

# Mutation D — strip the hero img; guard must catch it -------------------------
_mutant_d = re.sub(
    r'<img\b[^>]*\bclass=["\'][^"\']*hero-bg[^>]*>',
    '', _base_html, count=1, flags=re.IGNORECASE,
)
_errs_d = collect_errors(_mutant_d)
if any('missing-hero-img' in e for e in _errs_d):
    print("  ✓  Mutation D: missing img.hero-bg is caught")
else:
    msg = "Mutation D FAILED: guard did not catch a page with no <img class=\"hero-bg\">"
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)
_hero_checks += 1

# Mutation E — replace WebP preload with a JPEG preload; guard must catch it ---
_mutant_e = re.sub(
    r'<link\b[^>]*\brel\s*=\s*["\']preload["\'][^>]*\.webp[^>]*>',
    f'<link rel="preload" as="image" href="assets/img/city/{_base_slug}.jpg" fetchpriority="high">',
    _base_html, count=1, flags=re.IGNORECASE,
)
_errs_e = collect_errors(_mutant_e)
if any('missing-webp-preload' in e for e in _errs_e):
    print("  ✓  Mutation E: WebP preload replaced with JPEG preload is caught")
else:
    msg = "Mutation E FAILED: guard did not catch a page with a JPEG-only preload"
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)
_hero_checks += 1

# Mutation F — decoy WebP prefetch must not fool the preload guard -------------
_decoy = (f'<link rel="prefetch" as="image" '
          f'href="assets/img/city/{_base_slug}.webp" type="image/webp">')
_mutant_f = re.sub(
    r'(<link\b[^>]*\brel\s*=\s*["\']preload["\'][^>]*)'
    + re.escape(_base_slug) + r'\.webp',
    r'\g<1>' + _base_slug + '.jpg',
    _base_html, count=1, flags=re.IGNORECASE,
)
_mutant_f = _mutant_f.replace('<link rel="stylesheet"',
                              _decoy + '\n  <link rel="stylesheet"', 1)
_mutant_f_head = extract_head(_mutant_f)
_mutant_preload = find_city_hero_preload(_mutant_f_head, _base_slug)
_mutant_webp = (_mutant_preload is not None and
                bool(re.search(r'\.webp["\']', _mutant_preload, re.IGNORECASE)) and
                bool(re.search(r'type\s*=\s*["\']image/webp["\']',
                               _mutant_preload, re.IGNORECASE)))
if not _mutant_webp:
    print("  ✓  Mutation F: decoy WebP prefetch does not satisfy preload guard")
else:
    msg = ("Mutation F FAILED: guard passed despite preload pointing to "
           ".jpg while a decoy WebP prefetch was present — assertions too loose")
    print(f"  ✗  {msg}")
    mutation_errors.append(msg)
_hero_checks += 1

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

# checks per city: blocking-script scan(1) + bare-CDN(2) + deferred-patterns(2)
#                  + hero-img(1) + webp-preload(1) = 7
checks_per_city = 1 + len(FORBIDDEN_BARE_SRC_SUBSTRINGS) + len(REQUIRED_PATTERNS) + 2
total_city_checks = checks_per_city * len(_published)
print(f"✅  OK — all checks pass across {len(_published)} published cities "
      f"({total_city_checks} total city checks · 6 mutations caught · "
      f"{_hero_checks} hero/preload attribute checks).")
sys.exit(0)
