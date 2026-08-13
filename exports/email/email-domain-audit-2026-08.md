# Email Domain Audit — Sprint 3 Pre-Ship
**Date:** August 13, 2026  
**Scope:** All public-facing departmental email addresses in HTML, vCards, JSON-LD schema, and metadata across the live site codebase.

---

## 1. Codebase Audit — Result: ✅ CLEAN

Searched all 165 HTML files (including 146 city pages), all vCard assets, and all exports. Three unique `@eternallifehospice.com` addresses are in use — none on the wrong domain.

| Address | Where used | Status |
|---|---|---|
| `info@eternallifehospice.com` | Footer contact column (all 146 city pages + index, 404, referral card, careers, etc.); JSON-LD `LocalBusiness` schema; email/newsletter exports | ✅ Correct |
| `aleksandra@eternallifehospice.com` | `card-aleksandra-dubina.html`, `assets/aleksandra-dubina.vcf`, email signature export, Care Brief reply-to | ✅ Correct |
| `denise@eternallifehospice.com` | `exports/email/eternal-life-email-signature-denise-chavez.html` only | ✅ Correct |

**`@eternalhospice.com` (shadow domain) in codebase:** **Zero occurrences** in any HTML, VCF, or metadata file. The only mention is in `exports/seo/nap-citation-verification-2026-07-14.md`, which documents it as an *external* directory listing problem (see §3 below).

---

## 2. Pattern & Convention — Confirmed

The `firstname@eternallifehospice.com` convention is consistently applied and documented in:
- `exports/print/business-cards-PRINT-SPECS.txt`
- `exports/email/email-signature-HOW-TO.txt`
- `exports/email/eternal-life-email-signature-TEMPLATE.html`

Any new staff email added in the future should follow this pattern.

---

## 3. External / DNS Items — Action Required by Team

These cannot be verified or fixed inside the codebase. They require account access.

### 3a. Shadow domain — `eternalhospice.com` (missing "life")
- Several third-party directory listings still show `info@eternalhospice.com` or cite `eternalhospice.com` as the website URL.
- This was documented in `exports/seo/nap-citation-verification-2026-07-14.md` (§7) and `exports/seo/nap-citation-cleanup-2026-07-14.md`.
- **Action:** Confirm with GoDaddy/Google Workspace whether a catch-all forwarding rule exists on `eternalhospice.com` so any mail sent to that domain reaches the real inbox. If no forwarding exists, set it up. Priority: anyone who emailed `aleksandra@eternalhospice.com` (the variant explicitly flagged in the Sprint 2 audit) should not be silently dropped.

### 3b. SPF record — `eternallifehospice.com`
- **Verified:** August 13, 2026 via DNS-over-HTTPS (dns.google)
- **Result: ✅ PASS**
- **Record found:**
  ```
  v=spf1 include:_spf.google.com include:spf.brevo.com ~all
  ```
- Both Google Workspace sends (`aleksandra@`, `info@`) and Brevo campaign sends are explicitly authorised. The `~all` softfail is appropriate for a domain that is actively verifying all senders.
- **Action:** None required. No changes needed in GoDaddy DNS.

### 3c. DKIM — Google Workspace
- **Verified:** August 13, 2026 — swept 20+ common selector names (`google`, `default`, `selector1`, `selector2`, `mail`, `k1`, `k2`, `dkim`, `gmail`, `elh`, etc.) via dns.google TXT + CNAME queries.
- **Result: ❌ FAIL — No DKIM TXT record published in DNS**
- No `*._domainkey.eternallifehospice.com` record was found under any selector.
- This means one of two things:
  1. DKIM signing has never been enabled in Google Admin, **or**
  2. The key was generated but never copy-pasted into GoDaddy DNS.
