---
name: Sticky vs overflow trap
description: Why position:sticky (pillar stack, sidebars) silently breaks on the ELH site, and the correct overflow pattern.
---

# position:sticky breaks when html gets `overflow-x:clip` while body has `overflow-x:hidden`

**Rule:** for horizontal-scroll protection on pages that also use `position:sticky`,
use `overflow-x:clip` on BOTH `html` and `body`. Never leave `body{overflow-x:hidden}`
once `html` has any non-visible overflow.

**Why:** `overflow-x:hidden` forces the other axis to compute to `auto`, making that
element a scroll container that "captures" descendant sticky elements. It only *seems*
harmless on `body` because, when `html` overflow is `visible`, the browser propagates
body's overflow up to the viewport and body stops acting as its own scroller — so
sticky still sticks to the viewport. The moment `html` gets `overflow-x:clip` (or any
non-visible value), that propagation stops, `body` becomes a real scroll container, and
every `position:sticky` inside it stops working. `clip` is the fix because it does NOT
force the other axis to `auto`, so the element never becomes a scroll container.

**How to apply:** ELH homepage sticky pillar stack (`.pcard`/`.pstack`, `#standard`) and
the amethyst gem sidebar rely on this. If sticky "stops working" after an unrelated CSS
tweak, check the `html`/`body` overflow pair first — not the sticky element itself. The
CSS on the sticky element is almost always fine; the ancestor overflow chain is the
culprit.

## Scrolling to a position:sticky target
`getBoundingClientRect().top` on a *stuck* sticky element returns its pinned
(painted) position, not its flow position — so `rect.top + scrollY` collapses to
~the current scroll and a smooth-scroll "goes nowhere." For scroll targets in a
sticky-stack (e.g. index.html Four Pillars `.pcard`s / `#stack-N`), sum
`offsetTop` up the `offsetParent` chain for the true flow offset, then subtract
the header height (`--hdr-h`). `scrollIntoView()` has the same stuck-position bug.
