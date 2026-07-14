---
name: Email newsletter QA & Brevo send pipeline
description: How to preview responsive email HTML reliably and how edits reach an already-queued Brevo campaign.
---

# Previewing responsive email HTML

Headless Chromium CLI (`--headless` and `--headless=new`) does **NOT** reliably
evaluate `@media (max-width:...)` media queries or shrink email tables
(`width="640" ... max-width:100%`) to the `--window-size` viewport in
`--screenshot` mode. It renders the full desktop table and clips it, which looks
like broken mobile even when real phones render fine.

**How to QA the mobile layout deterministically:**
1. Copy the email HTML.
2. Unwrap the mobile media block (delete the `@media ... {` and its closing `}`)
   so the mobile rules apply unconditionally.
3. Force the outer container to a phone width (e.g. replace
   `width:640px;max-width:100%` with `width:360px;max-width:360px`).
4. Screenshot at ~390px window. What you see now matches a real phone.

**Best ground truth:** send a real preview to a phone (see below). The user's
device is the source of truth, not headless.

# Edits vs. an already-queued Brevo campaign

Editing the exported HTML file does **NOT** change a campaign that is already
created/queued in Brevo — the campaign stores its own `htmlContent` snapshot.
To make a fix reach a scheduled send you must
`PUT /v3/emailCampaigns/{id}` with `{"htmlContent": <new html>}` (works while
status is `queued`/`scheduled`). Then re-`GET` to refresh any cached copy used
for cloning previews.

**Why:** previews are sent by cloning campaign #1's stored content into a new
campaign targeting a preview list, then `POST /sendNow`. If you forget to PUT
the queued campaign, the preview looks fixed but the real blast still sends the
old version.

# Care Brief masthead (intro email)

`exports/email/eternal-care-brief-introduction-email.html` masthead is a
two-column magazine cover: left `01`/date (right-aligned toward divider),
1px vertical divider, right logo + "Issue One" + title. Keep the copy
equidistant from the center divider (equal padding on both sides). Mobile keeps
the two columns (scaled down) rather than stacking — driven by classes
`mh-band / mh-left / mh-right / mh-01 / mh-logo / mh-title / mh-divline`.
The "new issue" template uses a different single-band masthead, so this layout
is intro-email-only.
