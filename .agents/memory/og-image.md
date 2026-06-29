---
name: OG / social share card
description: How the eternallifehospice.com share-preview image is made and how to update it.
---

# OG / social share card

The link-preview image lives at `assets/og-image.jpg` (1200×630). **Every page
references the same file** (`https://eternallifehospice.com/assets/og-image.jpg`),
except a few that point at their own hero (sound-bath, carebidet, city pages).
So replacing that one file updates the share card site-wide — no HTML edits.

**How it's generated:** build a temporary `og-card.html` at the repo root
(website/elh-preview/) styled with the site's embedded Fraunces + Jost @font-face
(the `inline-*.woff2` files), render it headless, then downscale:
```
chromium --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1200,630 --virtual-time-budget=4000 \
  --screenshot=/tmp/og.png http://localhost:5000/og-card.html
magick /tmp/og.png -resize 1200x630! -quality 90 -sampling-factor 4:2:0 -strip assets/og-image.jpg
```
Then **delete og-card.html** so no stray indexable page ships on this SEO-locked
site. Chromium binary is at a nix path (just call `chromium`).

**Gotcha:** headless `--window-size=1200,630` renders a viewport ~29px taller
than requested, leaving a white band at the bottom. Fix: size the card with
`100vw/100vh` and give `html,body` the dark plum background so it always fills,
then force-resize to 1200×630. **Why:** fixed `630px` heights leave the gap.

**Design language (current "elegant" card):** soft plum radial gradient, fine
double gold hairline frame, cream Fraunces headline with the middle word in
*italic* + gold tint, gold hairline+diamond divider, letter-spaced Jost tagline.

**Note:** the "share.google" label users sometimes see under the preview is
Google's own share-link wrapper, NOT controlled by our meta tags — sharing the
direct eternallifehospice.com URL shows the real domain.

## Plum-metallic logo (logo-plum.png)
- Only a cream/silver logo PNG exists (logo-cream.png, transparent bg). For LIGHT grounds, a flat plum fill loses the metallic sheen and a dark medallion behind cream logo reads "mortuary."
- Make a plum-metallic by mapping the logo's luminance through a plum gradient CLUT (deep plum shadows -> light lilac highlights), preserving alpha:
  - extract alpha; grayscale the RGB; `-sigmoidal-contrast 4,55%` to boost ribbon contrast; `-clut` with `gradient:"#200c24"-"#b585b0"`; re-apply alpha via CopyOpacity.
- **Why:** keeps the metallic ribbon shine while staying readable on cream — solves the "feels like a mortuary" complaint without any dark mass.
