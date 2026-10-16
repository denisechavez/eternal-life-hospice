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

Intake outage notifications must remain independent of the failed dependency
and must distinguish service failures from ordinary rejected spam.

**Why:** Rejected bots are expected; paging on them hides real interruptions to
families and referral partners. Using the guard database to gate its own outage
notifications would suppress alerts precisely when they are needed.

**How to apply:** Reuse the independent operations channel with only fixed
failure categories and aggregate counts. Keep cooldowns independent of the
guard database; any future fleet-wide coordination needs a separate healthy
service. Never include submitted information or provider exception details.

Browser intake regression tests must isolate all external transports and use
synthetic contacts; never send real leads or weaken deployed CAPTCHA guards.

**Why:** These journeys reach a real clinical intake team and outbound email.
The requested regression coverage is not permission to create clinical leads,
install CAPTCHA test keys or introduce a production bypass.

**How to apply:** Exercise the actual rendered UI and shared security module
against test-only provider/submission boundaries. Keep real server guard coverage
separate, and state clearly that a simulated challenge cannot validate the
provider's own cross-origin widget.
