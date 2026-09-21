# Eternal Life Hospice Forensic Handoff — Verified Addendum and Missing Final Block

**Prepared:** September 9, 2026  
**Purpose:** Complete the truncated end of the prior handoff and record the results of a live GitHub fetch, Replit deployment lookup, production fingerprint comparison, and city-indexing history review.

## Evidence labels

- **Confirmed by repository evidence**
- **Confirmed by live GitHub**
- **Confirmed on production**
- **Reported but not independently verified**
- **Inferred**
- **Unknown**

## 1. Live GitHub verification

### Remote fetch

`git fetch --prune origin` completed successfully on September 9, 2026.

The live GitHub heads returned by `git ls-remote --heads --tags origin` were:

| Remote branch | Commit |
|---|---|
| `audit/agent-pass-01` | `98e738a75dc72b42261372d924db7ed3176e8891` |
| `fix/content-reorg` | `d939dfb4a43be40c38e51a8a7eb04c388859b53d` |
| `main` | `cbcfa610a8369fe58688a8c945e805ccea8887bf` |
| `replit-agent` | `812cfc53c74d38239cd5b5e7e49276bd2e5bfe31` |
| `review/public-site-clean` | `cff4cbd0d616c293ec8df6931748872dd6d01310` |
| `stabilization-day-1-tweaks` | `0c6ca3f39d878e59976e0d03dacec6e550e36e99` |

### Current workspace versus GitHub

- **Confirmed by repository evidence:** Current branch is `design/google-review-cards-01`.
- **Confirmed by repository evidence:** Current HEAD is `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`.
- **Confirmed by live GitHub:** GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`.
- **Confirmed by repository evidence after fetch:** Current HEAD is zero commits behind and four commits ahead of GitHub `main`.
- **Confirmed by live GitHub:** There is no remote `design/google-review-cards-01` branch.

### Commit-object checks through GitHub's API

| Commit | Description | GitHub API result | Conclusion |
|---|---|---:|---|
| `c5d10b579db653fbe8fdb87743ddc7fce92ee26a` | Current workspace HEAD | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `4ac6d077fc33cb157183306549def34dce3b97e1` | Accessible Google-review redesign | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `cbcfa610a8369fe58688a8c945e805ccea8887bf` | Thousand Oaks search relevance | HTTP 200 | **Confirmed by live GitHub:** present and is `main` |

The current branch and its post-`cbcfa610` commits therefore do **not** exist in the live GitHub repository at the time of this check.

## 2. Production deployment revision

### Replit deployment service

Replit's deployment service returned:

- `isDeployed: true`
- `primaryUrl: https://eternallifehospice.com`
- `additionalUrls: https://eternal-life-hospice.replit.app`
- `deploymentType: autoscale`
- `hasSuccessfulBuild: true`
- `visibility: public`

This confirms the active deployment type and URLs, but the returned metadata contains no Git commit SHA, source revision, release ID, or repository ref.

The deployment-log service returned no available deployment logs from which a source SHA could be recovered.

### Production fingerprint

The production homepage was compared with both GitHub `main` and current workspace HEAD:

- Production does **not** contain the accessible review-card markers introduced by `4ac6d077`, including `reviewsGrid` and `Kind Words From Our Community`.
- GitHub `main` likewise does not contain those markers.
- Production does contain the older Google-review implementation present in GitHub `main`.
- After accounting for Replit's injected `https://i.replit.com/script.js` tag and a resulting closing-tag difference, production and the GitHub `main` homepage have a `difflib.SequenceMatcher` similarity ratio of approximately `0.99995`.
- GitHub `main` commit time is September 5, 2026 at 05:05:15 UTC.
- Production reports `Last-Modified: Sat, 05 Sep 2026 03:29:22 GMT`; this header is not itself a commit timestamp.

### Deployment conclusion

- **Confirmed on production:** The accessible review-card redesign is not deployed.
- **Confirmed on production:** The production homepage content matches the GitHub `main` generation closely enough to identify it as the pre-review-card version.
- **Inferred with high confidence:** Production is serving the site state represented by `cbcfa610a8369fe58688a8c945e805ccea8887bf`, or a build with the same homepage content.
- **Unknown:** Replit does not expose an exact Git revision in the available deployment metadata or logs, so the exact deployed commit cannot be proven cryptographically.

The defensible wording is: **production content is consistent with GitHub `main` at `cbcfa610`, but Replit did not expose an exact deployment SHA.**

## 3. City pages: why they changed from noindex to indexable

The reported noindex strategy was real but historical.

Project memory records the sequence explicitly:

1. The original city set consisted of 16 thin pages of approximately 666 words.
2. Those pages were considered a doorway-page risk.
3. They were intentionally parked:
   - `noindex`
   - removed from the XML sitemap
   - internal links stripped or converted to non-link spans
4. In June 2026, the city pages were expanded to approximately 1,500 words each with genuinely differentiated local content and unique location hero photography.
5. Once they were no longer thin doorway-like pages, they were “un-parked”:
   - `noindex` removed
   - added back to `sitemap.xml`
   - internal links restored
   - treated as real local SEO landing pages
6. The county page remained the primary coverage hub and strongest internal linker to individual city pages.

Repository history is consistent with this:

- June 27, 2026: coverage structure and city content work appears in commits including `4ac5c276`.
- June 28–July 22, 2026: localized content, new city pages, descriptions, images, and sitemap links were added through multiple commits.
- August 4, 2026: `bdcda02c` added `/care-brief` and 86 missing city pages to the sitemap.
- August 4, 2026: `b45bcb91` expanded unique programmatic city content and canonical consolidation.
- September 2026 audits and validators treated the expanded city pages as indexable localized service pages.

Current source evidence:

- Representative city pages contain no `noindex` directive.
- The city builder contains no current `noindex` generation rule.
- City pages are present in the canonical XML sitemap.
- City pages use self-canonical URLs and provider-linked Service schema.
- Prior specialized testing reported 145 city pages passing differentiation checks.

### City-indexing conclusion

- **Confirmed by project decision record:** City pages changed from noindex to indexable in June 2026.
- **Confirmed by repository evidence:** Current city pages are intended to be indexable.
- **Reason:** The pages were materially expanded and localized, addressing the original thin/doorway-page risk.
- **Protected decision:** Do not re-add blanket city-page noindex unless the owner explicitly reverses the strategy or an audit identifies specific pages that no longer meet the quality threshold.
- **Documentation issue:** Any summary saying city pages are currently “parked/noindex” is stale and conflicts with both the later decision record and current source.

## 4. Corrected claim-confidence summary

### Confirmed by repository evidence

- Current branch: `design/google-review-cards-01`
- Current HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- Current branch is four commits ahead of fetched `origin/main`
- Working tree was clean before this report file was added
- Static HTML/Python architecture
- Replit Autoscale deployment configuration
- Canonical non-www `.com` intent
- Organization identity and address
- Form and API source behavior
- Analytics and consent source behavior
- Structured-data validator behavior
- Production `/canvas-hub/*` blocking logic
- Current city pages are indexable
- County page is the principal coverage hub
- Google-review card implementation exists locally
- Premium review design is isolated from production website files

