#!/usr/bin/env python3
"""
Add LocalBusiness/MedicalOrganization JSON-LD with areaServed to city pages
that currently lack it.  Pages that already have areaServed are skipped.
"""

import json, re, glob, sys
from pathlib import Path

# ---------------------------------------------------------------------------
# City data: slug → (proper_name, county, lat, lng)
# County is "Los Angeles" or "Ventura"
# ---------------------------------------------------------------------------
CITY_DATA = {
    # Ventura County
    "brandeis":          ("Brandeis",           "Ventura",     34.3675, -119.0160),
    "casitas-springs":   ("Casitas Springs",    "Ventura",     34.3719, -119.2244),
    "el-rio":            ("El Rio",              "Ventura",     34.2399, -119.1733),
    "meiners-oaks":      ("Meiners Oaks",       "Ventura",     34.4500, -119.2500),
    "oak-view":          ("Oak View",            "Ventura",     34.4013, -119.2986),
    "piru":              ("Piru",                "Ventura",     34.4147, -118.7953),
    "point-mugu":        ("Point Mugu",          "Ventura",     34.1133, -119.1160),
    "santa-rosa-valley": ("Santa Rosa Valley",  "Ventura",     34.2478, -118.8894),
    "saticoy":           ("Saticoy",             "Ventura",     34.2794, -119.1489),
    "somis":             ("Somis",               "Ventura",     34.2750, -119.0006),

    # Los Angeles County
    "acton":             ("Acton",               "Los Angeles", 34.4733, -118.1950),
    "altadena":          ("Altadena",            "Los Angeles", 34.1897, -118.1320),
    "arleta":            ("Arleta",              "Los Angeles", 34.2444, -118.4219),
    "artesia":           ("Artesia",             "Los Angeles", 33.8653, -118.0831),
    "avalon":            ("Avalon",              "Los Angeles", 33.3428, -118.3289),
    "azusa":             ("Azusa",               "Los Angeles", 34.1336, -117.9076),
    "baldwin-park":      ("Baldwin Park",        "Los Angeles", 34.0853, -117.9608),
    "bell":              ("Bell",                "Los Angeles", 33.9775, -118.1872),
    "bell-gardens":      ("Bell Gardens",        "Los Angeles", 33.9653, -118.1553),
    "bellflower":        ("Bellflower",          "Los Angeles", 33.8817, -118.1170),
    "canyon-country":    ("Canyon Country",      "Los Angeles", 34.3972, -118.4475),
    "carson":            ("Carson",              "Los Angeles", 33.8317, -118.2819),
    "castaic":           ("Castaic",             "Los Angeles", 34.4883, -118.6269),
    "cerritos":          ("Cerritos",            "Los Angeles", 33.8583, -118.0648),
    "city-of-industry":  ("City of Industry",   "Los Angeles", 34.0153, -117.9622),
    "claremont":         ("Claremont",           "Los Angeles", 34.0967, -117.7198),
    "compton":           ("Compton",             "Los Angeles", 33.8958, -118.2200),
    "conejo-valley":     ("Conejo Valley",       "Los Angeles", 34.1706, -118.8376),
    "covina":            ("Covina",              "Los Angeles", 34.0900, -117.8881),
    "diamond-bar":       ("Diamond Bar",         "Los Angeles", 34.0289, -117.8103),
    "downey":            ("Downey",              "Los Angeles", 33.9401, -118.1331),
    "duarte":            ("Duarte",              "Los Angeles", 34.1394, -117.9775),
    "eagle-rock":        ("Eagle Rock",          "Los Angeles", 34.1397, -118.2073),
    "el-monte":          ("El Monte",            "Los Angeles", 34.0686, -118.0275),
    "el-segundo":        ("El Segundo",          "Los Angeles", 33.9192, -118.4165),
    "gardena":           ("Gardena",             "Los Angeles", 33.8883, -118.3089),
    "glendora":          ("Glendora",            "Los Angeles", 34.1361, -117.8653),
    "hacienda-heights":  ("Hacienda Heights",   "Los Angeles", 33.9931, -117.9692),
    "harbor-city":       ("Harbor City",         "Los Angeles", 33.7942, -118.2978),
    "hawaiian-gardens":  ("Hawaiian Gardens",   "Los Angeles", 33.8314, -118.0728),
    "hermosa-beach":     ("Hermosa Beach",       "Los Angeles", 33.8622, -118.3995),
    "highland-park":     ("Highland Park",       "Los Angeles", 34.1083, -118.1897),
    "hollywood":         ("Hollywood",           "Los Angeles", 34.0928, -118.3287),
    "huntington-park":   ("Huntington Park",    "Los Angeles", 33.9819, -118.2250),
    "la-canada-flintridge": ("La Cañada Flintridge", "Los Angeles", 34.1997, -118.2003),
    "la-crescenta":      ("La Crescenta",        "Los Angeles", 34.2319, -118.2353),
    "la-mirada":         ("La Mirada",           "Los Angeles", 33.9172, -118.0123),
    "la-puente":         ("La Puente",           "Los Angeles", 34.0325, -117.9494),
    "la-verne":          ("La Verne",            "Los Angeles", 34.1006, -117.7678),
    "lake-hughes":       ("Lake Hughes",         "Los Angeles", 34.6733, -118.4389),
    "lakewood":          ("Lakewood",            "Los Angeles", 33.8536, -118.1339),
    "lawndale":          ("Lawndale",            "Los Angeles", 33.8872, -118.3525),
    "littlerock":        ("Littlerock",          "Los Angeles", 34.5164, -117.9828),
    "llano":             ("Llano",               "Los Angeles", 34.4783, -117.8406),
    "lomita":            ("Lomita",              "Los Angeles", 33.7922, -118.3178),
    "lynwood":           ("Lynwood",             "Los Angeles", 33.9306, -118.2117),
    "maywood":           ("Maywood",             "Los Angeles", 33.9869, -118.1853),
    "monrovia":          ("Monrovia",            "Los Angeles", 34.1444, -117.9997),
    "montebello":        ("Montebello",          "Los Angeles", 34.0153, -118.1136),
    "monterey-park":     ("Monterey Park",       "Los Angeles", 34.0625, -118.1228),
    "montrose":          ("Montrose",            "Los Angeles", 34.2125, -118.2283),
    "newhall":           ("Newhall",             "Los Angeles", 34.3814, -118.5297),
    "norwalk":           ("Norwalk",             "Los Angeles", 33.9022, -118.0817),
    "palos-verdes-peninsula": ("Palos Verdes Peninsula", "Los Angeles", 33.7444, -118.3897),
    "paramount":         ("Paramount",           "Los Angeles", 33.8894, -118.1597),
    "pico-rivera":       ("Pico Rivera",         "Los Angeles", 33.9831, -118.0967),
    "pomona":            ("Pomona",              "Los Angeles", 34.0553, -117.7500),
    "rosemead":          ("Rosemead",            "Los Angeles", 34.0803, -118.0728),
    "rowland-heights":   ("Rowland Heights",    "Los Angeles", 33.9764, -117.9044),
    "san-dimas":         ("San Dimas",           "Los Angeles", 34.1067, -117.8067),
    "san-fernando":      ("San Fernando",        "Los Angeles", 34.2819, -118.4386),
    "san-gabriel":       ("San Gabriel",         "Los Angeles", 34.0961, -118.1058),
    "san-pedro":         ("San Pedro",           "Los Angeles", 33.7361, -118.2922),
    "sierra-madre":      ("Sierra Madre",        "Los Angeles", 34.1614, -118.0530),
    "signal-hill":       ("Signal Hill",         "Los Angeles", 33.8044, -118.1672),
    "silver-lake":       ("Silver Lake",         "Los Angeles", 34.0883, -118.2703),
    "south-el-monte":    ("South El Monte",      "Los Angeles", 34.0522, -118.0461),
    "south-gate":        ("South Gate",          "Los Angeles", 33.9547, -118.2120),
    "south-pasadena":    ("South Pasadena",      "Los Angeles", 34.1139, -118.1503),
    "stevenson-ranch":   ("Stevenson Ranch",     "Los Angeles", 34.3831, -118.5808),
    "sunland":           ("Sunland",             "Los Angeles", 34.2603, -118.3003),
    "temple-city":       ("Temple City",         "Los Angeles", 34.1064, -118.0578),
    "tujunga":           ("Tujunga",             "Los Angeles", 34.2608, -118.2786),
    "valley-village":    ("Valley Village",      "Los Angeles", 34.1683, -118.3964),
    "walnut":            ("Walnut",              "Los Angeles", 34.0211, -117.8631),
    "west-covina":       ("West Covina",         "Los Angeles", 34.0686, -117.9386),
    "whittier":          ("Whittier",            "Los Angeles", 33.9792, -118.0328),
}

