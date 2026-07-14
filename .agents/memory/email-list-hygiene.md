---
name: Email list hygiene pipeline
description: NeverBounce verification → Brevo master list flow, list IDs, and consent-flag caveat
---

# NeverBounce → Brevo list pipeline

- NeverBounce key = `NEVERBOUNCE_API_KEY` secret; API `https://api.neverbounce.com/v4.2/` with `key` query param. `jobs/search` for status/totals, `jobs/results` (paginated, items_per_page=1000) for per-row verdicts.
- NeverBounce job totals count rows, not unique emails — dedupe on download (2,007-row job reported 887 valid but only 736 unique valid addresses).
- Brevo list IDs: **8 = "Master Verified"** (only NeverBounce-valid, deduped), **9 = "Catch-All — send with caution"** (holding list), **7 = "Care Brief Subscribers"** (site opt-ins), **10 = "SYMPLR Network"** (cold hospital-staff emails scraped from the Google Drive facility PDFs, NeverBounce-valid only). Folder 1. Custom attribute `COMPANY` created; imports carry FIRSTNAME/LASTNAME/JOB_TITLE/COMPANY.
- Brevo import: `POST /contacts/import` with `jsonBody` (async → poll `/processes/{id}`).

**Contact SOURCE lives in Google Drive, not a CSV.** The "contacts on file" = ~800 scraped `vcsdatabase.com` facility PDFs organized into ~90 hospital/health-system folders (Google Drive connector `google-drive` is connected; in code_execution use `listConnections('google-drive')` → `settings.access_token` → Drive REST). Rebuild pipeline: download each PDF (`files/{id}?alt=media`) → `pdftotext -layout` → regex emails → dedupe. Emails are legit institutional domains (mednet.ucla.edu, cityofhope.org, cedars-sinai.org, usc.edu, dhs.lacounty.gov, kaiserpermanente.org…).

**Hospital domains verify with huge "unknown" rates on NeverBounce** (greylisting/timeouts): expect a LOW valid yield (~24-25%) from health-system scrapes. The full 4,587 scraped set is now fully verified across two jobs: **1,123 valid, 1,033 catch-all, 2,377 unknown, 54 invalid** → SYMPLR Network (#10) holds the 1,123 valids. "verified only" = `result=valid`, exclude catch-all + unknown + invalid. NeverBounce job needs ≥ 1 paid credit per email (bulk `jobs/create` with `input_location:supplied`, `auto_parse+auto_start`; poll `jobs/status`; `jobs/download` with `valids:1` for a valid-only CSV). NeverBounce plan auto-refills paid credits monthly.

**Consent caveat:** the scrubbed CRM export marks every contact "Review before bulk outreach" / consent "Unknown / not documented" — uniform boilerplate, not individual opt-outs. Contacts are B2B facility administrators; CAN-SPAM-compliant with unsubscribe + postal address, but keep sends professional/educational and honor unsubscribes immediately.

**Deliverability decision (user-directed, July 2026):** advised keeping cold scraped contacts OUT of an already-scheduled blast (7x volume spike of never-emailed addresses = spam/reputation risk); user chose to fold valid ones in anyway but as a SEPARATE list (SYMPLR Network #10) sent alongside Master Verified. **Why:** growth mandate outranks warm-up caution for this user — offer the safe path, but they decide.

**Update (July 14, 2026) — user reversed toward caution:** directs a slow, phased rollout. Send **Master Verified (#8, `result=valid` only, deduped) FIRST**; **hold catch-all (#9) and every unknown/questionable address** (incl. SYMPLR unknowns) until later. Do NOT fire any bulk/Care Brief send to #9 or unknowns without an explicit fresh go-ahead. **Why:** warm up sender reputation/deliverability on the cleanest addresses before touching riskier ones. **How to apply:** every send now starts with #8 valids only; "we will take it slowly."

**Routine:** each new list → NeverBounce job → valids into the target list (dedupe against ALL existing Brevo emails first, not just one list), catchalls into list 9, never import invalid/unknown/bad-syntax.