### Confirmed by live GitHub

- GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- GitHub has no `design/google-review-cards-01` branch
- Current HEAD `c5d10b...` is absent
- Review redesign `4ac6d077...` is absent
- Thousand Oaks commit `cbcfa610...` is present

### Confirmed on production

- `https://eternallifehospice.com` is deployed and public
- Deployment type is Autoscale
- The generated Replit URL is `https://eternal-life-hospice.replit.app`
- The current build is reported successful
- Production does not contain the accessible review-card redesign
- Production closely matches the GitHub `main` homepage
- Production is served through Google Frontend
- No Netlify headers were observed
- HTTPS `www` behavior previously failed and remains an external configuration concern

### Reported but not independently re-run

- Prior full predeploy pass
- Prior 177-URL crawl
- Care Brief redirect loop
- 653 parseable JSON-LD blocks
- 145 specialized city-page passes
- 606 coverage assertions
- 51 server/chat/coverage checks
- September 3 Lighthouse capture
- Earlier browser validation of the local review-card implementation

### Inferred

- Production is probably built from `cbcfa610`, because its homepage is effectively the same pre-review-card source.
- Replit, not Netlify, serves the canonical domain.
- Old deployment URLs may remain accessible unless account-side cleanup has been completed.

### Unknown

- Cryptographically exact deployed Git commit
- Replit deployment source revision
- Netlify account-side deletion/deactivation
- Current Search Console and Bing indexing
- Google-selected canonicals
- End-to-end form delivery
- Analytics destination receipt
- Current full accessibility and field-performance status

# MATERIAL FOR CODEX AND CLAUDE COWORK

## Current repository state

- Local branch: `design/google-review-cards-01`
- Local HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- GitHub `main`: `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- Divergence after live fetch: local branch is 4 ahead, 0 behind
- Remote feature branch: absent
- Local HEAD on GitHub: absent
- Review redesign commit on GitHub: absent
- Thousand Oaks commit on GitHub: present

## Verified deployment state

- Primary URL: `https://eternallifehospice.com`
- Additional URL: `https://eternal-life-hospice.replit.app`
- Deployment type: Replit Autoscale
- Visibility: public
- Deployment build status: successful
- Exact source SHA: not exposed
- Production fingerprint: closely matches GitHub `main` at `cbcfa610`
- Review-card redesign: not deployed

## Completed work

- Technical SEO and AI-search audit
- Static-site forensic audit
- Canonical and crawl-path remediation
- City canonical/entity corrections
- City-content expansion and re-indexing
- County/city structured-data normalization
- Accessibility-label and title cleanup
- WebP/LCP improvements
- SEO and schema regression guards
- Form-response/reply-to guards
- Production and preview `/canvas-hub` protections
- Organization and legal identity normalization
- Controlled Thousand Oaks SEO improvement
- Local accessible Google-review redesign
- Isolated premium review-section design exploration

## Protected decisions

- Canonical domain is `https://eternallifehospice.com`
- Public name is `Eternal Life Hospice`
- Legal name is `Eternal Life Hospice, Inc.`
- Canonical organization ID is `https://eternallifehospice.com/#organization`
- Founder title is `Founder and Chief Executive Officer`
- Address is `4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362`
- Production `/canvas-hub/*` must return 404
- Preview must block reports, correspondence, and newsletter-review exports
- County pages are broad coverage hubs
- Expanded city pages are indexable local landing pages
- City pages reference the canonical provider rather than create competing local organizations
- Nested structured-data nodes are recursively validated
- Netlify is intentionally retired
- No Review or AggregateRating schema should be added merely because reviews are displayed
- Complete review text must remain preserved in API data

## Current test evidence

- 177 sitemap URLs
- Prior crawl: 176 successful and one Care Brief loop
- 653 JSON-LD blocks, zero malformed
- 145 city pages passed specialized checks
- 606 coverage assertions passed
- 51 server/chat/coverage checks passed
- Metadata/H1 audit reported no missing or duplicate critical fields
- Header parity passed standard pages with 21 intentional exceptions
- Analytics detected on all 177 sitemap URLs; chat on 174
- September 3 Lighthouse capture: Performance 94, Accessibility 100, Best Practices 100, FCP 1.2s, LCP 2.7s, TBT 0ms, CLS 0
- Current clean install, full lint, full typecheck, full unit suite, and fresh production build remain not verified

## Unresolved items

- Exact deployment SHA is unavailable
- Local feature work is absent from GitHub
- Review-card redesign is absent from production
- HTTPS `www` TLS/canonical behavior
- Legacy-domain redirect
- Care Brief redirect loop
- Old Replit or Netlify URL exposure
- Netlify account-side shutdown
- Source/production security-header and compression parity
- End-to-end form and webhook delivery
- Analytics and call-tracking receipt
- Search Console/Bing status
- Current field Core Web Vitals
- Full WCAG/axe audit
- Image dimensions, loading hints, and large originals
- Artifact/referral-card indexing intent
- Stale city-noindex documentation

## External checks still required

1. Obtain the deployment revision from Replit support or deployment internals if a source-to-deployment manifest exists.
2. Inspect Replit custom-domain configuration for the `www` TLS/redirect failure.
3. Verify the legacy domain.
4. Inspect and retire any remaining Netlify sites, aliases, and deploy URLs.
5. Enumerate public Replit development/deployment URLs.
6. Inspect Search Console and Bing Webmaster Tools.
7. Run controlled form-delivery tests.
8. Verify Brevo, webhook, GA4, Clarity, WhatConverts, and Metricool receipt.
9. Run current mobile and desktop Lighthouse tests.
10. Run a complete accessibility audit.
11. Compare production headers and routes with `website/devserver.py`.
12. Confirm every protected `/canvas-hub/*` route returns 404 in production.

## Questions the independent audit must answer

1. Can Replit expose a cryptographically exact deployment source SHA?
2. Should the four local commits be pushed, discarded, or selectively promoted?
3. Should `design/google-review-cards-01` be published as a remote branch before review?
4. Is `4ac6d077` approved for GitHub and production, or is the premium redesign meant to supersede it?
5. Does every sitemap URL now resolve without loops?
6. Does `/care-brief` still loop?
7. Why does HTTPS `www` fail?
8. Is the legacy domain correctly redirected?
9. Are old Netlify and alternate Replit URLs public?
10. Do production headers match the intended Python-server policy?
11. Are all production `/canvas-hub/*` paths blocked?
12. Are confidential preview exports inaccessible?
13. Are all indexable city pages still sufficiently distinct and locally useful?
14. Which stale noindex documentation should be removed or corrected?
15. Are all structured-data blocks semantically valid, not merely parseable?
16. Do forms deliver successfully without exposing sensitive information?
17. Are analytics and call-tracking events received only after consent?
18. Are artifact and referral-card pages intentionally indexable?
19. What are the current mobile, desktop, and field performance results?
20. Can the repository and deployment process produce a reproducible commit-to-production manifest?

**End of handoff addendum.**# Eternal Life Hospice Forensic Handoff — Verified Addendum and Missing Final Block

