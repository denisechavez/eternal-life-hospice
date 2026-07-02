---
name: Referral Card 5 — locked design layout
description: The approved, print-verified layout for the flagship referral rack card; replicate this design for future referral cards.
---

# Referral Card 5 — LOCKED design (user-approved, July 2026)

Source of truth: `scripts/build-referral-card5-print.py` (edit + rerun; asserts 2pp 288×594pt, auto-builds CMYK). Trim 3.5×7.75in, file 3.75×8in (0.125in bleed + crop marks). Outputs to `exports/print/` (RGB) and `exports/print/print-ready-cmyk/` (send-to-MOO file).

## Front (deep plum background, cream/gold type)
1. Logo lockup, centered: hi-res cream infinity mark image
   (`brand-assets/Medical/eternal-life-hospice-infinity-cream-hires.png`, 1111×490,
   cropped from logo-cream-gold-subtitle master; ~840dpi at 95pt display width)
   + "Eternal" Fraunces 30pt cream vector text
   + "LIFE HOSPICE" Jost 600, 8.2pt, letters justified across 73% of Eternal's width, centered
   (official master proportions: symbol 85% / LIFE HOSPICE 73% of Eternal — never wider).
2. Gold pill "SAME-DAY ADMISSION".
3. Headline "Refer in One Call," (Fraunces 22.5pt) / "Scan, Fax or E-mail" (15.5pt) /
   "Answered 24/7 by a hospice nurse".
4. Phone 805.953.7273 huge gold Fraunces; "Fax referrals · 805.953.8530" below.
5. Cream-framed QR (decodes to eternallifehospice.com/refer, infinity center badge) + "SCAN TO REFER ONLINE" gold letterspaced.
6. Cream credential band: CMS, CDPH, ACHC, Epic logos (front sizes: CMS/Epic 24pt, ACHC 34pt, CDPH 50pt).
7. Plum footer, centered: referral@eternallifehospice.com (11pt bold cream), address, "SERVING VENTURA & LOS ANGELES COUNTY" (padding-bottom 9pt).

## Back (cream background)
1. "QUICK REFERRAL GUIDE" eyebrow + "Signs It May Be Time" (Fraunces plum).
2. Cream-tint rounded box: 6 gold-check signs (hospital stays/ER, weight loss/appetite, infections, decline despite treatment, help with dailies, comfort-focused goals).
3. Deep-plum "THE ETERNAL DIFFERENCE" panel, gold sparkle bullets: full line of integrative services; clinical & mobile services at no expense to families; zero complaints in 11 years of care.
4. Two-line services strip: Same-day admission · Transport · 24/7 nurse / Physician-led · Placement · Bereavement.
5. Credential logo row (back sizes: CMS/Epic 22pt, ACHC 30pt, CDPH 46pt).
6. "REFER 24/7" contact card: QR left; CALL 24/7 + FAX bold plum (9.6pt); divider; EMAIL full-width row (9.4pt bold plum referral@); OFFICE address.
7. "SERVING VENTURA & LOS ANGELES COUNTY" + plum footer bar "MEDICARE-CERTIFIED · CDPH-LICENSED · ACHC-ACCREDITED" + gold Fraunces italic "Care That Honors Life".

## Print-readiness bar (verify every rebuild)
- All embedded images ≥750dpi (pdfimages -list on the CMYK file); gs step must keep
  -dDownsample*=false -dAutoFilter*=false -dColorImageFilter=/FlateEncode or it silently drops to 300dpi.
- All type vector (embedded CID TrueType / Type 3 outlines) — never rasterized text.
- QR must decode (opencv) to https://eternallifehospice.com/refer.
- Preview: pdftoppm -r 120 both pages → side-by-side PNG (gap 40) at exports/print/previews/referral-card-5-front-back.png.

## MOO variant (the size actually ordered)
MOO's rack card trim is 3.67×8.5in — larger than the 3.5×7.75 design. Variant script
`scripts/build-referral-card5-moo-print.py` (derived from the main script, keep in sync):
MOO template spec: bleed 3.83×8.66in / trim 3.67×8.5 / safe 3.5×8.34 (0.08in bleed per
side). Full-bleed page 3.83×8.66in (chromium emits 276×624pt — assert that), NO crop marks
(MOO trims), design top-aligned, plum extends through the extra ~0.75in at bottom,
dashed gold cut guide + label at the 7.75in line sitting entirely in the waste strip
(user makes ONE bottom cut → final 3.67×7.75; guide is removed by the cut).
Back checklist margin narrowed 25→22pt so "daily activities" line doesn't wrap.
Deliverables split with pdfseparate into ...MOO-rack-FRONT/BACK-CMYK.pdf (MOO wants
one file per side).

**Why:** locked after ~23 iterations with the user; email/logo sizes/lockup proportions all deliberate.
**How to apply:** future referral cards start from this layout; do not re-explore logo treatments (cream mark on plum, gradient mark only on light backgrounds).
