# Public Form Intake — Production Operations

**Processor:** Replit deployment (`website/devserver.py` → `POST /api/form-submit`)  
**Delivery service:** Brevo transactional email (`BREVO_API`)  
**Outage alert channel:** Independent HTTPS webhook (`FORM_ALERT_WEBHOOK_URL`)
**Production domain:** `https://eternallifehospice.com`  
**No DNS change is part of this implementation.**

## Production routing

The public domain is served by the Replit Python deployment. The server validates each recognized form and asks Brevo to accept the internal notification. It returns JSON success only after Brevo accepts that internal message. Submission fields and files are not written to disk or a database.

The endpoint requires a same-origin browser request and limits each rightmost forwarded client address to 10 attempts per 10 minutes. Because Replit does not publish a sanitized forwarding-header contract, a separate socket-peer circuit breaker caps the entire proxy path at 30 attempts per 10 minutes; rotating a spoofed forwarded address cannot bypass that cap. Referral note fields are capped at 1,200 characters and rejected before delivery when they contain common identifiers such as dates of birth, record/insurance numbers, Social Security numbers, or explicitly labeled patient names. This is a guardrail, not permission to enter PHI; the public forms continue to request only a general, non-identifying situation.

| Public path / form | Internal destination | Requester acknowledgement |
|---|---|---|
| Homepage family request (`elh-family`) | `referral@eternallifehospice.com` | If a valid email was supplied |
| Homepage physician referral (`elh-physician`) | `referral@eternallifehospice.com` | No email field on this variant |
| Homepage case manager referral (`elh-casemanager`) | `referral@eternallifehospice.com` | If a valid email was supplied |
| Homepage care coordinator (`elh-coordinator`) | `referral@eternallifehospice.com` | No |
| `/refer` professional referral (`elh-physician`) | `referral@eternallifehospice.com` | Yes; work email is required |
| Hidden chat callback (`elh-chat-callback`) | `referral@eternallifehospice.com` | No; the chat confirms on screen |
| Homepage Care Brief voice form (`elh-voice`) | `info@eternallifehospice.com` | Yes |
| `/careers` (`elh-careers`) | `info@eternallifehospice.com` | Yes |
| `/care-brief.html` signup (`elh-care-brief-signup`) | `info@eternallifehospice.com` | Yes |

The sender is the established Brevo address `no-reply@eternallifehospice.com`. Acknowledgements contain only static wording and the generated confirmation ID; they never echo referral notes, clinical descriptions, or uploaded files.

## Browser acceptance and failure behavior

- The homepage, `/refer`, careers, Care Brief signup, and chat callback submit to `/api/form-submit`.
- JavaScript requires a JSON response containing both `"ok": true` and `"accepted": true`. A generic HTTP 200 or an HTML preview page is not considered success.
- If validation or Brevo delivery fails, the form remains usable, the submit button is restored, and the page shows the 24/7 fallback: `805.953.7273`.
- Cross-origin submissions return `403`; throttled clients return `429`; both responses include the phone fallback.
- `POST /` now returns 404 JSON instead of a fake preview success.

## Delivery outage alerts

Every failed internal delivery still writes the privacy-safe workflow event
`FORM_DELIVERY_FAILED provider=brevo`. After three failures within five
minutes, the processor sends one JSON alert to the independently configured
`FORM_ALERT_WEBHOOK_URL`. Alerts are suppressed for 15 minutes after an alert,
so a continuing Brevo outage cannot flood the team. The alert channel is
best-effort and never changes the public response.

The alert JSON contains exactly these fields:

```json
{
  "timestamp": "2026-08-26T12:00:00Z",
  "environment": "production",
  "processor_status": "delivery_unavailable",
  "failure_count": 3
}
```

Set `FORM_ALERT_ENVIRONMENT` to the deployment label (for example,
`production`). Store the webhook URL as a Replit secret or environment value;
never place it in source control. If no URL is configured, the processor
continues serving the phone fallback and does not send an external alert.

## Synthetic end-to-end test

Run:

```sh
python3 website/test-form-intake.py
```

The `SyntheticEndToEndTest` starts the real Python application handler and a local Brevo-compatible capture server. It submits only:

- synthetic referrer name,
- reserved fictional `805.555.0199` phone number,
- `synthetic-e2e@example.com`,
- a statement explicitly marked as a non-PHI routing check.

The test confirms:

1. the app returns accepted JSON only after the internal message is accepted;
2. the internal message is addressed to `referral@eternallifehospice.com`;
3. a separate acknowledgement is addressed to the synthetic requester;
4. the internal message contains the synthetic routing note;
5. the requester acknowledgement does not echo that note;
6. the captured messages are cleared in the test teardown.

This test creates no Brevo, mailbox, database, or filesystem retention record. For a live post-deploy smoke test, use the same synthetic-only values, confirm the message and acknowledgement in their destination mailboxes, then delete both mailbox messages. Brevo retains only its normal transactional metadata according to the account retention policy; the application itself has no record to remove.

The same test suite includes a synthetic Brevo-outage check. It forces the
provider to fail, submits four synthetic requests, confirms every response is
`502` with `805.953.7273`, confirms exactly one alert after the third failure,
and verifies that the alert contains no submitted values.

## Netlify duplicate

The separate Netlify copy is not the production processor. Production browser code targets `/api/form-submit`, a route provided by the Replit deployment. The Netlify `submission-created.js` file is explicitly labeled legacy-only. Both Netlify build configurations run `website/strip-netlify-form-routing.py` in their ephemeral build workspace, removing legacy Netlify Forms attributes and changing native form actions to `/api/form-submit`. If someone opens the Netlify hostname, the Replit-only same-origin API is unavailable and the public UI shows the phone fallback instead of a false confirmation.

Do not repoint DNS or make the Netlify copy authoritative without explicit approval and a new end-to-end routing test.

## Operational checks

1. Confirm `BREVO_API` exists in the Replit production environment.
2. Confirm `FORM_ALERT_WEBHOOK_URL` and `FORM_ALERT_ENVIRONMENT` exist in the Replit production environment and that the webhook is monitored by the intake team.
3. Confirm `referral@eternallifehospice.com` is monitored by the intake team.
4. Watch workflow logs for `FORM_DELIVERY_FAILED provider=brevo`; submitted fields are never logged.
5. If Brevo is unavailable, callers should use `805.953.7273`; do not change the endpoint to return success during an outage.
