# Inbound Backlink Audit & Monitoring — Eternal Life Hospice

**Date:** July 14, 2026
**Prepared for:** Eternal Life Hospice, Inc. — eternallifehospice.com
**Scope:** Off-site SEO — who links to / lists our website, the quality of those
links, broken-link recovery, toxic-link risk, and local-citation (name / address /
phone) consistency. This is the companion to the on-site SEO audit
(`on-site-seo-audit-2026-07-14.md`), which covered the pages themselves.

---

## The short version (what we found and what to do)

1. **There are at least two extra "shadow" websites for the same business.**
   `eternalhospice.com` and `eternallifehospiceinc.com` are near-identical copies
   of our site. They even pull their images and links straight from our real
   domain. This splits our brand and search authority across three domains instead
   of concentrating it on one. **This is the single most important finding** — it
   is worth more than any backlink cleanup. **Action:** decide on one official
   domain (recommended: `eternallifehospice.com`) and point the others at it with
   permanent redirects. (Requires access to those domains' hosting — see the data
   request at the end.)

2. **Our name, address, and phone are inconsistent across the internet.** The
   official address on our site is **4165 E Thousand Oaks Blvd, Suite 325B,
   Westlake Village, CA 91362**, but California's state health database and the
   major hospice directories list **30941 Agoura Road, Suite 112, Westlake
   Village, CA 91361**. Inconsistent addresses confuse Google and hurt local
   ranking. **Action:** pick the one correct address and fix it everywhere (fix
   list below).

3. **Our Yelp page is filed under the wrong business name** — "Westlake Village
   Hospice" (5.0 stars, 6 reviews) at our exact HQ address. Great reviews, wrong
   name. **Action:** claim the listing and rename it to "Eternal Life Hospice."

4. **No toxic or spammy links were found in public discovery.** A Google
   "disavow" file is **not needed right now**. We've still prepared a ready-to-use
   template (`disavow-template.txt`) so it's on the shelf if a spam attack ever
   happens — but our recommendation is **do not submit it**.

5. **No broken inbound links were detectable from available data**, and the
   redirects already in place cover every page we've renamed. A complete
   broken-link check still needs Google Search Console data (see below).

