---
name: Shared chrome accessibility
description: Propagation and selector rules for accessible shared headers and footers.
---

Footer changes must be propagated through both standard-page synchronization and city-page regeneration. Desktop touch-target selectors must remain weak enough for mobile visibility rules to override them.

**Why:** Shared footer markup follows two output paths, and a more-specific desktop link selector can unintentionally expose a hidden utility action on narrow screens.

**How to apply:** After shared header or footer accessibility changes, validate both page families, scan for nested interactive elements, and run the 320px browser regression in addition to parity checks.

## Public footer phone labels

The owner now explicitly allows **Main** beside the top WhatConverts footer number. Do not label the second number Direct or expose a Tracking label.

**Why:** The October 16, 2026 request to put the WhatConverts number first and label it Main supersedes the earlier blanket ban on role labels; other internal routing labels remain unnecessary.

**How to apply:** Follow the current order in footer-layout.md and preserve click-to-call behavior.

Journal approvals hash the entire document, including shared footer markup.
Update phone-only chrome at response time for existing Journal source files
and frozen snapshots rather than rewriting those files during footer sync.

**Why:** A harmless footer change must not turn an approved article into a new
unapproved editorial version or interrupt its scheduled release.

**How to apply:** Keep signed Journal sources out of bulk footer synchronization
and check the publicly rendered contact order without changing approval hashes.

Website main-number approval does not authorize changing acknowledgment letters
or external Google/WhatConverts profile identity. Preserve employee identities,
role mailboxes, independent direct numbers and no-swap behavior.

**Why:** The owner explicitly limited future phone-setting consolidation to the
website, including its public call links, not email copy or external profiles.

**How to apply:** Treat historical company numbers as website projection inputs,
not permission for a repository-wide number replacement or profile update.