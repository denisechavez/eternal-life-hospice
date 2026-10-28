---
name: Client acknowledgment delivery boundary
description: The owner chose company Gmail, not Brevo, for client acknowledgment delivery.
---

Client acknowledgment emails must use the company's Gmail mailbox, not Brevo. Do not fall back to Brevo if Gmail fails.

The company's info@eternallifehospice.com and referral@eternallifehospice.com addresses are separate mailboxes, not aliases.

**Why:** The owner explicitly confirmed that both role addresses are separate mailboxes.

**How to apply:** Obtain the appropriate authorization for each role mailbox before using it as a sender. Access to a connected employee mailbox does not establish access to either role mailbox. Do not replace an existing Gmail connection without explaining its impact and obtaining approval.

Do not confuse default/custom OAuth configuration with authorization for a different mailbox.

**Why:** Changing connector configuration can leave the same employee mailbox authorized, despite appearing to complete setup for a role mailbox.

**How to apply:** Verify the actual Gmail profile after authorization changes. Consult current connector instructions before switching accounts, and explain any impact on other apps using the existing connection before asking the owner to disconnect it.

**Why:** The owner explicitly stated, “I do not want the e-mail that goes to client to go through brevo,” then selected “let it go through our gmail.” Form processing in Replit and the service delivering an email must be explained separately; a WhatConverts lead notification is not the approved customer acknowledgment.

**How to apply:** Use the managed Gmail connection with a verified company mailbox and preserve the approved branded copy and layout. Test without creating duplicate intake requests; identify any real test recipient and obtain confirmation before sending. A Gmail acknowledgment failure must not turn an already accepted intake into a failed request. This instruction does not authorize removing Brevo from newsletters, marketing or internal notifications, or disabling WhatConverts tracking. Keep changes in preview until publishing is approved. Never impersonate an unverified sender alias.