> **Important honesty note about the data.** A *complete* backlink report — every
> referring domain, every anchor text, and whether each link is "dofollow" or
> "nofollow" — can only come from **Google Search Console** (the free tool for
> the verified website) or a paid backlink tool. Our website has Search Console
> **not yet verified** (there's a placeholder in the code waiting for a code).
> Everything in this report was found through **public web search of real, live
> listings** — it is accurate and actionable, but it is a *partial* view. The
> last two sections tell you exactly how to unlock the full picture. We did **not**
> invent or estimate any link data.

---

## 1. Referring domains & citations we could verify (public discovery)

These are real, live pages that reference the business as of July 14, 2026.
"Link type" (dofollow/nofollow) is marked *unknown* wherever it can't be
confirmed without inspecting the live tag or Search Console — we're not guessing.

| Referring domain | What it is | Relevance / Quality | NAP it shows | Link type |
|---|---|---|---|---|
| **hcai.ca.gov** | CA Dept. of Health Care Access & Information — official state facility record (HCAI ID 406560025) | **Healthcare — authoritative (.gov)** | 30941 Agoura Rd, WLV 91361 | Reference (gov) |
| **medicare.gov / cms.gov** (Care Compare) | Federal Medicare hospice directory | **Healthcare — authoritative (.gov)** | *CCN not yet confirmed — see note* | Reference (gov) |
| **achc.org** | Our accreditation body | **Healthcare — authoritative** | — | Unknown |
| **bbb.org** | Better Business Bureau profile | Citation / trust directory | Phone matches; address not shown | Nofollow (typical) |
| **hospice.io** | Hospice comparison directory | Healthcare directory | 30941 Agoura Rd, Ste 112, 91361 | Unknown |
| **hospicematch.com** | Hospice comparison directory | Healthcare directory | 30941 Agoura Rd, Ste 112, 91361 | Unknown |
| **hospicecarenow.com** | Hospice directory | Healthcare directory | Westlake Village listing | Unknown |
| **yelp.com** | Consumer reviews | Citation / directory (neutral) | **Wrong name: "Westlake Village Hospice"** @ 4165 E Thousand Oaks Blvd | Nofollow (typical) |
| **eternalhospice.com** | **Duplicate site (same owner)** | ⚠️ Special — see §2 | Mirrors our site | Dofollow to us |
| **eternallifehospiceinc.com** | **Duplicate site (same owner)** | ⚠️ Special — see §2 | Mirrors our site | Dofollow to us |

**Important correction (why verifying matters):** an early search result pointed
to Medicare Care Compare hospice **#551534** — on inspection that record is
**"Silverado Hospice — Los Angeles," a different company**, so we did **not**
record it as ours. The correct Medicare CCN for Eternal Life Hospice must be
confirmed from the official CMS record before we cite it anywhere.

**Classification legend:** *Healthcare-relevant / authoritative* = the strongest,
most trusted references (government and accreditation). *Citation/directory* =
standard business listings (useful for local SEO, usually nofollow). *Neutral* =
general listings. *Spam/toxic* = none found.

---

## 2. The "three websites" problem (highest priority)

> **STATUS UPDATE (verified same day):** This has since been checked live and is
> **resolved at the domain level** — both `eternalhospice.com` and
> `eternallifehospiceinc.com` now permanently (301) redirect to
> `https://eternallifehospice.com/`. See `domain-consolidation-2026-07-14.md` for
> the verification evidence and the two minor optional polish items that remain.
> The recommendation below is preserved as the original finding.

Two other live websites are copies of ours:

- **`eternalhospice.com`**
- **`eternallifehospiceinc.com`**

Both are near-identical to `eternallifehospice.com`. In fact they load their
images from `eternallifehospice.com/assets/…` and their menu links point back to
`eternallifehospice.com`. That tells us they're **owned by / connected to the
business**, not third-party impersonators.

**Why this matters (plain language):** Google wants to send searchers to *one*
authoritative website per business. When the same content lives on three domains:

- Search authority and reviews get **split three ways** instead of stacking on one
  strong domain.
- Google may show a *different* domain than the one we're investing in.
- Directories are citing **mixed** domains and addresses (see §3), which compounds
  the confusion.
- It's a classic **duplicate-content** situation that can suppress rankings.

**Recommended fix (in order):**

1. **Choose one official domain.** Recommended: **`eternallifehospice.com`** — it's
   the one we actively build, it's in all current collateral, and it's the brand
   name without the "inc."
2. **301-redirect the other two domains** (`eternalhospice.com` and
   `eternallifehospiceinc.com`) to `https://eternallifehospice.com/`. A 301 is a
   permanent redirect that hands most of the SEO value of the old domain to the
   new one. *This must be done at each domain's own hosting/DNS — it cannot be done
   from this project's `_redirects` file, which only controls our own domain.*
3. **Keep the extra domains registered** (don't let them lapse) so no one else can
   grab them — but point them all at the one real site.
4. Once redirected, **update the directories** in §3 to the single official domain.

> If there's a business reason to keep a separate site (e.g. a legacy referral
> relationship), tell us and we'll recommend the least-harmful setup (e.g.
> canonical tags). Redirecting is the cleanest option in almost every case.

---

## 3. Name / Address / Phone (NAP) consistency spot-check

Google rewards a business whose **name, address, and phone are identical
everywhere**. Right now they aren't. Phone and fax are consistent (good); the
**address and business name are not**.

| Field | Our official version (site + `replit.md`) | What's out there | Fix |
|---|---|---|---|
| **Name** | Eternal Life Hospice, Inc. | Yelp shows **"Westlake Village Hospice"** | Rename the Yelp listing |
| **Address** | 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA **91362** | HCAI (state), hospice.io, hospicematch show **30941 Agoura Road, Suite 112, Westlake Village, CA 91361** | **Decide the one correct address**, then correct it on every listing |
| **Phone** | 805.953.7273 | Consistent everywhere ✅ (hospice.io shows a garbled "(80-5)-953-7273" — cosmetic) | Fix the cosmetic format on hospice.io |
| **Fax** | 805.953.8530 | Consistent ✅ | — |
| **Email** | info@eternallifehospice.com | Some listings show a `@yahoo.com` address | Standardize to the branded email |

