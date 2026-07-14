---
name: media-kit page
description: Durable lessons for the /media-kit digital press+referral kit and the ELH print source files
---

- [Pillar rack cards are genuinely DOUBLE-SIDED with DISTINCT backs](#) — the 4 "Eternal Standard" rack cards (source `J52551_RubenA_948_RACK_CARD-0{1..4}...p1/p2`) each have a front (p1 = the pillar) AND a back (p2). The backs SHARE the "The Eternal Standard / four-pillar rail" left column but the right column is different per card (card1=What Clinical Confidence Means, card2=First 48 Hours + What Families Can Expect, card3=Comfort Is More Than Medication + Holistic Modalities, card4=Compliance-Led Care). **Why:** a digital "reading order" of the physical kit must interleave front→back for all four cards (not just show 4 fronts + one back) or it silently drops 3 pages of real content. **How to apply:** full reading order = folder cover, welcome, coverage, 24/7 nurse flap, then card1 front/back … card4 front/back, then back cover (13 pages).

- [Referral card is 4×9 both faces — crop by edge-columns, NOT density](#) — the referral back has a cream-background footer (EHR platform logos + contact). A density/longest-run crop silently drops that low-density footer (wrong ~0.81 aspect vs the front's ~0.45). Same trap applies to any card back with a pale footer. **How to apply:** crop with the edge-column trimbox method (x-extent = columns with colden>0.45; y-extent from left/right edge strips; +9px inset); verify front & back come out the same size.

- [Kit page JPGs are the single source for BOTH the viewer and the PDFs](#) — `assets/kit/*.jpg` drive the on-page flipbook/gallery AND the download PDFs (`assets/downloads/*.pdf`, mirrored to `exports/digital/`). **How to apply:** any change to a page image means rebuilding the affected PDF from the same JPGs so viewer and download stay identical.

- [Site-chrome links must be root-absolute to survive nested pages](#) — the site has pages in subdirs (`blog/`, `care-brief/`, `resources/`). Those pages write existing chrome links as `href="../family-guide"` (depth-relative) or `href="/refer"` (root-absolute). A bare `href="media-kit"` resolves to `/blog/media-kit` → 404. **Why:** sed-injecting a bare relative link across all pages breaks it everywhere except the site root. **How to apply:** inject site-wide nav/footer links as root-absolute (`/media-kit`), matching the sibling `/refer`.

- [Downloads must live INSIDE website/elh-preview/ to publish](#) — only that folder deploys to Netlify. Website download buttons point at `assets/downloads/*.pdf`; `exports/` copies are repo deliverables only and are NOT reachable by the live site.

- [Flipbook engine mirrors family-guide](#) — same bootveil + booklet/scroll toggle + page-turn timing; see `family-guide.md` for the shared gotchas (timing duplicated in CSS+JS, reduced-motion last-in-source-wins, and screenshots only capture the cover so QA via curl/asset-200s). Page count is derived at runtime from the DOM, so adding/removing pages needs no JS change. On-brand QR built by `scripts/build-media-kit-qr.py` (adapted from `build-refer-qr.py`).
