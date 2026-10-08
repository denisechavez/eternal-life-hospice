# Compare reading journeys with accepted website submissions

## Measurement contract

Use the existing GA4 property loaded by `assets/analytics.js` (`G-WTMEYKXW8H`).
No new tracker, dashboard, identifier or visitor-data store is required.
The existing consent-aware Umami events and their payloads remain unchanged.

| Event in GA4 | Meaning | Fixed custom parameters |
| --- | --- | --- |
| `related_reading_click` | Click on an editorially curated reading link | `source_page`, `destination_page`, `topic` |
| `request_care_click` | Click on the Family · Seeking care CTA | `source_page`, `destination_page`, `placement` |
| `referral_cta_click` | Click on an internal `/refer` link | `source_page`, `destination_page`, `placement` |
| `form_success` | The website endpoint returned HTTP success, `ok: true` and `accepted: true` | `source_page`, `form`, `submission_type` |

`form_success` is not a submission attempt, email acknowledgement, clinical
eligibility decision, completed clinical referral or admission. Never label these
counts “admissions,” “patients” or census growth. An accepted request still needs
intake-team follow-through.

### Separate intent from accepted outcomes

| Authored form name | `submission_type` | Report classification |
| --- | --- | --- |
| `elh-family` | `care` | Accepted family care request |
| `elh-physician` | `referral` | Accepted professional referral request |
| `elh-casemanager` | `referral` | Accepted discharge-planning request |
| `elh-coordinator` | `professional_contact` | Care Ally relationship contact; exclude from care/referral totals |
| `elh-voice` | `team_contact` | Care Brief/education contact; exclude from care/referral totals |

These classifications use only authored form names, not input fields, selected
options or message contents. Do not send names, emails, phone numbers, patient
details, organisation names, messages, confirmation receipts or submitted fields
to analytics. Mirrored parameters are constructed from an explicit allowlist;
queries and fragments are not included in custom route dimensions.

## GA4 setup (property administrator)

After publishing the changes, open **Admin → Data display → Custom definitions →
Create custom dimension**. Reuse existing definitions if present; do not create
duplicates. Use **Event** scope for each:

| Suggested display name | Event parameter | Applies to |
| --- | --- | --- |
| Reading / CTA source page | `source_page` | Reading, care/referral clicks and accepted submissions |
| Reading / CTA destination page | `destination_page` | Reading and care/referral clicks |
| Reading topic | `topic` | Reading clicks only |
| Website form | `form` | Accepted submissions |
| Website submission type | `submission_type` | Accepted submissions |
| CTA placement (optional) | `placement` | Care/referral clicks |

Allow approximately 24–48 hours for custom dimensions to become available in
reports. They do not backfill historical reports. New GA4 outcomes likewise do
not backfill earlier Umami-only submissions.

For a privacy-safe acceptance check, use a synthetic submission and GA4 Realtime
or a locally enabled DebugView session; do not enable debug mode globally in the
published loader. Verify one `form_success` with a fixed form/category and no
entered content. The intake regression tests use synthetic responses and never
deliver a real submission.

If outcomes are needed as GA4 key events, create derived events in GA4 from
`form_success` with `submission_type = care` and `submission_type = referral`,
then mark those derived events as key events. Do not mark unfiltered
`form_success` as a care-request key event: it includes relationship/education
contacts. Do not sum a derived event and its underlying `form_success` as two
submissions. The website emits only the one original accepted event.

## One GA4 Exploration, not a new application dashboard

Create an Exploration named **Reading → website intake** with these tabs:

1. **Reading activity:** Free-form table using Source page, Destination page
   and Reading topic, filtered to `event_name = related_reading_click`; show
   Event count and Total users. This identifies the curated reading links used.
2. **Accepted intake:** Free-form table using Event name, Website submission
   type and Website form. Filter to `event_name = form_success` and
   `submission_type` equal to `care` or `referral`. Show Event count and Total
   users separately; a person can submit more than one form.
