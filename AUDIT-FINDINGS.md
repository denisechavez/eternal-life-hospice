# Eternal Life Hospice Static Site — Forensic Audit Findings

**Audit scope:** `website/elh-preview/` at the repository state inspected on 2026-08-25.
**Method:** read-only static inspection, clean-checkout build in `/tmp`, local route-resolution model, and source-level parsing. No remote state was changed. No application/configuration/content/asset file was modified.

## Audit boundaries and halt-condition review

- **Credentials:** no committed credential literal was verified. Potential matches were environment-variable references, test fixtures, or vendor-documentation examples. Values were not exposed. **UNDETERMINED** whether every deployed secret is absent from hosting-provider configuration; that cannot be established from source.
- **PHI:** the public-site source contains form field labels for referral, career, and contact workflows, but the audit did not identify a public-site data file containing a patient record. Source markup cannot establish what is stored by Netlify or third-party vendors. **UNDETERMINED; requires platform/vendor review.**
- **Clean build:** the configured production build completed in a clean temporary checkout. The first build altered the committed `assets/search-index.json`; the immediately repeated build produced identical file hashes and the same 201-HTML route set.
- **Production branch / deployed state:** **UNDETERMINED; requires Netlify dashboard verification.** No branch setting is declared in either repository `netlify.toml`.

## Findings register

