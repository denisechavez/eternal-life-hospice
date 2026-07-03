---
name: Form auto-reply (Netlify submission-created)
description: How the client-facing auto-reply email works on the ELH Netlify site, and the constraints that shaped it.
---

# Form auto-reply

`netlify/functions/submission-created.js` sends a warm acknowledgement email to
people who submit a lead form. Netlify auto-invokes any function literally named
`submission-created` once per verified form submission — there is no wiring in
the HTML; the filename IS the trigger.

**Rule: never break the submission.** The handler returns `statusCode: 200` on
every path (missing key, parse error, Resend failure) so a failed auto-reply can
never mark the form submission or the internal team notification as failed.
**Why:** internal lead capture is the business-critical path; the auto-reply is a
courtesy layer on top and must degrade silently.

**Rule: gate sends by an explicit form allowlist**, not by "does an `email` field
exist." **Why:** gating on field presence would reply to any future/crafted form
carrying an `email` field. A reply still only goes out when the submission has a
valid email, so a form is safe to allowlist even if its email field is optional.
Allowlisted: `elh-family`, `elh-casemanager`, `elh-careers` (collect email), and
`elh-physician` (the /refer page added an OPTIONAL work email → PHI-free referral
confirmation; the homepage physician form has no email field so it's unaffected,
and that form lives in `index.html` also named `elh-physician`). Never
auto-replied to: `elh-coordinator`, `elh-chat-callback`.

**Chat callback → referral inbox (no auto-reply):** `elh-chat-callback`
submissions trigger an internal notification email via Resend to
referral@eternallifehospice.com (code-controlled, independent of Netlify UI
notifications), then the handler returns — NO auto-reply to the requester.
**Why:** user decision (July 2026) — the chat widget already confirms on-screen,
so an email confirmation is redundant. The form still collects an optional
`email` field purely as contact info for the team. The internal email may
include the requester's note; nothing is ever echoed to an outside address.

Content branches by form: careers / referral (`elh-physician`) / generic. The
referral branch greets by the referrer's first name (a professional, not the
patient — `referrer_name`/`first_name`/`name`, first token only) and never echoes
the `situation`/clinical free-text.

**Email provider = Resend.** Key lives in the Netlify dashboard as
`RESEND_API_KEY` (scope: All / Functions), NOT a Replit integration — Replit
integration secrets live in the Replit runtime and don't reach the Netlify
production function (same reason `ANTHROPIC_API_KEY` is set directly in Netlify).
Sending `from` info@eternallifehospice.com requires verifying the domain in
Resend (SPF/DKIM DNS records). Without the key set, the function no-ops.

**Compliance:** the reply body is static — it never echoes the submitted
message/details — to avoid accidentally reflecting PHI into outbound email.
