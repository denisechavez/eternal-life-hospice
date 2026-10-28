---
name: Website phone roles
description: Main-number regressions must retain office contacts and approved email copy without invalidating Journal approvals.
---

Public Main contacts, explicitly labeled office contacts and approved acknowledgment emails are distinct phone roles.

**Why:** Phone consistency is role-specific, not permission to replace every occurrence of the office number. Website confirmations may project the care CTA to Main without altering the approved emailed letter.

**How to apply:** Test public response boundaries with synthetic payloads and block external transports. Keep signed Journal documents unchanged; use synthetic documents to exercise the runtime phone projection. Do not send real submissions or emails to verify phone formatting.

Browser tests must distinguish approval-controlled source content from the public response.

**Why:** Preserved source numbers can be intentional. A fixture mismatch is not permission to bulk-edit approved documents.

**How to apply:** Model the public response when checking public phone behavior; leave approval-controlled source content intact.
