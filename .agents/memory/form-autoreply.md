---
name: Form auto-reply (Netlify submission-created)
description: Production acknowledgement rules and the legacy Netlify duplicate.
---

# Form auto-reply

The public domain's Replit processor sends internal notifications and
allowlisted requester acknowledgements through Brevo. The old
`netlify/functions/submission-created.js` behavior is legacy-only for the
separate Netlify duplicate and is not a production intake path.

**Rule: internal acceptance is authoritative.** Never show success unless Brevo
accepts the internal notification. If the internal message succeeds but the
courtesy acknowledgement fails, preserve success to avoid duplicate referrals
and record the acknowledgement failure separately.
**Why:** internal lead capture is the business-critical path; retrying an
already accepted referral creates a different safety risk.

**Rule: gate sends by an explicit form allowlist**, not by "does an `email` field
exist." **Why:** gating on field presence would reply to any future/crafted form
carrying an `email` field. A reply still only goes out when the submission has a
valid email, so a form is safe to allowlist even if its email field is optional.
Allowlisted: `elh-family`, `elh-casemanager`, `elh-careers`,
`elh-care-brief-signup`, `elh-voice` (collect email), and `elh-physician` (the
/refer page now REQUIRES a work email → PHI-free referral confirmation; the
homepage physician form has no email field so it's unaffected, and that form
lives in `index.html` also named `elh-physician`). Never auto-replied to:
`elh-coordinator`, `elh-chat-callback`.

**Chat callback → referral inbox (no auto-reply):** `elh-chat-callback`
submissions trigger an internal notification email via Resend to
referral@eternallifehospice.com (code-controlled, independent of Netlify UI
notifications), then the handler returns — NO auto-reply to the requester.
**Why:** user decision (July 2026) — the chat widget already confirms on-screen,
so an email confirmation is redundant. The form still collects an optional
`email` field purely as contact info for the team. The internal email may
include the requester's note; nothing is ever echoed to an outside address.

Content branches by form: Care Brief signup (`elh-care-brief-signup` gets a
BRANDED welcome email via `renderSignupHtml` — logo header, latest-issue/library
buttons, Family Guide PDF download, share-by-mailto block; all links/assets use
the LIVE site URL, so they only resolve after Git→Sync) / voice
(`elh-voice`, "thank you for offering your voice") / careers / referral
(`elh-physician` AND `elh-casemanager` — the homepage discharge form is also a
professional referral, so it gets the same "we received your referral" copy, per
user July 2026) / generic. The
referral branch greets by the referrer's first name (a professional, not the
patient — `referrer_name`/`first_name`/`name`, first token only) and never echoes
the `situation`/clinical free-text.

**Production email provider = Brevo.** Its key lives in the Replit runtime.
Resend remains relevant only to the legacy Netlify function and must not be
used as evidence that a public-domain referral was delivered.

**Compliance:** the reply body is static — it never echoes the submitted
message/details — to avoid accidentally reflecting PHI into outbound email.
