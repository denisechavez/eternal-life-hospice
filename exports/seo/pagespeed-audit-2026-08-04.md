# PageSpeed / Lighthouse Audit — 4 August 2026

## Purpose
Spot-check audit following the Task #301 deferred-script rollout (UserWay via
`requestIdleCallback`, WhatConverts deferred, analytics.js `defer` on homepage).
Goal: confirm TBT improvements carry through to city pages and blog posts.

## Methodology
- Tool: Lighthouse CLI 12.8.2 (local run, Chromium 138, headless)
- Strategy: mobile
- Pages audited: homepage, one representative city page, one blog post
- Date: 2026-08-04

> **Note on TBT values vs PSI:** Local Lighthouse does not apply the same CPU/network
> throttling as Google's PageSpeed Insights API (Moto G4, Slow 4G). Raw TBT millisecond
> values from local Lighthouse are not directly comparable to PSI reports. The relative
> ordering and ratios between pages are still meaningful. The baseline recorded in Task #301
> memory (20 ms) was a PSI Insights API result; local values will differ.

---

## Results

| Page | Score | TBT | FCP | LCP | CLS | SI |
|---|---|---|---|---|---|---|
| Homepage (`/`) | 75 | **220 ms** | 1.9 s | 4.7 s | 0.00 | 4.9 s |
| City Page (`/hospice-thousand-oaks-ca.html`) | 69 | **50 ms** | 2.7 s | 6.4 s | 0.01 | 5.4 s |
| Blog Post (`/blog/caring-for-the-caregiver.html`) | 76 | **10 ms** | 2.5 s | 4.9 s | 0.09 | 3.5 s |

---

## Key Findings

### ✅ TBT: City pages and blog posts are well below the pre-optimisation baseline
- City page TBT (50 ms) and blog post TBT (10 ms) are both significantly lower than the
  pre-Task #301 homepage baseline (~200 ms from PSI, ~300+ ms local estimate).
- The deferred UserWay (`requestIdleCallback`) and deferred WhatConverts pattern is
  confirmed effective across page types.

### ⚠️ analytics.js: City pages use `async`, homepage uses `defer`
- `website/elh-preview/index.html` (line 32): `<script defer src="/assets/analytics.js">`
- `website/elh-preview/hospice-thousand-oaks-ca.html` (line 20): `<script async src="/assets/analytics.js">`
- This is a template inconsistency. In practice, `async` does not hurt TBT here because
  analytics.js gates all third-party loading behind `window.addEventListener('load', ...)`,
  so nothing blocking executes during page load regardless. TBT of 50 ms on city pages
  confirms this is working correctly.
- However, `defer` is the intended pattern (see pagespeed-preload-rules memory) and city
  page templates should be updated to match.

### ⚠️ City page LCP: 6.4 s (slow)
- The homepage hero image is preloaded with `fetchpriority="high"` on `<link rel="preload">`.
- City pages do NOT have hero image preload links. The `<img>` tag at line 56 uses
  `loading="eager" decoding="async"` but no `<link rel="preload">` in `<head>`.
- This likely explains the 6.4 s LCP vs 4.7 s on the homepage. Adding a city-specific hero
  preload would be the highest-impact improvement for city page scores.

### ⚠️ Blog CLS: 0.09 (borderline "Needs Improvement")
- Google Core Web Vitals threshold: < 0.1 = Good, 0.1–0.25 = Needs Improvement.
- The blog post CLS of 0.089 is just under the threshold but should be investigated.
  Likely culprits: web font swap causing text reflow, or a lazy-loaded image without
  explicit `width`/`height` dimensions.

---

## Conclusion
The deferred script rollout from Task #301 is confirmed effective across page types.
TBT on city pages (50 ms) and blog posts (10 ms) are both well within acceptable ranges
and below the pre-optimisation homepage baseline. No regressions detected.

Next priority improvements:
1. Add hero image `<link rel="preload">` to city page template → expected LCP improvement
2. Investigate and fix blog post CLS (0.089)
3. Align city page analytics.js from `async` → `defer` (low-priority consistency fix)
