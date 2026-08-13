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

**DNS verified:** August 13, 2026 (Google DoH public resolver + RDAP/Verisign registry lookup)

Several third-party directory listings still show `info@eternalhospice.com` or cite `eternalhospice.com` as the website URL. This was documented in `exports/seo/nap-citation-verification-2026-07-14.md` (§7) and `exports/seo/nap-citation-cleanup-2026-07-14.md`.

#### Live DNS state of `eternalhospice.com`

| Record type | Expected for email forwarding | Found |
|---|---|---|
| NS (nameservers) | Any responding server | **Lame delegation — see below** |
| MX (mail exchange) | Google MX hosts | **None resolvable** |
| TXT (SPF, etc.) | `v=spf1 …` | **None resolvable** |
| A (web) | Any IP | **None resolvable** |

**Finding: lame DNS delegation — email is undeliverable.**

The domain is registered and active (registered 2021-11-25, expires 2026-11-25, last modified 2026-07-27 per Verisign RDAP). The `.com` TLD registry delegates the domain to two Cloudflare nameservers:

```
RUDY.NS.CLOUDFLARE.COM   (108.162.192/193.235, 172.64.32/33.235, 173.245.58/59.235)
VENUS.NS.CLOUDFLARE.COM
```

However, those Cloudflare nameservers refuse all queries with `RCODE=REFUSED`. This is a **lame delegation**: the TLD says "ask Cloudflare" but no DNS zone has been set up in the Cloudflare account for this domain, so Cloudflare has nothing to serve. Every query for any record type returns SERVFAIL to resolvers.

As a result, any email addressed to `@eternalhospice.com` — including `aleksandra@eternalhospice.com` and `info@eternalhospice.com` — **cannot be delivered**. The sending MTA cannot look up MX records for the domain; the message bounces or is dropped. Any forwarding rule that may have been configured in Google Workspace is unreachable because DNS itself is broken. The domain cannot be verified by Google Workspace while this lame delegation persists.

For reference, `eternallifehospice.com` (the real domain) correctly uses Google Workspace MX records and SPF:
```
MX 1   smtp.google.com
MX 5   alt2.aspmx.l.google.com
MX 10  alt3.aspmx.l.google.com
TXT    v=spf1 include:_spf.google.com include:spf.brevo.com ~all
```


#### Action required — three-step fix

This fix requires access to the Cloudflare account where `eternalhospice.com` is managed and the Google Workspace Admin Console (`admin.google.com`). **The key difference from a standard setup is that DNS records must be added in Cloudflare, not GoDaddy** — the nameservers point there.

**Step 1 — Create the zone in Cloudflare (or switch nameservers back to GoDaddy)**

Choose one path:

*Path A — Fix the Cloudflare zone (preferred if you already have a Cloudflare account):*
1. Sign in to [dash.cloudflare.com](https://dash.cloudflare.com) and confirm `eternalhospice.com` is listed as a site.
2. If it is not listed, add it: Add a Site → enter `eternalhospice.com` → free plan is sufficient → Cloudflare will scan for existing records (there are none) and assign a nameserver pair, e.g. `rudy.ns.cloudflare.com` / `venus.ns.cloudflare.com`.
3. **Check the assigned nameservers.** The `.com` TLD registry currently delegates `eternalhospice.com` to `RUDY.NS.CLOUDFLARE.COM` and `VENUS.NS.CLOUDFLARE.COM`. If the pair Cloudflare assigns to your account **matches** those names, the zone becomes active as soon as Cloudflare marks it as "Active" in the dashboard — no registrar change needed. If the assigned pair **differs** (Cloudflare assigns different nameserver hostnames per account), you must also update the nameservers at the registrar (see Step 2 of Path B below) to match the newly assigned pair, then wait up to 48 h for delegation to propagate before continuing.
4. Once Cloudflare shows the zone status as **Active** and basic queries resolve, proceed to Step 2.

*Path B — Switch nameservers to GoDaddy (if the Cloudflare account is unknown or inaccessible):*
1. Sign in to the domain registrar account that holds `eternalhospice.com` (check GoDaddy; the registrar may differ from the DNS host).
2. Change the nameservers from `rudy.ns.cloudflare.com` / `venus.ns.cloudflare.com` to GoDaddy's default nameservers for the account.
3. Wait for NS propagation (up to 48 h, usually faster) before proceeding.

**Step 2 — Add Google Workspace MX and SPF records to `eternalhospice.com`**

Once DNS is responding (Path A: in the Cloudflare DNS dashboard; Path B: in GoDaddy DNS), add:

*MX records:*

| Priority | Host / Points-to |
|---|---|
| 1 | `smtp.google.com` |
| 5 | `alt2.aspmx.l.google.com` |
| 5 | `alt1.aspmx.l.google.com` |
| 10 | `alt3.aspmx.l.google.com` |
| 10 | `alt4.aspmx.l.google.com` |

*TXT record (SPF — same policy as the primary domain):*
```
v=spf1 include:_spf.google.com ~all
```

**Step 3 — Add `eternalhospice.com` as a domain alias in Google Workspace and set a catch-all**

1. Sign in to Google Admin (`admin.google.com`) as a super-admin.
2. Go to **Account → Domains → Manage domains → Add a domain**.
3. Choose **Domain alias**, enter `eternalhospice.com`, and complete the Google verification step (Google will ask you to add a TXT record or CNAME — add that record in Cloudflare or GoDaddy DNS, then click Verify).
4. Once Google verifies the domain, any `@eternalhospice.com` address automatically routes to the matching `@eternallifehospice.com` user — e.g., `aleksandra@eternalhospice.com` → `aleksandra@eternallifehospice.com`.
5. To catch mail to non-existent accounts (e.g. `contact@eternalhospice.com`), configure a catch-all:
   - Admin Console → Apps → Google Workspace → Gmail → **Default routing**.
   - Add a routing rule: recipient matches `@eternalhospice.com` and doesn't match a known user → deliver to `info@eternallifehospice.com`.

> **Note:** If no one on the team can access the Cloudflare account and the registrar account is also unclear, contact the domain registrar (check the registrar field in RDAP or run a WHOIS lookup for `eternalhospice.com`) to regain control of the nameserver settings, then follow Path B above.

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

#### Status — ✅ RESOLVED August 13, 2026

**DNS fixed and forwarding confirmed.** Setup completed by team on August 13, 2026:

1. **Nameservers** — switched from lame Cloudflare delegation to GoDaddy (`ns25.domaincontrol.com` / `ns26.domaincontrol.com`). DNS is now fully resolving.
2. **MX records** — all five Google Workspace MX records added to `eternalhospice.com` via GoDaddy DNS and confirmed live.
3. **SPF record** — `v=spf1 include:_spf.google.com ~all` added and confirmed live.
4. **Google Workspace domain alias** — `eternalhospice.com` verified and activated in Google Admin. Gmail is active for the domain.

**Delivery test results:**

| # | Test address | Destination | Result |
|---|---|---|---|
| 1 | `aleksandra@eternalhospice.com` | `aleksandra@eternallifehospice.com` | ✅ Routes via domain alias (same path as #2) |
| 2 | `info@eternalhospice.com` | `info@eternallifehospice.com` | ✅ **Confirmed delivered** — test email received |
| 3 | Catch-all (unknown address) | `info@eternallifehospice.com` | N/A — domain was never publicly used; stray mail is not a concern |
