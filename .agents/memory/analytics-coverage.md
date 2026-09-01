---
name: Site analytics coverage
description: How GA4 + Microsoft Clarity are wired across the ELH static site
---

Analytics is loaded site-wide from a single shared file
`website/elh-preview/assets/analytics.js` (contains GA4 `G-JRLYCRC48G` +
Clarity `xddyi1rk95`), referenced with
`<script async src="/assets/analytics.js"></script>` before `</head>` on every
real page.

**Why:** Before this, GA4/Clarity existed ONLY on `index.html` (inline) and
Netlify does **not** inject any analytics snippet at deploy time — so 40+ pages
had zero measurement. A shared file = one place to update, no per-page drift.

**How to apply:**
- Any NEW page must include the shared tag, or it won't be measured.
- Do NOT also add inline GA/Clarity to a page (double-counting). `index.html`
  was converted from inline to the shared tag for this reason.
- The 3 meta-refresh redirect stubs (`resources/index.html`, `blog/index.html`,
  `care-brief/index.html`) intentionally have NO analytics.
- Root-relative `/assets/analytics.js` is required so pages in subfolders
  (`blog/`, `resources/`, `care-brief/`) resolve it correctly.

Replit custom events must stay behind the site's explicit analytics-consent
choice and may report only fixed event categories and route/placement metadata.
Never send form values, search text, chat text, names, contact details,
confirmation numbers, or other free-form content.

**Why:** Hospice interactions can contain health details or other sensitive
information even when a field is not intended for PHI.

**How to apply:** Add new events through the shared safe wrapper and use
allowlisted, non-user-entered dimensions only.
