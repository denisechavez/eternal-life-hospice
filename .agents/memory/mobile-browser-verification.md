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
