# Intake outage alerts

Intake protection reuses the independent `FORM_ALERT_WEBHOOK_URL` channel
used for email-delivery outages. No additional credentials are required.
`FORM_ALERT_ENVIRONMENT` labels the environment (default: `production`).
Do not point test runs at the real operations channel.

## When an alert is attempted

Each dependency has its own counter: three failures within five minutes
trigger an alert, with a 15-minute cooldown. Counters are bounded,
thread-safe and **per server process**, not fleet-wide. A new process starts
with fresh counters. They deliberately do not depend on the guard database:
an outage must not disable its own notification path.

| `processor_status` | Meaning / first check |
| --- | --- |
| `guard_storage_unavailable` | Guard database connection, query or commit failed. Check database availability and the abuse-guard schema. Failed delivery-slot cleanup also counts. |
| `turnstile_unavailable` | Configured verification cannot operate: timeout, HTTP/JSON/protocol failure, provider internal error, rejected server secret or incomplete key pair. Check provider health and server configuration without logging keys. |
| `guard_configuration_unavailable` | Intake signing key is absent or too short. Check server configuration without logging the key. |
| `delivery_unavailable` | Existing email-delivery alert; independent of the guard counters. |

Missing/invalid/expired visitor tokens, duplicate/replayed submissions,
hostname/action mismatches, honeypots and rate-limit rejections are not
service outages. Turnstile is optional when both keys are absent; that is
not an outage either.

## Privacy and public behavior

The webhook receives only timestamp, environment, fixed processor status
and aggregate failure count (capped during floods). It receives no form
contents, names, contacts, IPs, tokens, secrets, request URLs or exception
details. Keep environment labels operational, never patient-specific.

Verification outages return HTTP 503 with a retry instruction and
805.953.7273. They never bypass protection or claim delivery. If delivery
already failed, cleanup outages preserve the existing HTTP 502 telephone
fallback. Webhook failures are best-effort and keep the cooldown; they log
only the exception type, not the endpoint or response. An unset webhook
means no notification is sent. No recovery notification is currently sent.

## Verification

Run `python3 website/test-form-antispam.py` for guard, alert and real
HTTP/PostgreSQL regressions, and `python3 website/test-form-intake.py` for
delivery regressions. Both use synthetic submissions; guard alerts are
intercepted or sent to a mock endpoint. Do not run these against production.
