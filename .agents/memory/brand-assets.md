---
name: Brand asset library (logos)
description: Where the ELH logo variants and third-party affiliate/partner logos are stored, and the compliance rule before any partner logo goes on the live site.
---

# Brand asset library

Repo-root **`brand-assets/`** is the organized logo library (NOT published — it
sits outside `website/elh-preview/`, so nothing here auto-deploys to the live
site). Two folders, named by the user:

- **`brand-assets/Medical/`** — Eternal Life Hospice's OWN brand logos (copies of
  the canonical site assets, given descriptive filenames): metallic-plum
  transparent (the primary mark), plum, cream, cream+gold-subtitle, plum/cream
  header versions, and the metallic-on-white-box variant (avoid on cream — the
  box shows). The live site keeps using the originals in
  `website/elh-preview/assets/` + `assets/img/`; this folder is the reference set.
- **`brand-assets/ELH-affiliates-and-partners/`** — 13 THIRD-PARTY logos supplied
  by the user (VNAA, Ventura County Homecare Assn, NAHC, Coalition for
  Compassionate Care of CA, ACHE, National Palliative Care Registry, Providence,
  Kaiser Permanente, Hoag, City of Hope, Epic, "Certified Consultant", AltaMed).

## Compliance rule — DO NOT publish partner/affiliate logos without review
Storing these for reference is fine. **Do not place any third-party
affiliate/partner logo on the live site (or in printed collateral) implying a
partnership, endorsement, or affiliation without an explicit compliance review.**
**Why:** for a Medicare hospice, implying a referral-source relationship can
raise Anti-Kickback / Stark exposure, and using another org's mark can be
false-affiliation / trademark misuse. Membership/accreditation marks (e.g. a
professional association you actually belong to) are only OK with proof of
current membership and the org's usage terms; hospitals/health systems
(Providence, Kaiser, Hoag, City of Hope, AltaMed) must NOT be shown as
"partners." Keep any future use factual and permission-backed.
**How to apply:** if asked to add these to a website "affiliations/partners"
section, flag this first and confirm membership/permission + framing before use.

## Official-logo rule for apps

Use an official Eternal Life Hospice logo asset in every ELH app and internal
product. Do not substitute a generic icon, initials, or a recreated wordmark for
the app-level brand identity.

For dark app headers and sidebars, the approved locked treatment is the
transparent stacked logo with translucent cream artwork and gold
“LIFE HOSPICE” lettering. Do not add a plaque, card, box, or other background
behind the logo, and do not recolor the logo with a custom gradient.

**Why:** The user established this as a standing brand rule so all ELH software
surfaces remain visibly authentic and consistent, then explicitly approved this
dark-surface treatment on September 21, 2026.

**How to apply:** Source the logo from `brand-assets/Medical/` or the canonical
public-site logo assets. Choose the approved color variant that preserves
contrast in its placement. For dark app chrome, use the cream-and-gold stacked
transparent asset without a backing shape.
