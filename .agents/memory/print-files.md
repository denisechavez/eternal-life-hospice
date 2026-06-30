---
name: Print-ready files (rack cards, flyers, etc.)
description: How to produce print-ready PDFs for Eternal Life Hospice from HTML.
---

# Print-ready files

Deliverables go in repo-root `exports/`, filed by type (NOT in
`website/elh-preview/`, which is the deployed site): `exports/print/` for
print-ready PDFs (rack cards, flyers, brochures), `exports/decks/` for
presentations. Keep filing tidy + descriptive filenames (user preference). Build temp `rack-*.html` / `*-print.html` in the elh-preview
root so they can load the inline brand fonts + assets over localhost:5000, render,
then **delete the temp HTML** (SEO-locked site must ship no stray pages).

**Sizing/bleed:** rack card = 4"×9" trim → build at **4.25"×9.25"** (0.125" bleed
all sides), 300 DPI. Keep important content ≥0.25" inside trim (the gold frame
sits ~0.2" inside trim). CSS: `@page{size:4.25in 9.25in;margin:0}` + a `.card`
sized in inches with `print-color-adjust:exact` so the cream bg bleeds full-page.

**Generate vector-text PDF** (sharper than raster) and merge sides:
```
chromium --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=/tmp/rack-front.pdf http://localhost:5000/rack-front.html
pdfunite /tmp/rack-front.pdf /tmp/rack-back.pdf exports/<name>.pdf
pdfinfo exports/<name>.pdf | grep "Page size"   # must read 306 x 666 pts = 4.25x9.25in
```
Verify the REAL pdf with `pdftoppm -r 150 -png` then view — the headless
*screenshot* viewport renders ~tall and shows a false white band at the bottom;
the PDF itself is correct. Output is RGB; most digital printers accept RGB + a
note that bleed is included. No TrimBox/crop marks are set (Chrome can't); fine
for online/office shops — just tell them "trim to 4×9, 0.125 bleed included."

**Logo:** use `assets/logo-eternal-trans.png` (661×525, white bg removed → keeps
metallic sheen, no holes) on cream grounds; `assets/logo-cream.png` (all-cream)
on dark/plum grounds. `logo-plum.png` is only 360px = too low-res for large
print. `logo-eternal.png` has an opaque white box (bad on cream).

**Slim referral rack cards (Moo, fits inside presentation folder):** trim
**3.5×7.75in**, 0.125 bleed → art 3.75×8.0in. Crop marks ARE wanted: build the
`@page` slightly larger (**4.0×8.25in**, pdfinfo = 288×594pts) and draw the 8
trim ticks yourself as thin abs-positioned `<div>`s in the .page (Chrome can't
emit real TrimBox). Layout: `.page`(4.0×8.25) → `.bleed`(abs inset 0.125in,
3.75×8.0, holds full-bleed bg) → content padded `--safe:0.375in` (=0.25 trim +
0.25 safe... actually 0.125 trim-inset + 0.25 safe). Put 2 .page divs (front+back)
in ONE html w/ `page-break-after:always` → 2-page PDF in one render, no pdfunite.
Escape literal `%` in any CSS passed through Python `%`-formatting (gradients,
50%, 100%) — easier to token-replace color vars than `%`-format.

**QR asset:** `assets/qr-eternallifehospice.png` (reusable, plain plum-on-white, no
logo) → https://eternallifehospice.com, made with python `qrcode` (ECC Q, version 3).
Verify it decodes: `pip install opencv-python-headless` then
`cv2.QRCodeDetector().detectAndDecode()` (pyzbar/zbar not installed). Concept-art QR
is decorative — never reuse it.

**Referral-page QR (`/refer`):** `scripts/build-refer-qr.py` generates the two
masters encoding https://eternallifehospice.com/refer at **ECC level H** (so the
centered infinity badge survives): `assets/qr-refer.png` (1480px, deep-plum #3C1C3B
on WHITE, for print on light tiles) + `assets/img/qr-refer-cream.png` (1024px, plum
#5B2E59 on CREAM #F5F0EB, light-backed variant for dark surfaces, matches the footer
qr-cream.png look). The infinity glyph (with its metallic gradient) is lifted from
qr-cream.png's center, not redrawn. Script self-verifies via cv2 decode. The 5
referral cards carry /refer; the footer QR, the reusable site QR, business cards and
the 4 pillar rack cards stay on the homepage (general brand, not the referral CTA).