**Prepared:** September 9, 2026  
**Purpose:** Complete the truncated end of the prior handoff and record the results of a live GitHub fetch, Replit deployment lookup, production fingerprint comparison, and city-indexing history review.

## Evidence labels

- **Confirmed by repository evidence**
- **Confirmed by live GitHub**
- **Confirmed on production**
- **Reported but not independently verified**
- **Inferred**
- **Unknown**

## 1. Live GitHub verification

### Remote fetch

`git fetch --prune origin` completed successfully on September 9, 2026.

The live GitHub heads returned by `git ls-remote --heads --tags origin` were:

| Remote branch | Commit |
|---|---|
| `audit/agent-pass-01` | `98e738a75dc72b42261372d924db7ed3176e8891` |
| `fix/content-reorg` | `d939dfb4a43be40c38e51a8a7eb04c388859b53d` |
| `main` | `cbcfa610a8369fe58688a8c945e805ccea8887bf` |
| `replit-agent` | `812cfc53c74d38239cd5b5e7e49276bd2e5bfe31` |
| `review/public-site-clean` | `cff4cbd0d616c293ec8df6931748872dd6d01310` |
| `stabilization-day-1-tweaks` | `0c6ca3f39d878e59976e0d03dacec6e550e36e99` |

### Current workspace versus GitHub

- **Confirmed by repository evidence:** Current branch is `design/google-review-cards-01`.
- **Confirmed by repository evidence:** Current HEAD is `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`.
- **Confirmed by live GitHub:** GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`.
- **Confirmed by repository evidence after fetch:** Current HEAD is zero commits behind and four commits ahead of GitHub `main`.
- **Confirmed by live GitHub:** There is no remote `design/google-review-cards-01` branch.

### Commit-object checks through GitHub's API

| Commit | Description | GitHub API result | Conclusion |
|---|---|---:|---|
| `c5d10b579db653fbe8fdb87743ddc7fce92ee26a` | Current workspace HEAD | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `4ac6d077fc33cb157183306549def34dce3b97e1` | Accessible Google-review redesign | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `cbcfa610a8369fe58688a8c945e805ccea8887bf` | Thousand Oaks search relevance | HTTP 200 | **Confirmed by live GitHub:** present and is `main` |

The current branch and its post-`cbcfa610` commits therefore do **not** exist in the live GitHub repository at the time of this check.

## 2. Production deployment revision

### Replit deployment service

Replit's deployment service returned:

- `isDeployed: true`
- `primaryUrl: https://eternallifehospice.com`
- `additionalUrls: https://eternal-life-hospice.replit.app`
- `deploymentType: autoscale`
- `hasSuccessfulBuild: true`
- `visibility: public`

This confirms the active deployment type and URLs, but the returned metadata contains no Git commit SHA, source revision, release ID, or repository ref.

The deployment-log service returned no available deployment logs from which a source SHA could be recovered.

### Production fingerprint

The production homepage was compared with both GitHub `main` and current workspace HEAD:

- Production does **not** contain the accessible review-card markers introduced by `4ac6d077`, including `reviewsGrid` and `Kind Words From Our Community`.
- GitHub `main` likewise does not contain those markers.
- Production does contain the older Google-review implementation present in GitHub `main`.
- After accounting for Replit's injected `https://i.replit.com/script.js` tag and a resulting closing-tag difference, production and the GitHub `main` homepage have a `difflib.SequenceMatcher` similarity ratio of approximately `0.99995`.
- GitHub `main` commit time is September 5, 2026 at 05:05:15 UTC.
- Production reports `Last-Modified: Sat, 05 Sep 2026 03:29:22 GMT`; this header is not itself a commit timestamp.

### Deployment conclusion

- **Confirmed on production:** The accessible review-card redesign is not deployed.
- **Confirmed on production:** The production homepage content matches the GitHub `main` generation closely enough to identify it as the pre-review-card version.
- **Inferred with high confidence:** Production is serving the site state represented by `cbcfa610a8369fe58688a8c945e805ccea8887bf`, or a build with the same homepage content.
- **Unknown:** Replit does not expose an exact Git revision in the available deployment metadata or logs, so the exact deployed commit cannot be proven cryptographically.

The defensible wording is: **production content is consistent with GitHub `main` at `cbcfa610`, but Replit did not expose an exact deployment SHA.**

## 3. City pages: why they changed from noindex to indexable

The reported noindex strategy was real but historical.

Project memory records the sequence explicitly:

1. The original city set consisted of 16 thin pages of approximately 666 words.
2. Those pages were considered a doorway-page risk.
3. They were intentionally parked:
   - `noindex`
   - removed from the XML sitemap
   - internal links stripped or converted to non-link spans
4. In June 2026, the city pages were expanded to approximately 1,500 words each with genuinely differentiated local content and unique location hero photography.
5. Once they were no longer thin doorway-like pages, they were “un-parked”:
   - `noindex` removed
   - added back to `sitemap.xml`
   - internal links restored
   - treated as real local SEO landing pages
6. The county page remained the primary coverage hub and strongest internal linker to individual city pages.

Repository history is consistent with this:

- June 27, 2026: coverage structure and city content work appears in commits including `4ac5c276`.
- June 28–July 22, 2026: localized content, new city pages, descriptions, images, and sitemap links were added through multiple commits.
- August 4, 2026: `bdcda02c` added `/care-brief` and 86 missing city pages to the sitemap.
- August 4, 2026: `b45bcb91` expanded unique programmatic city content and canonical consolidation.
- September 2026 audits and validators treated the expanded city pages as indexable localized service pages.

Current source evidence:

- Representative city pages contain no `noindex` directive.
- The city builder contains no current `noindex` generation rule.
- City pages are present in the canonical XML sitemap.
- City pages use self-canonical URLs and provider-linked Service schema.
- Prior specialized testing reported 145 city pages passing differentiation checks.

### City-indexing conclusion

- **Confirmed by project decision record:** City pages changed from noindex to indexable in June 2026.
- **Confirmed by repository evidence:** Current city pages are intended to be indexable.
- **Reason:** The pages were materially expanded and localized, addressing the original thin/doorway-page risk.
- **Protected decision:** Do not re-add blanket city-page noindex unless the owner explicitly reverses the strategy or an audit identifies specific pages that no longer meet the quality threshold.
- **Documentation issue:** Any summary saying city pages are currently “parked/noindex” is stale and conflicts with both the later decision record and current source.

## 4. Corrected claim-confidence summary

### Confirmed by repository evidence

- Current branch: `design/google-review-cards-01`
- Current HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- Current branch is four commits ahead of fetched `origin/main`
- Working tree was clean before this report file was added
- Static HTML/Python architecture
- Replit Autoscale deployment configuration
- Canonical non-www `.com` intent
- Organization identity and address
- Form and API source behavior
- Analytics and consent source behavior
- Structured-data validator behavior
- Production `/canvas-hub/*` blocking logic
- Current city pages are indexable
- County page is the principal coverage hub
- Google-review card implementation exists locally
- Premium review design is isolated from production website files