SAMEASES = [
    "https://www.facebook.com/eternallifehospiceinc",
    "https://www.instagram.com/eternallifehospice/",
    "https://www.linkedin.com/company/eternal-life-hospice/",
    "https://www.youtube.com/@EternalLifeHospice",
    "https://maps.google.com/?cid=9771388271577679785",
]

ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "4165 E Thousand Oaks Blvd, Suite 325B",
    "addressLocality": "Westlake Village",
    "addressRegion": "CA",
    "postalCode": "91362",
    "addressCountry": "US",
}

def build_block(city_name: str, county: str, lat: float, lng: float) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": ["MedicalOrganization", "LocalBusiness"],
        "@id": "https://eternallifehospice.com/#organization",
        "name": "Eternal Life Hospice, Inc.",
        "url": "https://eternallifehospice.com",
        "description": (
            f"Medicare-certified hospice care in {city_name}, {county} County "
            f"\u2014 serving {city_name} and surrounding communities."
        ),
        "telephone": "+18059537273",
        "email": "info@eternallifehospice.com",
        "hasMap": "https://maps.google.com/?cid=9771388271577679785",
        "sameAs": SAMEASES,
        "address": ADDRESS,
        "areaServed": [
            {"@type": "City", "name": f"{city_name}, California"},
            {"@type": "AdministrativeArea", "name": f"{county} County, California"},
        ],
        "medicalSpecialty": "https://schema.org/Hospice",
        "image": "https://eternallifehospice.com/assets/og-image.jpg",
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": lat,
            "longitude": lng,
        },
    }


