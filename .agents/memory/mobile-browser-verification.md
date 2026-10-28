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

Resized Chromium viewports are not real software-keyboard verification.

**Why:** Desktop emulation can shrink both layout and visual viewports but
does not reproduce iOS visual-only panning, automatic input zoom, native
keyboard controls or autofill overlays.

**How to apply:** Report resized-viewport checks as emulation. Keep physical
device keyboard testing separate; never infer native keyboard usability
from passing headless geometry and focus-order checks.

For deterministic connection-failure coverage, abort at the browser request
layer rather than destroying the local fixture's HTTP socket.

**Why:** Chromium can transparently resend a POST after a socket closes,
consuming a queued retry response before the UI ever sees a failure.

**How to apply:** Keep failure injection local and count browser-level attempts;
do not assume one destroyed connection equals one failed user submission.

History traversal and back-forward cache restoration are different test outcomes.
Use `pageshow.persisted` plus document identity to establish a real cached restore,
not just a `back_forward` navigation entry.

**Why:** A no-store fixture can reload successfully on every Back/Forward traversal
while never exercising the old document's retained state. Cache-eligible fixture
HTML exposed actual cached restores in the same Chromium session.

**How to apply:** Test both reload and cached restoration without changing deployed
headers or API no-store protection. Report cache misses explicitly when the browser
cannot restore a document; never label a fallback reload as a cache hit.
