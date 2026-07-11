---
name: Google Business Profile linkage
description: Which Google Maps listing is canonical for ELH, the retired duplicate to avoid, and how the site links to it.
---

# Google Business Profile (local SEO)

## Canonical listing
- The live, user-managed profile is named exactly **"Eternal Life Hospice"** (KG id `/g/11z90ngwsq`).
- Canonical URL used sitewide: **`https://maps.google.com/?cid=9771388271577679785`** (CID = decimal of `0x879af1dca9ce47a9`, taken from the user's own Maps place link).
- Linked from the site in two ways: `"hasMap"` + 7th `sameAs` entry in the 19 full org JSON-LD blocks, and the visible footer address link on every page.

## Retired duplicate — do NOT link it
- An older listing **"Eternal Life Hospice, Inc."** (place_id `ChIJ8TnEjG4l6IARTsNF_xMDyyI`, CID 2507101001983837006) still shows in Google. The user "took it down" but it lingers; its old website eternallifehospiceinc.com now redirects to eternallifehospice.com.
- The site's city pages used to carry this place_id in `hasMap` and the footer address link — all replaced July 2026. **Why:** splitting signals across two listings dilutes local ranking; only the canonical CID may appear in code.
- **How to apply:** any new page/collateral linking Google Maps must use the canonical CID URL. If the duplicate resurfaces, the fix is on Google's side (suggest-edit "permanently closed"/merge via GBP support), not in code.
- Old web presences still indexed (confusing NAP signals): eternalhospice.com (yahoo email, old hours) and eternallifehospiceinc.com — worth cleaning up/redirecting at the source when possible.
