---
name: Field Outreach Tracker app
description: The internal full-stack tracker app that lives in this repo alongside the marketing site — its deploy model, auth, and storage decisions.
---

# Field Outreach Tracker (`outreach-tracker/`)

A private, mobile-first internal web app for logging brochure-drop field visits (company,
address, date, contact, notes, follow-up status, photos/business cards). Separate from the
public marketing site.

## Two deploy targets now live in ONE repo
- **Marketing site** = `website/elh-preview/` → publishes to Netlify via Git→Sync (unchanged).
- **Tracker** = `outreach-tracker/` (Express + Replit Postgres) → deployed via **Replit Deployments**, NOT Netlify. Netlify only ever builds `website/elh-preview`.
- The Replit **"Start application" workflow now runs the tracker** on port 5000 (`cd outreach-tracker && npm start`). The old static-site preview workflows ("Preview Site" / the http.server one) were removed — so the live preview pane shows the tracker, not the marketing site. To preview the marketing site again, reconfigure a workflow to serve `website/elh-preview`.

## Auth / security decisions
- Custom **phone-number + password** auth (bcryptjs, express-session in Postgres via connect-pg-simple). Two users only; each sets their own password on first sign-in.
- **`MAX_USERS = 2`**, enforced atomically with `pg_advisory_xact_lock` inside a txn (not a bare COUNT).
- Registration gated by **`REGISTRATION_CODE`** env var (share the value with the user out-of-band; it's a signup gate, not a secret password). **Keep it in Replit Secrets, never in `.replit` `[userenv.shared]`** (that file is committed → exposed). Gotcha: a key present in shared env AND showing as a "secret" was the *same single entry* — `deleteEnvVars({environment:"shared"})` removed it entirely, ungating registration (`requiresCode` went false). Restore via `requestEnvVar({requestType:"secret"})`, then restart.
- **`SESSION_SECRET` is required** — the server `process.exit(1)`s if it's missing (already exists as a Replit secret). Cookie `secure: "auto"` so it works on both localhost (http) and the HTTPS proxy.
- In-memory rate limiting on `/api/login` and `/api/register` (single instance is fine for 2 users).

## Storage decision
- Photos are **resized client-side (canvas, ~1280px JPEG) and stored as Postgres BYTEA**, served via `/api/photos/:id`. Chose this over Replit Object Storage to avoid the blueprint's confirmation friction and keep the tool self-contained. **If photo volume grows, migrate to object storage.**

## Design = the "Eternal Field Log" prototype (user-preferred)
- The user supplied an HTML prototype (`attached_assets/ELH_Field_Log_Prototype*.html`) and said "I prefer what claud built." The frontend was **rebuilt to match that prototype** and wired to the real backend (auth + Postgres + photo storage) instead of the prototype's local `window.storage`.
- Editorial masthead ("Eternal Field Log"), 3 tabs: **Log a visit / Follow-up (count) / Export**. Signature visit cards with a colored left rail + a "clock" showing days-out / due / days-late / done, computed client-side from `follow_up_due`.
- **Data model is richer than the first build:** company(org), category, address, city, county, visit_date, contact_name/title/email/phone, `materials` (JSONB array of chips = pocket folder + the 4 Eternal Standard pillars + full kit), notes, owner, `follow_up_due` (date), `followup_status`, `attested`. Photo kinds are **`card` + `site`** (business card + materials-in-place).
- Follow-up `status` values are the prototype's set: **Not started / Email sent / Replied / Meeting booked / Closed / No interest** (stored in `followup_status`; old brochure_left/etc. set is gone).
- Export tab = live stats + client-side CSV download (photos excluded, "travel separately"). The prototype's destructive "Clear all visits" reset was **replaced** with per-card Delete (safer for real data).

## Compliance features kept from the prototype (valuable for a hospice)
- **PHI guardrail:** a regex set scans the notes textarea live; a match turns the guard box red and blocks Save. Never let patient info into this log.
- **Required attestation:** "I confirm these notes contain no patient information" checkbox is required to save; enforced **server-side too** (POST rejects `attested !== true`) and stored on the row.

## Deferred
- **Automated follow-up email sending is intentionally NOT built** — user was still choosing an email platform/CRM. Wiring real sending (e.g. Resend, already used by the site) is the natural next step.