| ID | Class | File | Line | Observed value | Proposed fix or DECISION REQUIRED | Occurrence count | Affected file count | Confidence |
|---|---|---|---:|---|---|---:|---:|---|
| ELH-A-001 | BUILD REPRODUCIBILITY | `netlify.toml`; `website/elh-preview/assets/search-index.json` | 33–36; generated file | First clean production build changes the committed search index; second build is byte-equivalent. | **DECISION REQUIRED:** confirm whether the generated index or its generator is the source of truth. No remediation performed. | 1 generated file changed | 1 | HIGH |
| ELH-A-002 | BUILD CONFIGURATION | `netlify.toml`; `website/elh-preview/netlify.toml` | 33–40; 3–15 | Root config sets `base = "website/elh-preview"` and command `bash ../elh-predeploy.sh`; a second nested `netlify.toml` declares a different direct build command. | **DECISION REQUIRED:** establish which configuration is authoritative in the deployed Netlify project. | 2 configuration files | 2 | HIGH |
| ELH-A-003 | DEPLOY BLOCKER | `website/elh-preview/care-brief/caring-for-the-caregiver.html` | header-parity output | Existing `header-parity-check` and pre-deploy chain fail: missing standard header, hamburger, search, Request Care CTA, and cream logo. | **DECISION REQUIRED:** determine whether this reader page is an intentional exception or requires a standard header. No remediation performed. | 5 failed assertions | 1 | HIGH |
| ELH-A-004 | ROUTING AMBIGUITY | `website/elh-preview/_redirects`; `resources.html`; `resources/index.html` | 35–37 | `/resources` and `/resources/` redirect to `/resources.html`, while `resources/index.html` also exists. Similar file/directory pairs exist for blog and Care Brief. | **DECISION REQUIRED:** verify Netlify runtime precedence and the intended canonical route behavior. | 3 route families | 6 | MEDIUM — source establishes coexistence; runtime precedence requires deployed verification. |
| ELH-A-005 | SITEMAP | `website/elh-preview/sitemap.xml` | 2–176 | 173 sitemap URLs; 21 indexable source routes absent. | **DECISION REQUIRED:** confirm the intended indexing policy for each omitted route before adding/removing anything. | 21 routes | 21 | HIGH |
| ELH-A-006 | CANONICAL / ENTITY SIGNAL | `hospice-lake-hughes-ca.html`; `hospice-llano-ca.html`; `hospice-point-mugu-ca.html` | 5, 9, JSON-LD blocks | Each source page canonicalizes and publishes OG/JSON-LD page identifiers for a different city page. | **DECISION REQUIRED:** verify legal/SEO intent and page identity before changing canonical or structured-data values. | 3 pages; 6 duplicated page IDs | 3 | HIGH |
| ELH-A-007 | SITEMAP / ROBOTS | `blog/caring-for-the-caregiver.html`; `sitemap.xml` | page head; sitemap entry | The Caregiver blog article is `noindex,follow` and appears in the sitemap. | **DECISION REQUIRED:** choose whether the page should be indexed or omitted from sitemap; do not change both by assumption. | 1 URL | 2 | HIGH |
| ELH-A-008 | SEARCH METADATA | 15 public artifact/social pages; `care-brief/index.html` | respective heads | Missing title/description/canonical/OG/Twitter metadata is concentrated in indexable social/asset pages and a Care Brief redirect stub. | **DECISION REQUIRED:** decide whether these are intended public/indexable routes or should remain utility artifacts. | 17 metadata-gap routes | 16 | HIGH |
| ELH-A-009 | FORMS / PLATFORM | all nine Netlify forms | see A5 inventory | Source markup identifies static Netlify forms; source alone cannot prove Netlify dashboard form detection or deployed submission handling. | **DECISION REQUIRED:** dashboard verification required; no source conclusion is sufficient. | 9 forms | 4 | HIGH |
| ELH-A-010 | STRUCTURED DATA | 145 organization-bearing pages | JSON-LD blocks | One organization `@id` is repeated cross-document; three city pages reuse other cities’ WebPage/Breadcrumb IDs. | **DECISION REQUIRED:** schema/legal review of entity modeling and corrected page identity. No replacement schema class is proposed. | 146 repeated org IDs; 6 conflicting page IDs | 148 | HIGH |
| ELH-A-011 | PRIVACY REVIEW — RELEASE-BLOCKING PENDING REVIEW | `assets/analytics.js`; form pages | analytics.js 35–97, 264–279 | Consent-gated GA4, Clarity, Brevo, Metricool and WhatConverts are available across form-bearing pages; UserWay loads regardless of the analytics consent path. Vendor masking, recipient data, and contractual posture cannot be verified in source. | **DECISION REQUIRED:** privacy/compliance review before release. Do not remove scripts in this phase. | 5 tracking vendors plus UserWay | 201 pages; 4 form pages | HIGH for source loads; MEDIUM for runtime/vendor behavior. |
| ELH-A-012 | CSP | `_headers` | 8 | Metricool’s external script URL is not allowed by `script-src` or `connect-src`. `frame-src` contains both `'none'` and a UserWay host. | **DECISION REQUIRED:** verify intended CSP behavior in a deployed browser; no policy change proposed. | 2 directive concerns | 1 | HIGH |
| ELH-A-013 | CONTENT DUPLICATION | 145 city pages | body-text comparison | All 145 location pages form one cosine-similarity cluster above 90% (9,741 qualifying page pairs). | **DECISION REQUIRED:** editorial/SEO review; consolidation is not proposed. | 9,741 pairs | 145 | HIGH — method is documented in A11. |
| ELH-A-014 | PERFORMANCE INVENTORY | `assets/img/city/*`; all HTML | asset and tag scan | 80 images exceed 500 KB; largest is 8,867,555 bytes. 5 image tags lack `alt`; 715 lack explicit width and/or height; 550 lack lazy-loading/fetchpriority. | **DECISION REQUIRED:** performance/accessibility prioritization only; no assets removed or rewritten. | 80 / 5 / 715 / 550 respectively | 184 / 5 / 162 / 180 respectively | HIGH |
| ELH-A-015 | MARKUP / ENCODING | all HTML | source scan | No mojibake (`Ã`, `Â`, `â€`, replacement character) or mixed `http://` asset references found. Standards-level HTML validation was not available from installed tooling. | **UNDETERMINED:** run a standards validator only in an approved follow-on phase. | 0 detected encoding/mixed-content defects | 0 | MEDIUM — static scan is not a complete HTML5 validator. |
| ELH-A-016 | PROTECTED-TERM BASELINE | `website/elh-preview/` | see A15 | Protected-term searches establish the baseline counts shown in A15. Matched content was not changed. | **DECISION REQUIRED:** preserve these counts as the regression baseline for future approved work. | 1,995 total matching lines across supplied searches | 196 | HIGH |

---

## A1 — Build and configuration reproducibility

### Effective configuration present in repository

**Root `netlify.toml` (the configuration referenced by `website/test-predeploy-chain.sh`):**

