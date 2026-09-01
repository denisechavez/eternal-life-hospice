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
- **Preview setup (July 2026), user-approved:** "Start application" = marketing site on port 5000 webview (front-facing default; `python3 website/devserver.py`); "Outreach Tracker (internal)" = `PORT=3000 npm start`, console — user flips between them with the preview-pane port toggle. Keep the WEBSITE on 5000 so front-facing work always previews by default. Tracker's Replit Deployment (production) runs independently; field staff use the deployed URL.
- **Ownership after the visit-history migration:** the standalone tracker owns all future visits and photos; the main marketing site owns public pages and referral intake only, and its legacy tracker tables are not authoritative.

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

## Business-card AI auto-fill
- A "Do you have their business card?" Yes/No toggle drives contact entry. **No** → user must type street address + contact name (client `validate()` enforces). **Yes** → snapping the card photo calls the extract endpoint and auto-fills contact fields **fill-only-if-empty** (never clobbers what the user typed); the toggle is UI-only, not persisted.
- **Vision extraction uses the Replit OpenAI AI integration (gateway), not a personal key** — client built from `AI_INTEGRATIONS_OPENAI_*` env vars; model is a gpt-5.x vision model via chat-completions with `response_format: json_object`. **Why:** avoids user API-key friction; usage bills Replit credits. gpt-5 models forbid `temperature` and `max_tokens` (use `max_completion_tokens`).
- Extract endpoint is auth-gated + rate-limited, validates the data URL and caps decoded size, and **lazy-requires the AI module returning 503 if absent** so the app still boots without AI. Enforcement of the No-card required fields is client-side only (acceptable: 2 trusted users; server can't see the toggle).

## Logged-out runtime QA
- Always browser-render the logged-out Tracker after frontend changes; syntax and backend tests alone are insufficient.

**Why:** Removed optional controls once left stale direct event bindings that threw before authentication initialized, leaving only the loading veil while every server route and test still passed.

**How to apply:** Guard bindings for optional elements and require a no-console-error logged-out browser render before calling the Tracker healthy.

## Deferred
- **Automated follow-up email sending is intentionally NOT built** — user was still choosing an email platform/CRM. Wiring real sending (e.g. Resend, already used by the site) is the natural next step.
