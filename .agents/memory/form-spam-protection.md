---
name: Intake spam protection
description: Abuse prevention must preserve real families and professional referrals.
---
Do not blacklist a telephone area code as a proxy for spam. Preserve genuine
out-of-area callers and allow professional offices to make multiple referrals.

Use one shared contact formatter across intake surfaces. Never silently truncate
a number to ten digits or strip arbitrary text into an apparently valid number.

**Why:** A legacy homepage-only formatter changed input before the shared
validator could examine it, concealing malformed values and losing international
digits. The owner asks for automatic phone formatting and email checks to reduce
junk requests, not exclusion of legitimate callers.

**How to apply:** Preserve country codes, validate the complete value on both
browser and server and retain optional-email callback paths. Email syntax
validation cannot establish that a mailbox exists or replace spam verification.

**Why:** The owner reported a burst of suspicious 202 callbacks; that is evidence
of an incident, not evidence that every caller with that area code is abusive.
Telephone numbers do not reliably identify a family's current location.

**How to apply:** Enforce verification, replay prevention and short-lived
duplicate/rate controls on the server. Shared limits must work across Autoscale
instances. Persist keyed digests rather than intake contents or raw contacts.
When a configured CAPTCHA service is unavailable, fail clearly with a telephone
fallback rather than claiming delivery or silently skipping verification.

Do not assume a normal browser's same-origin GET includes an Origin header.
Challenge issuance and submission need different, tightly scoped origin checks.

**Why:** A real referral failed before submission because the browser-style
security GET was rejected, while test helpers that always supplied Origin
passed. Mocking the challenge endpoint also hid this integration failure.

**How to apply:** Test actual challenge HTTP requests with browser-default
headers, not only explicit-Origin helpers or mocked challenge responses.
Keep POST verification strict, reject conflicting origins and validate
cross-site denial alongside every legitimate-browser regression.

A missed acknowledgment warrants an operations alert even when isolated;
do not apply the verification outage's multi-failure threshold to it.

**Why:** Low-volume legitimate requests can lose their only receipt without
ever reaching an outage threshold. The internal intake is already accepted,
so asking the visitor to retry risks duplicate referrals.

**How to apply:** Keep acknowledgment alerts separate from verification and
internal-delivery incidents, preserve successful submission semantics and
never retry the original intake to repair a missing receipt.

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

An interrupted intake request has an unknown delivery outcome, not a confirmed
failure. Preserve entered fields and direct the visitor to call to confirm
receipt before another request; never automatically retry it.

**Why:** The owner explicitly requires avoiding duplicate referrals when the
browser loses the response after intake may already have received the request.
Verification failure before submission and explicit rejection are different
from an unknown delivery outcome.

**How to apply:** Keep these outcomes distinct across family, referral and chat
journeys. Use the approved clickable care-team CTA below. Do not change accepted
submission semantics to recover a missing receipt email.

Keep uncertain-delivery reminders bounded and tab-scoped, with no saved contact
or clinical information. Reopening a widget is not confirmation of non-receipt,
and a reminder expiring is not evidence that intake failed.

**Why:** A response can be lost after intake accepts the request; a new form
must not encourage a duplicate, but an indefinite lockout can also prevent care.

**How to apply:** Offer a clickable care-team call link and explain both outcomes:
confirmed receipt needs no resubmission; confirmed non-receipt permits a new,
blank manual request. Never use the reminder as authority to retry automatically.

## Request acknowledgments

The owner requires an immediate branded receipt email for support requests,
referrals and other form requests when the submitter provides an email address.
Care-request wording should explain that the care team will make contact based
on urgency, without promising an unapproved response deadline.

**Why:** Families and referring professionals need reassurance that their
request was received and clear expectations about the next contact.

**How to apply:** Keep acknowledgments specific to the request type, exclude
patient or clinical details and give urgent care requests a telephone fallback.
Never describe a queued or provider-accepted email as confirmed inbox delivery.

The owner's final approved care CTA supersedes all previous availability
variations in acknowledgment emails and online confirmation screens:

> Need to speak with someone now?
>
> We're here for you 24 hours a day, 7 days a week.
>
> Call 805.953.7273

**Why:** The owner explicitly approved this exact wording for consistent,
unmistakable care-related phone availability. It does not promise immediate
appointments, editorial responses or clinical eligibility.

**How to apply:** Preserve the wording exactly and make the call label a
telephone link. Apply it to care requests/referrals/callbacks and the
care-support portion of general meeting acknowledgments. Do not substitute
shorter “24/7” phrases or alter other owner-approved copy. Keep development
changes unpublished until the owner approves publishing.
