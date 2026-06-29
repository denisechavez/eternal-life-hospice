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
exist." Only `elh-family`, `elh-casemanager`, `elh-careers` collect an email.
`elh-physician`, `elh-coordinator`, `elh-chat-callback` are phone-only and must be
skipped (they'd need SMS, which the client doesn't have). **Why:** gating on field
presence would reply to any future/crafted form carrying an `email` field.

**Email provider = Resend.** Key lives in the Netlify dashboard as
`RESEND_API_KEY` (scope: All / Functions), NOT a Replit integration — Replit
integration secrets live in the Replit runtime and don't reach the Netlify
production function (same reason `ANTHROPIC_API_KEY` is set directly in Netlify).
Sending `from` info@eternallifehospice.com requires verifying the domain in
Resend (SPF/DKIM DNS records). Without the key set, the function no-ops.

**Compliance:** the reply body is static — it never echoes the submitted
message/details — to avoid accidentally reflecting PHI into outbound email.
