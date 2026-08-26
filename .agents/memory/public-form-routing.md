---
name: Public form routing
description: Operational constraint for ELH public forms across Google-hosted and Netlify deployments.
---

The public domain is served from Google/Replit infrastructure, so its production form processor must run in the Replit-hosted application. Netlify form declarations and functions belong only to the separate duplicate and cannot be treated as delivery for the public domain.

**Why:** The Google-hosted public endpoint returned a preview response to form POSTs while the client code treated its HTTP 200 as a successful referral. A visually successful confirmation is therefore not evidence that a team received a referral.

**How to apply:** Public browser forms must use the Replit same-origin processor and show success only after its delivery provider accepts the internal notification. After each relevant publish, verify the public HTML targets that processor, then send one clearly labeled no-email synthetic professional referral using a reserved fictional phone number. Treat provider acceptance as necessary but not sufficient: the intake team must confirm receipt in the referral mailbox and delete the test message. The Gmail connection for the info mailbox cannot prove referral-mailbox delivery. Preserve the phone fallback and explicit Netlify separation before changing hosting or DNS.