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

## MOO variant (the size actually ordered — FULL SCALE, no cutting)
Variant script `scripts/build-referral-card5-moo-print.py` (derived from the main
script, keep in sync). MOO template spec: bleed 3.83×8.66in / trim 3.67×8.5 /
safe 3.5×8.34 (0.08in per side). Page = full bleed (chromium emits 276×624pt —
assert that), NO crop marks (MOO trims). Design fills the ENTIRE card: content
scaled via CSS zoom 1.048571 on .art (design units: art 263.25×595.15pt, bleed
≈5.5pt/side), extra height absorbed by enlarged section gaps; bottom groups
re-anchored bottom:0 to true bleed edge (front footer h56.5 pad-b 5.5; back bar
h42.5 pad-b 4.5). Wrap fixes at this scale: back checklist margin 19pt, office
row margin 22pt/padding 6pt. Note zoom divides effective image dpi (~718 floor —
still fine). Deliverables split with pdfseparate into ...MOO-rack-FRONT/BACK-CMYK.pdf.

**Why:** locked after ~23 iterations with the user; email/logo sizes/lockup proportions all deliberate.
**How to apply:** future referral cards start from this layout; do not re-explore logo treatments (cream mark on plum, gradient mark only on light backgrounds).

## MOO safe-zone fix (July 2026, locked)
Rule: at MOO scale (bleed 3.83x8.66 / trim 3.67x8.5 / safe 3.5x8.34), every element must fit the SAFE area, which in design units (pre-zoom 1.048571) is ~240pt wide — narrower than the original 252pt trim the layout was designed for.
**Why:** the original front credential band (gap 17, CMS/Epic 24/64, CDPH 50, ACHC 34) totaled ~260pt and crossed the trim line — logos would be physically cut.
Locked MOO values: front band gap 11pt, CMS/Epic max 23/60pt, CDPH 46pt, ACHC 32pt; front address 8.2pt; back credential bar 6.4pt/0.9pt letter-spacing; art overfill 263.6x595.5pt (seals right-edge white seam).
**How to apply:** after any layout edit, render 300dpi and measure content extents vs safe px 50..1100 (trim 24..1126) before delivering.

## Wordmark font spec (July 2026, locked)
The front-cover "Eternal" wordmark must be Fraunces weight 455 with font-variation-settings 'opsz' 58 (30pt).
**Why:** default rendering (weight 480, auto opsz) was visibly chunkier than the brand logo master; the master uses Fraunces' display cut. Measured width/height ratio of master wordmark = 4.335; 455/58 renders 4.25-4.31 (closest match; opsz 144 too narrow at 3.62, no-opsz too wide/heavy).
**How to apply:** any HTML re-creation of the logo lockup needs the explicit opsz setting — Chromium does NOT auto-apply a matching optical size. Verify vs brand-assets/Medical/eternal-life-hospice-logo-cream-gold-subtitle.png at equal cap height.
Brand palette confirmed identical to site: deep #3C1C3B, plum #5B2E59, gold #C9B07E, cream #F5F0EB (CMYK PDF round-trips deep plum exactly).

## July 2026 revision (current state)
- FRONT cream band: label "CREDENTIALS & CERTIFICATIONS" (6.2pt/1.8ls, #A8874F) above CMS/CDPH/ACHC (22/42/30pt); Epic REMOVED; band height 62pt (bottom edge unchanged 56.5pt).
- BACK: credential-logo row REMOVED (text line MEDICARE-CERTIFIED · CDPH-LICENSED · ACHC-ACCREDITED remains in footer). New group "COORDINATED SECURE COMMUNICATION" (6.6pt/1.9ls) with 5 referral-platform logos in white chips, 3+2 rows: Aidin 11pt / naviHealth 17pt / WellSky 10.5pt, then AIDA 13pt / Ensocare 17pt.
- Platform logos live in brand-assets/ELH-affiliates-and-partners/ (aida.svg, aidin.png, navihealth.png, ensocare.png, wellsky.png) — user-supplied.
- **Compliance caveat (told user):** third-party platform logos on print collateral = nominative use only; user confirmed direction but should only print if ELH actively receives referrals on each platform.
