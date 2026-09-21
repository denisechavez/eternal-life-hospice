---
name: Approved footer layout
description: Defines the user-approved responsive layout behavior for the public ELH footer.
---

At approximately 1024px wide, preserve the complete footer as one compact seven-column row: brand, Hospice Care, Services, Resources, Service Areas, About, and Contact, with For Professionals under Contact.

**Why:** The user explicitly identified this arrangement as the proper layout; a four-column intermediate breakpoint created visible inconsistencies between pages.

**How to apply:** Keep the seven-column layout through compact desktop widths. Reflow only below that range, using three columns first, then two, then one on narrow mobile screens. Preserve current verified business details when using an older visual reference.

## Phone-number rule

The footer must always display Eternal's primary landline, **805.953.7273**, as the first phone number and the WhatConverts line, **805.295.4688**, separately beneath it. Protect the primary element with WhatConverts' `no-swap` class.

**Why:** Dynamic number insertion previously replaced both footer lines with the tracking number, making Eternal's main landline disappear.

**How to apply:** Treat 805.953.7273 as the constant primary number and 805.295.4688 as the separate tracked/direct line on every public page. Any footer generator or synchronization change must preserve both.