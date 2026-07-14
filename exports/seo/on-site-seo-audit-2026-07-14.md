# On-Site SEO, Meta & Technical Audit — Eternal Life Hospice

**Date:** July 14, 2026
**Scope:** The live website only (`website/elh-preview/`, which publishes to
eternallifehospice.com). This is a technical/on-page pass — titles, descriptions,
canonicals, social-share tags, structured data, sitemap, analytics, and the AI
answer file. Backlinks and off-site work are handled in a separate task.

---

## The short version (what changed and why it matters)

1. **Visitor tracking was only running on the home page.** Every other page —
   all 40+ of them — had no Google Analytics or Microsoft Clarity code. So the
   business could see traffic to the front door but was effectively blind to how
   people used the city pages, blog, resources, referral page, and everything
   else. **Fixed:** one shared tracking file is now loaded on every real page, so
   all pages now report visits and behavior. This is the single most valuable
   fix in this pass — it restores accurate measurement across the whole site.

2. **The home page was missing the tags that control how it looks when shared**
   (on Facebook, LinkedIn, texts, and X/Twitter). **Fixed:** added the missing
   share-preview tags so the home page now shows a proper title, description, and
   image card when someone shares it — matching every other page on the site.

3. **A few page titles and many descriptions were too long** and were getting cut
   off in Google results. **Fixed:** trimmed the longest ones so they read
   cleanly in search listings without losing the important local keywords.

4. **The AI answer file (`llms.txt`) pointed to a page that no longer exists** and
   was missing several newer pages. **Fixed:** updated it so AI search tools
   (ChatGPT, Perplexity, Google AI, etc.) get current, accurate information.

Everything else on the technical side checked out clean — no broken links, no
broken images, valid structured data, and a complete, accurate sitemap.

---

## Before → After (page-by-page essentials)

### 1. Analytics coverage — the big one
| | Before | After |
|---|---|---|
| Home page (`/`) | GA4 + Clarity present (inline) | GA4 + Clarity via shared file |
| All other 40+ pages | **No tracking at all** | GA4 + Clarity via shared file |
| How it's loaded | Copy-pasted only on home page | One shared file: `/assets/analytics.js` |

- Created `website/elh-preview/assets/analytics.js` containing both Google
  Analytics 4 (`G-JRLYCRC48G`) and Microsoft Clarity (`xddyi1rk95`).
- Added `<script async src="/assets/analytics.js"></script>` to **44 pages**.
- Replaced the home page's old inline tracking with the same shared file, so it
  is **not double-counted**.
