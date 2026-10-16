---
name: Approved footer layout
description: Defines the user-approved responsive layout behavior for the public ELH footer.
---

At approximately 1024px wide, preserve the complete footer as one compact seven-column row: brand, Hospice Care, Services, Resources, Service Areas, About, and Contact, with For Professionals under Contact.

**Why:** The user explicitly identified this arrangement as the proper layout; a four-column intermediate breakpoint created visible inconsistencies between pages.

**How to apply:** Keep the seven-column layout through compact desktop widths. Reflow only below that range, using three columns first, then two, then one on narrow mobile screens. Preserve current verified business details when using an older visual reference.

## Phone-number rule

The footer displays the WhatConverts number **805.410.1151** first, labeled **Main**, followed by the landline **805.953.7273** without a role label. Protect the landline with WhatConverts' `no-swap` class.

**Why:** On October 16, 2026, the owner explicitly requested the WhatConverts number on top and labeled Main, superseding the previous ordering and blanket no-role-label instruction. Dynamic number insertion previously replaced both lines; the landline must remain separately visible.

**How to apply:** Apply this contact order consistently to standard pages, city pages and frozen public article chrome. Preserve both click-to-call destinations; do not change non-footer phone CTAs.