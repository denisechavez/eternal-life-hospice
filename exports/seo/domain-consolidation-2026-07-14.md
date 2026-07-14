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

## What we verified (live test, July 14, 2026)

| Domain tested | What happens | Final destination | Permanent (301)? |
|---|---|---|---|
| `eternalhospice.com` | Forwards (via a `www` hop) | `https://eternallifehospice.com/` | ✅ Yes |
| `www.eternalhospice.com` | Forwards (via a `www` hop) | `https://eternallifehospice.com/` | ✅ Yes |
| `eternallifehospiceinc.com` | Forwards directly | `https://eternallifehospice.com/` | ✅ Yes |
| `www.eternallifehospiceinc.com` | Forwards directly | `https://eternallifehospice.com/` | ✅ Yes |
| `eternallifehospice.com` (the real one) | Loads the site | — | — (this is home) |

**Bottom line:** every version of both extra domains lands on
`https://eternallifehospice.com/`, and every hop along the way is a permanent 301.
The "three websites" problem flagged as the #1 finding in the backlink audit is
**resolved at the domain level**.

> Note: this redirect lives on **the extra domains' own hosting**, not in this
> project. That's correct and expected — the audit specifically said it could not
> be done from our site's `_redirects` file. Nothing in this project needed to
> change to achieve the consolidation.

---

## Two small, optional polish items (not blockers)

These do **not** affect the core result — authority is already consolidating.
They're minor tidy-ups for whoever manages the two extra domains, if/when it's
convenient:

1. **Deep links go to "Page Not Found" instead of forwarding.**
   The homepage of each extra domain forwards perfectly. But a *specific inner
   page* — e.g. `eternalhospice.com/resources` — currently shows a 404 rather than
   forwarding to `eternallifehospice.com/resources`. In practice this matters very
   little (almost nobody links to inner pages of the old mirror sites), but the
   cleanest setup is a **"forward every path" (wildcard) 301** so any old link
   lands on the matching page. *Fix location: the extra domains' hosting/DNS —
   not this project.*

2. **`eternalhospice.com` takes an extra hop.**
   It forwards to `www.eternallifehospice.com` first, then to
   `eternallifehospice.com`. It still ends up in the right place with permanent
   redirects, so Google handles it fine; pointing it **straight** at
   `https://eternallifehospice.com/` in one hop is marginally cleaner and slightly
   faster. `eternallifehospiceinc.com` already does the clean single hop.
   *Fix location: the extra domains' hosting/DNS — not this project.*

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
