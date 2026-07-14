---
name: Media Kit flipbook mechanics
description: How the /media-kit open-book flipbook stays pixel-sharp and animates page turns; the transitionend gotcha that truncates the flip.
---

# Media Kit flipbook — "static spread + transient leaf"

The /media-kit viewer is a **two-page side-by-side open-book spread** (center spine;
right page peels onto the left). Its architecture is deliberately split so pages are
**pixel-sharp at rest**:

- Resting pages are plain **untransformed** `<img>` (`#pgL` / `#pgR`) inside uniform
  `.sheet` boxes. No 3D transform while idle.
- A single absolutely-positioned `.leaf` (`#lfF` front / `#lfB` back) is the **only**
  element that ever gets `rotateY` + `backface-visibility`, and only during the ~1s turn.
  On completion it resets and `renderStatic()` repaints both sides flat.

**Why:** applying a 3D transform (even `rotateY(0)`) to a retina element forces it onto a
rasterized GPU layer at CSS-pixel resolution → visibly blurry text. Keep transforms off
resting pages entirely; confine them to the transient leaf.

## Spread / turn model
- `SPREADS` = 7 states: `{one:0}` (front cover), 5 interior `{l,r}` pairs, `{one:11}`
  (back cover). `one` = single centered page.
- `leafTurn()` runs ONLY between two **adjacent, both-non-single** spreads. Cover
  open/close and back cover (single↔spread) and non-adjacent dot jumps use `crossFade()`.
- Uniform sheet `aspect-ratio:1620/2500` + `--paper` bg + `object-fit:contain`
  letterboxes the varying-aspect pillar cards. **Do NOT pad the image files** — the PDF
  builder (`scripts/build-media-kit-pdf.py`) must stay synced to the same assets/order.
- Page data (src + cache-buster + alt) is single-sourced by reading it out of the 12
  gallery `.page` `<img>` elements. Gallery ("scroll") view remains the rich mobile fallback.

## GOTCHA: transitionend truncates the flip
A `transitionend` listener on `#leaf` MUST filter `e.target===leaf && e.propertyName==='transform'`.
`.leaf .face::after` (the sweep-shadow) has its own `transition:opacity .5s`; pseudo-element
transitionend dispatches on the owning `.face` and **bubbles** to `#leaf`. Unfiltered, it
fires end() at ~0.5s and snaps the page shut halfway through the 1s turn (end state still
looks correct, so static screenshots hide the bug). Keep a no-arg safety `setTimeout(end,1300)`
and let the no-event path through.

**Mobile drift:** no dedicated single-leaf mobile fallback — <820px scales the spread down
with tap-to-enlarge; Gallery view is the rich fallback. Accepted.
