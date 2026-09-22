---
name: Google Business Profile linkage
description: Verified canonical Google Business Profiles for Eternal and Westlake, plus the retired Eternal duplicate that must remain blocked.
---

# Google Business Profile (local SEO)


## Eternal and Westlake are separated
- As verified through Google Places on September 20, 2026, Eternal uses CID `9771388271577679785`, phone `(805) 953-7273`, `eternallifehospice.com`, and Suite 325B.
- Westlake uses a distinct CID `5753774355151396017`, phone `(818) 791-0611`, `westlakevillagehospiceinc.com`, and Suite 325D.
- **Why:** these matching agency details and distinct identifiers prevent referrals, reviews, and local-search signals from crossing between the two businesses.
- **How to apply:** Eternal's site may use only Eternal's verified identifier. Keep Westlake's CID, Place ID, phone, and domain blocked from Eternal public files.

## Retired duplicate — do NOT link it
- An older listing **"Eternal Life Hospice, Inc."** (place_id `ChIJ8TnEjG4l6IARTsNF_xMDyyI`, CID 2507101001983837006) still shows in Google. The user "took it down" but it lingers; its old website eternallifehospiceinc.com now redirects to eternallifehospice.com.
- The site's city pages used to carry this place_id in `hasMap` and the footer address link — all replaced July 2026. **Why:** splitting signals across two listings dilutes local ranking; only the canonical CID may appear in code.
- **How to apply:** if the duplicate resurfaces, the fix is on Google's side (suggest-edit "permanently closed"/merge via GBP support), not by pointing Eternal pages to Westlake's profile.
- Old web presences still indexed (confusing NAP signals): eternalhospice.com (yahoo email, old hours) and eternallifehospiceinc.com — worth cleaning up/redirecting at the source when possible.

## September 22, 2026 identity collision
- Google’s live Places record for Eternal’s canonical CID became a hybrid: Westlake’s name and main phone `(805) 870-0103`, Eternal’s Suite 325B address and website.
- Google simultaneously retained Westlake’s separate Suite 325D record with `(818) 791-0611`, so this is an entity conflation rather than a simple phone-field typo.
- **Why:** both hospices share a building, category and related ownership, while Westlake’s own site, NPI record and directories correctly associate its main number `(805) 870-0103` with Westlake. Google’s reconciliation can overwrite a manual correction when its entity graph remains merged.
- **How to apply:** do not keep correcting only the phone. Escalate the hybrid CID to Google Business Profile support as an incorrect merge, providing both legal names, suites, phones, domains and distinct Place IDs/CIDs.