**The address question is the key decision.** Before fixing citations, confirm
which address is current and correct — **4165 E Thousand Oaks Blvd (91362)** or
**30941 Agoura Road (91361)**. The state health database (HCAI) uses the Agoura
Road address, so that discrepancy should be reconciled deliberately (it may
require a filing with HCAI/CDPH, not just a website edit).

**Citations to correct once the address is confirmed** (priority order):

1. **Google Business Profile** — the most important listing of all (our canonical
   Maps listing is already identified internally).
2. **HCAI (hcai.ca.gov)** — authoritative state record; correcting this may need
   an official update, not a self-service edit.
3. **Bing Places** — Bing's equivalent of Google Business Profile (confirm it
   exists / is claimed).
4. **Apple Maps (Apple Business Connect)** — powers iPhone Maps searches.
5. **Yelp** — claim, rename to "Eternal Life Hospice," fix address.
6. **BBB, hospice.io, hospicematch, hospicecarenow** — update NAP + official domain.

---

## 4. Broken inbound links & redirect recovery

**Goal:** make sure no outside website is pointing at a page on our domain that
now returns "Page Not Found," because that wastes both referral traffic and SEO
value.

**Findings from available data:**

- The external references we found point to our **home page and existing pages/
  anchors** (e.g. `/#first48`, `/#medicare`) — all live.
- Our `_redirects` file already **catches every page we've renamed or merged**:
  the old county pages, the old `/providers` page, and the short URLs for
  `/refer` and `/media-kit`. So the URLs most likely to be linked from old print
  pieces or partner sites are already safely forwarded.
- **No broken inbound links were detectable** from public discovery.

**What still needs Search Console:** the only way to be 100% sure no external site
links to a dead URL is Search Console's **"Top linked pages"** report. Once we
have it, any linked URL that 404s gets a one-line 301 added to `_redirects`. Until
then, this item is **verified clean as far as available data shows, with a final
check pending GSC**. *(No changes to `_redirects` were required in this pass.)*

---

## 5. Toxic-link review & disavow recommendation

