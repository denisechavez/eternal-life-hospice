---
name: Intake spam protection
description: Abuse prevention must preserve real families and professional referrals.
---
Do not blacklist a telephone area code as a proxy for spam. Preserve genuine
out-of-area callers and allow professional offices to make multiple referrals.

**Why:** The owner reported a burst of suspicious 202 callbacks; that is evidence
of an incident, not evidence that every caller with that area code is abusive.
Telephone numbers do not reliably identify a family's current location.

**How to apply:** Enforce verification, replay prevention and short-lived
duplicate/rate controls on the server. Shared limits must work across Autoscale
instances. Persist keyed digests rather than intake contents or raw contacts.
When a configured CAPTCHA service is unavailable, fail clearly with a telephone
fallback rather than claiming delivery or silently skipping verification.

Shared chat assets also need a new immutable URL when security behavior changes.

**Why:** Older, frozen published pages can retain cache-immutable script URLs,
causing legitimate visitors to keep using the unprotected submission protocol.

**How to apply:** Refresh application-chrome asset URLs when serving those
pages, without editing their frozen editorial content or inventing new approvals.
