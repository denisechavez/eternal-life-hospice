---
name: Site analytics coverage
description: How GA4 + Microsoft Clarity are wired across the ELH static site
---

Analytics is loaded site-wide from a single shared file
`website/elh-preview/assets/analytics.js` (contains GA4 `G-JRLYCRC48G` +
Clarity `xddyi1rk95`), referenced with
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

Website submission success means the intake endpoint accepted the request, not that a patient was admitted. Keep care-request intent separate from general team-contact intent when interpreting conversions.

**Why:** ELH's objective is census growth, but website interaction counts cannot establish clinical eligibility, completed referrals or admissions. Combining unrelated contact clicks or treating submission attempts as completed intake would overstate the conversion funnel.

**How to apply:** Distinguish clicks, starts, attempts and confirmed website submission outcomes in reporting. Do not label any of those outcomes as an admission without a separate verified operational source. Custom event metadata must not include visitor-entered care or referral details.
