---
name: Shared chrome accessibility
description: Propagation and selector rules for accessible shared headers and footers.
---

Footer changes must be propagated through both standard-page synchronization and city-page regeneration. Desktop touch-target selectors must remain weak enough for mobile visibility rules to override them.

**Why:** Shared footer markup follows two output paths, and a more-specific desktop link selector can unintentionally expose a hidden utility action on narrow screens.

**How to apply:** After shared header or footer accessibility changes, validate both page families, scan for nested interactive elements, and run the 320px browser regression in addition to parity checks.