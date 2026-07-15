# NAP Citation Cleanup — Verification Pass

**Date verified:** July 14, 2026
**For:** Eternal Life Hospice, Inc. — eternallifehospice.com
**Verifies:** `nap-citation-cleanup-2026-07-14.md` (the action guide)
**Method:** live web fetch + search of each listing on July 14, 2026 (public,
un-authenticated view — the same view a searcher or Google sees).

> **⚠️ Four verification passes have been completed. The [Fourth verification
> pass](#fourth-verification-pass) section at the bottom has the most current
> live status. The summary immediately below is the *first* pass only.**

---

## The master record we checked every listing against

| Field | Correct value |
|---|---|
| Business name | Eternal Life Hospice |
| Address | 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362 |
| Phone | (805) 953-7273 |
| Fax | (805) 953-8530 |
| Email | info@eternallifehospice.com |
| Website | https://eternallifehospice.com |

---

## Bottom line

**The corrections have not landed yet.** As of this check, **every hospice
directory we can read still shows the old Agoura Road / 91361 address**, and the
state record (HCAI) is unchanged. Two of the changes in the guide also need to be
re-scoped after what this pass uncovered — see the Yelp finding below, which is
the most important thing in this report.

Nothing here means the cleanup was done wrong. Directory and state edits take time
to process, and some listings may have been submitted but not yet published. This
report simply records the **current live state** so you know exactly what still
needs doing.

---

## Result by listing

### 1. Google Business Profile — ⚠️ can't fully verify from outside
- The public/search view shows the **correct** Thousand Oaks Blvd address and the
  correct phone, which is a good sign.
- **What we cannot confirm from outside:** whether the older duplicate
  **"Eternal Life Hospice, Inc."** listing has actually been closed or merged.
  That is only visible when signed into the profile at business.google.com.
- **Remaining action:** sign in and confirm (a) the live profile matches the
  master record exactly and (b) the duplicate "Inc." listing is closed/merged so
  reviews and ranking signals consolidate onto the one real listing.

### 2. Yelp — ❌ NOT renamed, and the guide's instruction needs to change
This is the key finding of the verification pass.

- The Yelp listing **"Westlake Village Hospice"** (5.0★, 6 reviews) is **still
  named that** and is marked **Claimed**.
- **More importantly, it is a *different company*, not Eternal Life under a wrong
  name.** The evidence: it has its **own website** (`westlakevillagehospiceinc.com`),
  its **own phone** ((805) 870-0103, not our 953-7273), its **own Greater Conejo
  Valley Chamber membership**, and its **own separate BBB profile** — and it says
  it was **established in 2015**.
- **Conclusion:** the original audit assumed this listing was our business filed
  under the wrong name. It is not. **Do not claim or rename it** — doing so would
  be taking over another business's listing.
- **Remaining action (revised):** disregard the "rename Yelp" step. Instead, note
  that **Eternal Life Hospice does not appear to have its own Yelp listing at all**
  — creating and claiming a fresh, correctly-named Yelp profile is a clean,
  compliant way to start building our own reviews. (Optional; low priority.)

### 3. HCAI — the state record — ❌ still the old address (expected)
- hcai.ca.gov (HCAI ID **406560025**) still shows **30941 Agoura Rd, Westlake
  Village, CA 91361**, status **Open**.
- This is the one the guide warned would take longest — it needs a filing with
  HCAI/CDPH, not a self-service edit, and it's the source many directories copy.
- **Remaining action:** confirm the address-update filing has been submitted to
  HCAI/CDPH; until the state record flips, the directories below will keep
  re-inheriting the Agoura Road address.

### 4. Bing Places — ⚠️ can't confirm claim/edit from outside
- No public confirmation the listing is claimed or corrected. Aggregated data
  still associates the old shadow domain (`eternalhospice.com`) as the website.
- **Remaining action:** claim/confirm at bingplaces.com and set the master record.

### 5. Apple Business Connect — ⚠️ can't confirm from outside
- Not verifiable without signing into the account.
- **Remaining action:** claim/confirm at businessconnect.apple.com.

### 6. Directory listings

| Listing | Live state on Jul 14, 2026 | Verdict |
|---|---|---|
| **BBB** (bbb.org) | Profile shows **"Eternal Life Hospice, Inc"**, phone **(805) 953-7273** ✅; street address not displayed publicly (normal for BBB) | ✅ phone/name OK; uses legal "Inc" name |
| **hospice.io** | Still **30941 Agoura Road, Suite 112, 91361**; phone still garbled **"(80-5) -953-7273"** | ❌ not fixed (address + phone format) |
| **hospicematch.com** | Still **30941 Agoura Road, Suite 112, CA 91361**; banner says **"This listing is not yet verified."** | ❌ not fixed / not claimed |
| **hospicecarenow.com** | Still **30941 AGOURA ROAD, SUITE 112, 91361** | ❌ not fixed |
| **caring.com** | No Eternal Life Hospice listing found | ⬜ still not listed |

### 7. The `@yahoo.com` email — ⚠️ none seen live, shadow sites still up
- No live `@yahoo.com` address surfaced on any listing in this pass. Where an
  email appeared it was `info@eternalhospice.com` (branded, but on the **shadow
  domain**, not the official one).
- The two shadow domains (`eternalhospice.com`, `eternallifehospiceinc.com`) still
  appear in search results and several directories still cite them as the website.
  Redirecting/consolidating those domains is tracked as a **separate task** and is
  not repeated here — but note the directory "website" fields should ultimately
  point to **https://eternallifehospice.com**.

---

## Updated checklist (current status)

- [ ] Google Business Profile — search view correct; **duplicate "Inc." closure/merge unconfirmed** (needs account sign-in)
- [x] Yelp — **verified: separate company, do NOT rename** (guide step retired; optionally create our own Yelp listing)
- [ ] HCAI (hcai.ca.gov) — **still Agoura Rd / 91361**; confirm the CDPH/HCAI filing was submitted
- [ ] Bing Places — claim/correct unconfirmed
- [ ] Apple Business Connect — claim/correct unconfirmed
- [x] BBB — name + phone correct (address hidden by BBB, which is normal)
- [ ] hospice.io — **still Agoura Rd + garbled phone**
- [ ] hospicematch.com — **still Agoura Rd + unverified**
- [ ] hospicecarenow.com — **still Agoura Rd**
- [ ] caring.com — still not listed
- [x] No `@yahoo.com` email seen live in this pass

## What to do next (in priority order)
1. **HCAI/CDPH filing** — this is the upstream source; the directories keep copying
   its Agoura Road address, so nothing downstream fully settles until it flips.
2. **Google Business Profile** — sign in and confirm the duplicate "Inc." listing
   is closed/merged (the one item with the biggest local-ranking impact).
3. **The three directories** (hospice.io, hospicematch, hospicecarenow) — each
   needs a manual claim/edit to the Thousand Oaks Blvd address; hospice.io also
   needs its phone display fixed to **(805) 953-7273**.
4. **Bing Places / Apple Business Connect** — claim/confirm; can't be verified
   from the outside.
5. **Re-run this verification pass** in ~2–4 weeks to confirm the edits published.

> **Note on the guide:** the "rename Yelp" step in
> `nap-citation-cleanup-2026-07-14.md` should be treated as retired — that listing
> belongs to a different, real business (Westlake Village Hospice, Inc.).

---
---

## Re-verification pass

**Re-checked:** ~2–4 weeks after the first pass (recorded under the same file
date; the workspace clock is fixed at July 14, 2026).
**Method:** same as the first pass — live web fetch of each listing's public,
un-authenticated page (the view a searcher and Google see).

### Bottom line — still not published

**No change since the first pass.** Every hospice directory we can read still
shows the old **30941 Agoura Road / 91361** address, and the state record (HCAI)
is still on Agoura Road. Because HCAI is the upstream source the directories copy
from, nothing downstream will settle until that state filing flips. This is the
expected outcome for a re-check this soon — directory and state edits publish on
a delay — so a **third pass is still needed** once the HCAI/CDPH filing lands.

### Result by listing (re-check)

| Listing | Live state on re-check | Change since 1st pass? |
|---|---|---|
| **HCAI** (hcai.ca.gov, ID 406560025) | Still **30941 Agoura Rd, Westlake Village, CA 91361**, status **Open** | ❌ no change |
| **hospice.io** | Still **30941 Agoura Road, Suite 112, 91361**; phone **still garbled "(80-5) -953-7273"** | ❌ no change |
| **hospicematch.com** | Still **30941 Agoura Road, Suite 112, CA 91361**; banner still **"This listing is not yet verified."** | ❌ no change |
| **hospicecarenow.com** | Still **30941 AGOURA ROAD, SUITE 112, 91361** | ❌ no change |
| **BBB** (bbb.org) | Aggregated data shows the correct **4165 E Thousand Oaks Blvd, Suite 325B, 91362** and phone **(805) 953-7273**; still uses legal **"Inc"** name | ✅ still OK |
| **Yelp** | Still **"Westlake Village Hospice"** (the separate, real business) — as expected; **do not touch** | ✅ confirmed, no action |
| **Google Business Profile** | Search view still shows the correct Thousand Oaks Blvd address; duplicate **"Inc."** closure/merge still **not confirmable from outside** (needs account sign-in) | ⚠️ unconfirmed |
| **Bing Places / Apple Business Connect** | Not verifiable without signing into the accounts | ⚠️ unconfirmed |
| **caring.com** | Still no Eternal Life Hospice listing found | ⬜ still not listed |

### Updated checklist (re-check status)

- [ ] HCAI (hcai.ca.gov) — **still Agoura Rd / 91361**; the CDPH/HCAI address-update filing has NOT landed yet (upstream blocker)
- [ ] hospice.io — **still Agoura Rd + garbled phone "(80-5) -953-7273"**
- [ ] hospicematch.com — **still Agoura Rd + unverified**
- [ ] hospicecarenow.com — **still Agoura Rd**
- [ ] Google Business Profile — search view correct; duplicate "Inc." closure/merge still unconfirmed (needs sign-in)
- [ ] Bing Places — unconfirmed
- [ ] Apple Business Connect — unconfirmed
- [ ] caring.com — still not listed
- [x] BBB — name + phone correct (address hidden by BBB, which is normal)
- [x] Yelp — separate company, correctly left untouched

### What to do next (unchanged priority)

1. **HCAI/CDPH filing is the gate.** Until the state record flips off Agoura Road,
   hospice.io / hospicematch / hospicecarenow will keep re-inheriting the old
   address no matter how many times they're edited. Confirm the filing was
   actually submitted, then let it process.
2. **Google Business Profile** — sign in and confirm the duplicate "Inc." listing
   is closed/merged (biggest local-ranking lever, and account-only).
3. **Re-run this verification a third time** once the HCAI filing is confirmed
   landed (likely several more weeks), since that's what unblocks the directories.

---
---

## Third verification pass

**Re-checked:** July 15, 2026 (live web fetch, same method as prior passes).
**Pages fetched directly:** hcai.ca.gov facility page · hospice.io listing ·
hospicematch.com listing · hospicecarenow.com listing.

### Bottom line — HCAI filing has not landed; all directories unchanged

**No change since the second pass.** The HCAI state record still shows the old
Agoura Road address, which confirms the address-update filing with HCAI/CDPH
has **not yet been processed**. Because the three hospice directories (hospice.io,
hospicematch, hospicecarenow) pull from that state record, they all still show
Agoura Road too — exactly as expected while the upstream filing is pending.

A **fourth check is needed once the HCAI/CDPH filing is confirmed received and
processed** by the state (can take several additional weeks after submission).

### Result by listing (third check — live fetches, July 15, 2026)

| Listing | Live state | Change since 2nd pass? |
|---|---|---|
| **HCAI** (hcai.ca.gov, ID 406560025) | Still **30941 Agoura Rd, Westlake Village, CA 91361**, status **Open** | ❌ no change — filing not yet processed |
| **hospice.io** | Still **30941 Agoura Road, Suite 112, Westlake Village, CA 91361**; phone still garbled **"(80-5) -953-7273"** | ❌ no change |
| **hospicematch.com** | Still **30941 Agoura Road, Suite 112, Westlake Village, CA 91361**; banner still **"This listing is not yet verified."** | ❌ no change |
| **hospicecarenow.com** | Still **30941 AGOURA ROAD, SUITE 112, Westlake Village, CA 91361** | ❌ no change |
| **BBB** (bbb.org) | Not re-fetched this pass; previously confirmed correct | ✅ carry-forward |
| **Yelp** | Separate company — not touched, as confirmed in pass 1 | ✅ no action |
| **Google Business Profile** | Not verifiable from outside; search view was correct in prior passes | ⚠️ unconfirmed (needs sign-in) |
| **Bing Places / Apple Business Connect** | Not verifiable without signing into the accounts | ⚠️ unconfirmed |
| **caring.com** | Not re-fetched this pass; still not listed as of pass 2 | ⬜ still not listed |

> **hospice.io listing URL confirmed:** https://hospice.io/care/eternal-life-hospice-inc-westlake-village-ca/
> (the city-level URL used in prior passes returned a 404; the provider-level URL above is the live, correct page).

### Updated checklist (third-check status)

- [ ] HCAI (hcai.ca.gov) — **still Agoura Rd / 91361**; CDPH/HCAI address-update filing has NOT processed yet (upstream blocker)
- [ ] hospice.io — **still Agoura Rd + garbled phone "(80-5) -953-7273"**; listing URL: hospice.io/care/eternal-life-hospice-inc-westlake-village-ca/
- [ ] hospicematch.com — **still Agoura Rd + unverified**
- [ ] hospicecarenow.com — **still Agoura Rd**
- [ ] Google Business Profile — search view was correct; duplicate "Inc." closure/merge still unconfirmed (needs sign-in)
- [ ] Bing Places — unconfirmed (needs sign-in)
- [ ] Apple Business Connect — unconfirmed (needs sign-in)
- [ ] caring.com — still not listed
- [x] BBB — name + phone correct (address hidden by BBB, which is normal)
- [x] Yelp — separate company, correctly left untouched

### What to do next

1. **HCAI/CDPH filing status** — confirm with your licensing/compliance contact
   that the address-update filing was actually submitted, and ask for the
   expected processing timeline. Nothing downstream (hospice.io, hospicematch,
   hospicecarenow) will self-correct until that state record flips.
2. **Google Business Profile** — sign in and confirm the duplicate **"Eternal
   Life Hospice, Inc."** listing is closed or merged (the single action with
   the biggest local-ranking impact, and the one that can't be done from outside).
3. **Run a fourth pass** once the HCAI filing is confirmed processed — that is
   when the directories are expected to update.

---
---

## Fourth verification pass

**Re-checked:** July 15, 2026 (live web fetch, same method as prior passes).
**Pages fetched directly:** hcai.ca.gov facility page · hospice.io listing ·
hospicematch.com listing · hospicecarenow.com listing.

> **URL updates noted this pass:** Several directory URLs changed since the
> third pass. Correct current URLs are recorded in the results table below and
> should be used for all future checks.

### Bottom line — HCAI filing still has not landed; directories unchanged

**No change since the third pass.** The HCAI state record still shows the old
**30941 Agoura Road / 91361** address, confirming the address-update filing with
HCAI/CDPH has **not yet been processed**. Because the three hospice directories
(hospice.io, hospicematch, hospicecarenow) pull their data from that state
record, all three still show the old address as well — exactly as expected while
the upstream filing is pending.

Since HCAI has not yet flipped, manual edits directly on the directories would
be premature — they would simply be overwritten the next time those sites
re-sync from the state record. **The HCAI filing remains the gate.** No manual
directory work is unblocked until the state record shows the Thousand Oaks Blvd
address.

### Result by listing (fourth check — live fetches, July 15, 2026)

| Listing | Current URL | Live state | Change since 3rd pass? |
|---|---|---|---|
| **HCAI** (hcai.ca.gov, ID 406560025) | https://hcai.ca.gov/facility/eternal-life-hospice-inc/ | Still **30941 Agoura Rd, Westlake Village, CA 91361**, Facility Status: **Open** | ❌ no change — filing not yet processed |
| **hospice.io** | https://hospice.io/care/eternal-life-hospice-inc-westlake-village-ca/ | Still **30941 Agoura Road, Suite 112, Westlake Village, CA 91361**; phone still garbled **"(80-5) -953-7273"** | ❌ no change |
| **hospicematch.com** | https://www.hospicematch.com/hospices/eternal-life-hospice-inc *(URL changed from prior pass)* | Still **30941 Agoura Road, Suite 112, Westlake Village, CA 91361**; banner still **"This listing is not yet verified."** | ❌ no change (URL updated) |
| **hospicecarenow.com** | https://www.hospicecarenow.com/united-states/california/westlake-village/eternal-life-hospice *(URL changed from prior pass)* | Still **30941 AGOURA ROAD, SUITE 112, Westlake Village, CA 91361** | ❌ no change (URL updated) |
| **BBB** (bbb.org) | Not re-fetched this pass; previously confirmed correct | ✅ carry-forward |  |
| **Yelp** | Separate company — not touched, as confirmed in pass 1 | ✅ no action |  |
| **Google Business Profile** | Not verifiable from outside; search view was correct in prior passes | ⚠️ unconfirmed (needs sign-in) |  |
| **Bing Places / Apple Business Connect** | Not verifiable without signing into the accounts | ⚠️ unconfirmed |  |
| **caring.com** | Not re-fetched this pass; still not listed as of pass 2 | ⬜ still not listed |  |

### Updated checklist (fourth-check status)

- [ ] HCAI (hcai.ca.gov) — **still Agoura Rd / 91361**; CDPH/HCAI address-update filing has NOT processed yet *(upstream blocker — nothing below unblocks until this flips)*
- [ ] hospice.io — **still Agoura Rd + garbled phone "(80-5) -953-7273"**; manual edit unblocked only after HCAI flips
- [ ] hospicematch.com — **still Agoura Rd + unverified**; manual claim/edit unblocked only after HCAI flips
- [ ] hospicecarenow.com — **still Agoura Rd**; manual correction unblocked only after HCAI flips
- [ ] Google Business Profile — search view was correct; duplicate "Inc." closure/merge still unconfirmed (needs sign-in)
- [ ] Bing Places — unconfirmed (needs sign-in)
- [ ] Apple Business Connect — unconfirmed (needs sign-in)
- [ ] caring.com — still not listed
- [x] BBB — name + phone correct (address hidden by BBB, which is normal)
- [x] Yelp — separate company, correctly left untouched

### What to do next

1. **HCAI/CDPH filing is the gate.** Confirm with your licensing/compliance
   contact that the address-update filing was actually submitted. Until the
   state record at hcai.ca.gov/facility/eternal-life-hospice-inc/ shows
   4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362,
   none of the three hospice directories will self-correct.
2. **Once HCAI flips** — immediately claim/edit the three directories manually:
   - **hospice.io** — edit address and fix the garbled phone format
   - **hospicematch.com** — claim the listing (still unverified) and update address
   - **hospicecarenow.com** — correct the address
3. **Google Business Profile** — sign in and confirm the duplicate **"Eternal
   Life Hospice, Inc."** listing is closed or merged (account-only action with
   the biggest local-ranking impact; does not depend on HCAI).
4. **Run a fifth pass** after the HCAI flip and after manual directory edits
   are submitted, to confirm the corrected addresses have published.
