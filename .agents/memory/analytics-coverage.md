---
name: Site analytics coverage
description: How GA4 + Microsoft Clarity are wired across the ELH static site
---

Analytics is loaded site-wide from a single shared file
`website/elh-preview/assets/analytics.js`, referenced with
`<script async src="/assets/analytics.js"></script>` before `</head>` on every
real page.

**Why:** Before this, GA4/Clarity existed ONLY on `index.html` (inline), so 40+
pages had zero measurement. A shared file = one place to update, no per-page drift.

**How to apply:**
- Any NEW page must include the shared tag, or it won't be measured.
- Do NOT also add inline GA/Clarity to a page (double-counting). `index.html`
  was converted from inline to the shared tag for this reason.
- The 3 meta-refresh redirect stubs (`resources/index.html`, `blog/index.html`,
  `care-brief/index.html`) intentionally have NO analytics.
- Root-relative `/assets/analytics.js` is required so pages in subfolders
  (`blog/`, `resources/`, `care-brief/`) resolve it correctly.

## Conversion measurement semantics

The owner explicitly authorized the Google Ads Website Lead Form conversion
destination `AW-18384023405/JC8lCKGQ9qsdEO3el75E`, value 1 USD, for confirmed
website form submissions. This supersedes the earlier base-tag-only scope for
that specific conversion, not permission for enhanced conversions or remarketing.

**Why:** The owner supplied the event snippet to measure successful advertising
leads; attempts, uncertain delivery and validation failures must not count.

**How to apply:** Emit from the shared verified-intake acceptance boundary,
after HTTP success plus explicit `ok` and `accepted`, with optional-tracking
consent. Deduplicate receipt IDs locally only; never send receipts or entered
form data to advertising. Preserve explicit GA4 destinations for other events.

Keep care/referral and reading custom events explicitly routed to GA4 when
the shared Google tag also has an advertising destination.

**Why:** Adding an Ads configuration changes the destinations of unscoped
Google events; care-seeking activity must not silently become advertising events.

**How to apply:** Preserve the explicit analytics-only destination when adding
or changing custom events. Installing the base Ads tag does not authorize
care-event conversion tracking, remarketing audiences or enhanced conversions.

Website submission success means the intake endpoint accepted the request, not that a patient was admitted. Keep care-request intent separate from general team-contact intent when interpreting conversions.

**Why:** ELH's objective is census growth, but website interaction counts cannot establish clinical eligibility, completed referrals or admissions. Combining unrelated contact clicks or treating submission attempts as completed intake would overstate the conversion funnel.

**How to apply:** Distinguish clicks, starts, attempts and confirmed website submission outcomes in reporting. Do not label any of those outcomes as an admission without a separate verified operational source. Custom event metadata must not include visitor-entered care or referral details.

## Curated reading measurement

Keep reading-event dimensions tied to editorial page routes and topic/group keys,
not visitor URLs, visible labels or form content. Preserve existing conversion
instrumentation when extending measurement to another analytics destination.

**Why:** Reading journeys concern potentially sensitive end-of-life care. The
approved measurement scope is fixed source, destination and topic only, using the
existing consent-aware GA4 loader without another tracker or dashboard.

**How to apply:** Emit only curated metadata, recheck consent on each interaction
and never delay navigation for delivery. Before comparing reading with care/referral
outcomes, confirm the outcomes exist in the same reporting service; do not assume
loading GA4 means every existing custom event is sent to GA4.

Keep reading context on the reading event rather than persisting or attaching a
visitor's reading history to accepted submissions. An outcome's source page is
the intake page, not an inferred originating article.

**Why:** Comparing existing consented event sequences is sufficient for the
approved reporting scope; carrying inferred end-of-life interests into outcome
records would add unnecessary sensitive context.

**How to apply:** Compare reading-step routes/topics with subsequent accepted
events in GA4 Explorations. Do not require a reading topic on the success event
or add attribution cookies/session storage to make that column appear.

Analytics releases must change every immutable script URL when the shared
script's bytes change, including authored templates, generator output and
request-time HTML transforms.
Follow the existing content-derived version check rather than keeping a city-
specific version override.

**Why:** Passing handler tests does not prove returning visitors receive new
events; a year-long cached URL can silently keep the old bridge active.
Request-time HTML transforms can also undo a correct authored asset version.

**How to apply:** Check asset-version consistency as part of publishing, not
just event behavior. Keep the unchanged-URL mutation check in the release chain.

## Approved consent presentation

Use the selected Refined Privacy Panel rather than the old cookie pill.
The owner approved its cream, plum and muted-gold treatment with Essential
only, Accept all and inline Manage preferences.

**Why:** The owner requested a different notification style and explicitly
selected this canvas design on October 27, 2026.

**How to apply:** Preserve the selected presentation when maintaining consent.
Keep optional trackers grouped and off until accepted; preserve saved choices
and the footer entry point. Treat future visual edits separately from changing
what visitors consent to.

## Call-tracking ownership

Use Nimbata, not WhatConverts, as the website browser call tracker. Keep it
behind optional tracking consent.

**Why:** On October 28, 2026, the owner explicitly authorized uninstalling
WhatConverts. This supersedes the earlier instruction to keep both browser
trackers.

**How to apply:** Do not reintroduce WhatConverts browser scripts or automatic
form capture. Preserve intake email delivery, both existing phone-number
placements and historical reporting/account data. Removing the website tag
does not authorize closing the provider account or deleting historical data.
Account-side number replacement and actual call attribution still require provider verification. Preserve
approval-hashed Journal source bytes when updating analytics versions; refresh
their script URLs in the final served HTML instead.

Verify tracker execution against the site's security policy, not just the
presence of a script element.

**Why:** Nimbata's tag was present in the DOM while its CDN was blocked by the
response policy. Installation alone did not prove that the tracker ran.

**How to apply:** Test script and connection permissions for the configured
provider endpoints, and check browser network responses when changing trackers.
Keep permissions specific rather than allowing arbitrary third-party hosts.

When verifying permission withdrawal that reloads the page, retain tracking
evidence from the departing document as well as checking the new document.

**Why:** A fresh document has an empty event queue even if the previous one
already emitted a conversion. Checking only the reloaded page can therefore
give a false privacy assurance.

**How to apply:** Exercise the actual settings controls and reload, capture
outgoing-document events without storing entered data, and distinguish a late
response to an abandoned submission from a confirmed result on the new page.

The owner explicitly approved the site-wide `unsafe-eval` tradeoff for
Nimbata on October 28, 2026, after being told it weakens script protection
for every allowed script, not just Nimbata.

**Why:** The configured vendor tag generates attribution-rule functions at
runtime. Its CDN returned HTTP 200, but the strict policy still stopped it
before it opened a tracking session.

**How to apply:** Preserve optional consent and specific provider host
permissions. Check successful session traffic, not only script downloads.
Do not treat this approval as permission for additional trackers, form
capture, live test calls, routing changes or broader security relaxations.
