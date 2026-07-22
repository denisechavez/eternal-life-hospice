---
name: SEO technical audit decisions
description: Decisions made implementing the 36-point technical SEO brief (July 2026); schema rules, redirect strategy, content claims requiring human sign-off
---

# SEO Technical Audit — Key Decisions

## FAQPage schema rule (enforced from brief item 17)
- **Rule:** Add FAQPage schema ONLY when the complete questions AND answers are visibly displayed as Q&A pairs on that same page.
- **Applied:** FAQPage schema was REMOVED from `family-guide.html` — the booklet pages cover the topics but not as matching visible Q&A pairs.
- **Valid FAQPage schema locations:** `index.html` (homepage FAQ accordion is visible) and `refer.html` (Provider FAQ section is visible).
- **Why:** Google's guidelines deindex or ignore schema that doesn't match page content; can also trigger manual actions.

## OG image completeness standard
- Every published page needs `og:image`, `og:image:width` (1200), `og:image:height` (630), AND `og:image:alt`.
- City pages use their own local hero photo for `og:image` (e.g. `thousand-oaks.jpg`), not the shared `og-image-v2.jpg`.
- Twitter cards: every page should also have `twitter:title`, `twitter:description`, `twitter:image`.

## Canonical redirect strategy
- Netlify handles http→https at CDN level automatically.
- `_redirects` adds belt-and-suspenders rules for www/http variants → canonical https non-www (3 rules, `301!` force).
- Never add a Netlify preview deploy URL anywhere in content — they change per deploy.

## Content claims requiring human sign-off (not auto-fixed — accuracy depends on operational reality)
1. **"integrative therapies offered in every plan at no expense"** (homepage about section, ~line 1593) — Brief flags this. If true, it's fine; if not universally offered, add qualifier "when appropriate for the patient's care plan."
2. **"Same-Day Admissions"** (hero icon pills, hero quick-pill, ~lines 1184/1217) — pill text has no qualifier. FAQ answer and meta description correctly say "when clinically appropriate." The pill should ideally match. Consider changing pill to "Same-Day Admission*" or "Rapid Admission" to avoid an implied guarantee.
3. **"hospice-certified physicians"** (Clinical Confidence section ~line 1298, holistic medicine modal ~line 1467, chat widget ~line 1798) — this is a meaningful claim. Verify physicians on staff hold formal hospice/palliative medicine board certification. If not universally board-certified, safer phrasing: "physicians experienced in hospice and palliative care."
4. **"hospital-grade expertise"** (Clinical Confidence section) — subjective/marketing language; low risk but flag if brief-level compliance audit is ever done externally.

## Homepage Person schema for Aleksandra Dubina
- Added as standalone JSON-LD block on `index.html` head; links to `/aleksandra`.
- **Do NOT add Person schema to the `/aleksandra` page UNLESS that page is also updated** — two conflicting Person schemas for the same person on different pages can confuse crawlers.

## WebSite SearchAction schema
- Added `potentialAction: SearchAction` to the `WebSite` schema on homepage.
- The `?s=` query parameter is a standard WordPress-style search URL — the site is static and doesn't actually process it, but it's a common signal Google uses to understand the site is searchable. Low-risk addition.

## Sitemap maintenance
- After any content change, update `lastmod` in `sitemap.xml` to the date of the change (ISO 8601, YYYY-MM-DD).
- Use `sed -i` to target individual `<url>` blocks by their `<loc>` value.
