---
name: Print-ready files (rack cards, flyers, etc.)
description: How to produce print-ready PDFs for Eternal Life Hospice from HTML.
---

# Print-ready files

Deliverables go in repo-root `exports/` (NOT in `website/elh-preview/`, which is
the deployed site). Build temp `rack-*.html` / `*-print.html` in the elh-preview
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
metallic sheen, no holes) on cream grounds. `logo-plum.png` is only 360px = too
low-res for large print. `logo-eternal.png` has an opaque white box (bad on cream).