```toml
[build]
  base = "website/elh-preview"
  publish = "."
  command = "bash ../elh-predeploy.sh"

[functions]
  directory = "netlify/functions"
  node_bundler = "esbuild"
```

The root configuration does not declare a production branch. **UNDETERMINED; requires Netlify dashboard verification.**

**Nested `website/elh-preview/netlify.toml` also exists:**

```toml
[build]
  command = "node netlify/scripts/sync-city-data.js && node assets/build-search-index.js"
  publish = "."
[functions]
  directory = "netlify/functions"
  node_bundler = "esbuild"
```

**Redirect and header files:** `website/elh-preview/_redirects` (77 lines) and `website/elh-preview/_headers` (57 lines). No other `netlify.toml`, `_redirects`, `_headers`, or `robots.txt` files were found outside this pair plus the root configuration.

### Build scripts and generated files

| Script / configuration reference | Observed behavior |
|---|---|
| `website/elh-predeploy.sh` | Runs cookie, chat-teaser, city-script, header-parity, footer-parity checks; runs `assets/build-search-index.js` and `assets/update-sitemap-dates.js`; verifies sentinel output. |
| `netlify/scripts/sync-city-data.js` | Generates `website/city-data.json` from city-page markup. |
| `assets/build-search-index.js` | Generates `website/elh-preview/assets/search-index.json` from HTML metadata. |
| `assets/update-sitemap-dates.js` | Writes `website/elh-preview/sitemap.xml`; it is called by the root pre-deploy wrapper, not by the nested direct command. |
| `netlify/plugins/check-pagespeed` | Declared plugin; source is in `netlify/plugins/check-pagespeed/`. |

### Clean-checkout result

1. `node netlify/scripts/sync-city-data.js && node assets/build-search-index.js` completed in a clean temporary checkout.
2. `city-data.json` was already up to date for 145 cities.
3. The first build added `/blog/the-caregiver-who-needs-care` and `/care-brief/caring-for-the-caregiver` to the generated index and changed **only** `assets/search-index.json`.
4. A second identical build had no file-hash difference from the first build output and retained a 201-document route set.

**Conclusion:** output is stable after generation, but source and build output are not identical from a clean checkout because a committed generated file changes. Source-of-truth status is ambiguous.

---

## A2 — Internal-link resolution (route-aware)

### Routing model observed

- 201 HTML documents are present.
- Static pretty routes are modeled from `*.html`, directory indexes, root `index.html`, and `_redirects`.
- `_redirects` includes canonical-domain enforcement, legacy aliases, `/resources` aliases, referral/media-kit short URLs, two `200` rewrites for `/sitemap` and `/services`, an OG image compatibility redirect, and tracker/API proxy rules.
- No redirect loop was found in static `_redirects` parsing.
- No static redirect chain longer than one source→destination hop was found.
- Application of redirect status and Netlify directory precedence are **UNDETERMINED** without deployed runtime verification.

### Resolution results

| Result | Occurrence count | Affected file count | Observed value |
|---|---:|---:|---|
| True unresolvable internal page targets | 0 | 0 | None after physical route, asset, pretty-route, and `_redirects` resolution. |
| Broken fragment identifiers | 0 | 0 | All 235 non-empty same-document fragment references matched an `id`/`name` target. |
| Empty `#` controls | 3 | 2 | `404.html:71`; `referral-card.html:189,254`. These are UI controls, not page destinations. |
| `sms:` share target requiring scheme-aware handling | 1 | 1 | `referral-card.html:173`. Not a confirmed broken route. |
| Absolute canonical-host links | 189 | 183 | `https://eternallifehospice.com/...`; runtime status is **UNDETERMINED**. |
| External links | not live-tested | — | Reported separately as **UNDETERMINED**; no remote requests were made. |

**Absolute retired/noncanonical hosts:** source-level scan found no `http://eternallifehospice.com` or `www.eternallifehospice.com` internal-link target requiring a finding. Legacy-domain rules exist in `_redirects`.

---

## A3 — Search architecture inventory

### Inventory method

For each HTML document, the audit read source `<title>`, meta description, canonical, robots, first-level `<html lang>`, H1s, OG/Twitter values, sitemap membership, and resolved incoming internal links. The route inventory contains **193 indexable** and **8 non-indexable** documents. Exact per-route source values are retained in source markup; this report records the complete exception set and aggregate inventory because location pages share the same tested metadata template.

