#!/usr/bin/env python3
"""
Task 408 fix-pass B: correct the >> double-close bug introduced in fix pass A,
and complete the county hub page Twitter card.
"""

import json, re, os, glob

PREVIEW = "website/elh-preview"

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ── 1. Fix >> double-close on all city pages ────────────────────────────────
# The previous regex captured up to the closing quote but not >, so the new
# tag (which ends with >) was inserted while the original > remained → >>
# Fix: in meta description and og:description tags, replace any closing ">> with ">

city_files = glob.glob(os.path.join(PREVIEW, "hospice-*-ca.html"))
fixed_count = 0

for fpath in sorted(city_files):
    html = read(fpath)
    # Find occurrences of double >> specifically at end of meta tags
    # Pattern: attribute-value close quote followed by >>
    # We target the two specific tags that were affected
    new_html = html

    # Fix meta name="description" tag ending in >>
    new_html = re.sub(
        r'(<meta name="description" content="[^"]*")>>',
        r'\1>',
        new_html
    )
    # Fix meta property="og:description" tag ending in >>
    new_html = re.sub(
        r'(<meta property="og:description" content="[^"]*")>>',
        r'\1>',
        new_html
    )

    if new_html != html:
        write(fpath, new_html)
        fixed_count += 1

print(f"Fixed >> bug in {fixed_count} city pages")

# Verify no remaining >> in meta description / og:description tags
remaining = 0
for fpath in sorted(city_files):
    html = read(fpath)
    if re.search(r'<meta name="description" content="[^"]*">>', html):
        print(f"  STILL HAS >> in description: {os.path.basename(fpath)}")
        remaining += 1
    if re.search(r'<meta property="og:description" content="[^"]*">>', html):
        print(f"  STILL HAS >> in og:description: {os.path.basename(fpath)}")
        remaining += 1
if remaining == 0:
    print("✓ No remaining >> in description/og:description tags")

# ── 2. Complete county hub page Twitter card ─────────────────────────────────
hub_path = os.path.join(PREVIEW, "hospice-ventura-and-los-angeles-county-ca.html")
if os.path.exists(hub_path):
    html = read(hub_path)
    if 'twitter:title' not in html:
        # Page has twitter:card + twitter:site — add title/description/image
        hub_twitter = (
            r'\1'
            '<meta name="twitter:title" content="Hospice Care in Ventura &amp; LA County | Eternal Life Hospice">'
            '<meta name="twitter:description" content="Independent, Medicare-certified hospice care across Ventura and Los Angeles County. Care at home with a nurse on call 24/7. Call 805.953.7273.">'
            '<meta name="twitter:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">'
        )
        html_new = re.sub(
            r'(<meta name="twitter:site" content="@EternalLifeHospice">)',
            hub_twitter, html, count=1
        )
        if html_new != html:
            write(hub_path, html_new)
            print("✓ Added Twitter title/description/image to county hub page")
        else:
            print("  No change to county hub page")
    else:
        print("✓ County hub page already has twitter:title")
else:
    print(f"  County hub page not found: {hub_path}")

# ── 3. Sanity check: verify no >> in head of sample pages ───────────────────
print("\nSanity check — head sections:")
sample = [
    "hospice-thousand-oaks-ca.html",
    "hospice-arleta-ca.html",
    "hospice-artesia-ca.html",
    "hospice-acton-ca.html",
]
for fname in sample:
    path = os.path.join(PREVIEW, fname)
    html = read(path)
    head_end = html.find('</head>')
    head = html[:head_end] if head_end > 0 else html[:3000]
    has_double = '>>' in head
    desc_m = re.search(r'<meta name="description" content="([^"]+)">', head)
    twitter_title = 'twitter:title' in head
    og_locale = 'og:locale' in head
    print(f"  {fname}:")
    print(f"    >> in head: {has_double}")
    print(f"    og:locale: {og_locale}  twitter:title: {twitter_title}")
    if desc_m:
        print(f"    desc: {desc_m.group(1)[:100]}")

print("\nDone.")
