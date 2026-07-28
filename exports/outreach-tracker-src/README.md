# Eternal Field Log — Outreach Tracker

Internal field visit-capture and follow-up tracking app for the Eternal Life Hospice outreach team.

---

## Production builds & the trim test

The deployment build command (`npm install && npm test`) runs seven test files in sequence:

1. `test-scanhint-reset.js` — scan-hint DOM reset logic (no DB required)
2. `test-rec-btn-aria.js` — record-button ARIA state (no DB required)
3. `test-backup-trim.js` — backup_log 90-day trim (requires `DATABASE_URL`)
4. `test-backup-email.js` — full and incremental backup email (requires `DATABASE_URL`; skipped cleanly when `BACKUP_EMAIL` or `BREVO_API` are absent)
5. `test-rate-limit-trigger.js` — backup trigger rate-limit (requires `DATABASE_URL`)
6. `test-backup-brevo-failure.js` — Brevo error surfacing (requires `DATABASE_URL`)
7. `test-backup-cooldown-session.js` — backup-button cooldown sessionStorage persistence (no DB required)

`DATABASE_URL` is a **Replit runtime-managed variable** — it is automatically injected in both development and production build environments by Replit's PostgreSQL integration. No manual secret configuration is required.

`DATABASE_URL` is a **Replit runtime-managed variable** — it is automatically injected in both development and production build environments by Replit's PostgreSQL integration. No manual secret configuration is required. The trim test will have a live database connection during every deploy build.

---

## Setup in a new Replit

### 1. Create the Replit
- Create a new **Node.js** Replit
- Upload or paste all files from this directory (excluding `node_modules/`)
- Run `npm install` in the Shell

### 2. Enable the PostgreSQL integration
- In the Replit sidebar → **Tools → Database** → enable PostgreSQL
- This sets `DATABASE_URL` automatically

### 3. Run the schema
```bash
psql $DATABASE_URL < schema.sql
```

### 4. Set Secrets
In **Tools → Secrets**, add:

| Secret | Value |
|---|---|
| `SESSION_SECRET` | A long random string (32+ chars) |
| `REGISTRATION_CODE` | Team admin code for first-time registration |

For AI card scanning and voice notes, also enable the **OpenAI integration** in Replit Integrations — this sets `AI_INTEGRATIONS_OPENAI_API_KEY` and `AI_INTEGRATIONS_OPENAI_BASE_URL` automatically.

### 5. Start the app
Click **Run**, or in the Shell:
```bash
npm start
```

The app listens on port 5000 and will be served at your Replit dev URL.

---

## Features
- **Log a visit** — capture organization, contact, address, visit date, and materials left
- **Business card scan** — photo → AI auto-fill of contact fields (requires OpenAI integration)
- **Voice notes** — record a voice memo → AI transcription into the notes field
- **Follow-up queue** — filter visits by status (Not started / Email sent / Replied / Meeting booked / Closed / No interest)
- **Export** — download all visits as a CSV

## Security notes
- Max 2 user accounts (enforced at DB level with advisory lock)
- `REGISTRATION_CODE` required to create accounts
- Sessions stored in Postgres, 30-day rolling cookie
- `noindex, nofollow` meta tag — not indexed by search engines
- All routes require authentication; photos served only to authenticated users

## Tech stack
- **Express** + **express-session** + **connect-pg-simple**
- **bcryptjs** for password hashing
- **pg** (node-postgres) for database
- **openai** SDK for card scanning and voice transcription
- Vanilla JS frontend (no build step)
