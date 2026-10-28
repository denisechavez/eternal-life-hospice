# Full-photo social image regression tests

From the repository root:

```sh
python3 -m unittest discover -s .agents/scripts/tests -v
```

Uses `unittest` and the renderer's existing Pillow/fontTools tooling, checked-in
Fraunces font and official reverse logo. No network, production dependency
changes, publication or approved-artwork regeneration.

The three fixtures are generated locally from fixed shapes and colors: a
near-white architectural wall, mottled foliage and a dark room. Both an existing
headline and a long, three-line headline run across GBP (1200×900), Facebook
(1080×1350), LinkedIn (1200×627) and Pinterest (1000×1500).

Checks cover:

- Upper-left shading on both axes, including negative controls for reversed masks.
- At least **3:1** cream-to-background contrast beneath every solid headline
  glyph pixel (large-text minimum). A second render with headline drawing
  suppressed supplies the background; measuring cream pixels in the completed
  image would give misleading results. Antialiased edges are excluded.
- Actual rasterized text bounds within the pinned title-safe region, font
  reduction for the long headline, explicit rejection of unfit text and a
  minimum 10%-of-height gap above the logo backing.
- Correct output dimensions, visible official logo pixels and unclipped logo
  ink. Landscape backing rectangles can intentionally bleed off-canvas.
- The real package-builder branch copying October 27 Facebook JPEG bytes and
  approved safe-area metadata unchanged, while rendering the other 19 images.
  This runs in a temporary directory using a local JPEG sentinel.

When the private approved reference exists at
`generated-artifacts/facebook-style-exploration/01-full-photo.jpg`, an additional
SHA-256 pin checks the actual October 27 approval. A clean checkout without this
ignored artifact skips only that pin; the byte-preserving package test always
runs. Do not update the pin to make a replacement image pass without approval.

These tests measure lossless renderer output, not third-party platform
recompression or subjective photographic suitability.
