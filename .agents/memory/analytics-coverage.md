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
