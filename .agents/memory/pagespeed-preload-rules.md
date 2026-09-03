---
name: PageSpeed mobile optimisation — preload rules
description: What it took to get ELH homepage from 72% → 97% mobile Performance on PageSpeed Insights.
---

## The working formula (Jul 2026, Lighthouse 13, Slow 4G mobile)

```html
<!-- Image preloads: fetchpriority="high" MUST be on the <link>, NOT on the <img> inside <picture> -->
<link rel="preload" as="image" href="assets/img/hero-mobile-640.webp"
      media="(max-width:768px)" type="image/webp" fetchpriority="high">
<link rel="preload" as="image" href="assets/img/inline-cdca7d25f7.webp"
      media="(min-width:769px)" type="image/webp" fetchpriority="high">

<!-- Font preloads: keep ALL used weights; removing Fraunces harms FCP without helping LCP -->
<link rel="preload" as="font" href="assets/fonts/inline-3c986c6628.woff2" type="font/woff2" crossorigin>
<link rel="preload" as="font" href="assets/fonts/inline-9a18143814.woff2" type="font/woff2" crossorigin>
<link rel="preload" as="font" href="assets/fonts/inline-7c1d820d25.woff2" type="font/woff2" crossorigin>

<!-- Preconnects: GTM, Clarity, AND Brevo (Brevo = 220ms LCP saving) -->
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://www.clarity.ms">
<link rel="preconnect" href="https://cdn.brevo.com">

<!-- analytics.js: defer (not async) = 30ms TBT vs 200ms -->
<script defer src="/assets/analytics.js"></script>
```

## Key lessons

**Why:** `fetchpriority="high"` on the `<img>` fallback inside `<picture>` causes the browser's
preload scanner to fetch the WRONG image (the desktop JPEG fallback) with high priority on mobile.
It must be on the `<link rel="preload">` instead, where it correctly promotes the preloaded hero
WebP to "Highest" browser priority — ahead of the 266KB Fraunces font preloads.

**The trap:** Removing Fraunces preloads seemed logical (reduce bandwidth competition) but LCP
stayed at ~9.5s with OR without them. The real fix was `fetchpriority` on the preload link.
Fraunces preloads are needed for FCP (1.4s vs 2.6s without them).

**Before / after:**
- FCP: 3.4s → 1.4s (font preloads)
- LCP: 9.7s → ~2s (fetchpriority on image preload link)
- TBT: 200ms → 20ms (analytics.js defer)
- Score: 72 → 97

## Clarity causes non-deterministic LCP

Scores bounced 72% ↔ 97% on identical code. Root cause: Clarity's session-recording
initialization (DOM layout reads / forced reflows) sometimes ran BEFORE the hero image
painted → pushed LCP to ~9.5s. Fix: gate all third-party injection (GA4, Clarity, Brevo)
behind `window addEventListener('load', init)` inside analytics.js. Hero paints at ~1.5s;
load event fires at ~2–3s; Clarity can never interfere with LCP. analytics.js stays `defer`.

## Do NOT repeat these mistakes
1. Never put `fetchpriority="high"` on the `<img>` fallback src inside `<picture>` — it triggers
   a wasted high-priority fetch for the wrong (desktop) image on mobile viewports.
2. Never remove Fraunces preloads to "fix LCP" — they don't cause LCP issues; they help FCP.
3. The `crossorigin` attribute is required on all font preloads (even same-origin) to match
   the anonymous-CORS request that @font-face makes.

## Static asset cache policy

Static assets use a one-year immutable browser cache; the generated search index remains
revalidated so site search cannot become stale.

**Why:** The site's CSS and JavaScript references carry explicit version query strings, and
images/fonts are deployment-controlled static files. A one-day cache caused Lighthouse to
report avoidable repeat-visit transfer cost.

**How to apply:** Whenever a named CSS or JavaScript file changes, bump its query-string
version in the shared page sources. Do not apply immutable caching to the search index or HTML.

The production proxy may rewrite the asset directive from `public` to `private` while
preserving the one-year `max-age`; verify the TTL and `immutable` flag rather than expecting
the origin header text to remain identical.

**Why:** The deployed production response applies its own cache privacy policy even when the
origin server and fallback headers specify public caching.

**How to apply:** Treat a production asset response as fixed when it has the intended long
`max-age` and `immutable` behavior, while leaving HTML and search-index revalidation intact.
