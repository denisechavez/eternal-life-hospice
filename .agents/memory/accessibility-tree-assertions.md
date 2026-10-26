---
name: Accessibility-tree assertions
description: Reading announcement text from Chromium accessibility snapshots.
---

Reconstruct accessible text by traversing child IDs from the relevant region rather than joining the flat accessibility response.

**Why:** Chromium's flat response can place a link's text after unrelated nodes instead of inside its surrounding sentence. Joining that response creates false failures even when the complete message is exposed correctly.

**How to apply:** In browser announcement tests, assert the region's live priority and atomic property, then traverse its subtree to compare the exposed message. These checks verify browser semantics, not actual speech from a particular screen reader.
