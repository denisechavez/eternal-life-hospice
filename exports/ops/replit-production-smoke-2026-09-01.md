# Replit Production Smoke Test

**Verified:** 2026-09-01 at 03:57 UTC  
**Canonical production URL:** https://eternallifehospice.com  
**Generated Replit URL:** https://eternal-life-hospice.replit.app  
**Scope:** Replit chat and coverage independence verification before any Netlify freeze decision.

## Release status

- Replit deployment metadata reported a public Autoscale deployment.
- The active deployment reported a successful build.
- The canonical domain was the deployment's primary URL.
- The generated Replit URL was the deployment's additional URL.
- Both production URLs returned the expected Pasadena coverage result.
- The approved Replit API implementation was already present on the active production build; no additional source change was required for this verification.

## Local release checks

- `python3 website/test-replit-chat-coverage.py` — **PASS**, 27 checks.
- `python3 website/check-city-scripts.py` — **PASS**, 145 published city pages.
- `python3 website/clean-stale-aliases.py --check --remove-redundant` — **PASS**, 24 aliases clean.
- `python3 website/check-header-parity.py` — **PASS**, 177 standard pages and 23 intentional exceptions.
- `bash website/test-predeploy-chain.sh` — **PASS**, all pre-deploy checks and sentinel self-tests.
- Working tree was clean before this evidence record was added.

## Live production smoke results

| Check | Result | Evidence |
| --- | --- | --- |
| Served city lookup | **PASS** | `GET /api/coverage?city=Pasadena` returned HTTP 200 with `served: true` and `city: "Pasadena"`. |
| Ambiguous city lookup | **PASS** | `GET /api/coverage?city=West` returned HTTP 200 with `ambiguous: true` and four suggestions. |
| Emergency chat guard | **PASS** | Same-origin `POST /api/chat` returned HTTP 200 with `guarded: true` and a deterministic 911 instruction. |
| Harmless hospice question | **PASS** | Same-origin `POST /api/chat` for “What is hospice care?” returned HTTP 200, `configured: true`, and a non-empty hospice answer. |
| Cross-origin rejection | **PASS** | A request with `Origin: https://attacker.example` returned HTTP 403 with `error: "invalid_origin"` and no `Access-Control-Allow-Origin` header. |

No patient information, referral data, credentials, or other sensitive content was used in these checks.

## Live independence audit

- The live homepage returned HTTP 200 and loaded `assets/chat.js`.
- The live homepage contained **zero** `/.netlify/functions/` paths.
- The live `assets/chat.js` contained **zero** `/.netlify/functions/` paths.
- The live `assets/chat.js` used same-origin `/api/chat` and `/api/coverage`.
- The focused source regression also confirmed that the public agent metadata advertises no Netlify coverage endpoint.

**Conclusion:** The canonical Replit site is independently serving the chat and coverage functions required by this task. The production smoke test is green.

## Netlify decision

Netlify was not changed, frozen, unpublished, or deleted during this verification. This report supports a future freeze decision, but it does not by itself complete the broader operational checklist. In particular, the readiness workbook still requires the separate no-PHI referral delivery confirmation, standalone tracker field-use confirmation, link audit, and observation period before Netlify retirement.

**Current decision:** Keep the Netlify copy available pending the remaining operational sign-offs. The Replit chat/coverage independence gate is **PASS**.