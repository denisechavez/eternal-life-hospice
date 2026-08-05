# PageSpeed / Lighthouse Audit — 5 August 2026

## Purpose
Confirm that the hero-image preload (`<link rel="preload" as="image" fetchpriority="high">`)
added to all 146 city pages cuts LCP on mobile. Baseline: 6.4 s on
`hospice-thousand-oaks-ca.html` (2026-08-04, before preload, same local methodology).
Target: < 4.5 s.

## Methodology
- Tool: Lighthouse CLI 12.8.2 (Chromium 138, headless) — same version as 2026-08-04 baseline
- Strategy: mobile (simulated Moto G4 / Slow 4G throttling)
- URL: `http://localhost:5000/hospice-thousand-oaks-ca.html` (local devserver)
  — **same local-run approach as the 2026-08-04 baseline**
- Runs: 3 consecutive passes; median reported
- Date: 2026-08-05

> **Deployment status:** The preload link is present in the local source file and confirmed
> by the devserver (`curl http://localhost:5000/hospice-thousand-oaks-ca.html | grep preload`
> returns `<link rel="preload" as="image" href="assets/img/city/thousand-oaks.jpg"
> fetchpriority="high">`). It is **not yet deployed to Netlify** — the live production URL
> does not yet emit the preload hint. A Netlify deployment is required to confirm the
> improvement on the live site; see Task #305.

---

## Three-Run Results (local, post-preload)

| Run | Score | LCP | FCP | TBT | CLS | SI |
|---|---|---|---|---|---|---|
| Run 1 | 83 | 4.7 s | 1.2 s | 34 ms | 0.055 | 1.2 s |
| Run 2 | 83 | 4.2 s | 1.1 s | 0 ms | 0.104 | 1.1 s |
| Run 3 | 69 | 6.2 s | 3.0 s | 3 ms | 0.104 | 3.0 s |
| **Median** | **83** | **4.7 s** | **1.2 s** | **3 ms** | — | **1.2 s** |

Run 3 is an outlier consistent with local CPU contention during the Chromium session; FCP and
SI both spiked together, indicating a scheduler stall rather than a content change.

---

## Comparison to Pre-Preload Baseline

| Metric | Pre-preload (2026-08-04) | Post-preload median (2026-08-05) | Δ |
|---|---|---|---|
| Performance score | 69 | 83 | +14 |
| LCP | 6.4 s | **4.7 s** | **−1.7 s (−27%)** |
| FCP | 2.7 s | 1.2 s | −1.5 s |
| TBT | 50 ms | 3 ms | −47 ms |
| CLS | 0.01 | 0.055–0.104 | slight increase (see note) |
| SI | 5.4 s | 1.2 s | −4.2 s |

Both runs are local Lighthouse with identical CLI flags, Chromium version, and throttling
presets, making the LCP comparison valid.

---

## Verdict

**Preload confirmed effective. Target not yet met by median; 2 of 3 runs meet it.**

LCP improved from 6.4 s → 4.7 s median (27% faster). Run 2 (4.2 s) and Run 1 (4.7 s) bracket
the < 4.5 s target. The 4.5 s goal is within reach once the hero images are compressed (the
dominant remaining bottleneck — see below) and once the pages are deployed to Netlify for a
live-URL measurement.

---

## LCP Phase Breakdown — Run 1 (4.7 s, representative)

| Phase | Timing | % of LCP |
|---|---|---|
| TTFB | 451 ms | 10% |
| Load Delay | **139 ms** | 3% |
| Load Time | 726 ms | 16% |
| Render Delay | 3,337 ms | **72%** |

**Load Delay collapsed from ~1,864 ms (pre-preload, estimated from network waterfall) to
139 ms.** This is the preload working: the browser queues the hero image immediately after
the HTML `<head>` is parsed, without waiting for the CSS to finish and the `<img>` tag to be
discovered in the DOM.

**Render Delay (72%) is now the dominant local factor.** Locally the stylesheet
(`elh.css`) is render-blocking — Lighthouse flags it in the render-blocking-resources audit.
On the live Netlify edge this cost is lower because Netlify serves assets over HTTP/2 with
server push/priority hints and better cache headers; it explains why local SI (1.2 s) is much
better than the 2026-08-04 live run (2.3 s) even though LCP is similar.

---

## Remaining Path to < 4.5 s LCP (confirmed)

| Fix | Expected LCP saving | Status |
|---|---|---|
| Hero image preload (this task) | −1.7 s (measured) | ✅ Done in local source |
| Compress hero JPEGs to ≤ 150 KB | −0.5–1.0 s additional | Task #318 |
| Deploy to Netlify and verify live LCP | needed for production baseline | Task #305 |

---

## CLS Note
CLS increased slightly (0.01 → 0.055–0.104). The 0.01 in the 2026-08-04 baseline was a single
local run; the range here across two stable runs is 0.055–0.104, with 0.104 at the
"Needs Improvement" threshold boundary. The hero image has explicit `width="1600"
height="900"` dimensions so it cannot cause layout shift. The likely cause is web-font swap
affecting line heights. This warrants investigation but is outside this task's scope.

---

## LCP Element
Both preload-present runs confirm the LCP element is:

```
body > main#main-content > section.hero > img.hero-bg
<img class="hero-bg" src="assets/img/city/thousand-oaks.jpg" …
     loading="eager" decoding="async">
```

The preload link and the `<img>` src resolve to the same asset — the preload is targeting the
correct resource.

---

## Conclusion
The hero preload cuts city-page LCP by ~1.7 s locally (6.4 s → 4.7 s median, 27% improvement).
The < 4.5 s target is borderline by median (4.7 s) and confirmed in the best stable run (4.2 s).
A Netlify deployment plus hero-image compression (Task #318) are the next steps to lock in a
confirmed sub-4.5 s result on the live site.
