---
name: Media kit flipbook page order
description: The /media-kit flipbook mirrors a physical presentation folder; page order must follow book anatomy, not content grouping.
---

# Media kit flipbook = physical folder anatomy

`website/elh-preview/media-kit.html` is a flipbook that mirrors the **printed
press/media kit** (a die-cut presentation folder + the 4 Eternal Standard pillar
rack cards). It flips in **DOM order** — the JS just reads `querySelectorAll('#pages .page')`
and auto-numbers folios by index, so page sequence is controlled entirely by the
order of the `<section class="page">` elements.

**Required order (like a real book/folder):**
1. Front cover (`01-front-cover`)
2. **Inside front cover** = Welcome letter (`02-welcome`)
3–10. Interior content = the 4 pillar cards, front+back (`05`–`12`: Clinical,
   Guided, Comfort, Compliance)
11. **Inside back cover** = Coverage/insurance (`03-coverage`)
12. Back cover (`13-back-cover`)

**Why:** The user thinks of this as a book. The inside back cover is the *last*
inside page (facing the back cover), NOT the second page. Coverage was originally
placed at position 3 (right after the inside front cover) and the user flagged it:
"the 3rd page is actually the inside of the back cover." So `03-coverage` must sit
**just before** `13-back-cover`, and `02-welcome` stays as the inside front cover.

**How to apply:** When adding/reordering media-kit pages, keep book anatomy —
cover → inside front cover → interior → inside back cover → back cover. Don't sort
by asset filename number (03 is intentionally near the end). The same DOM order
also drives the Gallery/scroll view, so it stays consistent automatically.

The **downloadable PDF** must stay in the same order — rebuild it with
`scripts/build-media-kit-pdf.py` (its `PAGES` list mirrors this order and must be
kept in sync with the flipbook DOM). That script writes both the live-site copy
and the `exports/digital/` mirror in one run.