**Finding:** public discovery surfaced **no spammy, irrelevant, or link-farm
domains** pointing at us. The only unusual domains are the two **owned duplicate
sites** in §2 — those are a consolidation task, **not** a disavow target (you
don't disavow your own sites; you redirect them).

**Recommendation: DO NOT submit a disavow file at this time.** Google itself
advises against disavowing unless you have a real spam problem or a manual
penalty. Filing one unnecessarily can *remove* good links by mistake.

**Prepared anyway (on the shelf):** `disavow-template.txt` in this folder is a
ready-to-use, correctly-formatted disavow file with instructions and **zero active
entries**. If a spam-link attack ever appears in Search Console, add the bad
domains to that file and upload it at the Google Disavow Tool. Not before.

---

## 6. How to earn high-quality backlinks (prioritized, compliance-safe)

All recommendations stay inside Anti-Kickback / Stark boundaries: we earn links by
being **useful, findable, and community-present** — never by paying for referrals
or implying paid affiliations. Ordered by effort-to-payoff.

**Quick wins (do first):**

1. **Claim & complete every authoritative directory** — Google Business Profile,
   Bing Places, Apple Business Connect, and the free hospice directories
   (hospice.io, hospicematch, caring.com, hospicecarenow). Consistent NAP + our
   real domain on each. These are the foundation of local SEO.
2. **Fix the Yelp name** and keep those 5-star reviews attached to the right
   business.
3. **List with professional associations we already belong to / qualify for** —
   e.g. the California Hospice & Palliative Care Association (CHAPCA) and the
   National Hospice and Palliative Care Organization (NHPCO) member directories.
   Membership = a legitimate, high-trust healthcare link.

**Medium effort (steady authority building):**

4. **Local community organizations.** Chambers of commerce (Westlake Village /
   Greater Conejo Valley), and the nonprofits we already support (per our
   community-giving collateral) often list partners and sponsors — a clean,
   compliant local link. Keep the standard non-affiliation disclosure on any
   philanthropy page.
5. **Educational / informational content that others cite.** Our resources, blog,
   and family-guide pages are genuinely helpful. Pitch them (not our services) to
   local senior centers, faith communities, grief-support groups, and libraries
   as free family resources they can link to.
6. **Local press & "expert source" placements.** Offer plain-language expert
   commentary (hospice myths, how the Medicare hospice benefit works, caregiver
   support) to local outlets and the Conejo/Ventura community press. Editorial
   mentions are among the strongest links — and stay firmly on the "education,
   not inducement" side of the compliance line.

**Ongoing:**

7. **Reclaim unlinked mentions.** When a site names "Eternal Life Hospice" without
   linking, a polite request to add the link is quick, free authority.
8. **Consolidate first.** None of the above pays off fully until the three-domain
   problem (§2) is fixed — otherwise new links keep getting split across domains.

**Compliance guardrails (always):** never offer or accept payment for referrals;
never imply a clinical or financial affiliation that doesn't exist; never publish
partner/health-system logos without a compliance review; no medical-efficacy
claims for integrative therapies.

---

## 7. What we need from you to complete the full audit

To turn this partial (but real) picture into a *complete* backlink report, we need
**Google Search Console** verified for the site. It's free and takes ~10 minutes.

**Step 1 — Verify the site in Google Search Console.**
- Go to search.google.com/search-console and add the property
  **`eternallifehospice.com`** (choose the "Domain" property if you have DNS/GoDaddy
  access — it's the most complete; otherwise "URL prefix").
- Google will give you a verification code. Two easy ways to use it:
  - **DNS method (best):** add the TXT record Google gives you in GoDaddy. This
    verifies the *whole domain* including subdomains.
  - **HTML tag method:** send us the `<meta name="google-site-verification" …>`
    code and we'll drop it into the site's home page (a placeholder is already
    waiting in the code), then you click **Git → Sync** to publish and hit
    "Verify."

**Step 2 — Export two reports and send them to us:**
- **Links → "Top linking sites"** (referring domains) — export as CSV.
- **Links → "Top linked pages"** (which of our pages get linked) — export as CSV.
- (Optional) **Links → "Top linking text"** (anchor text) — export as CSV.

**Step 3 (optional but ideal) — access to the two extra domains' hosting** (or
whoever manages `eternalhospice.com` and `eternallifehospiceinc.com`) so the
redirects in §2 can actually be set up.

Once we have the Search Console exports, we'll produce the complete referring-
domain table (with dofollow/nofollow + anchor text), finish the broken-link sweep,
and set up ongoing monitoring.

---

## Appendix A — Methodology (so this is repeatable)

1. **Discovery:** public web search for the business name, address, phone, and
   credentials to surface live listings and referencing domains.
2. **Verification:** each candidate was fetched and inspected — we discarded a
   mismatched Medicare record (Silverado Hospice) rather than record it as ours.
3. **Classification:** each domain tagged by relevance/quality
   (healthcare-authoritative / directory / neutral / spam) and, where verifiable,
   link type.
4. **NAP spot-check:** every listing's name/address/phone compared against the
   official version in `replit.md` and on the site.
5. **Broken-link check:** referenced URLs cross-referenced against live pages and
   the existing `_redirects` file.
6. **Toxicity screen:** scanned for spam/link-farm patterns (none found).
7. **Gaps flagged:** anything requiring Search Console or third-party access was
   marked pending rather than estimated.

## Appendix B — Ongoing monitoring template (monthly, once GSC is live)

Track month-over-month in a simple sheet:

| Month | Referring domains (count) | New links | Lost links | Broken inbound (404) | Toxic flagged | Actions taken |
|---|---|---|---|---|---|---|
| | | | | | | |

- **New links:** thank/nurture the source; add good ones to a partner list.
- **Lost links:** if a valuable link disappeared, ask the site to restore it.
- **Broken inbound (404):** add a 301 in `_redirects` immediately.
- **Toxic flagged:** only escalate to a disavow if there's a real spam pattern or
  a manual action in Search Console.
