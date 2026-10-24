---
name: Mobile browser verification
description: Limits of synthetic pointer checks in headless mobile emulation.
---

Do not interpret a failed coordinate-based click in headless mobile emulation
as proof of a broken destination. Check the actual URL and compare layout
and visual viewport dimensions before changing application links.

**Why:** Desktop-to-mobile resizing in a single browser session produced a
wider layout viewport than the emulated screen. Synthetic mouse and touch
attempts did not navigate, while activating the same real anchor in the
browser reached the correct form at all tested widths.

**How to apply:** Test anchor navigation and destination visibility separately
from physical hit-target usability. Report browser anchor activation as such;
do not claim it verifies real touch gestures.

Desktop Chromium may reserve space for a vertical scrollbar, so its visual
viewport can be narrower than the requested layout viewport.

**Why:** Treating visualViewport.width as equal to the emulated width rejects
healthy desktop layouts. Smooth anchor scrolling can also still be moving
after the document and fonts finish loading.

**How to apply:** Compare the requested width with innerWidth, compare visual
viewport width with documentElement.clientWidth at scale 1, and wait for
anchor scrolling to settle before measuring visibility.
