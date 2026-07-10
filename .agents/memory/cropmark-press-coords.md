---
name: Crop-mark press sheet coordinate spaces
description: Why card content drifted below trim in the referral-card crop-mark press script, and the two-space coordinate rule that fixes it.
---

# Crop-mark press sheet: two coordinate spaces

`scripts/build-referral-card5-cropmarks-press.py` assembles a print sheet with
crop marks (in `.sheet`) around a card + its edge-clamp bleed ring (children of
an absolutely-positioned `.bleed` container that is itself offset by `MARGIN`).

**Rule:** crop marks use SHEET coordinates; anything inside `.bleed` must use
bleed-LOCAL coordinates (`sheet coord - MARGIN`). Mixing them double-counts
`MARGIN` and shifts the whole card down-and-right relative to the crop marks,
which quietly pushes bottom content (the gold tagline) past the trim line.

**Why:** the bug looked like a trim/geometry error but the crop marks measured
correct — only the card was shifted, because the fg/clamp pieces used sheet
coords while sitting inside the MARGIN-offset `.bleed`.

**How to apply:** when adding/adjusting pieces inside `.bleed`, use the local
constants (FL/FT/FR/FB/BL/BT), not the sheet-space ones (FGL/FGT/BE_*/TX/TY).

**Second fix in same script:** cards are rasterized (chromium print-to-pdf of the
exact standalone layout → pdftoppm 600 DPI) and placed as fixed `<img>`. Placing
the card as nested HTML let it reflow inside the absolutely-positioned/zoomed
container and drift ~17pt vs the standalone layout. A raster of the true
standalone render cannot reflow, so trim fidelity is exact.

**QA:** crop page 2 to the trim box (300 DPI: `pdftoppm -x 112 -y 112 -W 1101
-H 2550`) and confirm the bottom tagline is fully inside. Assert 2 pages /
318x666pt / CMYK / 0 DeviceRGB, and that the MOO deliverable files stay
byte-untouched (`git status --porcelain` on them = empty).
