# NAP Citation Cleanup — Verification Pass

**Date verified:** July 14, 2026
**For:** Eternal Life Hospice, Inc. — eternallifehospice.com
**Verifies:** `nap-citation-cleanup-2026-07-14.md` (the action guide)
**Method:** live web fetch + search of each listing on July 14, 2026 (public,
un-authenticated view — the same view a searcher or Google sees).

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