### Aggregate inventory

| Attribute | Result |
|---|---|
| Indexable HTML routes | 193 |
| Non-indexable HTML routes | 8 |
| Missing title | 1: `assets/img/amethyst-tmp/gallery.html` |
| Missing description | 15: gallery; 14 `assets/social/*.html`; `care-brief/index.html` |
| Missing canonical | 14: gallery plus all 13 non-indexable metadata-light social artifacts except Care Brief index |
| Missing `<html lang>` | 1: gallery |
| Pages without exactly one H1 | 9: `assets/social/elh-social-brand-brief.html` (5); `assets/social/index.html`, `mosaic-m1`, `mosaic-m3`, `mosaic-m5`, `mosaic-m7`, `mosaic-m9`, `care-brief/index.html`, and `media-kit.html` (0) |
| Missing any OG field (title/description/url/image/type) | 15 |
| Missing any required Twitter field (card/title/description/image) | 17; the above 15 plus `referral-card.html` and `sitemap.html` |
| Exact duplicate titles | 0 |
| Exact duplicate descriptions | 0 |
| Titles outside 30–60 characters | 22 |
| Descriptions missing or outside 120–160 characters | 169 of 193 |

### Canonical conflicts

| Source route | Observed canonical | Occurrences | Affected files |
|---|---|---:|---:|
| `/hospice-lake-hughes-ca` | `https://eternallifehospice.com/hospice-santa-clarita-ca` | 1 | 1 |
| `/hospice-llano-ca` | `https://eternallifehospice.com/hospice-palmdale-ca` | 1 | 1 |
| `/hospice-point-mugu-ca` | `https://eternallifehospice.com/hospice-oxnard-ca` | 1 | 1 |
| `/care-brief/` index stub | canonical `https://eternallifehospice.com/care-brief` while `care-brief.html` also represents that canonical destination | 1 route family | 2 |

The first three canonical targets physically resolve; no canonical target was statically found to resolve through a redirect or fail. The intended page identity of the three cross-city canonicals is a **DECISION REQUIRED**.

### Indexable routes with zero incoming internal links

`/assets/img/amethyst-tmp/gallery`, `/assets/social/elh-social-brand-brief`, `/assets/social/` index, `/care-brief/` index, and `/sitemap`.

Occurrence count: **5 routes**. Affected file count: **5**. Other location pages have navigation/footer/sitemap paths but should be re-evaluated only after the documented route-precedence decision.

---

## A4 — Sitemap integrity

`sitemap.xml` contains 173 canonical-host HTTPS `<loc>` values (lines 2–176), all with the observed `2026-08-13` last-modified value.

### Indexable routes absent from sitemap

1. `/about/aleksandra-dubina`
2. `/assets/img/amethyst-tmp/gallery`
3. `/assets/social/amethyst-duotone`
4. `/assets/social/bowl-wash`
5. `/assets/social/elh-social-brand-brief`
6. `/assets/social/eye-split`
7. `/assets/social/` index
8. `/assets/social/mosaic-m1`
9. `/assets/social/mosaic-m3`
10. `/assets/social/mosaic-m5`
11. `/assets/social/mosaic-m7`
12. `/assets/social/mosaic-m9`
13. `/assets/social/mosaic-pinterest`
14. `/assets/social/pen-graphic-pop`
15. `/assets/social/stillness-card`
16. `/blog/the-caregiver-who-needs-care`
17. `/care-brief/caring-for-the-caregiver`
18. `/care-brief/` index
19. `/care-brief`
20. `/referral-card`
21. `/resources/pain-symptom-management`

**Count:** 21 occurrences across 21 files.

`/blog/caring-for-the-caregiver` is both `noindex,follow` and present in the sitemap. The sitemap contains no noncanonical host/protocol values and no URL disallowed by `robots.txt` based on static matching.

---

## A5 — Forms

All nine source forms are `method="POST"` and carry Netlify form markup. Every form has a hidden `form-name` field and the `bot-field` honeypot. Source markup alone cannot establish Netlify project-level form detection or deployed form delivery: **UNDETERMINED; requires dashboard verification.**

