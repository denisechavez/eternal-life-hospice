#!/usr/bin/env python3
"""
Comprehensive fix for city-page WebP hero migration.

Pass 1 — fix the 88 already-updated pages:
  <img class="hero-bg" src="assets/img/city/CITY.jpg"" …>   ← double-quote bug
  →  <img class="hero-bg" src="assets/img/city/CITY.jpg" …>

Pass 2 — handle the 58 pages that had no <img class="hero-bg">:
  a. Update <link rel="preload" href="...CITY.jpg" …>
     → href="...CITY.webp" type="image/webp"
  b. Insert <picture>…</picture> as first child of the hero section
     deriving city name from the h1 in that section.
"""

import re
import os
import glob

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = sorted(glob.glob(os.path.join(BASE, "hospice-*-ca.html")))
WEBP_DIR = os.path.join(BASE, "assets", "img", "city")

fixed_dquote = 0
added_img = 0
errors = []


def title_case_city(slug):
    """Convert 'thousand-oaks' → 'Thousand Oaks'."""
    exceptions = {"van", "de", "la", "del"}
    parts = slug.split("-")
    return " ".join(p if p in exceptions else p.capitalize() for p in parts)


for page_path in PAGES:
    page_name = os.path.basename(page_path)
    city_slug = page_name.replace("hospice-", "").replace("-ca.html", "")

    with open(page_path, "r", encoding="utf-8") as f:
        html = f.read()

    changed = False

    # ── Check which state this page is in ────────────────────────────────────
    has_picture = "<picture>" in html
    has_hero_bg = 'class="hero-bg"' in html
    has_webp_preload = f'href="assets/img/city/{city_slug}.webp"' in html
    has_jpg_preload = f'href="assets/img/city/{city_slug}.jpg"' in html
    webp_file = os.path.join(WEBP_DIR, f"{city_slug}.webp")

    if not os.path.exists(webp_file):
        errors.append(f"{page_name}: WebP file missing — {city_slug}.webp")
        continue

    # ── Fix 1: double-quote bug in already-converted pages ───────────────────
    # Pattern: src="assets/img/city/CITY.jpg"" — two closing quotes
    if has_hero_bg and has_picture:
        dq_pattern = (
            r'(<img class="hero-bg" src="assets/img/city/[^"]+\.jpg)""\s'
        )
        new_html, n = re.subn(dq_pattern, r'\1" ', html)
        if n > 0:
            html = new_html
            changed = True
            fixed_dquote += 1

    # ── Fix 2: pages with no img.hero-bg — add picture + update preload ──────
    if not has_hero_bg:
        city_display = title_case_city(city_slug)

        # a) Update preload: .jpg → .webp + add type
        if has_jpg_preload:
            old_preload = (
                f'<link rel="preload" as="image" href="assets/img/city/{city_slug}.jpg"'
                f' fetchpriority="high">'
            )
            new_preload = (
                f'<link rel="preload" as="image" href="assets/img/city/{city_slug}.webp"'
                f' type="image/webp" fetchpriority="high">'
            )
            if old_preload in html:
                html = html.replace(old_preload, new_preload, 1)
                changed = True
            else:
                errors.append(f"{page_name}: preload pattern not matched verbatim")

        # b) Insert <picture> as first child of the hero section
        hero_open_pattern = r'(<section class="hero hero--city hero--tall">)'
        picture_block = (
            f'<picture>'
            f'<source srcset="assets/img/city/{city_slug}.webp" type="image/webp">'
            f'<img class="hero-bg" src="assets/img/city/{city_slug}.jpg"'
            f' alt="{city_display}, California" width="1536" height="1024"'
            f' loading="eager" decoding="async">'
            f'</picture>'
        )
        new_html, n = re.subn(
            hero_open_pattern,
            r'\1' + picture_block,
            html,
        )
        if n == 1:
            html = new_html
            changed = True
            added_img += 1
        elif n == 0:
            errors.append(f"{page_name}: hero section opening tag not found")
        else:
            errors.append(f"{page_name}: hero section opening tag matched {n} times")

    if changed:
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)

print(f"Double-quote fixed : {fixed_dquote}")
print(f"img added (no-img) : {added_img}")
print(f"Errors             : {len(errors)}")
for e in errors:
    print(f"  ✗ {e}")
