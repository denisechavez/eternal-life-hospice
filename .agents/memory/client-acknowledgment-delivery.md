---
name: Client acknowledgment delivery boundary
description: The owner chose company Gmail, not Brevo, for client acknowledgment delivery.
---

Client acknowledgment emails must use the company's Gmail mailbox, not Brevo. Do not fall back to Brevo if Gmail fails.

**Why:** The owner explicitly stated, “I do not want the e-mail that goes to client to go through brevo,” then selected “let it go through our gmail.” Form processing in Replit and the service delivering an email must be explained separately; a WhatConverts lead notification is not the approved customer acknowledgment.

**How to apply:** Use the managed Gmail connection with a verified company mailbox and preserve the approved branded copy and layout. Test without creating duplicate intake requests; identify any real test recipient and obtain confirmation before sending. A Gmail acknowledgment failure must not turn an already accepted intake into a failed request. This instruction does not authorize removing Brevo from newsletters, marketing or internal notifications, or disabling WhatConverts tracking. Keep changes in preview until publishing is approved. Never impersonate an unverified sender alias.
