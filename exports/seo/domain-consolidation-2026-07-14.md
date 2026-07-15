# Domain Consolidation — Verification & Status

**Date:** July 14, 2026
**Business:** Eternal Life Hospice, Inc.
**Official domain:** https://eternallifehospice.com/
**Companion to:** `inbound-backlink-audit-2026-07-14.md` (§2, "the three websites problem")

---

## The headline (plain language)

**Good news: the hardest part is already done.** The two extra "shadow"
websites — `eternalhospice.com` and `eternallifehospiceinc.com` — are **no longer
running as separate copies of the site**. Both now automatically forward visitors
(and, just as important, Google) to the one official domain,
**eternallifehospice.com**, using a **permanent (301) redirect**.

A "301" is the specific type of forward that tells Google *"this move is
permanent — hand the search credit over to the new address."* That is exactly the
outcome this task was aiming for: search authority stops splitting three ways and
starts stacking on the single domain we actually invest in.

We confirmed this by visiting each domain live and following the forwarding chain
to its destination. The evidence is below.

---

## What we verified (live test, July 14–15, 2026)

### Homepage forwarding — ✅ working

| Domain tested | HTTP code | Redirects to | Permanent (301)? |
|---|---|---|---|
| `eternalhospice.com/` | 301 | `https://www.eternallifehospice.com/` (then → real site) | ✅ Yes |
| `eternallifehospiceinc.com/` | 301 | `https://eternallifehospice.com/` | ✅ Yes |

### Deep-path forwarding — ❌ not yet working (action needed)

| URL tested | HTTP code | Result |
|---|---|---|
| `eternalhospice.com/resources` | 404 | Page Not Found — path not forwarded |
| `eternallifehospiceinc.com/resources` | 404 | Page Not Found — path not forwarded |

**Bottom line:** the homepage redirect is solid and search authority is consolidating.
The remaining gap is that GoDaddy's forwarding is configured as root-only, so any
deep link to the old domains returns a 404 instead of forwarding to the matching page.
Fix is one checkbox in GoDaddy — see the guide below.

> Note: this redirect lives on **the extra domains' own hosting**, not in this
> project. That's correct and expected — the audit specifically said it could not
> be done from our site's `_redirects` file. Nothing in this project needed to
> change to achieve the consolidation.

---

## Two small, optional polish items — action available

These do **not** affect the core result — authority is already consolidating.
They're minor tidy-ups for whoever manages the two extra domains in GoDaddy.

> **Step-by-step instructions:** `exports/seo/godaddy-wildcard-redirect-guide-2026-07-15.md`
> That guide walks through both fixes (wildcard forwarding + single-hop cleanup)
> in plain language with screenshots-friendly descriptions and verification steps.

1. **Deep links go to "Page Not Found" instead of forwarding.** *(Priority fix)* — ❌ still pending as of July 15, 2026
   The homepage of each extra domain forwards perfectly. But a *specific inner
   page* — e.g. `eternalhospice.com/resources` — currently shows a 404 rather than
   forwarding to `eternallifehospice.com/resources`. The fix is a single checkbox
   in GoDaddy's forwarding settings: **"Forward with Path"** (also called
   "Forward all paths" or "Include path and query string" depending on GoDaddy's
   current interface). Once enabled, any old link lands on the matching page.
   *Fix location: GoDaddy domain forwarding settings — not this project.*

2. **`eternalhospice.com` takes an extra hop.** *(Nice-to-have)* — ❌ still pending as of July 15, 2026
   It forwards to `www.eternallifehospice.com` first, then to
   `eternallifehospice.com`. It still ends up in the right place with permanent
   redirects, so Google handles it fine; pointing it **straight** at
   `https://eternallifehospice.com/` in one hop is marginally cleaner and slightly
   faster. `eternallifehospiceinc.com` already does the clean single hop.
   *Fix: change "Forward to" field in GoDaddy to remove the `www` prefix.*

---

## Re-verification — July 15, 2026

Live tests run after the GoDaddy guide was written confirm the fixes **have not yet been applied** in GoDaddy. The table below is the current state — everything is the same as the initial July 14 audit.

### Homepage forwarding — ✅ still working

| Domain tested | HTTP code | Redirects to | Permanent (301)? |
|---|---|---|---|
| `eternalhospice.com/` | 301 | `https://www.eternallifehospice.com` (extra hop) | ✅ Yes |
| `eternallifehospiceinc.com/` | 301 | `https://eternallifehospice.com` (clean) | ✅ Yes |

### Deep-path forwarding — ❌ still not working

| URL tested | HTTP code | Result |
|---|---|---|
| `eternalhospice.com/resources` | 404 | Page Not Found — path not forwarded |
| `eternalhospice.com/blog` | 404 | Page Not Found — path not forwarded |
| `eternallifehospiceinc.com/resources` | 404 | Page Not Found — path not forwarded |
| `eternallifehospiceinc.com/media-kit` | 404 | Page Not Found — path not forwarded |

**Action needed:** Log in to GoDaddy and follow the guide at
`exports/seo/godaddy-wildcard-redirect-guide-2026-07-15.md` to enable
"Forward with Path" on both domains. This is a ~10-minute task entirely inside
the GoDaddy control panel — nothing in this project needs to change.
Once done, re-test the four deep-path URLs above and update this section to ✅.

---

## Housekeeping to keep the win (ongoing)

- **Keep both extra domains registered — do not let them lapse.** As long as we
  own them and point them at the real site, the consolidation holds and no one
  else can grab a confusingly-similar name. If a renewal notice arrives for
  `eternalhospice.com` or `eternallifehospiceinc.com`, **renew it.**
- **Point directories at the one official domain.** Anywhere the business is
  listed online, the website field should read `eternallifehospice.com` (never one
  of the extra domains). This overlaps with the separate name/address cleanup work
  and is tracked there — no action needed here beyond awareness.

---

## What this task did and didn't need

- **Needed:** confirm the official domain (`eternallifehospice.com`) and verify the
  two extra domains permanently redirect to it. ✅ Both confirmed.
- **Did not need:** any change inside this project. The redirects live on the
  extra domains' own hosting, exactly as the audit predicted.
- **Left open (by design):** the two optional polish items above and the ongoing
  "keep registered / directories point to the official domain" housekeeping — all
  of which happen at external hosting/registrars, not in this codebase.

*Method: each domain and a sample of `www`/deep-path variations were requested
live and their redirect chains followed to the final destination, recording the
HTTP status (301 = permanent) at every hop.*