| File:line | Name | Action | Classification | Named fields (submit controls omitted) |
|---|---|---|---|---|
| `care-brief.html:127` | `elh-care-brief-signup` | `/care-brief` | STATIC NETLIFY FORM | `form-name`, `bot-field`, `first_name`, `email` |
| `careers.html:192` | `elh-careers` | `/` | STATIC NETLIFY FORM | `form-name`, `subject`, `bot-field`, `first_name`, `last_name`, `email`, `phone`, `role`, `resume`, `message` |
| `index.html:1772` | `elh-family` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `bot-field`, `first_name`, `last_name`, `phone`, `email`, `relationship`, `message` |
| `index.html:1773` | `elh-physician` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `bot-field`, `provider_first_name`, `provider_last_name`, `practice`, `phone`, `npi`, `situation`, `county`, `preferred_time` |
| `index.html:1774` | `elh-casemanager` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `bot-field`, `first_name`, `last_name`, `facility`, `phone`, `email`, `needs`, `county`, `urgency` |
| `index.html:1775` | `elh-coordinator` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `bot-field`, `first_name`, `last_name`, `organization`, `role`, `phone`, `message` |
| `index.html:1776` | `elh-voice` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `bot-field`, `first_name`, `last_name`, `organization`, `role`, `email`, `phone`, `interest`, `message` |
| `index.html:2078` | `elh-chat-callback` | `/` | STATIC NETLIFY FORM | `form-name`, `source`, `bot-field`, `name`, `phone`, `email`, `preferred_time`, `message` |
| `refer.html:319` | `elh-physician` | `/` | STATIC NETLIFY FORM | `form-name`, `audience`, `source`, `subject`, `bot-field`, `referrer_name`, `phone`, `referrer_role`, `facility`, `county`, `timeframe`, `email`, `preferred_time`, `situation` |

No nested forms were detected. No form action was statically unresolvable. Unnamed submit controls are present but are not data fields. Duplicate form-name values (`elh-physician`) occur in two separate forms and require no source conclusion.

---

## A6 — Business information / NAP

The counts below are literal source-match counts, including metadata, JSON-LD, visible content, and repeated shared footer markup. They are not a claim that the rendered site has that many unique visible locations.

| Exact value / target | Occurrences | Files | Observed consistency |
|---|---:|---:|---|
| `Eternal Life Hospice, Inc.` | 220 | 184 | Organization form; repeatedly used in JSON-LD. |
| `Eternal Life Hospice` | 4,671 | 216 | Includes the longer organization string and brand mentions. |
| `4165 E Thousand Oaks Blvd` | 346 | 190 | Paired in source with Westlake Village, CA 91362. |
| `Suite 325B` | 341 | 186 | No `Suite 102` literal found by the supplied suite search. |
| `805.953.7273` | 1,343 | 195 | Primary visible business number. |
| `805.953.8530` | 184 | 180 | Fax value. |
| `info@eternallifehospice.com` | 533 | 188 | Primary business email. |
| `1.800.MEDICARE` | 181 | 179 | Medicare footer/disclaimer number. |
| `tel:18059537273` | 526 | 182 | Corresponds numerically to displayed `805.953.7273`. |
| `tel:18006334227` | 178 | 178 | Corresponds to 1-800-MEDICARE. |
| `mailto:info@eternallifehospice.com` | 187 | 181 | Primary email target. |

Additional `tel:` targets: `tel:+18059537273` (2 occurrences, 2 files), `tel:8059537273` (3, 1), and `tel:+15624131677` (1, 1). Additional personnel mailto targets occur once each for `aleksandra@…` and `denise@…`; share-mail links carry no recipient by design.

**Visible-target comparison:** the primary telephone target is numerically consistent with displayed `805.953.7273`, formatting aside. The audit did not find a conflicting business street address, business phone, or business email in public HTML.

**Manual visual review required:** linked PDFs and image assets can carry visible NAP/credential text not verifiable by plain-text source search. At minimum review `ELH_Family_Guide.pdf`, `assets/downloads/eternal-life-referral-card-digital.pdf`, `assets/downloads/eternal-life-press-kit-digital.pdf`, all business-card/logo/credential/QR images, and city hero assets. This is a manual-review inventory, not a conclusion about their contents.

