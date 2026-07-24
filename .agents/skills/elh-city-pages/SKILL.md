---
name: elh-city-pages
description: Build, update, and maintain the Eternal Life Hospice city landing pages (hospice-CITY-ca.html). Use when adding a new city page, replacing a city hero photo, auditing city page quality, or sourcing location-identifiable photos for any of the 58+ service-area cities across Ventura and Los Angeles County.
---

# ELH City Pages — Build & Maintain

## City Page Inventory

58 city pages at `website/elh-preview/hospice-{slug}-ca.html`.
The county hub page is `hospice-ventura-and-los-angeles-county-ca.html` (photo hero + map section).
Photos: `website/elh-preview/assets/img/city/{slug}.jpg` (1536×1024, 82% quality JPEG).

## Photo Standards

Every page must have a **clearly identifiable** city-specific photo — a local landmark a resident would recognise:
- City hall, historic downtown main street, iconic park, cultural institution, harbour/beach, famous building
- **Not acceptable**: generic aerial, anonymous street corner, neighbourhood map, plain valley panorama

### Preferred Sources (CC-licensed, free to use)
1. **Wikimedia Commons** — best quality, CC-licensed. Search pattern:
   `https://en.wikipedia.org/wiki/CITY_NAME,_California` → read the infobox image or body images.
   Download via the Wikimedia file page `/wiki/File:FILENAME` → "Original file" link.
2. **imageSearch tool** with query like `"CITY NAME" California city hall OR downtown landmark site:commons.wikimedia.org OR site:upload.wikimedia.org`

### Download & Resize Pipeline

```python
import urllib.request, subprocess
UA = 'EternalLifeHospice/1.0 (https://eternallifehospice.com; info@eternallifehospice.com) Python/3.x'
# Download
req = urllib.request.Request(url, headers={'User-Agent': UA})
with urllib.request.urlopen(req, timeout=15) as r:
    open('/tmp/city_SLUG', 'wb').write(r.read())
# Resize to 1536×1024 center-crop
subprocess.run(['magick', '/tmp/city_SLUG', '-auto-orient',
    '-resize', '1536x1024^', '-gravity', 'Center',
    '-extent', '1536x1024', '-quality', '82',
    'website/elh-preview/assets/img/city/SLUG.jpg'])
```
Rate-limit Wikimedia: `time.sleep(2)` between downloads. Process in batches of 5.

## Hero HTML Pattern (city pages)

```html
<section class="hero hero--city hero--tall">
  <img class="hero-bg" src="assets/img/city/SLUG.jpg"
       alt="CITY NAME, California" width="1536" height="1024"
       loading="eager" decoding="async">
  <div class="eyebrow">SERVING CITY · REGION · LOS ANGELES COUNTY</div>
  <h1>Hospice Care in CITY NAME, California</h1>
  <p>Eternal Life Hospice provides physician-supported hospice care for eligible patients
     and families in CITY NAME and surrounding communities…</p>
  <div class="hero-btns">
    <a class="btn-gold" href="tel:18059537273">Call for Hospice Guidance</a>
    <a class="btn-ghost" href="family-guide">Read the Family Guide →</a>
    <a class="btn-ghost" href="refer">Refer a Patient →</a>
  </div>
</section>
```

## County Hub Page

`hospice-ventura-and-los-angeles-county-ca.html` uses:
1. `hero--city` photo hero (Conejo Valley panoramic) as the top section
2. A standalone map section (`service-hero-map.png`) directly below it
3. Standard body content (distinction, county quicknav with all 58 city links)

## Identifiability Check — Known Iconic Photos by City

| City | Photo subject |
|------|--------------|
| Sylmar | LA Aqueduct Cascades (Second Aqueduct Cascades) |
| Pacoima | Famous Pacoima murals |
| North Hills | Sepulveda & Plummer intersection |
| Panorama City | Panorama City neighbourhood aerial |
| Van Nuys | LA Municipal Court Van Nuys Division |
| Long Beach | Downtown skyline/harbour |
| West Hollywood | Sunset Tower, Sunset Blvd |
| Ojai | Ojai Valley / arcade arches |
| Rancho Palos Verdes | Pacific coastline |
| San Marino | Huntington Library Rose Garden |

## Fallback Detection

Run this to find any pages still using the generic fallback:
```bash
grep -l 'inline-cdca7d25f7' website/elh-preview/hospice-*-ca.html
```
Zero results = all pages have unique city photos.

## Adding a New City Page

1. Copy the closest existing city page as template
2. Update slug, title, meta description, canonical URL, BreadcrumbList JSON-LD, h1, eyebrow, body copy
3. Source a landmark photo using the pipeline above
4. Add `<img class="hero-bg">` in the hero section
5. Update `hospice-ventura-and-los-angeles-county-ca.html` county-quicknav section to include the new city link
6. Add the city to the sitemap (`sitemap.xml`)
