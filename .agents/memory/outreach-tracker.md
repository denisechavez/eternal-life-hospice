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
- Registration gated by **`REGISTRATION_CODE`** env var (share the value with the user out-of-band; it's a signup gate, not a secret password).
- **`SESSION_SECRET` is required** — the server `process.exit(1)`s if it's missing (already exists as a Replit secret). Cookie `secure: "auto"` so it works on both localhost (http) and the HTTPS proxy.
- In-memory rate limiting on `/api/login` and `/api/register` (single instance is fine for 2 users).

## Storage decision
- Photos are **resized client-side (canvas, ~1280px JPEG) and stored as Postgres BYTEA**, served via `/api/photos/:id`. Chose this over Replit Object Storage to avoid the blueprint's confirmation friction and keep the tool self-contained. **If photo volume grows, migrate to object storage.**

## Deferred
- **Automated follow-up email sending is intentionally NOT built** — user was still choosing an email platform/CRM. App only tracks follow-up status + offers a copyable branded email draft. Wiring real sending (e.g. Resend, already used by the site) is the natural next step.
