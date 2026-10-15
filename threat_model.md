# Threat Model

## Project Overview

Eternal Life Hospice is a static marketing website for a Medicare-certified
hospice. Although the content is largely static HTML, production is served by a
custom Python HTTP server (`website/devserver.py`, despite the name it is the
deployed production server per `website/start-published-site.sh`) running on
Replit Autoscale at https://eternallifehospice.com (public visibility).

The server adds dynamic behavior on top of the static files:
- Public JSON APIs: `/api/coverage` (service-area lookup, CORS `*`),
  `/api/google-reviews`, `/api/chat` (OpenAI-backed assistant), `/api/form-submit`
  (lead/referral/careers intake delivered via Brevo).
- A Clerk-authenticated "Studio" journal review/approval surface
  (`/studio`, `/api/studio/journal`, `/api/__clerk` proxy) backed by PostgreSQL.
- An internal "Growth Intelligence" dashboard under `/growth-intelligence` and
  `/canvas-hub/dashboard/...` that reports marketing analytics (Google Analytics,
  Search Console, WhatConverts, Brevo).

Tech stack: Python stdlib `http.server`, PostgreSQL (`psycopg`), Node for
reporting/build helpers, Clerk for Studio auth, OpenAI, Brevo, Google Places.

## Assets

- **Application secrets** — `CLERK_SECRET_KEY`, `DATABASE_URL`, `GOOGLE_API_KEY`,
  `BREVO_API`, `WHATCONVERTS_TOKEN/SECRET`, `GOOGLE_REPORTING_SERVICE_ACCOUNT_JSON_V2`,
  OpenAI keys. All server-side; never exposed to the browser.
- **Lead/referral intake data (PII/PHI)** — names, contact info, referral details
  submitted via `/api/form-submit` and delivered to Brevo.
- **Business/marketing intelligence** — GA4 sessions/key events, Search Console
  queries and pages, WhatConverts lead counts/sources/markets/call stats and
  account identifiers, Brevo campaign names/subjects and subscriber/list counts.
- **Journal content and approval state** — PostgreSQL journal release records and
  reviewer decisions, gated on a single designated reviewer identity.

## Trust Boundaries

- **Browser to server** — all requests untrusted; same-origin check enforced on
  state-changing/public POST APIs (`/api/form-submit`, `/api/chat`).
- **Public vs internal** — the marketing site is public; the Growth Intelligence
  dashboard and Studio are intended to be internal/authenticated.
- **Server to PostgreSQL** — parameterized queries only (`journal_release.py`).
- **Server to external APIs** — Google, Brevo, WhatConverts, OpenAI, Clerk; secret
  keys attached server-side only.
- **User vs reviewer** — Studio writes require a Clerk session verified against
  Clerk's API for the single `aleksandra@eternallifehospice.com` reviewer, plus an
  exact-origin check.

## Scan Anchors

- Production entry point: `website/devserver.py` (`PrettyURLHandler`), launched by
  `website/start-published-site.sh`.
- Highest-risk code: the `/canvas-hub/dashboard/api/*` reporting routes in
  `do_GET` and `website/growth-intelligence-reporting.mjs`; Studio auth in
  `website/studio_auth.py` / `website/studio_site.py`; intake in
  `website/form_intake.py`.
- Public surfaces: static HTML, `/api/coverage`, `/api/google-reviews`,
  `/api/chat`, `/api/form-submit`, `/api/journal-release-status`,
  `/api/journal-photo/<digest>`.
- Authenticated surfaces (Clerk reviewer): `/studio` protected chunks,
  `/api/studio/journal` POST.
- Intended-internal surfaces: `/growth-intelligence`, `/canvas-hub/dashboard/*`.
- Dev-only/ignore unless proven reachable: the many `website/*.py` build/test/QA
  scripts (not wired into the request path), `artifacts/review-design-sandbox`
  (design mockup), `/canvas-hub/*` non-dashboard namespaces (404 in production).

## Threat Categories

### Information Disclosure / Elevation of Privilege

The Growth Intelligence dashboard and its reporting APIs
(`/canvas-hub/dashboard/api/elh-reporting`, `/whatconverts-reporting`,
`/brevo-reporting`) are intended to be internal but are reachable without any
authentication in production (see new vulnerability). All other sensitive write
paths (Studio journal approval) correctly require a Clerk-verified reviewer and an
exact trusted Origin. Public APIs must continue to avoid returning PII and must
keep secrets server-side.

### Spoofing / Tampering

`/api/form-submit` and `/api/chat` enforce a strict same-origin check
(`Origin` netloc must equal `Host`) plus per-client and global rate limiting.
Rate-limit keys never trust a leading `X-Forwarded-For`; a socket-peer circuit
breaker remains authoritative. Studio POSTs additionally require an allowed Origin.

### Injection

Database access uses parameterized queries. The reporting subprocess passes the
`period` argument as an argv element (no shell), limiting injection risk. Journal
photo lookups validate the digest against `^[a-f0-9]{64}$`. Path handling for
static/canvas files uses `commonpath`/`is_relative_to` containment checks.