---

## A7 — Structured data

- **665** JSON-LD script blocks across **181** HTML files parsed successfully; malformed blocks: **0**.
- Parsed entity-node type inventory: `BreadcrumbList` 180; `FAQPage` 157; `WebPage` 156; `MedicalOrganization + LocalBusiness` 146; `Article` 11; `BlogPosting` 7; `CollectionPage` 2; and one each of `Book`, `Blog`, `Person`, `HowTo`, and `Service`.
- Repeated organization entity: `@id` `https://eternallifehospice.com/#organization`; name `Eternal Life Hospice, Inc.`; URL `https://eternallifehospice.com`; telephone `+18059537273`; email `info@eternallifehospice.com`; address `4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362, US`; 146 cross-document occurrences.
- Repeated organization `sameAs`: Facebook, Instagram, LinkedIn, YouTube, and Google Maps CID `9771388271577679785`. Ownership/accuracy is **UNDETERMINED; requires manual verification.**
- No `identifier` field was found in the parsed nodes.

### Duplicate page identifiers

| `@id` value | Occurrences | Affected files |
|---|---:|---|
| `…/hospice-santa-clarita-ca#webpage` and `#breadcrumb` | 2 each | `hospice-lake-hughes-ca.html`, `hospice-santa-clarita-ca.html` |
| `…/hospice-palmdale-ca#webpage` and `#breadcrumb` | 2 each | `hospice-llano-ca.html`, `hospice-palmdale-ca.html` |
| `…/hospice-oxnard-ca#webpage` and `#breadcrumb` | 2 each | `hospice-point-mugu-ca.html`, `hospice-oxnard-ca.html` |

**All `@type` concerns are DECISION REQUIRED:** city pages use a repeated `MedicalOrganization`/`LocalBusiness` entity with a Westlake Village physical address while targeting service-area cities. No replacement type is proposed in this audit.

---

## A8 — Robots and crawler directives

Complete `robots.txt` policy observed:

```text
User-agent: *
Allow: /
Disallow: /assets/search-index.json

User-agent: anthropic-ai
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Meta-ExternalAgent
Allow: /
User-agent: YouBot
Allow: /

User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: Bytespider
Disallow: /
User-agent: cohere-ai
Disallow: /
User-agent: Diffbot
Disallow: /
User-agent: omgili
Disallow: /

Content-Signal: training=no; search=yes; ai-input=yes
Sitemap: https://eternallifehospice.com/sitemap.xml
```

No X-Robots-Tag was found in `netlify.toml` or `_headers`. Absence of `llms.txt` is not classified as a defect; an `llms.txt` file is present in this repository.

---

## A9 — Third-party scripts and privacy surface

All 201 HTML pages include local `assets/analytics.js?v=20260727h`. The source implements a consent path for non-essential analytics after `elh_cc=all`; source cannot establish production cookie behavior or vendor data handling.

| Source / runtime-loaded service | Page count | Appears on form page | Observed source evidence |
|---|---:|---|---|
| Google Analytics / GTM `www.googletagmanager.com` | 201 eligible pages | Yes | dynamically loaded by `analytics.js` |
| Microsoft Clarity `clarity.ms` | 200 (`/refer` excluded in source) | Yes, except referral page | dynamically loaded by `analytics.js` |
| Brevo `cdn.brevo.com` | 201 eligible pages | Yes | dynamically loaded by `analytics.js` |
| Metricool `tracker.metricool.com` | 201 eligible pages | Yes | dynamically loaded by `analytics.js` |
| WhatConverts `s.ksrndkehqnwntyxlhgto.com` | 201 eligible pages | Yes | dynamically loaded by `analytics.js` |
| UserWay `cdn.userway.org` | 201 | Yes | loaded outside the consent-gated path |

Eleven iframes occur only in `assets/social/index.html`; each points to a same-origin local social-artifact HTML file. No third-party iframe or source-level tracking-pixel image was found. No duplicate static load of the same analytics property was found.

**PRIVACY FINDING REQUIRING REVIEW / RELEASE-BLOCKING PENDING REVIEW:** personal/health-related form pages can load analytics/session replay after source-level consent. Repository source cannot independently establish field masking, form-value exclusion, consent enforcement, vendor contracts, or a HIPAA/data-processing posture.