- **Action Required (High Priority):**
  1. Log in to [Google Admin](https://admin.google.com) → Apps → Google Workspace → Gmail → Authenticate email.
  2. If no key exists, click **Generate new record** (leave the default `google` selector).
  3. Copy the full TXT record value (it starts with `v=DKIM1; k=rsa; p=...`).
  4. In GoDaddy DNS, create a new TXT record:
     - **Host:** `google._domainkey`
     - **Value:** (paste the full key from Google Admin)
     - **TTL:** 1 hour
  5. Return to Google Admin and click **Start authentication**. Allow up to 48 h for propagation, then verify with a test send.
- **Risk while missing:** Major providers (Gmail, Outlook, Yahoo) increasingly require DKIM to pass before trusting SPF alone. Brevo's deliverability scoring also factors DKIM in. Without it, campaigns and individual sends are at elevated spam risk.

### 3d. DMARC — `eternallifehospice.com`
- **Verified:** August 13, 2026 via DNS-over-HTTPS (dns.google)
- **Result: ✅ PASS**
- **Record found at `_dmarc.eternallifehospice.com`:**
  ```
  v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
  ```
- Policy is `p=none` (monitor only — no messages are quarantined or rejected). Aggregate reports are being sent to Brevo's DMARC reporting service, which means data is flowing.
- **Recommended next step:** Once DKIM is enabled and confirmed passing (§3c), upgrade to `p=quarantine` to actively protect the domain from spoofing. Do **not** move to `p=quarantine` before DKIM is fixed or legitimate sends may be rejected.

### 3e. Brevo sender authentication
- The Brevo account sends campaigns from `aleksandra@eternallifehospice.com` and uses `info@eternallifehospice.com` as reply-to.
- **Partial result — manual check required**
  - SPF for Brevo is confirmed published (`include:spf.brevo.com` in §3b). ✅
  - The domain verification token (`brevo-code:6bea88327a0aec44acd1a43fb89173d4`) is present in the root TXT records, confirming `eternallifehospice.com` has been claimed in the Brevo account. ✅
  - Brevo's API is IP-allowlisted and could not be queried programmatically from this environment. The Brevo-specific DKIM selector (if Brevo issued one) was not found in DNS — see §3c.
- **Action Required:** Log in to Brevo → Senders & IPs → Domains and check the status dashboard for `eternallifehospice.com`. Look for any amber or red indicators next to DKIM. If Brevo issued its own DKIM key (it does for some account tiers), add that record to GoDaddy DNS as well.
- **Note:** Resolving §3c (Google DKIM) is the highest-priority fix. Once that is green and Brevo's dashboard confirms all checks pass, the domain is fully authenticated.

### 3f. Directory listings with wrong domain
- BingPlaces and several healthcare directories (hospicecarenow.com, caring.com) still reference `eternalhospice.com` as the website. These are tracked for correction in the NAP citation cleanup (see `exports/seo/nap-citation-cleanup-2026-07-14.md`).

---

## Summary

The site codebase is fully consistent — every public email address uses `@eternallifehospice.com`. Sprint 3 can ship with no email address corrections needed in code.

**DNS authentication status as of August 13, 2026:**

| Check | Status | Notes |
|---|---|---|
| SPF | ✅ PASS | `v=spf1 include:_spf.google.com include:spf.brevo.com ~all` — covers Google Workspace + Brevo |
| DKIM | ❌ NOT PUBLISHED | No `*._domainkey` TXT record found under any selector — must be enabled in Google Admin and added to GoDaddy DNS (see §3c) |
| DMARC | ✅ PASS | `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com` — monitor mode, reports flowing to Brevo |
| Brevo domain claim | ✅ PASS | Verification token confirmed in DNS |
| Brevo DKIM check | ⚠️ MANUAL | Brevo dashboard must be checked manually (API is IP-allowlisted) |

**Before the next campaign goes out:** DKIM must be generated in Google Admin and published to GoDaddy DNS (§3c). Do not tighten DMARC to `p=quarantine` until DKIM is passing. Everything else is in order.