3. **Reading → care:** An open funnel: `related_reading_click` →
   `request_care_click` → `form_success` with `submission_type = care`.
   Use indirectly followed steps, not directly followed steps, so intervening
   pageviews do not break the journey.
4. **Reading → referral:** The same funnel with `referral_cta_click` and
   `form_success` with `submission_type = referral`.

Use a closed-funnel view when comparing only readers who entered at the reading
step. To include readers who submit directly without clicking a measured CTA,
compare a two-step reading → accepted-outcome funnel as well. Set and label a
consistent time window. GA4 funnels count users progressing through steps, not
accepted submission event totals; user journeys can span sessions unless
explicitly constrained. Do not describe them as session-only conversion rates.

For source/topic comparisons, filter the **reading step** to the desired
`source_page`, `destination_page` or `topic`, or compare reader segments in the
same Exploration. Do not apply a reading-topic event filter to `form_success`:
the topic belongs to the earlier reading event, not the form. Likewise,
`source_page` on a successful form is the intake page (`/` or `/refer`), not the
article previously read. The implementation deliberately does not carry reading
history or inferred health interests into outcome payloads or browser storage.

Compare observed journeys, not causation. Consent refusal, tracker blocking,
cross-device browsing and GA4 processing/thresholds limit what can be observed.
Clicks show intent, accepted website submissions show intake requests and only
an independently verified operational source can establish admissions.

## Consent, delivery and duplicate rules

- Only `elh_cc = all` permits events. Essential-only, missing/unreadable consent
  and consent revoked before submission acceptance suppress both destinations.
- Consent is checked at event time and again before GA4 delivery. Consent changed
  before the window-load callback also prevents GA4 boot.
- GA4 and Umami failures are isolated. Missing, throwing or rejecting trackers
  must not stop navigation, suppress the other destination or turn a successful
  intake response into a user-facing submission failure.
- No retry queue or cross-consent replay is added. If GA4 is absent before its
  loader is ready, the event may be lost rather than delaying care or retaining
  visitor history.
- Submit listeners do not emit GA4 outcomes. Each form emits from its accepted
  response hook only, once while that form remains on the page. Pending or already
  accepted forms reject repeated submit events; failed requests can be retried.
- A guard prevents repeated execution of the shared loader from binding handlers
  or booting third-party loaders again. Different forms and page reloads are
  separate requests; this is not a backend idempotency guarantee.
- Existing GA4 automatic collection/enhanced measurement is separate from these
  custom parameters. Audit property settings for automatic form interaction
  events and URL/query collection; never treat automatic `form_submit` as
  confirmed website acceptance.

## Regression checks

```sh
node --test website/test-custom-analytics-events.cjs website/test-submission-analytics.cjs
python3 website/test-form-intake.py
python3 website/test-internal-link-journeys.py
python3 website/check-analytics-version.py
```

The Node checks execute the actual shared analytics handlers and the actual
homepage/referral success hooks with synthetic API responses. They cover
essential-only consent, revocation, malformed/rejected/unaccepted responses,
tracker failure isolation, fixed metadata, category separation, retries and
duplicate submit/loader protection. Browser journey checks cover normal
keyboard navigation; their GA4 test double should retain the reading event
separately from any care/referral click on the same link.

## Immutable asset release rule

All authored analytics script URLs use the first 12 hexadecimal characters of
the shared script's SHA-256 as their `v` parameter. The city generator and
request-time link renderer derive the same URL from the current bytes,
without retired fixed-version rewrites or per-city version
overrides. Whenever `analytics.js` changes, update every HTML reference to the
new content-derived URL before publishing (preserve its async/defer attribute).
Pages generated from existing HTML templates inherit those references.

The pre-deploy chain runs `check-analytics-version.py`: it checks every authored
reference and actual city-template output, and its mutation self-test requires
the old URL to fail after the script bytes change. This is needed because
versioned assets have a one-year immutable cache; unchanged URLs can keep
returning visitors on the old event bridge.