def inject_block(content: str, block: dict) -> str:
    """Insert JSON-LD script after the last existing ld+json block."""
    json_str = json.dumps(block, indent=2, ensure_ascii=False)
    new_script = f'\n<script type="application/ld+json">\n{json_str}\n</script>'

    # Find the last ld+json closing tag
    matches = list(re.finditer(
        r'<script type="application/ld\+json">.*?</script>',
        content, re.DOTALL
    ))
    if not matches:
        # Fallback: insert before </head>
        return content.replace('</head>', new_script + '\n</head>', 1)

    last_end = matches[-1].end()
    return content[:last_end] + new_script + content[last_end:]


def process_files(dry_run: bool = False):
    files = sorted(glob.glob('website/elh-preview/hospice-*-ca.html'))
    files = [f for f in files if 'ventura-and-los-angeles-county' not in f]

    skipped = 0
    updated = 0
    errors = []

    for filepath in files:
        slug = filepath.replace('website/elh-preview/hospice-', '').replace('-ca.html', '')

        with open(filepath, encoding='utf-8') as fh:
            content = fh.read()

        if 'areaServed' in content:
            skipped += 1
            continue

        if slug not in CITY_DATA:
            errors.append(f"MISSING DATA: {slug}")
            continue

        city_name, county, lat, lng = CITY_DATA[slug]
        block = build_block(city_name, county, lat, lng)

        # Validate the block serializes cleanly
        try:
            json.loads(json.dumps(block))
        except Exception as e:
            errors.append(f"JSON ERROR for {slug}: {e}")
            continue

        new_content = inject_block(content, block)

        if dry_run:
            print(f"[DRY RUN] Would update: {filepath} ({city_name}, {county} County)")
        else:
            Path(filepath).write_text(new_content, encoding='utf-8')
            print(f"Updated: {filepath}")

        updated += 1

    print(f"\nSummary: {updated} updated, {skipped} skipped (already have areaServed), {len(errors)} errors")
    for e in errors:
        print(f"  ERROR: {e}")
    return errors


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    errors = process_files(dry_run=dry_run)
    sys.exit(1 if errors else 0)
