#!/usr/bin/env python3
"""
Task 408: Fix on-page metadata and social tags across city pages and core pages.
- City pages (146): differentiate meta descriptions, og-image v2, og:locale,
  og:image:width/height/alt, full Twitter card
- media-kit.html: add og:locale, full Twitter card
- careers/volunteer/sound-bath/care-brief: add twitter:title/description/image
"""

import json, re, os, sys

PREVIEW = "website/elh-preview"
CITY_DATA = "website/city-data.json"

# ── Load city data ──────────────────────────────────────────────────────────
with open(CITY_DATA) as f:
    cities = json.load(f)

city_index = {c["slug"]: c for c in cities}

# ── Helpers ─────────────────────────────────────────────────────────────────

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def differentiated_description(city, subregion, county):
    """Build a unique meta description that references the county sub-region."""
    city_name = city
    # Thousand Oaks is near HQ
    if city_name == "Thousand Oaks":
        return (
            "Eternal Life Hospice provides Medicare-certified hospice care in "
            "Thousand Oaks, CA — near our Westlake Village headquarters, serving the "
            "Conejo Valley. Physician-supported comfort care at home or in a facility. "
            "Call 805.953.7273."
        )
    if city_name == "Westlake Village":
        return (
            "Eternal Life Hospice is based in Westlake Village, CA — providing "
            "Medicare-certified, physician-supported hospice care in the Conejo Valley "
            "and across Ventura County. Call 805.953.7273."
        )
    # Generic differentiated template
    if subregion and subregion.lower() not in (county.lower(), city_name.lower()):
        location_str = f"{subregion}, {county}"
    else:
        location_str = county
    return (
        f"Eternal Life Hospice provides Medicare-certified hospice care in "
        f"{city_name}, CA \u2014 {location_str}. Physician-supported comfort care "
        f"at home or in a care facility. Call 805.953.7273."
    )

# ── Fix city pages ──────────────────────────────────────────────────────────

def fix_city_page(html_path, slug):
    city_obj = city_index.get(slug)
    if not city_obj:
        print(f"  WARN: no city data for slug '{slug}'")
        return False

    city     = city_obj["city"]
    subregion = city_obj.get("subregion", "")
    county   = city_obj.get("county", "")
    og_title = city_obj.get("title", f"Hospice Care in {city}, CA | Eternal Life Hospice")

    new_desc = differentiated_description(city, subregion, county)
    html     = read(html_path)
    changed  = False

    # 1. Update meta description (name="description")
    old_desc_match = re.search(
        r'(<meta name="description" content=")[^"]*(")', html)
    if old_desc_match:
        old_desc = old_desc_match.group(0)
        new_desc_tag = f'<meta name="description" content="{new_desc}">'
        if old_desc != new_desc_tag:
            html = html.replace(old_desc, new_desc_tag, 1)
            changed = True

    # 2. Update og:image from og-image.jpg → og-image-v2.jpg
    html_new = html.replace(
        '"https://eternallifehospice.com/assets/og-image.jpg"',
        '"https://eternallifehospice.com/assets/og-image-v2.jpg"'
    )
    if html_new != html:
        html = html_new
        changed = True

    # 3. Update og:description to match new description
    og_desc_match = re.search(
        r'(<meta property="og:description" content=")[^"]*(")', html)
    if og_desc_match:
        old_og_desc = og_desc_match.group(0)
        new_og_desc = f'<meta property="og:description" content="{new_desc}">'
        if old_og_desc != new_og_desc:
            html = html.replace(old_og_desc, new_og_desc, 1)
            changed = True

    # 4. After og:site_name, inject og:locale + og:image dimensions (if not already present)
    og_site_name_pat = r'(<meta property="og:site_name" content="Eternal Life Hospice">)'
    if 'og:locale' not in html:
        og_locale_block = (
            r'\1'
            '<meta property="og:locale" content="en_US">'
            f'<meta property="og:image:width" content="1200">'
            f'<meta property="og:image:height" content="630">'
            f'<meta property="og:image:alt" content="Hospice Care in {city}, CA | Eternal Life Hospice">'
        )
        html_new = re.sub(og_site_name_pat, og_locale_block, html, count=1)
        if html_new != html:
            html = html_new
            changed = True
    else:
        # Already has og:locale — ensure width/height/alt are present
        if 'og:image:width' not in html:
            img_dims = (
                f'<meta property="og:image:width" content="1200">'
                f'<meta property="og:image:height" content="630">'
                f'<meta property="og:image:alt" content="Hospice Care in {city}, CA | Eternal Life Hospice">'
            )
            og_locale_pat = r'(<meta property="og:locale" content="en_US">)'
            html_new = re.sub(og_locale_pat, r'\1' + img_dims, html, count=1)
            if html_new != html:
                html = html_new
                changed = True

    # 5. After twitter:card, inject full Twitter tags (if incomplete)
    twitter_card_pat = r'(<meta name="twitter:card" content="summary_large_image">)'
    if 'twitter:title' not in html:
        twitter_block = (
            r'\1'
            '<meta name="twitter:site" content="@EternalLifeHospice">'
            f'<meta name="twitter:title" content="{og_title}">'
            f'<meta name="twitter:description" content="{new_desc}">'
            '<meta name="twitter:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">'
        )
        html_new = re.sub(twitter_card_pat, twitter_block, html, count=1)
        if html_new != html:
            html = html_new
            changed = True

    if changed:
        write(html_path, html)
    return changed

