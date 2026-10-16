# Protected intake browser regressions

Run from the repository root:

```sh
node --experimental-websocket website/test-intake-browser.mjs
node website/test-intake-security.mjs
python3 website/test-form-antispam.py
```

The browser suite requires Node 20+ and Chromium on PATH (or `CHROMIUM_BIN`).
Node 20 needs the WebSocket flag. It uses the browser's debugging protocol
directly, so there is no additional npm package or browser download.
The PostgreSQL suite separately requires the existing development database.

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
- Intact submitted fields, fresh signed-token fields on retry, verification
  response, content type, real minimum-age delay and out-of-area phone retention.

Timeout acceleration applies only to the module's two-minute challenge timer.
The real short security wait remains in force. Reduced motion makes navigation
and chat greeting deterministic without replacing the UI or its event handlers.

## Isolation and limits

No application backend, database, mailer, provider SDK, environment secrets or
production security configuration is imported by the fixture. The two intake API
responses are synthetic; unrelated API requests fail except the read-only review
request. Browser request interception fulfills **every external request locally**,
including the Turnstile script, analytics and accessibility widgets. No synthetic
contact data is sent to a provider. These fixtures must not be run in production.

The synthetic widget tests the site's integration contract, not Cloudflare's
cross-origin iframe, real challenge risk scoring, provider availability or
provider accessibility. Existing module and HTTP/PostgreSQL tests remain
necessary for signed-token validation, replay prevention and server guards.

Any failed assertion exits nonzero and prints the active flow and original
failure. Polling failures include bounded DOM, security and browser diagnostics.
The fixture closes browser/server resources and removes its temporary profile.