### Confirmed by live GitHub

- GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- GitHub has no `design/google-review-cards-01` branch
- Current HEAD `c5d10b...` is absent
- Review redesign `4ac6d077...` is absent
- Thousand Oaks commit `cbcfa610...` is present

### Confirmed on production

- `https://eternallifehospice.com` is deployed and public
- Deployment type is Autoscale
- The generated Replit URL is `https://eternal-life-hospice.replit.app`
- The current build is reported successful
- Production does not contain the accessible review-card redesign
- Production closely matches the GitHub `main` homepage
- Production is served through Google Frontend
- No Netlify headers were observed
- HTTPS `www` behavior previously failed and remains an external configuration concern

### Reported but not independently re-run

- Prior full predeploy pass
- Prior 177-URL crawl
- Care Brief redirect loop
- 653 parseable JSON-LD blocks
- 145 specialized city-page passes
- 606 coverage assertions
- 51 server/chat/coverage checks
- September 3 Lighthouse capture
- Earlier browser validation of the local review-card implementation

### Inferred

- Production is probably built from `cbcfa610`, because its homepage is effectively the same pre-review-card source.
- Replit, not Netlify, serves the canonical domain.
- Old deployment URLs may remain accessible unless account-side cleanup has been completed.

### Unknown

- Cryptographically exact deployed Git commit
- Replit deployment source revision
- Netlify account-side deletion/deactivation
- Current Search Console and Bing indexing
- Google-selected canonicals
- End-to-end form delivery
- Analytics destination receipt
- Current full accessibility and field-performance status

# MATERIAL FOR CODEX AND CLAUDE COWORK

## Current repository state

- Local branch: `design/google-review-cards-01`
- Local HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- GitHub `main`: `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- Divergence after live fetch: local branch is 4 ahead, 0 behind
- Remote feature branch: absent
- Local HEAD on GitHub: absent
- Review redesign commit on GitHub: absent
- Thousand Oaks commit on GitHub: present

## Verified deployment state

- Primary URL: `https://eternallifehospice.com`
- Additional URL: `https://eternal-life-hospice.replit.app`
- Deployment type: Replit Autoscale
- Visibility: public
- Deployment build status: successful
- Exact source SHA: not exposed
- Production fingerprint: closely matches GitHub `main` at `cbcfa610`
- Review-card redesign: not deployed

## Completed work

- Technical SEO and AI-search audit
- Static-site forensic audit
- Canonical and crawl-path remediation
- City canonical/entity corrections
- City-content expansion and re-indexing
- County/city structured-data normalization
- Accessibility-label and title cleanup
- WebP/LCP improvements
- SEO and schema regression guards
- Form-response/reply-to guards
- Production and preview `/canvas-hub` protections
- Organization and legal identity normalization
- Controlled Thousand Oaks SEO improvement
- Local accessible Google-review redesign
- Isolated premium review-section design exploration

## Protected decisions

- Canonical domain is `https://eternallifehospice.com`
- Public name is `Eternal Life Hospice`
- Legal name is `Eternal Life Hospice, Inc.`
- Canonical organization ID is `https://eternallifehospice.com/#organization`
- Founder title is `Founder and Chief Executive Officer`
- Address is `4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362`
- Production `/canvas-hub/*` must return 404
- Preview must block reports, correspondence, and newsletter-review exports
- County pages are broad coverage hubs
- Expanded city pages are indexable local landing pages
- City pages reference the canonical provider rather than create competing local organizations
- Nested structured-data nodes are recursively validated
- Netlify is intentionally retired
- No Review or AggregateRating schema should be added merely because reviews are displayed
- Complete review text must remain preserved in API data

## Current test evidence

- 177 sitemap URLs
- Prior crawl: 176 successful and one Care Brief loop
- 653 JSON-LD blocks, zero malformed
- 145 city pages passed specialized checks
- 606 coverage assertions passed
- 51 server/chat/coverage checks passed
- Metadata/H1 audit reported no missing or duplicate critical fields
- Header parity passed standard pages with 21 intentional exceptions
- Analytics detected on all 177 sitemap URLs; chat on 174
- September 3 Lighthouse capture: Performance 94, Accessibility 100, Best Practices 100, FCP 1.2s, LCP 2.7s, TBT 0ms, CLS 0
- Current clean install, full lint, full typecheck, full unit suite, and fresh production build remain not verified

## Unresolved items

- Exact deployment SHA is unavailable
- Local feature work is absent from GitHub
- Review-card redesign is absent from production
- HTTPS `www` TLS/canonical behavior
- Legacy-domain redirect
- Care Brief redirect loop
- Old Replit or Netlify URL exposure
- Netlify account-side shutdown
- Source/production security-header and compression parity
- End-to-end form and webhook delivery
- Analytics and call-tracking receipt
- Search Console/Bing status
- Current field Core Web Vitals
- Full WCAG/axe audit
- Image dimensions, loading hints, and large originals
- Artifact/referral-card indexing intent
- Stale city-noindex documentation

## External checks still required

1. Obtain the deployment revision from Replit support or deployment internals if a source-to-deployment manifest exists.
2. Inspect Replit custom-domain configuration for the `www` TLS/redirect failure.
3. Verify the legacy domain.
4. Inspect and retire any remaining Netlify sites, aliases, and deploy URLs.
5. Enumerate public Replit development/deployment URLs.
6. Inspect Search Console and Bing Webmaster Tools.
7. Run controlled form-delivery tests.
8. Verify Brevo, webhook, GA4, Clarity, WhatConverts, and Metricool receipt.
9. Run current mobile and desktop Lighthouse tests.
10. Run a complete accessibility audit.
11. Compare production headers and routes with `website/devserver.py`.
12. Confirm every protected `/canvas-hub/*` route returns 404 in production.

## Questions the independent audit must answer

1. Can Replit expose a cryptographically exact deployment source SHA?
2. Should the four local commits be pushed, discarded, or selectively promoted?
3. Should `design/google-review-cards-01` be published as a remote branch before review?
4. Is `4ac6d077` approved for GitHub and production, or is the premium redesign meant to supersede it?
5. Does every sitemap URL now resolve without loops?
6. Does `/care-brief` still loop?
7. Why does HTTPS `www` fail?
8. Is the legacy domain correctly redirected?
9. Are old Netlify and alternate Replit URLs public?
10. Do production headers match the intended Python-server policy?
11. Are all production `/canvas-hub/*` paths blocked?
12. Are confidential preview exports inaccessible?
13. Are all indexable city pages still sufficiently distinct and locally useful?
14. Which stale noindex documentation should be removed or corrected?
15. Are all structured-data blocks semantically valid, not merely parseable?
16. Do forms deliver successfully without exposing sensitive information?
17. Are analytics and call-tracking events received only after consent?
18. Are artifact and referral-card pages intentionally indexable?
19. What are the current mobile, desktop, and field performance results?
20. Can the repository and deployment process produce a reproducible commit-to-production manifest?

**End of handoff addendum.**# Eternal Life Hospice Forensic Handoff — Verified Addendum and Missing Final Block

