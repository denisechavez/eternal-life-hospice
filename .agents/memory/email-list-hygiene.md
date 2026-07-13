---
name: Email list hygiene pipeline
description: NeverBounce verification → Brevo master list flow, list IDs, and consent-flag caveat
---

# NeverBounce → Brevo list pipeline

- NeverBounce key = `NEVERBOUNCE_API_KEY` secret; API `https://api.neverbounce.com/v4.2/` with `key` query param. `jobs/search` for status/totals, `jobs/results` (paginated, items_per_page=1000) for per-row verdicts.
- NeverBounce job totals count rows, not unique emails — dedupe on download (2,007-row job reported 887 valid but only 736 unique valid addresses).
- Brevo list IDs: **8 = "Master Verified"** (only NeverBounce-valid, deduped), **9 = "Catch-All — send with caution"** (holding list, never in the main send). Folder 1. Custom attribute `COMPANY` created; imports carry FIRSTNAME/LASTNAME/JOB_TITLE/COMPANY.
- Brevo import: `POST /contacts/import` with `jsonBody` (async → poll `/processes/{id}`).
- Campaign 1 (`elh-brief-issue1`) is staged in draft against list 8; unsubscribe tag confirmed, no placeholder.

**Consent caveat:** the scrubbed CRM export marks every contact "Review before bulk outreach" / consent "Unknown / not documented" — uniform boilerplate, not individual opt-outs. Contacts are B2B facility administrators; CAN-SPAM-compliant with unsubscribe + postal address, but keep sends professional/educational and honor unsubscribes immediately.

**Routine:** each new list → NeverBounce job → valids into list 8 (dedupe), catchalls into list 9, never import invalid/unknown/bad-syntax.
