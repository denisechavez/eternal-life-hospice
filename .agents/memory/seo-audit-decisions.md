---
name: SEO technical audit decisions
description: Technical SEO rules, staged optimization and the Q4 101-term keyword program with Thousand Oaks nursing priority.
---

# SEO Technical Audit — Key Decisions

## Q4 2026 keyword program
- **Rule:** Public-facing posts that accompany Journal articles must reflect the matching article's relevant master-list keywords across Facebook, GBP, Pinterest and LinkedIn.
- **Why:** The user explicitly requires keyword alignment between the blogs and all matching front-facing posts.
- **How to apply:** Carry the article's primary intent and applicable geographic phrases into natural platform-specific copy; do not force unrelated keywords, identical captions or all 101 terms into each post. Approval is still required before posting.
- **Rule:** The user requires 101 keyword IDs across rolling 30-day windows from October 8–December 31, 2026, plus all 101 in the final December 7–31 partial cycle. Preserve Google Ads IDs 1–96 and audit history; Thryv additions use IDs 97–101.
- **Why:** The objective is recurring service and local-search relevance, not a one-time mention of the keyword list.
- **How to apply:** Audit the named October 8–November 6 and November 7–December 6 cycles and rolling windows separately. Track exact wording separately from meaningful natural coverage; neither word counts nor assignments prove coverage or ranking gains. Preserve existing dates, slugs, imagery and educational purposes; obtain approval before optimization or supplemental scheduling.

## Thousand Oaks nursing and home-care priority
- **Rule:** Thousand Oaks is a primary market. Emphasize what hospice nurses do, how individualized visits work, caregiver responsibilities and the difference between 24/7 on-call support and continuous bedside nursing. Keep Thryv ranking observations separate from keyword coverage.
- **Why:** The user identified "Hospice Nursing Services Thousand Oaks CA" as the biggest Thryv opportunity and singled out home hospice care intent.
- **How to apply:** Support these related intents naturally in existing educational articles and channel-specific drafts; do not make five competing pages or infer ranks from phrase inclusion. Plan approval does not authorize publishing, sending or deployment.

## Preserve the Journal's editorial work during optimization
- **Rule:** Optimize existing Journal writing selectively, retaining its voice, dates, URLs, photography, crops and design. Length ranges guide planning, not padding. Do not manufacture locality by changing city names or create competing pages for closely related phrases.
- **Why:** The user explicitly values the existing Journal's writing and imagery and authorized targeted optimization rather than a replacement series.
- **How to apply:** Audit the whole corpus before revision, compare original and revised text with the same counting method and stage changes privately for fresh Studio approval. Preserve visible prose when harmonizing metadata unless a specific editorial change is intended. Report uncovered keyword-cycle combinations honestly and request separate approval for supplemental local articles.

## FAQPage schema rule (enforced from brief item 17)
- **Rule:** Add FAQPage schema ONLY when the complete questions AND answers are visibly displayed as Q&A pairs on that same page.
- **Applied:** FAQPage schema was REMOVED from `family-guide.html` — the booklet pages cover the topics but not as matching visible Q&A pairs.
- **Valid FAQPage schema locations:** `index.html` (homepage FAQ accordion is visible) and `refer.html` (Provider FAQ section is visible).
- **Why:** Google's guidelines deindex or ignore schema that doesn't match page content; can also trigger manual actions.

## City-page entity rule
- **Rule:** The homepage owns the complete `#organization` node, including the verified office address and coordinates. City and county coverage pages use provider-linked `Service` nodes with `areaServed`; they must not redefine the organization or attach service-area centroids as its `geo`.
- **Why:** Reusing one organization ID with different coordinates creates a contradictory local entity graph and can weaken trust in the hospice's NAP/location signals.
- **How to apply:** Preserve city latitude/longitude as content data if needed, but never emit it as the canonical organization's location. Run the structured-data pre-deploy check after schema changes.

## OG image completeness standard
- Every published page needs `og:image`, `og:image:width` (1200), `og:image:height` (630), AND `og:image:alt`.
- City pages use their own local hero photo for `og:image` (e.g. `thousand-oaks.jpg`), not the shared `og-image-v2.jpg`.
- Twitter cards: every page should also have `twitter:title`, `twitter:description`, `twitter:image`.

## Canonical redirect strategy
- Replit Publishing manages HTTPS and the custom domain.
- The Replit server owns historical page redirects and canonical extensionless routes.
- Never add a development or generated deployment URL to public content.

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
