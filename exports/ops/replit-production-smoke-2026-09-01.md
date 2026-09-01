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


## Controlled no-PHI referral delivery test

**Submitted:** 2026-09-01 04:13:39 UTC  
**Completed:** 2026-09-01 04:13:40 UTC  
**Route:** `https://eternallifehospice.com/refer` → same-origin `POST /api/form-submit`  
**Test label:** `Task 796 controlled no-PHI delivery test — 2026-09-01`

- **Processor acceptance — PASS:** HTTP 200 returned `accepted: true`, `acknowledgement_sent: true`, and `acknowledgement_error: false`. Receipt: `4F8D77C12AEB`. Brevo returned message ID `<202609010413.40012400777@smtp-relay.mailin.fr>`.
- **Referral mailbox delivery — PASS:** Gmail received a forwarded copy from `referral@eternallifehospice.com` to `info@eternallifehospice.com` at 04:13:45 UTC, with the forwarded internal referral carrying receipt `4F8D77C12AEB`.
- **Requester acknowledgement — PASS:** Gmail received `We received your request — Eternal Life Hospice` from `no-reply@eternallifehospice.com` to `info@eternallifehospice.com` at 04:13:40 UTC. The message contained the static acknowledgement and confirmation ID only; it did not contain the synthetic situation note.
- **Test data:** `ELH TEST — Do Not Call`, reserved fictional phone `805.000.0000`, `Eternal Life Hospice QA`, and the explicitly non-PHI situation `Synthetic non-PHI routing test only. Do not call.` No patient information was submitted.

## Live independence audit

- The live homepage returned HTTP 200 and loaded `assets/chat.js`.
- The live homepage contained **zero** `/.netlify/functions/` paths.
- The live `assets/chat.js` contained **zero** `/.netlify/functions/` paths.
- The live `assets/chat.js` used same-origin `/api/chat` and `/api/coverage`.
- The focused source regression also confirmed that the public agent metadata advertises no Netlify coverage endpoint.

**Conclusion:** The canonical Replit site is independently serving the chat and coverage functions required by this task. The production smoke test is green.

## Netlify decision

Netlify was not changed, frozen, unpublished, or deleted during this verification. This report supports a future freeze decision, but it does not by itself complete the broader operational checklist. In particular, the readiness workbook still requires standalone tracker field-use confirmation, link audit, and observation period before Netlify retirement.

**Current decision:** Keep the Netlify copy available pending the remaining operational sign-offs. The Replit chat/coverage independence gate is **PASS**.
## Observation record

**Observation window:** 2026-08-27 through 2026-09-01 UTC
**Observation end:** 2026-09-01 at 04:14 UTC
**Decision owner:** Eternal Life Hospice operations
**Rollback reference preserved:** Netlify production deploy `6a8d5522ffa55f00083c01fc` / Git commit `0c6ca3f39d878e59976e0d03dacec6e550e36e99` (published 2026-08-25). No Netlify setting, content, or deployment was changed.

This is a retrospective evidence window covering the available production records from Thursday, August 27 through Tuesday, September 1. The September 1 sweep is the only day with a complete retained check across all three operational signals; the missing daily records are treated as a readiness gap, not as a pass.

### Business-day checks

| UTC date | Production errors | Referral delivery | Analytics | Result |
| --- | --- | --- | --- | --- |
| 2026-08-27 | The read-only host investigation found the custom domain serving from the healthy Replit deployment; no application error was recorded in that evidence. | No form was submitted during the read-only investigation. | No analytics query was recorded. | Evidence gap; no retirement decision |
| 2026-08-28 | No retained deployment-log record is available for this date. | No retained delivery check is available for this date. | No retained analytics check is available for this date. | Evidence gap; no retirement decision |
| 2026-08-31 | No retained deployment-log record is available for this date. | No retained delivery check is available for this date. | No retained analytics check is available for this date. | Evidence gap; no retirement decision |
| 2026-09-01 | Deployment is public, Autoscale, and on a successful build. A restart produced transient health-check failures at 03:48:34 UTC; `/` returned 200 at 03:48:35 UTC and subsequent checks were healthy. | No referral submission was made in this smoke pass. The required no-PHI mailbox test remains a separate open gate. | Analytics access is authorized, but the query from 2026-08-27 00:00 UTC returned zero pageview rows; this is recorded as no collected telemetry, not zero traffic. | Current-day check recorded; no-go |

### September 1 final smoke and live checks

- `python3 website/test-replit-chat-coverage.py` — **PASS**, 27 checks.
- `python3 website/check-city-scripts.py` — **PASS**, 145 published city pages.
- `python3 website/clean-stale-aliases.py --check --remove-redundant` — **PASS**, 24 aliases clean.
- `python3 website/check-header-parity.py` — **PASS**, 177 standard pages and 23 intentional exceptions.
- `bash website/test-predeploy-chain.sh` — **PASS**, all pre-deploy checks and sentinel self-tests.
- `GET /`, `/refer`, `/robots.txt`, `/sitemap.xml`, the county page, and the Pasadena city page — **HTTP 200**.
- `GET /events` and `/providers` — **HTTP 404**, as required for retired/unavailable routes.
- Live homepage and `assets/chat.js` — **zero** `/.netlify/functions/` references.
- Live-referenced logo, font, and homepage asset checks — **HTTP 200**.
- A production screenshot of `https://eternallifehospice.com/` showed the homepage, credentials strip, hero, primary actions, cookie controls, and chat control rendering.

### Issues and disposition

1. **Transient startup health-check failures (resolved):** the deployment health probe raced the application during a restart at 03:48:34 UTC. The application returned 200 one second later, the deployment remained healthy, and no persistent application failure was found.
2. **Missing daily evidence for August 28 and August 31 (not resolved by inference):** those checks are not backfilled. This remains a process/readiness gap and is a reason to keep the old copy available.
3. **Analytics has no collected rows in the queried window (not an application error):** the analytics service is authorized, but no pageview telemetry was returned. This limits the stability conclusion and must not be represented as proof of normal traffic.
4. **Referral delivery proof is still open:** no referral was submitted in this observation pass. Keep the no-PHI delivery test and mailbox confirmation as a separate required gate before any Netlify freeze.
5. **Known Replit route-parity gaps remain:** the hosting investigation documents legacy aliases that still return 404 on Replit even though the Netlify copy redirects them. Do not retire the old copy until the approved route/link work is complete.

## Observation decision

**NO-GO for freezing, deactivating, or deleting Netlify as of 2026-09-01.**

The Replit deployment and final smoke test are green, and the Netlify rollback reference remains preserved. The decision stays **NO-GO** because the observation record has missing business-day evidence, analytics has no collected telemetry, referral delivery has not been re-proven in this window, and route/link work remains open. Netlify remains available and unchanged while those gates are completed.

### Cleanup status

**Confirmed:** 2026-09-01 04:20:14 UTC. The authorized mailbox user confirmed deletion of the original referral-mailbox message, its forwarded copy, and the requester acknowledgement. A Gmail verification query for receipt `4F8D77C12AEB` found the two visible copies in `TRASH`:

- Forwarded referral copy: `1a05b2c53291f4bc`
- Requester acknowledgement: `1a05b2c3fab065e6`

No test messages remain in the inboxes. The delivery-test cleanup gate is **CLOSED**.