**Prepared:** September 9, 2026  
**Purpose:** Complete the truncated end of the prior handoff and record the results of a live GitHub fetch, Replit deployment lookup, production fingerprint comparison, and city-indexing history review.

## Evidence labels

- **Confirmed by repository evidence**
- **Confirmed by live GitHub**
- **Confirmed on production**
- **Reported but not independently verified**
- **Inferred**
- **Unknown**

## 1. Live GitHub verification

### Remote fetch

`git fetch --prune origin` completed successfully on September 9, 2026.

The live GitHub heads returned by `git ls-remote --heads --tags origin` were:

| Remote branch | Commit |
|---|---|
| `audit/agent-pass-01` | `98e738a75dc72b42261372d924db7ed3176e8891` |
| `fix/content-reorg` | `d939dfb4a43be40c38e51a8a7eb04c388859b53d` |
| `main` | `cbcfa610a8369fe58688a8c945e805ccea8887bf` |
| `replit-agent` | `812cfc53c74d38239cd5b5e7e49276bd2e5bfe31` |
| `review/public-site-clean` | `cff4cbd0d616c293ec8df6931748872dd6d01310` |
| `stabilization-day-1-tweaks` | `0c6ca3f39d878e59976e0d03dacec6e550e36e99` |

### Current workspace versus GitHub

- **Confirmed by repository evidence:** Current branch is `design/google-review-cards-01`.
- **Confirmed by repository evidence:** Current HEAD is `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`.
- **Confirmed by live GitHub:** GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`.
- **Confirmed by repository evidence after fetch:** Current HEAD is zero commits behind and four commits ahead of GitHub `main`.
- **Confirmed by live GitHub:** There is no remote `design/google-review-cards-01` branch.

### Commit-object checks through GitHub's API

| Commit | Description | GitHub API result | Conclusion |
|---|---|---:|---|
| `c5d10b579db653fbe8fdb87743ddc7fce92ee26a` | Current workspace HEAD | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `4ac6d077fc33cb157183306549def34dce3b97e1` | Accessible Google-review redesign | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `cbcfa610a8369fe58688a8c945e805ccea8887bf` | Thousand Oaks search relevance | HTTP 200 | **Confirmed by live GitHub:** present and is `main` |

The current branch and its post-`cbcfa610` commits therefore do **not** exist in the live GitHub repository at the time of this check.

## 2. Production deployment revision

### Replit deployment service

Replit's deployment service returned:

- `isDeployed: true`
- `primaryUrl: https://eternallifehospice.com`
- `additionalUrls: https://eternal-life-hospice.replit.app`
- `deploymentType: autoscale`
- `hasSuccessfulBuild: true`
- `visibility: public`

This confirms the active deployment type and URLs, but the returned metadata contains no Git commit SHA, source revision, release ID, or repository ref.

The deployment-log service returned no available deployment logs from which a source SHA could be recovered.

### Production fingerprint

The production homepage was compared with both GitHub `main` and current workspace HEAD:

- Production does **not** contain the accessible review-card markers introduced by `4ac6d077`, including `reviewsGrid` and `Kind Words From Our Community`.
- GitHub `main` likewise does not contain those markers.
- Production does contain the older Google-review implementation present in GitHub `main`.
- After accounting for Replit's injected `https://i.replit.com/script.js` tag and a resulting closing-tag difference, production and the GitHub `main` homepage have a `difflib.SequenceMatcher` similarity ratio of approximately `0.99995`.
- GitHub `main` commit time is September 5, 2026 at 05:05:15 UTC.
- Production reports `Last-Modified: Sat, 05 Sep 2026 03:29:22 GMT`; this header is not itself a commit timestamp.

### Deployment conclusion

- **Confirmed on production:** The accessible review-card redesign is not deployed.
- **Confirmed on production:** The production homepage content matches the GitHub `main` generation closely enough to identify it as the pre-review-card version.
- **Inferred with high confidence:** Production is serving the site state represented by `cbcfa610a8369fe58688a8c945e805ccea8887bf`, or a build with the same homepage content.
- **Unknown:** Replit does not expose an exact Git revision in the available deployment metadata or logs, so the exact deployed commit cannot be proven cryptographically.

The defensible wording is: **production content is consistent with GitHub `main` at `cbcfa610`, but Replit did not expose an exact deployment SHA.**

## 3. City pages: why they changed from noindex to indexable

The reported noindex strategy was real but historical.

Project memory records the sequence explicitly:

1. The original city set consisted of 16 thin pages of approximately 666 words.
2. Those pages were considered a doorway-page risk.
3. They were intentionally parked:
   - `noindex`
   - removed from the XML sitemap
   - internal links stripped or converted to non-link spans
4. In June 2026, the city pages were expanded to approximately 1,500 words each with genuinely differentiated local content and unique location hero photography.
5. Once they were no longer thin doorway-like pages, they were “un-parked”:
   - `noindex` removed
   - added back to `sitemap.xml`
   - internal links restored
   - treated as real local SEO landing pages
6. The county page remained the primary coverage hub and strongest internal linker to individual city pages.

Repository history is consistent with this:

- June 27, 2026: coverage structure and city content work appears in commits including `4ac5c276`.
- June 28–July 22, 2026: localized content, new city pages, descriptions, images, and sitemap links were added through multiple commits.
- August 4, 2026: `bdcda02c` added `/care-brief` and 86 missing city pages to the sitemap.
- August 4, 2026: `b45bcb91` expanded unique programmatic city content and canonical consolidation.
- September 2026 audits and validators treated the expanded city pages as indexable localized service pages.

Current source evidence:

- Representative city pages contain no `noindex` directive.
- The city builder contains no current `noindex` generation rule.
- City pages are present in the canonical XML sitemap.
- City pages use self-canonical URLs and provider-linked Service schema.
- Prior specialized testing reported 145 city pages passing differentiation checks.

### City-indexing conclusion

- **Confirmed by project decision record:** City pages changed from noindex to indexable in June 2026.
- **Confirmed by repository evidence:** Current city pages are intended to be indexable.
- **Reason:** The pages were materially expanded and localized, addressing the original thin/doorway-page risk.
- **Protected decision:** Do not re-add blanket city-page noindex unless the owner explicitly reverses the strategy or an audit identifies specific pages that no longer meet the quality threshold.
- **Documentation issue:** Any summary saying city pages are currently “parked/noindex” is stale and conflicts with both the later decision record and current source.

## 4. Corrected claim-confidence summary

### Confirmed by repository evidence

- Current branch: `design/google-review-cards-01`
- Current HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- Current branch is four commits ahead of fetched `origin/main`
- Working tree was clean before this report file was added
- Static HTML/Python architecture
- Replit Autoscale deployment configuration
- Canonical non-www `.com` intent
- Organization identity and address
- Form and API source behavior
- Analytics and consent source behavior
- Structured-data validator behavior
- Production `/canvas-hub/*` blocking logic
- Current city pages are indexable
- County page is the principal coverage hub
- Google-review card implementation exists locally
- Premium review design is isolated from production website files

### Confirmed by live GitHub

- GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- GitHub has no `design/google-review-cards-01` branch
- Current HEAD `c5d10b...` is absent
- Review redesign `4ac6d077...` is absent
- Thousand Oaks commit `cbcfa610...` is present

### Confirmed on production

- `https://eternallifehospice.com` is deployed and public
- Deployment type is Autoscale
- The generated Replit URL is `https://eternal-life-hospice.replit.app`
- The current build is reported successful
- Production does not contain the accessible review-card redesign
- Production closely matches the GitHub `main` homepage
- Production is served through Google Frontend
- No Netlify headers were observed
- HTTPS `www` behavior previously failed and remains an external configuration concern

### Reported but not independently re-run

- Prior full predeploy pass
- Prior 177-URL crawl
- Care Brief redirect loop
- 653 parseable JSON-LD blocks
- 145 specialized city-page passes
- 606 coverage assertions
- 51 server/chat/coverage checks
- September 3 Lighthouse capture
- Earlier browser validation of the local review-card implementation

### Inferred

- Production is probably built from `cbcfa610`, because its homepage is effectively the same pre-review-card source.
- Replit, not Netlify, serves the canonical domain.
- Old deployment URLs may remain accessible unless account-side cleanup has been completed.

### Unknown

- Cryptographically exact deployed Git commit
- Replit deployment source revision
- Netlify account-side deletion/deactivation
- Current Search Console and Bing indexing
- Google-selected canonicals
- End-to-end form delivery
- Analytics destination receipt
- Current full accessibility and field-performance status

# MATERIAL FOR CODEX AND CLAUDE COWORK

## Current repository state

- Local branch: `design/google-review-cards-01`
- Local HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- GitHub `main`: `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- Divergence after live fetch: local branch is 4 ahead, 0 behind
- Remote feature branch: absent
- Local HEAD on GitHub: absent
- Review redesign commit on GitHub: absent
- Thousand Oaks commit on GitHub: present

## Verified deployment state

- Primary URL: `https://eternallifehospice.com`
- Additional URL: `https://eternal-life-hospice.replit.app`
- Deployment type: Replit Autoscale
- Visibility: public
- Deployment build status: successful
- Exact source SHA: not exposed
- Production fingerprint: closely matches GitHub `main` at `cbcfa610`
- Review-card redesign: not deployed

## Completed work

- Technical SEO and AI-search audit
- Static-site forensic audit
- Canonical and crawl-path remediation
- City canonical/entity corrections
- City-content expansion and re-indexing
- County/city structured-data normalization
- Accessibility-label and title cleanup
- WebP/LCP improvements
- SEO and schema regression guards
- Form-response/reply-to guards
- Production and preview `/canvas-hub` protections
- Organization and legal identity normalization
- Controlled Thousand Oaks SEO improvement
- Local accessible Google-review redesign
- Isolated premium review-section design exploration

## Protected decisions

- Canonical domain is `https://eternallifehospice.com`
- Public name is `Eternal Life Hospice`
- Legal name is `Eternal Life Hospice, Inc.`
- Canonical organization ID is `https://eternallifehospice.com/#organization`
- Founder title is `Founder and Chief Executive Officer`
- Address is `4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362`
- Production `/canvas-hub/*` must return 404
- Preview must block reports, correspondence, and newsletter-review exports
- County pages are broad coverage hubs
- Expanded city pages are indexable local landing pages
- City pages reference the canonical provider rather than create competing local organizations
- Nested structured-data nodes are recursively validated
- Netlify is intentionally retired
- No Review or AggregateRating schema should be added merely because reviews are displayed
- Complete review text must remain preserved in API data

## Current test evidence

- 177 sitemap URLs
- Prior crawl: 176 successful and one Care Brief loop
- 653 JSON-LD blocks, zero malformed
- 145 city pages passed specialized checks
- 606 coverage assertions passed
- 51 server/chat/coverage checks passed
- Metadata/H1 audit reported no missing or duplicate critical fields
- Header parity passed standard pages with 21 intentional exceptions
- Analytics detected on all 177 sitemap URLs; chat on 174
- September 3 Lighthouse capture: Performance 94, Accessibility 100, Best Practices 100, FCP 1.2s, LCP 2.7s, TBT 0ms, CLS 0
- Current clean install, full lint, full typecheck, full unit suite, and fresh production build remain not verified

## Unresolved items

- Exact deployment SHA is unavailable
- Local feature work is absent from GitHub
- Review-card redesign is absent from production
- HTTPS `www` TLS/canonical behavior
- Legacy-domain redirect
- Care Brief redirect loop
- Old Replit or Netlify URL exposure
- Netlify account-side shutdown
- Source/production security-header and compression parity
- End-to-end form and webhook delivery
- Analytics and call-tracking receipt
- Search Console/Bing status
- Current field Core Web Vitals
- Full WCAG/axe audit
- Image dimensions, loading hints, and large originals
- Artifact/referral-card indexing intent
- Stale city-noindex documentation

## External checks still required

1. Obtain the deployment revision from Replit support or deployment internals if a source-to-deployment manifest exists.
2. Inspect Replit custom-domain configuration for the `www` TLS/redirect failure.
3. Verify the legacy domain.
4. Inspect and retire any remaining Netlify sites, aliases, and deploy URLs.
5. Enumerate public Replit development/deployment URLs.
6. Inspect Search Console and Bing Webmaster Tools.
7. Run controlled form-delivery tests.
8. Verify Brevo, webhook, GA4, Clarity, WhatConverts, and Metricool receipt.
9. Run current mobile and desktop Lighthouse tests.
10. Run a complete accessibility audit.
11. Compare production headers and routes with `website/devserver.py`.
12. Confirm every protected `/canvas-hub/*` route returns 404 in production.

## Questions the independent audit must answer

1. Can Replit expose a cryptographically exact deployment source SHA?
2. Should the four local commits be pushed, discarded, or selectively promoted?
3. Should `design/google-review-cards-01` be published as a remote branch before review?
4. Is `4ac6d077` approved for GitHub and production, or is the premium redesign meant to supersede it?
5. Does every sitemap URL now resolve without loops?
6. Does `/care-brief` still loop?
7. Why does HTTPS `www` fail?
8. Is the legacy domain correctly redirected?
9. Are old Netlify and alternate Replit URLs public?
10. Do production headers match the intended Python-server policy?
11. Are all production `/canvas-hub/*` paths blocked?
12. Are confidential preview exports inaccessible?
13. Are all indexable city pages still sufficiently distinct and locally useful?
14. Which stale noindex documentation should be removed or corrected?
15. Are all structured-data blocks semantically valid, not merely parseable?
16. Do forms deliver successfully without exposing sensitive information?
17. Are analytics and call-tracking events received only after consent?
18. Are artifact and referral-card pages intentionally indexable?
19. What are the current mobile, desktop, and field performance results?
20. Can the repository and deployment process produce a reproducible commit-to-production manifest?

**End of handoff addendum.**# Eternal Life Hospice Forensic Handoff — Verified Addendum and Missing Final Block

**Prepared:** September 9, 2026  
**Purpose:** Complete the truncated end of the prior handoff and record the results of a live GitHub fetch, Replit deployment lookup, production fingerprint comparison, and city-indexing history review.

