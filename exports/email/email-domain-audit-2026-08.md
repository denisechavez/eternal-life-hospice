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
- **Check:** Log into GoDaddy DNS and confirm a TXT record of the form `v=spf1 include:_spf.google.com ~all` (or equivalent for Google Workspace) exists.
- **Risk if missing:** Outbound mail from `@eternallifehospice.com` may land in spam at major providers.

### 3c. DKIM — Google Workspace
- **Check:** In Google Admin → Apps → Google Workspace → Gmail → Authenticate email, confirm DKIM signing is enabled and the DNS record is published.
- **Risk if missing:** Same as SPF — deliverability drops and spoofing vectors open.

### 3d. DMARC — `eternallifehospice.com`
- **Check:** Confirm a DNS TXT record exists at `_dmarc.eternallifehospice.com`, e.g. `v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@eternallifehospice.com`.
- **Recommended policy:** Start at `p=none` (monitor only) if not already set, then graduate to `p=quarantine` once SPF and DKIM are confirmed passing.

### 3e. Brevo sender authentication
- The Brevo account sends campaigns from `aleksandra@eternallifehospice.com` and uses `info@eternallifehospice.com` as reply-to.
- **Check:** In Brevo → Senders & IPs → Domains, confirm `eternallifehospice.com` shows all authentication checks as green. Re-authenticate if any fail.

### 3f. Directory listings with wrong domain
- BingPlaces and several healthcare directories (hospicecarenow.com, caring.com) still reference `eternalhospice.com` as the website. These are tracked for correction in the NAP citation cleanup (see `exports/seo/nap-citation-cleanup-2026-07-14.md`).

---

## Summary

The site codebase is fully consistent — every public email address uses `@eternallifehospice.com`. Sprint 3 can ship with no email address corrections needed in code. The remaining items (§3 above) are DNS/account-level tasks for the team to verify and complete before any major PR push or email campaign goes out.
