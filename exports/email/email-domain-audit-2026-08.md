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
- **Initial check:** August 13, 2026 — swept 20+ common selector names (`google`, `default`, `selector1`, `selector2`, `mail`, `k1`, `k2`, `dkim`, `gmail`, `elh`, etc.) via dns.google TXT + CNAME queries.
- **Re-verified:** August 13, 2026 — queried `google._domainkey.eternallifehospice.com` via DNS-over-HTTPS (dns.google). Response: **NXDOMAIN (Status 3)** — record still not present.
- **Result: ❌ FAIL — No DKIM TXT record published in DNS**
- No `*._domainkey.eternallifehospice.com` record was found under any selector.
- **Status:** Awaiting team action. The steps below must be completed by a Google Admin account holder before this can pass.
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
- **Baseline verified:** August 13, 2026 via DNS-over-HTTPS (dns.google)
- **Baseline record (still live until DKIM is confirmed):**
  ```
  v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
  ```
- Policy was `p=none` (monitor only — no messages are quarantined or rejected). Aggregate reports flow to Brevo's DMARC reporting service.

**Target policy — upgrade to `p=quarantine` once DKIM passes (§3c)**

Quarantine mode routes spoofed mail to the recipient's spam folder instead of the inbox. It is the standard second step in the `none → quarantine → reject` graduation path and is safe as long as both SPF and DKIM are passing for every authorised sender (Google Workspace + Brevo).

**Step-by-step: how to make the change in GoDaddy DNS**

> ⚠️ **Prerequisite:** Confirm DKIM is passing before touching DMARC (see §3c). Tightening DMARC while DKIM is broken will cause legitimate mail to land in spam.

1. Log in to [GoDaddy DNS Manager](https://dcc.godaddy.com/manage/dns) for `eternallifehospice.com`.
2. Find the existing TXT record with **Host** `_dmarc` (value currently starts with `v=DMARC1; p=none`).
3. Click **Edit** on that record and replace the **Value** with:
   ```
   v=DMARC1; p=quarantine; rua=mailto:rua@dmarc.brevo.com
   ```
4. Leave **Host** as `_dmarc` and **TTL** at 1 hour (or whatever it is currently). Click **Save**.
5. Allow up to 1 hour for propagation. Verify the change:
   ```
   # From any terminal or browser tool:
   https://dns.google/resolve?name=_dmarc.eternallifehospice.com&type=TXT
   # Expect: "v=DMARC1; p=quarantine; rua=mailto:rua@dmarc.brevo.com"
   ```

**Post-change verification checklist**

- [ ] DNS query above shows `p=quarantine`
- [ ] Send a test email from `aleksandra@eternallifehospice.com` (Google Workspace) to a Gmail address — check it lands in inbox, not spam
- [ ] Trigger a small Brevo test campaign (or use Brevo's built-in inbox-preview / spam-score tool) and confirm deliverability score is unchanged
- [ ] Check Brevo → Senders & IPs → Domains: all indicators for `eternallifehospice.com` are green
- [ ] Allow 24–48 h then check the Brevo DMARC report for any new failures

**When all boxes are checked**, update the status line in the Summary table below to: `✅ QUARANTINE — p=quarantine enforced, aggregate reports → Brevo`.

> **Next graduation step (future):** After 30+ days at `p=quarantine` with zero legitimate-mail failures in the DMARC reports, upgrade to `p=reject` for full spoofing protection.

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
| DMARC | ⏳ UPGRADE PENDING | Currently `p=none` (monitor); upgrade to `p=quarantine` ready — awaiting DKIM confirmation (§3c). Full steps + checklist in §3d. |
| Brevo domain claim | ✅ PASS | Verification token confirmed in DNS |
| Brevo DKIM check | ⚠️ MANUAL | Brevo dashboard must be checked manually (API is IP-allowlisted) |

**Before the next campaign goes out:** DKIM must be generated in Google Admin and published to GoDaddy DNS (§3c). Once DKIM is confirmed passing, follow the §3d step-by-step to upgrade DMARC from `p=none` → `p=quarantine` in GoDaddy DNS and run the post-change verification checklist. Everything else is in order.