## Evidence labels

- **Confirmed by repository evidence**
- **Confirmed by live GitHub**
- **Confirmed on production**
- **Reported but not independently verified**
- **Inferred**
- **Unknown**

## 1. Live GitHub verification

### Remote fetch

`git fetch --prune origin` completed successfully on September 9, 2026.

The live GitHub heads returned by `git ls-remote --heads --tags origin` were:

| Remote branch | Commit |
|---|---|
| `audit/agent-pass-01` | `98e738a75dc72b42261372d924db7ed3176e8891` |
| `fix/content-reorg` | `d939dfb4a43be40c38e51a8a7eb04c388859b53d` |
| `main` | `cbcfa610a8369fe58688a8c945e805ccea8887bf` |
| `replit-agent` | `812cfc53c74d38239cd5b5e7e49276bd2e5bfe31` |
| `review/public-site-clean` | `cff4cbd0d616c293ec8df6931748872dd6d01310` |
| `stabilization-day-1-tweaks` | `0c6ca3f39d878e59976e0d03dacec6e550e36e99` |

### Current workspace versus GitHub

- **Confirmed by repository evidence:** Current branch is `design/google-review-cards-01`.
- **Confirmed by repository evidence:** Current HEAD is `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`.
- **Confirmed by live GitHub:** GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`.
- **Confirmed by repository evidence after fetch:** Current HEAD is zero commits behind and four commits ahead of GitHub `main`.
- **Confirmed by live GitHub:** There is no remote `design/google-review-cards-01` branch.

### Commit-object checks through GitHub's API

| Commit | Description | GitHub API result | Conclusion |
|---|---|---:|---|
| `c5d10b579db653fbe8fdb87743ddc7fce92ee26a` | Current workspace HEAD | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `4ac6d077fc33cb157183306549def34dce3b97e1` | Accessible Google-review redesign | HTTP 422, “No commit found for SHA” | **Confirmed by live GitHub:** absent from this GitHub repository |
| `cbcfa610a8369fe58688a8c945e805ccea8887bf` | Thousand Oaks search relevance | HTTP 200 | **Confirmed by live GitHub:** present and is `main` |

The current branch and its post-`cbcfa610` commits therefore do **not** exist in the live GitHub repository at the time of this check.

## 2. Production deployment revision

### Replit deployment service

Replit's deployment service returned:

- `isDeployed: true`
- `primaryUrl: https://eternallifehospice.com`
- `additionalUrls: https://eternal-life-hospice.replit.app`
- `deploymentType: autoscale`
- `hasSuccessfulBuild: true`
- `visibility: public`

This confirms the active deployment type and URLs, but the returned metadata contains no Git commit SHA, source revision, release ID, or repository ref.

The deployment-log service returned no available deployment logs from which a source SHA could be recovered.

### Production fingerprint

The production homepage was compared with both GitHub `main` and current workspace HEAD:

- Production does **not** contain the accessible review-card markers introduced by `4ac6d077`, including `reviewsGrid` and `Kind Words From Our Community`.
- GitHub `main` likewise does not contain those markers.
- Production does contain the older Google-review implementation present in GitHub `main`.
- After accounting for Replit's injected `https://i.replit.com/script.js` tag and a resulting closing-tag difference, production and the GitHub `main` homepage have a `difflib.SequenceMatcher` similarity ratio of approximately `0.99995`.
- GitHub `main` commit time is September 5, 2026 at 05:05:15 UTC.
- Production reports `Last-Modified: Sat, 05 Sep 2026 03:29:22 GMT`; this header is not itself a commit timestamp.

### Deployment conclusion

- **Confirmed on production:** The accessible review-card redesign is not deployed.
- **Confirmed on production:** The production homepage content matches the GitHub `main` generation closely enough to identify it as the pre-review-card version.
- **Inferred with high confidence:** Production is serving the site state represented by `cbcfa610a8369fe58688a8c945e805ccea8887bf`, or a build with the same homepage content.
- **Unknown:** Replit does not expose an exact Git revision in the available deployment metadata or logs, so the exact deployed commit cannot be proven cryptographically.

The defensible wording is: **production content is consistent with GitHub `main` at `cbcfa610`, but Replit did not expose an exact deployment SHA.**

## 3. City pages: why they changed from noindex to indexable

The reported noindex strategy was real but historical.

Project memory records the sequence explicitly:

1. The original city set consisted of 16 thin pages of approximately 666 words.
2. Those pages were considered a doorway-page risk.
3. They were intentionally parked:
   - `noindex`
   - removed from the XML sitemap
   - internal links stripped or converted to non-link spans
4. In June 2026, the city pages were expanded to approximately 1,500 words each with genuinely differentiated local content and unique location hero photography.
5. Once they were no longer thin doorway-like pages, they were “un-parked”:
   - `noindex` removed
   - added back to `sitemap.xml`
   - internal links restored
   - treated as real local SEO landing pages
6. The county page remained the primary coverage hub and strongest internal linker to individual city pages.

Repository history is consistent with this:

- June 27, 2026: coverage structure and city content work appears in commits including `4ac5c276`.
- June 28–July 22, 2026: localized content, new city pages, descriptions, images, and sitemap links were added through multiple commits.
- August 4, 2026: `bdcda02c` added `/care-brief` and 86 missing city pages to the sitemap.
- August 4, 2026: `b45bcb91` expanded unique programmatic city content and canonical consolidation.
- September 2026 audits and validators treated the expanded city pages as indexable localized service pages.

Current source evidence:

- Representative city pages contain no `noindex` directive.
- The city builder contains no current `noindex` generation rule.
- City pages are present in the canonical XML sitemap.
- City pages use self-canonical URLs and provider-linked Service schema.
- Prior specialized testing reported 145 city pages passing differentiation checks.

### City-indexing conclusion

- **Confirmed by project decision record:** City pages changed from noindex to indexable in June 2026.
- **Confirmed by repository evidence:** Current city pages are intended to be indexable.
- **Reason:** The pages were materially expanded and localized, addressing the original thin/doorway-page risk.
- **Protected decision:** Do not re-add blanket city-page noindex unless the owner explicitly reverses the strategy or an audit identifies specific pages that no longer meet the quality threshold.
- **Documentation issue:** Any summary saying city pages are currently “parked/noindex” is stale and conflicts with both the later decision record and current source.

## 4. Corrected claim-confidence summary

### Confirmed by repository evidence

- Current branch: `design/google-review-cards-01`
- Current HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- Current branch is four commits ahead of fetched `origin/main`
- Working tree was clean before this report file was added
- Static HTML/Python architecture
- Replit Autoscale deployment configuration
- Canonical non-www `.com` intent
- Organization identity and address
- Form and API source behavior
- Analytics and consent source behavior
- Structured-data validator behavior
- Production `/canvas-hub/*` blocking logic
- Current city pages are indexable
- County page is the principal coverage hub
- Google-review card implementation exists locally
- Premium review design is isolated from production website files

### Confirmed by live GitHub