**Swapping a QR inside an already-built card PDF (no source HTML survives):** the 5
referral-card masters embed the QR as a 1480×1480 FlateDecode ICCBased-RGB bpc8 image
XObject (same dims as the source QR png). Replace it in place with pikepdf — find the
Image XObject where Width==Height==1480, then `obj.write(zlib.compress(rgb_bytes),
filter=pikepdf.Name.FlateDecode)` (pikepdf.write expects data ALREADY encoded for the
declared filter; raw must be 1480*1480*3 bytes = `Image.convert('RGB').tobytes()`),
delete any /DecodeParms, keep Width/Height/ColorSpace. Then regenerate the CMYK copies
from the updated RGB masters with the ghostscript command below. Verify each PDF by
`pdftoppm -r 200 -png` + cv2 decode → must read the /refer URL; page size stays
288×594pts. (card5 references the same QR XObject on both pages — replacing once
updates both.)

**Business cards (double-sided, Moo):** trim **3.5×2.0in**, 0.125 bleed → art
3.75×2.25; build `@page` at **4.0×2.5in** (pdfinfo = 288×180pt) with the same 8
hand-drawn corner crop ticks + 2 `.page` divs (front/back) → 2-page PDF in one
render. Front = name/title + logo-eternal-trans lockup + contact + credentials/
coverage footer; back = logo-cream on plum gradient + tagline + reusable QR.
Generator: `scripts/build-business-cards.py` (edit CARDS dict, writes HTML into
elh-preview, render, move PDF to exports/print/, DELETE temp HTML). Editable
template + specs live in `exports/print/`. Personal emails are drafts
(firstname@eternallifehospice.com) — flag to confirm before printing. CEO title
used (not "founder-led", per valuation optics).

**LOCKED brand CMYK / Pantone (for ALL print collateral).** Cards are built in
RGB then converted; a press auto-converting RGB→CMYK shifts plum (muddy/blue) and
gold (flat). Lock to these (CMYK = faithful ghostscript SWOP-style conversion of
the brand RGB, also what the delivered CMYK PDFs contain):
- Deep plum `#3C1C3B` → C69 M90 Y45 K53 → ~PANTONE 5185 C / 519 C
- Plum      `#5B2E59` → C65 M90 Y37 K28 → ~PANTONE 518 C
- Gold      `#C9B07E` → C22 M28 Y57 K0  → ~PANTONE 4525 C (metallic alt 871 C)
- Cream     `#F5F0EB` → C2 M4 Y6 K0     → ~paper white / PANTONE 9043 C
Press fixes if proof is off: deep plum muddy → drop Yellow ~8-12pts; gold flat →
hold Y57, add ≤4K, never add Cyan (→olive). Pantone = closest visual ref only,
confirm against a Color Bridge book.

**Brand color swatch sheet (`exports/print/eternal-life-brand-color-reference-cmyk.pdf`).** A one-page **Letter** (8.5×11, NOT a rack-card size) CMYK reference to send with every print job: 2×2 grid of the four locked colors as printed patches, each labelled with its CMYK build + HEX + closest Pantone, plus the press-fix notes. Built the same vector way (temp `swatch-sheet.html` in elh-preview → chromium print-to-pdf → ghostscript RGB→CMYK below → delete temp html). Patches are filled with the brand **HEX**; the gs default conversion lands them exactly on the locked CMYK (verified: deep plum→69/90/45/53, plum→65/90/37/28, gold→22/28/57/0, cream→2/4/6/0), so the sheet's swatches and its printed numbers agree. Keep content tight (patch ≤1.2in, ~0.5in page padding) or it spills to a 2nd page — always `pdfinfo | grep Pages` must read **1**. Referenced in referral-rack-cards-PRINT-SPECS.txt.

**Make a press-ready CMYK PDF from an RGB one** (ghostscript installed via
`installSystemDependencies(["ghostscript"])`; no bundled iccprofiles dir, uses
gs built-in default CMYK — fine, fully converts vectors AND embedded images):
```
gs -q -dBATCH -dNOPAUSE -dSAFER -sDEVICE=pdfwrite \
  -dProcessColorModel=/DeviceCMYK -sColorConversionStrategy=CMYK \
  -dOverrideICC=true -dPDFSETTINGS=/prepress -dAutoRotatePages=/None \
  -o out-CMYK.pdf in.pdf
```
Verify: `data.count(b"DeviceRGB")==0`; read back CMYK by decompressing Flate
streams and regexing `([0-9.]+ ){4}[kK]`. Page size preserved (288×594pts).
Referral cards: keep RGB masters in `exports/print/`, ship the CMYK copies in
`exports/print/print-ready-cmyk/` (suffix `-CMYK`). The full kit (press-kit folder + 4 pillar cards + old rack card) is also CMYK-converted into `print-ready-cmyk/press-kit/` with a README manifest of files-to-send. Not every card uses every
brand color (e.g. card-5 minimal has its own plum/cream tints) — that's expected.