# ── Fix media-kit.html ───────────────────────────────────────────────────────

def fix_media_kit():
    path = os.path.join(PREVIEW, "media-kit.html")
    html = read(path)
    changed = False

    # Add og:locale after og:site_name (it has og:site_name already)
    if 'og:locale' not in html:
        og_site_name_pat = r'(<meta property="og:site_name" content="Eternal Life Hospice">)'
        html_new = re.sub(og_site_name_pat,
            r'\1<meta property="og:locale" content="en_US">',
            html, count=1)
        if html_new != html:
            html = html_new
            changed = True

    # Add twitter tags — media-kit has only twitter:card, no twitter:site/title/desc/image
    twitter_card_pat = r'(<meta name="twitter:card" content="summary_large_image">)'
    if 'twitter:site' not in html:
        mk_twitter = (
            r'\1'
            '<meta name="twitter:site" content="@EternalLifeHospice">'
            '<meta name="twitter:title" content="Eternal Care Kit — Eternal Life Hospice">'
            '<meta name="twitter:description" content="The Eternal Life Hospice Care Kit — turn the pages online or download the print-ready PDF. Care That Honors Life.">'
            '<meta name="twitter:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">'
        )
        html_new = re.sub(twitter_card_pat, mk_twitter, html, count=1)
        if html_new != html:
            html = html_new
            changed = True

    if changed:
        write(path, html)
    return changed

# ── Fix core pages with incomplete Twitter cards ─────────────────────────────

CORE_PAGES = {
    "careers.html": {
        "twitter_title": "Careers at Eternal Life Hospice | Join Our Care Team",
        "twitter_desc":  "Join the care team at Eternal Life Hospice across Ventura and Los Angeles counties. We welcome nurses, aides, social workers, chaplains and integrative therapists who want work that matters, close to home.",
    },
    "volunteer.html": {
        "twitter_title": "Become a Hospice Volunteer | Eternal Life Hospice",
        "twitter_desc":  "Volunteer with Eternal Life Hospice across Ventura and Los Angeles counties. Bring companionship, respite and presence to families facing the end of life. Training provided, no medical background required. Call 805.953.7273.",
    },
    "sound-bath.html": {
        "twitter_title": "Sound Bath Therapy in Hospice Care | Eternal Life Hospice",
        "twitter_desc":  "The Sound Bath at Eternal Life Hospice — original soundscapes and Tibetan and crystal singing bowls offered gently at the bedside for rest and comfort. Offered for relaxation and comfort, at no additional expense when included in the care plan.",
    },
    "care-brief.html": {
        "twitter_title": "The Eternal Care Brief | Eternal Life Hospice",
        "twitter_desc":  "The Eternal Care Brief: a bi-monthly care publication from Eternal Life Hospice for professional care teams and families. Clinical guidance, family support, whole-person comfort, and program integrity.",
    },
}

def fix_core_page(filename, twitter_title, twitter_desc):
    path = os.path.join(PREVIEW, filename)
    html = read(path)
    changed = False

    # All these pages have twitter:card + twitter:site but miss title/desc/image
    twitter_site_pat = r'(<meta name="twitter:site" content="@EternalLifeHospice">)'
    if 'twitter:title' not in html:
        addition = (
            r'\1'
            f'<meta name="twitter:title" content="{twitter_title}">'
            f'<meta name="twitter:description" content="{twitter_desc}">'
            '<meta name="twitter:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">'
        )
        html_new = re.sub(twitter_site_pat, addition, html, count=1)
        if html_new != html:
            html = html_new
            changed = True

    if changed:
        write(path, html)
    return changed

# ── Main ────────────────────────────────────────────────────────────────────

city_files = sorted(
    f for f in os.listdir(PREVIEW)
    if f.startswith("hospice-") and f.endswith("-ca.html")
)

print(f"Processing {len(city_files)} city pages...")
city_ok = city_skip = city_fail = 0
for fname in city_files:
    # slug = strip hospice- prefix and -ca.html suffix
    slug = fname[len("hospice-"):-len("-ca.html")]
    html_path = os.path.join(PREVIEW, fname)
    try:
        changed = fix_city_page(html_path, slug)
        if changed:
            city_ok += 1
        else:
            city_skip += 1
    except Exception as e:
        print(f"  ERROR {fname}: {e}")
        city_fail += 1

print(f"  changed={city_ok}  already-ok={city_skip}  errors={city_fail}")

print("\nProcessing media-kit.html...")
print("  changed" if fix_media_kit() else "  no changes needed")

print("\nProcessing core pages...")
for fname, kw in CORE_PAGES.items():
    result = fix_core_page(fname, **kw)
    print(f"  {fname}: {'changed' if result else 'no changes needed'}")

print("\nDone.")