- Skipped only the 3 invisible "redirect" helper files (they instantly forward
  visitors and shouldn't be tracked).
- **Why a shared file:** one place to update in future (add a tag, change an ID)
  instead of editing 44 pages by hand. Netlify is **not** injecting analytics at
  deploy time, so this had to live in the site itself.

### 2. Home page social-share & canonical tags
| Tag | Before | After |
|---|---|---|
| `og:url` | missing | `https://eternallifehospice.com/` |
| `og:site_name` | missing | `Eternal Life Hospice` |
| `twitter:card` + title/description/image | **all missing** | added (large image card) |
| Canonical | `...com` (no slash) | `...com/` (matches sitemap & `og:url`) |

Every other page already had a Twitter card; the home page — the most-shared page
— was the only one missing it. Now consistent site-wide.

### 3. Titles trimmed (were being cut off in Google)
| Page | Before (chars) | After (chars) |
|---|---|---|
| Home | ~82 — "…Ventura & Los Angeles County Hospice" | ~65 — "Eternal Life Hospice — Care That Honors Life \| Ventura & LA County" |
| Care Brief article | 99 — had the brand name twice | ~70 — "Hospice Is Part of Life — A Continuation of Care \| Eternal Life Hospice" |

Remaining titles all fall in a healthy range. A few blog-post titles run slightly
long (78–84 characters) but that is normal for descriptive article headlines and
was left as-is.

### 4. Meta descriptions tightened
- **21 pages** had descriptions trimmed to a cleaner length (roughly 130–160
  characters) so they display fully in search results.
- **13 city pages** had a repeated boilerplate phrase shortened
  ("Independent, integrative comfort care brought home, with a nurse on call
  24/7." → "Independent comfort care at home, with a nurse on call 24/7.").
  **Every neighborhood keyword was preserved** — only filler was cut.
- Before, descriptions ran as long as **231 characters**; after, the vast
  majority are under 160.
- **Deliberately left slightly long (185–210 chars):** a handful of city pages
  (Beverly Hills, Camarillo, Malibu, Oxnard, Newbury Park, Woodland Hills,
  Thousand Oaks). Their descriptions carry unique neighborhood names that help
  each city page rank locally and look distinct from its neighbors. Cutting them
  further would remove valuable local keywords for a cosmetic gain. Recommend
  leaving as-is unless you want strict 160-character uniformity.

### 5. AI answer file (`llms.txt`) refreshed
| | Before | After |
|---|---|---|
| Dead link | `/providers` (page was retired) | replaced with `/refer` |
| Missing pages | blog, media-kit, sound-bath, careers | all added |
| Cost wording | blunt "$0 out of pocket" | "covered by the Medicare Hospice Benefit — most patients pay little to nothing out of pocket" (accurate & compliant) |
| Brand section | none | added The Eternal Standard four pillars + tagline |

---

## What was checked and found HEALTHY (no changes needed)

- **Broken links:** none. Every internal link and every image/asset resolves.
  (An automated crawler flagged some social "share this" links as broken — those
  were false positives; the links are valid and point to Facebook/LinkedIn/X.)
- **External links:** all resolve. A few return "blocked" codes to automated
  checkers (ACHC, CDPH, Instagram, Aidin) — that's normal bot-protection, not a
  broken link.
- **Structured data (schema):** every JSON-LD block on every page is valid and
  parses cleanly. City pages carry LocalBusiness data; articles carry Article
  data; the site carries Organization/WebSite data.
- **Sitemap:** exactly 41 URLs — a perfect 1-to-1 match with the 41 public,
  indexable pages. No private/noindex pages leaked in; nothing missing.
- **robots.txt:** correctly allows crawling and points to the sitemap.
- **Noindex hygiene:** the internal-only pages (CareBidet, the Care Brief hub,
  the 404 page, and the 3 redirect helpers) are correctly hidden from search and
  correctly excluded from the sitemap.
- **Duplicate-content protection:** every page has a self-referencing canonical.

---

## City-page review (13 city pages + 1 county hub)

These were reviewed for the "doorway page" risk (near-identical pages that Google
penalizes). **Verdict: healthy, keep them.** Each city page has:

- a unique title and H1 (e.g. "Hospice Care in Malibu"),
- a genuinely unique intro written for that place ("along the Malibu coast — from
  Point Dume and the Malibu Colony…" vs. "across Ventura — from the Pier and
  Downtown…"),
- unique neighborhood lists, a unique hero image, and per-city LocalBusiness
  structured data,
- ~7,000 characters of content each — not thin.

The shared parts (navigation, footer, the standard-of-care sections) are the
normal, expected template. **Recommendation:** keep all city pages; just make
sure any *future* city pages get the same genuinely-unique intro treatment rather
than a find-and-replace of the city name.

---

## Recommended follow-ups (optional, not done in this pass)

1. **Google Search Console verification:** the home page still has a placeholder
   comment for the verification code. Once you have the code from Search Console,
   it can be pasted in so Google can report indexing/traffic directly.
2. **"No copays / $0" wording:** several pages state hospice is at no cost. The
   Medicare Hospice Benefit does allow small copays for some outpatient drugs and
   respite care. Not an SEO issue, but worth a light compliance wording review
   across the site (the `llms.txt` file was already softened in this pass).
3. **Sitemap `lastmod` dates:** accurate today; refresh them whenever page
   content meaningfully changes so search engines re-crawl promptly.
4. **Strict 160-char descriptions:** if you want every city description under 160
   characters for uniformity, that can be a quick follow-up — noting the local-
   keyword trade-off above.

---

## Files changed in this task

- **Created:** `website/elh-preview/assets/analytics.js`
- **Rewrote:** `website/elh-preview/llms.txt`
- **Edited (analytics tag added):** 44 pages
- **Edited (home page head — titles/OG/Twitter/canonical):** `index.html`
- **Edited (title):** `care-brief/hospice-is-part-of-life-a-continuation-of-care.html`
- **Edited (descriptions):** 21 pages, plus the shared phrase on 13 city pages

*Nothing was published. Changes go live when you click **Git → Sync** in Replit,
which triggers Netlify to deploy.*