---

## A10 — Content Security Policy

Only `website/elh-preview/_headers:8` contains a CSP:

```text
default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.clarity.ms https://scripts.clarity.ms https://cdn.brevo.com https://sibautomation.com https://www.google-analytics.com https://s.ksrndkehqnwntyxlhgto.com https://cdn.userway.org; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.userway.org; font-src 'self' https://fonts.gstatic.com data: https://cdn.userway.org; img-src 'self' data: https:; connect-src 'self' https://www.google-analytics.com https://region1.google-analytics.com https://www.clarity.ms https://in.clarity.ms https://cdn.brevo.com https://api.brevo.com https://stats.g.doubleclick.net https://www.google.com https://s.ksrndkehqnwntyxlhgto.com https://p.ksrndkehqnwntyxlhgto.com https://process.iconnode.com https://cdn.userway.org https://widget.userway.org; media-src 'self'; frame-src 'none' https://cdn.userway.org; frame-ancestors 'self'; form-action 'self';
```

Static source matching shows `https://tracker.metricool.com/resources/be.js` is not permitted by the listed `script-src` and Metricool is absent from `connect-src`. The simultaneous `'none'` and host-source values in `frame-src` require deployed-browser verification. Netlify’s application of `_headers` is **UNDETERMINED** from source alone.

---

## A11 — Content thinness and duplication

**Method:** visible body text was extracted after script/style/tag removal. Location-page similarity used cosine similarity over normalized word-frequency vectors.

Pages below 300 words (20):

`assets/social/stillness-card.html` (8), `blog/index.html` (10), `care-brief/index.html` (10), `resources/index.html` (10), `assets/social/mosaic-m5.html` (14), `mosaic-m1.html` (15), `mosaic-m3.html` (15), `assets/social/amethyst-duotone.html` (16), `assets/social/bowl-wash.html` (20), `mosaic-m7.html` (23), `assets/social/pen-graphic-pop.html` (23), `mosaic-m9.html` (24), `assets/social/eye-split.html` (25), `assets/social/mosaic-pinterest.html` (25), `card-denise-chavez.html` (55), `card-aleksandra-dubina.html` (70), `assets/social/index.html` (73), `assets/img/amethyst-tmp/gallery.html` (134), `referral-card.html` (175), `media-kit.html` (277).

Location-page similarity cluster: **all 145 city pages** have at least one >90% connection, producing **9,741** pairwise relationships above threshold. This is a report-only result; content consolidation is a **DECISION REQUIRED**.

---

## A12 — Orphans split by type

### Orphan HTML routes

Static incoming-link resolution found five indexable document routes with no inbound page link: gallery, social brand brief, social index, Care Brief index, and sitemap. Sitemap/redirect behavior may provide an alternative access path; runtime behavior is **UNDETERMINED**.

### Potentially unreferenced assets

627 non-HTML content/assets were inventoried. A naive HTML-reference pass marked 586 as not directly referenced, but this is an upper bound because it does not fully interpret CSS URLs, dynamic JavaScript paths, Netlify functions, generated files, or direct-download URLs. Examples include `.well-known/*`, `assets/audio/aleksandra-welcome.mp3`, city image alternatives, `assets/city-neighborhoods.json`, generator scripts, and downloadable PDFs. **Report only; do not delete.**

---

## A13 — Performance inventory

### Largest deployed/repository assets

The clean build retains the same asset tree; the following are the 25 largest files by bytes:

