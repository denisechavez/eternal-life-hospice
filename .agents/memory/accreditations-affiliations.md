---
name: Accreditations & Affiliations trust section
description: The on-site credentials trust block, what may be listed, and why per-org verification deep-links are avoided
---

# Accreditations & Affiliations (homepage trust section)

A dedicated `#accreditations` section lives on the homepage (`index.html`,
inline-CSS, placed just before `<!-- LEAD CAPTURE -->`). It shows ELH's three
held credentials as badge cards (reuses `assets/img/cred-{cms,cdph,achc}.png`)
with a "Verify ↗" link to each issuer's official lookup, plus a compliance note.
This is separate from the animated `.cred-strip` marquee (which stays; it links
to the accreditor homepages, this section links to verification portals).

## Rule: list only credentials/memberships ELH actually holds
- Held today: Medicare-certified (CCN **B31709**, certified 21 Jan 2022),
  CDPH-licensed, ACHC-accredited. These are safe to show.
- Association memberships (CHAPCA, National Alliance for Care at Home) and new
  directory listings (Caring.com, HospiceDirectory.org) are **NOT joined/live
  yet** (see `exports/seo/directory-listings-playbook-2026-07-14.md` progress
  tracker — all boxes unchecked). Do NOT add badges for them until joined & the
  listing is live. An HTML comment marks where a new `.accred-card` goes.
- **Why:** compliance posture bans false-affiliation/endorsement; a badge for an
  unheld membership is exactly that.

## Verify links point to official PORTALS, not per-org deep-links
- Medicare-certified → `medicare.gov/care-compare/?providerType=Hospice`
- CDPH-licensed → CDPH Cal Health Find home
- ACHC-accredited → `achc.org/search-facilities/`
- **Why:** the Medicare Care Compare per-org deep-link
  `/care-compare/details/hospice/B31709` does NOT resolve — it errors
  "Could not load provider details" and bounces to the Care Compare welcome
  page (verified via real-browser screenshot; Care Compare's provider id differs
  from the aggregator-listed CCN). Don't ship a per-org Care Compare deep-link
  built from the CCN; link the official search/verify portal instead.
- **How to apply:** if a stable per-org verified profile is later confirmed in a
  real browser, swap the portal link for it; never trust a curl/webFetch 200 on
  Care Compare (it's an SPA that returns 200 + welcome shell for bad ids).