- GitHub `main` is `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- GitHub has no `design/google-review-cards-01` branch
- Current HEAD `c5d10b...` is absent
- Review redesign `4ac6d077...` is absent
- Thousand Oaks commit `cbcfa610...` is present

### Confirmed on production

- `https://eternallifehospice.com` is deployed and public
- Deployment type is Autoscale
- The generated Replit URL is `https://eternal-life-hospice.replit.app`
- The current build is reported successful
- Production does not contain the accessible review-card redesign
- Production closely matches the GitHub `main` homepage
- Production is served through Google Frontend
- No Netlify headers were observed
- HTTPS `www` behavior previously failed and remains an external configuration concern

### Reported but not independently re-run

- Prior full predeploy pass
- Prior 177-URL crawl
- Care Brief redirect loop
- 653 parseable JSON-LD blocks
- 145 specialized city-page passes
- 606 coverage assertions
- 51 server/chat/coverage checks
- September 3 Lighthouse capture
- Earlier browser validation of the local review-card implementation

### Inferred

- Production is probably built from `cbcfa610`, because its homepage is effectively the same pre-review-card source.
- Replit, not Netlify, serves the canonical domain.
- Old deployment URLs may remain accessible unless account-side cleanup has been completed.

### Unknown

- Cryptographically exact deployed Git commit
- Replit deployment source revision
- Netlify account-side deletion/deactivation
- Current Search Console and Bing indexing
- Google-selected canonicals
- End-to-end form delivery
- Analytics destination receipt
- Current full accessibility and field-performance status

# MATERIAL FOR CODEX AND CLAUDE COWORK

## Current repository state

- Local branch: `design/google-review-cards-01`
- Local HEAD: `c5d10b579db653fbe8fdb87743ddc7fce92ee26a`
- GitHub `main`: `cbcfa610a8369fe58688a8c945e805ccea8887bf`
- Divergence after live fetch: local branch is 4 ahead, 0 behind
- Remote feature branch: absent
- Local HEAD on GitHub: absent
- Review redesign commit on GitHub: absent
- Thousand Oaks commit on GitHub: present

## Verified deployment state

- Primary URL: `https://eternallifehospice.com`
- Additional URL: `https://eternal-life-hospice.replit.app`
- Deployment type: Replit Autoscale
- Visibility: public
- Deployment build status: successful
- Exact source SHA: not exposed
- Production fingerprint: closely matches GitHub `main` at `cbcfa610`
- Review-card redesign: not deployed

## Completed work

- Technical SEO and AI-search audit
- Static-site forensic audit
- Canonical and crawl-path remediation
- City canonical/entity corrections
- City-content expansion and re-indexing
- County/city structured-data normalization
- Accessibility-label and title cleanup
- WebP/LCP improvements
- SEO and schema regression guards
- Form-response/reply-to guards
- Production and preview `/canvas-hub` protections
- Organization and legal identity normalization
- Controlled Thousand Oaks SEO improvement
- Local accessible Google-review redesign
- Isolated premium review-section design exploration

## Protected decisions

- Canonical domain is `https://eternallifehospice.com`
- Public name is `Eternal Life Hospice`
- Legal name is `Eternal Life Hospice, Inc.`
- Canonical organization ID is `https://eternallifehospice.com/#organization`
- Founder title is `Founder and Chief Executive Officer`
- Address is `4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362`
- Production `/canvas-hub/*` must return 404
- Preview must block reports, correspondence, and newsletter-review exports
- County pages are broad coverage hubs
- Expanded city pages are indexable local landing pages
- City pages reference the canonical provider rather than create competing local organizations
- Nested structured-data nodes are recursively validated
- Netlify is intentionally retired
- No Review or AggregateRating schema should be added merely because reviews are displayed
- Complete review text must remain preserved in API data

## Current test evidence

- 177 sitemap URLs
- Prior crawl: 176 successful and one Care Brief loop
- 653 JSON-LD blocks, zero malformed
- 145 city pages passed specialized checks
- 606 coverage assertions passed
- 51 server/chat/coverage checks passed
- Metadata/H1 audit reported no missing or duplicate critical fields
- Header parity passed standard pages with 21 intentional exceptions
- Analytics detected on all 177 sitemap URLs; chat on 174
- September 3 Lighthouse capture: Performance 94, Accessibility 100, Best Practices 100, FCP 1.2s, LCP 2.7s, TBT 0ms, CLS 0
- Current clean install, full lint, full typecheck, full unit suite, and fresh production build remain not verified

## Unresolved items

- Exact deployment SHA is unavailable
- Local feature work is absent from GitHub
- Review-card redesign is absent from production
- HTTPS `www` TLS/canonical behavior
- Legacy-domain redirect
- Care Brief redirect loop
- Old Replit or Netlify URL exposure
- Netlify account-side shutdown
- Source/production security-header and compression parity
- End-to-end form and webhook delivery
- Analytics and call-tracking receipt
- Search Console/Bing status
- Current field Core Web Vitals
- Full WCAG/axe audit
- Image dimensions, loading hints, and large originals
- Artifact/referral-card indexing intent
- Stale city-noindex documentation

## External checks still required

1. Obtain the deployment revision from Replit support or deployment internals if a source-to-deployment manifest exists.
2. Inspect Replit custom-domain configuration for the `www` TLS/redirect failure.
3. Verify the legacy domain.
4. Inspect and retire any remaining Netlify sites, aliases, and deploy URLs.
5. Enumerate public Replit development/deployment URLs.
6. Inspect Search Console and Bing Webmaster Tools.
7. Run controlled form-delivery tests.
8. Verify Brevo, webhook, GA4, Clarity, WhatConverts, and Metricool receipt.
9. Run current mobile and desktop Lighthouse tests.
10. Run a complete accessibility audit.
11. Compare production headers and routes with `website/devserver.py`.
12. Confirm every protected `/canvas-hub/*` route returns 404 in production.

## Questions the independent audit must answer

1. Can Replit expose a cryptographically exact deployment source SHA?
2. Should the four local commits be pushed, discarded, or selectively promoted?
3. Should `design/google-review-cards-01` be published as a remote branch before review?
4. Is `4ac6d077` approved for GitHub and production, or is the premium redesign meant to supersede it?
5. Does every sitemap URL now resolve without loops?
6. Does `/care-brief` still loop?
7. Why does HTTPS `www` fail?
8. Is the legacy domain correctly redirected?
9. Are old Netlify and alternate Replit URLs public?
10. Do production headers match the intended Python-server policy?
11. Are all production `/canvas-hub/*` paths blocked?
12. Are confidential preview exports inaccessible?
13. Are all indexable city pages still sufficiently distinct and locally useful?
14. Which stale noindex documentation should be removed or corrected?
15. Are all structured-data blocks semantically valid, not merely parseable?
16. Do forms deliver successfully without exposing sensitive information?
17. Are analytics and call-tracking events received only after consent?
18. Are artifact and referral-card pages intentionally indexable?
19. What are the current mobile, desktop, and field performance results?
20. Can the repository and deployment process produce a reproducible commit-to-production manifest?

**End of handoff addendum.**