1. `assets/img/city/somis.jpg` — 8,867,555
2. `assets/img/city/stevenson-ranch.jpg` — 8,750,429
3. `assets/img/city/hollywood.jpg` — 6,274,002
4. `assets/img/city/hawaiian-gardens.jpg` — 5,596,671
5. `assets/img/city/acton.jpg` — 5,431,896
6. `assets/img/city/newhall.jpg` — 3,730,264
7. `assets/img/city/harbor-city.jpg` — 3,273,805
8. `assets/img/city/meiners-oaks.jpg` — 3,258,388
9. `assets/img/city/brandeis.jpg` — 3,235,232
10. `assets/img/city/piru.jpg` — 3,205,671
11. `assets/img/city/west-hills.jpg` — 3,137,935
12. `assets/img/city/lake-hughes.jpg` — 2,777,703
13. `assets/img/city/maywood.jpg` — 2,748,351
14. `assets/img/city/avalon.jpg` — 2,628,143
15. `assets/img/city/oak-view.jpg` — 2,499,081
16. `assets/img/city/arleta.jpg` — 2,231,339
17. `assets/img/city/monrovia.jpg` — 2,218,143
18. `assets/downloads/eternal-life-press-kit-digital.pdf` — 1,997,845
19. `assets/img/city/san-dimas.jpg` — 1,951,383
20. `assets/social/elh-eye.png` — 1,747,302
21. `assets/img/city/azusa.jpg` — 1,706,898
22. `assets/social/elh-amethyst.png` — 1,666,095
23. `assets/img/city/valley-village.jpg` — 1,610,633
24. `assets/social/elh-bowl.png` — 1,480,780
25. `assets/img/city/duarte.jpg` — 1,405,737

Additional inventory: 80 images over 500 KB; one duplicate binary-hash cluster (`assets/og-image.jpg` and `assets/og-image-v2.jpg`); no source maps found; 1,441 image tags; 191 stylesheet links; 548 script tags with `src`; 1,234 local-font references. Exact inline script/style duplication includes a normalized script block shared by 14 social/gallery artifact pages.

---

## A14 — Markup validity and encoding

- Missing `<!DOCTYPE html>`: none detected.
- Missing charset declaration: none detected.
- Duplicate `id` attributes within one source page: no static duplicates detected.
- Mixed-content `http://` `src`/`href` assets: none detected.
- Mojibake/replacement-character scan (`Ã`, `Â`, `â€`, `�`): no source occurrence detected.
- A standards-level HTML5 parse was **UNDETERMINED** because no validator was installed or added in this read-only audit.

---

## A15 — Protected-term regression baseline

The supplied searches were run case-insensitively over `website/elh-preview/`. Nothing matching these terms was changed.

| Supplied search group | Hit count |
|---|---:|
| `We are here. Always.` | 0 |
| `palliative` | 26 |
| `Westlake Village Hospice` / `Joint Commission` / `WVH` | 10 |
| `physician-supported` / `physician led` / `physician-led` | 1,181 |
| `cannabis` / `psilocybin` / `CBD` | 7 |
| `healing propert` / `therapeutic propert` / `amethyst` | 63 |
| `compassionate` / `overwhelm` | 46 |
| `eternalhospice.com` / `support@` | 5 |
| `noindex` | 16 |
| `Suite (325|102)[A-Z]?` | 341 |

The high-volume physician-supported and suite hits are repeated city-page metadata/footer content. Exact source line locations remain discoverable by the supplied `grep` commands; no protected-term wording was normalized or otherwise altered in this phase.

---

## A16 — Retired Events follow-up verification

**Checked:** 2026-08-26

The retired Events routes were rechecked against the canonical production host. All
six slash and non-slash variants return HTTP 404 and contain no `Event` JSON-LD:

| Route family | Variants checked | Result |
|---|---:|---|
| `/events` | 2 | 404; no Event JSON-LD |
| `/events/caregiver-support-workshop` | 2 | 404; no Event JSON-LD |
| `/events/community-grief-circle` | 2 | 404; no Event JSON-LD |

The reproducible check is `python3 website/check-retired-events.py`. A source scan
also finds zero `/events` route references or `Event` JSON-LD blocks in the current
`website/elh-preview/` HTML/XML/redirect source. The sitemap contains no Event URL,
and `_redirects` contains no Event redirect or replacement route.

The latest supplied Search Console report still lists three valid historical items,
all last detected on 2026-08-25. The accompanying URL Inspection live test reports
“URL doesn't have this enhancement.” This is residual Search Console state awaiting
Google's next recrawl, not current production markup; do not add placeholder Event
fields, request indexing for the 404 URLs, or create a replacement Events page.

No Netlify duplicate files or routing were changed as part of this verification.

## End of phase

No remediation was performed. This report is the only intended repository change from the audit phase. Do not alter site files, configuration, content, assets, crawler directives, or protected-term language without explicit written approval.