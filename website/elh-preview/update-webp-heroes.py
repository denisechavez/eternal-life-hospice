#!/usr/bin/env python3
"""
Update all 146 city pages to serve WebP hero images.

Changes per page:
1. <link rel="preload" href="...CITY.jpg" fetchpriority="high">
   → <link rel="preload" href="...CITY.webp" type="image/webp" fetchpriority="high">

2. <img class="hero-bg" src="assets/img/city/CITY.jpg" ...>
   → <picture><source srcset="assets/img/city/CITY.webp" type="image/webp">
     <img class="hero-bg" src="assets/img/city/CITY.jpg" ...></picture>
"""

import re
import os
import glob

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = sorted(glob.glob(os.path.join(BASE, "hospice-*-ca.html")))
WEBP_DIR = os.path.join(BASE, "assets", "img", "city")

updated = 0
skipped = 0
errors = []

for page_path in PAGES:
    page_name = os.path.basename(page_path)
    with open(page_path, "r", encoding="utf-8") as f:
        html = f.read()

    # ── 1. Fix the preload link ──────────────────────────────────────────────
    # Match: href="assets/img/city/CITY.jpg" inside a preload link
    preload_pattern = (
        r'(<link rel="preload" as="image" href=")(assets/img/city/[^"]+)(\.jpg)(" fetchpriority="high">)'
    )

    def fix_preload(m):
        return f'{m.group(1)}{m.group(2)}.webp" type="image/webp" fetchpriority="high">'

    new_html, n_preload = re.subn(preload_pattern, fix_preload, html)

    # ── 2. Wrap hero img in <picture> ────────────────────────────────────────
    # Match: <img class="hero-bg" src="assets/img/city/CITY.jpg" ...>
    # The img is self-closing (no </img>); it ends with >
    hero_pattern = (
        r'(<img class="hero-bg" src=")(assets/img/city/)([^"]+)(\.jpg)(")'
        r'([^>]*>)'
    )

    def fix_hero(m):
        city_slug = m.group(3)
        rest_of_attrs = m.group(6)  # everything from the 5th attr onward, including >
        jpg_src = f'{m.group(2)}{city_slug}.jpg'
        webp_src = f'{m.group(2)}{city_slug}.webp'

        # Verify the WebP file exists
        webp_file = os.path.join(WEBP_DIR, f"{city_slug}.webp")
        if not os.path.exists(webp_file):
            errors.append(f"{page_name}: no WebP found for slug '{city_slug}'")
            return m.group(0)  # leave unchanged

        return (
            f'<picture>'
            f'<source srcset="{webp_src}" type="image/webp">'
            f'<img class="hero-bg" src="{jpg_src}"{m.group(5)}{rest_of_attrs}'
            f'</picture>'
        )

    new_html, n_hero = re.subn(hero_pattern, fix_hero, new_html)

    if n_preload == 0 and n_hero == 0:
        # Page already updated or uses a different structure — skip silently
        skipped += 1
        continue

    if n_preload != 1 or n_hero != 1:
        errors.append(
            f"{page_name}: unexpected match counts — preload={n_preload}, hero={n_hero}"
        )
        continue

    with open(page_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    updated += 1

print(f"Updated : {updated}")
print(f"Skipped : {skipped}")
print(f"Errors  : {len(errors)}")
for e in errors:
    print(f"  ✗ {e}")
