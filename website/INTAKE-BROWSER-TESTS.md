# Protected intake browser regressions

Run from the repository root:

```sh
node --experimental-websocket website/test-intake-browser.mjs
node website/test-intake-security.mjs
python3 website/test-form-antispam.py
```

## Phone-link interaction checks

```sh
node --experimental-websocket website/test-website-phone-browser.mjs
python3 website/test-website-phone.py
```

The focused phone browser suite needs Node 20+ and Chromium only; it does not
start PostgreSQL or the real intake backend. It loads the actual homepage,
contact card, chat script and intake-security module through the synthetic
fixture. Every API and third-party request is fulfilled locally. No form is
submitted and no email or AI provider is contacted.

At desktop and mobile widths it opens the chat, exercises the reachable local
emergency/nurse guidance and unavailable-AI fallback, opens a callback form and
calls the real `showFailure` renderer for verification, rejection and unknown
outcomes. A seeded tab reminder also exercises chat's own uncertain-outcome
renderer and close/reopen behavior. Assertions inspect rendered text and the
actual `tel:` URLs, not source strings. The historical FAQ chip definitions are
not exposed by the current chat UI and are not artificially enabled by this test.
The contact card's explicitly labeled office number remains distinct. Run the
paired Python suite to also protect approved acknowledgment email copy and
public response projection. This is display coverage, not submission coverage;
the broader intake suite below exercises submission outcome routing.

The browser suite requires Node 20+, Chromium on PATH (or `CHROMIUM_BIN`),
Python with `psycopg` and PostgreSQL's `initdb`/`pg_ctl` binaries on PATH.
Node 20 needs the WebSocket flag. It uses the browser's debugging protocol
directly, so there is no additional npm package or browser download.
The browser suite creates its own socket-only local PostgreSQL cluster and
disposable schema; it never uses the project's `DATABASE_URL`. The separate
`test-form-antispam.py` HTTP suite requires the existing development database.

## What the browser suite covers

The suite serves the unchanged homepage, referral page, chat script and shared
intake-security module from a temporary loopback HTTP server. For **each** family,
provider and chat flow, it runs desktop/keyboard and 390px mobile/touch cases:

- Required-input validation before requesting security.
- An interaction-required synthetic Turnstile button mounted by the actual module.
- Script load failure and successful script reload on retry.
- Provider error, expiry and timeout, with widget cleanup and no submission.
- Security-service failure, 403/429/503 delivery failure, malformed JSON and
  HTTP 200 without explicit acceptance.
- Assertive accessible errors, telephone fallback and preserved input values.
- Keyboard Tab/Shift+Tab access, Enter activation and unobstructed mobile taps.
- Disabled submission during verification and delivery, no early success, then
  actual visible confirmation only after the fixture releases acceptance.
- Intact submitted fields, fresh synthetic token fields on retry, verification
  response, content type, security wait and out-of-area phone retention.

Timeout acceleration applies only to the module's two-minute challenge timer.
It is disabled for the real-handler cases below. Reduced motion makes navigation
and chat greeting deterministic without replacing the UI or its event handlers.

## Real browser-to-handler checks

After the UI failure matrix, the fixture starts `intake-browser-backend.py`,
imports the actual `devserver.py` and `form_antispam.py` and forwards intake API
requests to that loopback backend without rewriting the browser's headers.
Within desktop and mobile, the negative security matrix and each form's
accepted/replay pair receive fresh backends/databases. Adding more form types
therefore cannot exhaust another case's production rate limit. No guard limits
are relaxed.

Both viewport cases verify:

- Browser-default GET without Origin, with `Sec-Fetch-Site: same-origin`.
- Same-origin GET with neither Origin nor Referer.
- POST rejection for absent, null and foreign Origin, even with same-origin
  Fetch Metadata. Only these negative cases alter headers through Chromium's
  request interception; all positive and cross-site requests use native headers.
- Missing security token and missing provider response rejection without mail
  or database reservations.
- The real shared module's newsletter, family, professional and chat submissions using
  signed tokens, the full 1.8-second minimum age, actual server validation,
  CAPTCHA-response checking and PostgreSQL reservations.
- Synthetic internal mail plus synthetic visitor acknowledgment, then replay
  rejection without additional mail.
- Cross-form token rejection.
- An intercepted second-origin document making actual cross-site GET and POST
  requests to the real endpoint. Browser-generated cross-site metadata must
  result in HTTP 403, no disclosed challenge token and no database/mail effects.
  These requests use `no-cors`; assertions inspect the handler's actual HTTP
  response, not an opaque response's unreadable browser body.

The real-server section mounts its synthetic challenge in a visible test
container. It checks shared-module/server integration, not page placement;
actual page placement and touch/keyboard access are checked by the six UI flows.

## Isolation and limits

The initial UI matrix uses synthetic intake API responses. The real-handler
mode uses a separate Python process that scrubs inherited credentials before
importing application modules and connects only to its disposable database.
Turnstile remains configured with synthetic credentials: its outbound
verification transport is intercepted, not bypassed. The actual submission
processor uses an injected synthetic mailer for both internal and receipt
messages. Python outbound TCP connections are blocked, and PostgreSQL has no
TCP listener. Unrelated API requests fail except the synthetic read-only review
request. Browser request interception fulfills **every external request locally**,
including the Turnstile script, analytics and accessibility widgets. No synthetic
contact data is sent to a provider. These fixtures must not be run in production.

The synthetic widget tests the site's integration contract, not Cloudflare's
cross-origin iframe, real challenge risk scoring, provider availability or
provider accessibility. Existing module and HTTP/PostgreSQL tests still cover
the broader malformed-input, concurrency, rate-limit and outage matrices.

Any failed assertion exits nonzero and prints the active flow and original
failure. Polling failures include bounded DOM, security and browser diagnostics.
The fixture closes browser/server resources, drops its isolated schema, stops
its PostgreSQL cluster and removes its temporary database and browser profile.
