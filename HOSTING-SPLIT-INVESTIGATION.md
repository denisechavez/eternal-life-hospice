# Hosting Split Investigation

**Investigation date:** 2026-08-27  
**Time basis:** UTC unless otherwise stated  
**Scope:** Read-only review of Git history, Replit deployment metadata, public Netlify deployment metadata, and safe GET requests to both live hosts. No forms were submitted. No DNS, domain, deployment, or runtime configuration was changed.

## Executive conclusion

Do **not** roll back Git or point the custom domain back to the current Netlify deployment.

The evidence establishes three separate milestones:

1. **Two hosts first coexisted:** Netlify had a public production deployment on 2026-06-24. Replit has an explicit publication record from 2026-07-09. Parallel hosting therefore existed by 2026-07-09.
2. **The custom domain changed authority:** The exact external setting change is not recorded in Git. The narrowest verified window is after the first Replit publication on 2026-07-09 and before the Replit-serving observation on 2026-08-26. Work on 2026-08-17 and 2026-08-18 still assumed Netlify controlled the custom-domain routes, suggesting—but not proving—a later switch.
3. **The hosts became operationally different:** Netlify's last production publish was 2026-08-25. Replit added its verified form processor on 2026-08-26 and published afterward. The live Replit site now has the safe referral endpoint; the live Netlify copy does not.

The safest path is to keep Replit authoritative and consolidate forward. First bring the required redirects into the Replit server, then replace the Netlify copy with path-preserving redirects to the canonical domain. Preserve both current deployments until those checks pass.

## Confidence labels

- **Verified:** Direct provider metadata, live response, or committed source establishes the fact.
- **Inferred:** Multiple records support the conclusion, but no provider event records the exact external change.
- **Unknown:** The available public and repository evidence cannot establish the fact.

## Dated timeline

| Date and time | Confidence | Event | Meaning |
|---|---|---|---|
| 2026-06-24 07:43:52 | Verified | Netlify production deploy `6a3b8ab5826444ef145fd7b6` was published. | The Netlify site existed before the current Git repository's initial commit. The deploy's present-day API response names the custom domain, but that field is not reliable historical proof that the domain was attached on June 24. |
| 2026-06-27 02:57:28 | Verified | Git initial commit `c1ec16a4b59cc278699cce8062781f511f8e2fc4`. | Earliest repository baseline. It already contained the website and a Replit preview workflow, but no root Netlify configuration. |
| 2026-06-29 11:44:21 | Verified | Commit `5152ee4277521c7c256a3f9fe3ff25c8bb51076b` added the root Netlify configuration. | Git-backed Netlify deployment became an explicit project path. |
| 2026-06-29 12:28:12 | Verified | First Git-referenced Netlify production publish found in provider history. | Netlify automatic production publishing was active. |
| 2026-07-09 20:32:58 | Verified | Replit publication marker `62b7f1881c5e1d3ae82eb35b9eb617ed441ab692`, build `2dc61231-0136-4761-9e16-19fff09dd174`. | First explicit evidence that this project was published on Replit. It does not establish custom-domain assignment. |
| 2026-07-10 04:44:14 | Verified | Commit `882d7b1a4f2617a12baeb98ddbff5136eef48adb` set Netlify's site base and publish directory. | Netlify was formalized as the static website deployment path. |
| 2026-07-13 22:23:00 | Verified | Commit `8cf066a44ace9efdfac25c9f1bed95bc55b9227f` added explicit Netlify Forms behavior and notifications. | Netlify-specific submission behavior was now part of the site design. |
| 2026-08-17 through 2026-08-18 | Inferred | Tracker work added Netlify `_redirects` proxies to a Replit deployment, including commit `03677d4821e9e5d8bfc4243194a21f8cb0ebd107`. | The project still treated Netlify routing as capable of controlling `eternallifehospice.com`. This is evidence of the team's hosting assumption, not proof of DNS authority. |
| 2026-08-25 08:41:33 | Verified | Netlify production deploy `6a8d5522ffa55f00083c01fc` published commit `0c6ca3f39d878e59976e0d03dacec6e550e36e99`. | This remains the live Netlify hostname's latest published build. |
| 2026-08-25 09:51:47 | Verified | Replit publication marker `4344de405d731b33906084946c6cf9af51955d25`. | Replit published a separate workspace snapshot about 70 minutes after the final Netlify publish. |
| 2026-08-26 07:52:21 | Verified observation | Hosting investigation commit `8808c15a71b4efe4a57b40e9f8e5147b1c80980b` recorded the custom domain resolving to Replit Autoscale through Replit-managed Google Cloud infrastructure. | The custom domain was definitively Replit-authoritative by this observation. |
| 2026-08-26 08:18:10 | Verified | Commit `22acd32e7990c9b1f14161e13112cb1c4c0fc3a7` added the Replit `/api/form-submit` processor and moved browser forms to it. | This is the first clear, material form-processing split between the two live deployments. |
| 2026-08-26 08:29:25 | Verified | Commit `7829d0f8471e64fe15f47ed88f6d47ba4744fce6` added privacy-safe delivery-outage alerts. | The Replit intake path gained safeguards absent from the Netlify copy. |
| 2026-08-26 08:31:22 | Verified | Replit publication marker `1b92ec4b7be6c526da13e5275ab17e6f4bc3689b`. | The safe Replit intake changes were published after the last Netlify build. |
| 2026-08-27 | Verified | Replit deployment metadata reports a healthy, public Autoscale deployment with `https://eternallifehospice.com` as primary and the generated Replit URL as additional. | Replit remains authoritative now. |

## Custom-domain switch window

### Strictly supportable window

- **Earliest possible from available Replit evidence:** 2026-07-09 20:32:58, when the first Replit publish is recorded.
- **Latest possible from direct observation:** 2026-08-26 07:52:21, when the domain was verified on Replit.

### Likely but unproven narrower window

The August 17–18 tracker tasks and redirects were written as though Netlify still controlled the public site's routing. If that assumption was correct at the time, the switch occurred between 2026-08-18 and 2026-08-26. Because current Netlify metadata still lists `eternallifehospice.com` as its custom domain even though DNS serves Replit, provider metadata alone cannot validate that assumption.

### Evidence required for an exact timestamp

An exact cutover time requires at least one of:

- Replit custom-domain activity or deployment history showing when the domain was attached
- Netlify domain-management audit history showing when DNS ceased reaching Netlify
- DNS-provider change history for the apex and `www` records
- A historical passive-DNS record with observation timestamps

No public historical DNS result found during this investigation was sufficient to establish that timestamp.

## Current host comparison

Observed on 2026-08-27 using safe GET requests only.

### Hosting identity

| Check | Custom domain | Netlify hostname |
|---|---|---|
| Host | `https://eternallifehospice.com` | `https://eternallifehospice.netlify.app` |
| Status | 200 | 200 |
| Server evidence | Google Frontend / Replit Autoscale | Netlify |
| Authoritative role | Primary production host | Stale parallel copy |
| Canonical URL in HTML | Custom domain | Custom domain |
| Latest identified deployment | Replit publication after form migration | Netlify deploy from 2026-08-25 |

Both copies declare the custom domain as canonical. The Netlify hostname is therefore explicitly noncanonical, but it still serves indexable duplicate HTML instead of redirecting visitors.

### Forms and callbacks

| Behavior | Custom domain | Netlify hostname | Risk |
|---|---|---|---|
| Homepage lead-form action | `/api/form-submit` | `/` | The Netlify copy does not use the verified Replit processor. |
| `/refer` form action | `/api/form-submit` | `/` | Repointing DNS to Netlify would change referral delivery behavior. |
| Success requirement | Accepted JSON from the Replit processor | Legacy Netlify form flow | Netlify can no longer be treated as equivalent without a new delivery test. |
| Privacy/rate-limit guardrails | Present in Replit processor | Not present in the live Netlify build | A DNS rollback would remove current safeguards. |
| Independent outage alert | Present on Replit | Absent from live Netlify build | Delivery failures would lose the current escalation path. |
| Hidden chat callback form | Removed from current custom-domain output | Present in live Netlify output | The hosts use different callback architectures. |

`GET /api/form-submit` returns 404 on both hosts, which is expected for the Replit host because the endpoint is POST-only. Source and the previously authorized synthetic no-PHI test establish that Replit handles the POST. No POST was made during this investigation.

### Routes and redirects

The Replit Python server does not consume Netlify's `_redirects` file. As a result, several aliases work on Netlify but return 404 on the authoritative custom domain.

| Route | Custom domain | Netlify hostname |
|---|---:|---:|
| `/refer-a-patient` | 404 | 301 to `/refer` |
| `/referral` | 404 | 301 to `/refer` |
| `/refer-patient` | 404 | 301 to `/refer` |
| `/providers` | 404 | 301 to `/refer` |
| `/kit`, `/presskit`, `/press-kit`, `/media` | 404 | 301 to `/media-kit` |
| `/aleksandra` | 404 | 301 to `/about/aleksandra-dubina` |
| `/denise` | 404 | 301 to `/card-denise-chavez` |
| `/resources/what-hospice-covers` | 404 | 301 to `/resources/medicare-hospice-benefit` |
| `/aleksandradubina` | 404 | 301 to `/about/aleksandra-dubina` |
| Old Care Brief paths | 404 | 301 to current Care Brief routes |
| `/blog/caring-for-the-caregiver` | 200 | 301 to `/blog/the-caregiver-who-needs-care` |
| `/blog/the-second-patient` | 404 | 301 to `/blog/the-caregiver-who-needs-care` |

This routing loss is a reason to consolidate forward, not a reason to restore the unsafe Netlify intake path.

### Events

The following return 404 on both hosts:

- `/events`
- `/events/`
- `/events/caregiver-support-workshop`
- `/events/community-grief-circle`

No Event URLs were found in either live sitemap. A rollback to an August 17-era snapshot could reintroduce Event pages or older redirect behavior and is therefore outside the approved state.

### Tracker

`/tracker`, `/tracker/`, and `/api/config` return 404 on both public website hosts. The current source `_redirects` file still contains historical proxy rules, but neither live host exposes the tracker through those routes. The tracker is now a separate standalone-app concern and should not determine the website hosting rollback.

### Robots and sitemap

- `robots.txt` is byte-identical on both hosts and points to the custom-domain sitemap.
- Both sitemaps contain canonical custom-domain URLs.
- The sitemap bodies differ. The custom-domain homepage has a 2026-08-26 last-modified date; Netlify's has 2026-08-13, confirming deployment drift.

## Rollback checkpoint assessment

| Candidate | Would restore | Would break or risk | Decision |
|---|---|---|---|
| `c1ec16a4` — 2026-06-27 initial Git baseline | Earliest repository version of the site | Removes two months of compliance, SEO, accessibility, content, form, and reliability work; does not change external DNS | Reject |
| `5152ee42` — 2026-06-29 Netlify configuration | Early Git-backed Netlify setup | Does not restore an external domain setting; removes later site fixes and all Replit intake safeguards | Reject |
| `62b7f188` — 2026-07-09 first Replit publication marker | Earliest known Replit-published snapshot | Does not detach the domain or remove Netlify; loses later production work | Reject |
| `03677d48` — 2026-08-17 tracker proxy activation | Netlify-oriented tracker and redirect assumptions | Predates current form reliability and retired-Event cleanup; proxy target is no longer the website architecture | Reject |
| Netlify deploy `6a8d5522ffa55f00083c01fc` / Git `0c6ca3f3` — 2026-08-25 | Current Netlify HTML and its working legacy redirects | Referral forms post to the legacy Netlify path, not the verified processor; current privacy and outage safeguards disappear; notification ownership is unverified | Reject as DNS or code rollback |
| `22acd32e` — 2026-08-26 form processor baseline | Verified Replit referral processing | Omits the immediately following independent outage-alert safeguard | Emergency code floor only, not preferred |
| `7829d0f8` — 2026-08-26 intake plus alerts | Verified form processor and privacy-safe outage alerting | Still requires current-route parity work; rolling the rest of the site to this point could discard later unrelated fixes | Preserve as known-good intake baseline |

## Option assessment

| Option | Referral safety | SEO/routing | Reversibility | Recommendation |
|---|---|---|---|---|
| Leave both hosts exactly as they are | High on canonical Replit host | Duplicate Netlify content and missing Replit redirects remain | High | Accept only as a short holding state |
| Consolidate forward on Replit | Preserves verified processor and alerts | Can restore redirect parity and eliminate duplicate content | High when staged | **Recommended** |
| Reverse only DNS/domain routing to Netlify | Regresses to unverified legacy intake | Restores Netlify redirects but makes stale content authoritative | Medium; DNS propagation complicates recovery | Reject |
| Roll Git back to a pre-split checkpoint and publish | Removes current intake and many later fixes | Unknown mixture of old routes, Events, and content | Technically reversible, operationally risky | Reject |
| Replace Netlify content with canonical redirects | Keeps Replit intake authoritative | Consolidates duplicate-host signals while preserving old links | High if current Netlify deploy is preserved | Recommended after Replit route parity |

## Recommended reversible consolidation runbook

No stage below should begin without separate user approval.

### Stage 0 — Preserve and record

1. Record the active Replit deployment, current custom-domain assignment, and Netlify deploy `6a8d5522ffa55f00083c01fc`.
2. Preserve the current Netlify deployment as an immutable rollback reference.
3. Confirm the referral mailbox, outage-alert channel, and 24/7 phone fallback are monitored.

**Approval hold point A:** Approve routing-parity implementation only. Do not change DNS or Netlify yet.

### Stage 1 — Restore route parity on Replit

1. Implement the approved permanent redirects in the Replit server rather than relying on Netlify `_redirects`.
2. Keep all retired Event routes at 404 or 410.
3. Keep tracker routing outside the website unless the standalone tracker task separately authorizes a stable link.
4. Add route tests covering status codes, destinations, and redirect loops.

**Verification:** All approved aliases return one-hop permanent redirects on the custom domain; canonical routes remain 200; Event routes remain unavailable; form tests pass.

**Approval hold point B:** Approve a Replit publish only after local validation.

### Stage 2 — Publish and verify Replit

1. Publish the validated Replit snapshot.
2. Confirm homepage, `/refer`, sitemap, robots, canonical metadata, redirects, and Event 404 behavior.
3. Run one authorized synthetic no-PHI referral through `/refer`.
4. Require processor acceptance, receipt in `referral@eternallifehospice.com`, any intended synthetic acknowledgement, and deletion of the mailbox test records.
5. Confirm the delivery-outage webhook remains configured without exposing its value.

**Approval hold point C:** Approve changing the Netlify duplicate only after the Replit checks pass.

### Stage 3 — Convert Netlify to path-preserving canonical redirects

1. Replace duplicate content on the `netlify.app` hostname with permanent, path-preserving redirects to `https://eternallifehospice.com`.
2. Do not host referral forms or a second form processor on Netlify.
3. Verify representative content, referral, Care Brief, media-kit, and retired Event paths.
4. Keep the preserved Netlify deploy available for rollback during monitoring.

**Verification:** Netlify URLs issue one-hop permanent redirects to matching canonical paths; no form accepts a submission on the Netlify hostname; no redirect loop involves the still-attached custom-domain metadata.

**Approval hold point D:** Approve removing stale domain attachments or deactivating the old site only after monitoring.

### Stage 4 — Monitor, then retire stale ownership

1. Monitor referrals, 404s, redirect traffic, Search Console, and deployment logs for at least one normal operating cycle.
2. Remove the stale custom-domain association from Netlify after verifying Replit remains authoritative.
3. Keep or deactivate the Netlify redirect site based on whether old `netlify.app` links still receive traffic.

## Emergency recovery rule

If a Replit publish fails, restore the previous known-good **Replit deployment** first. Do not use the current Netlify copy as an emergency referral host.

A DNS move to Netlify is acceptable only after Netlify has:

- an independently verified processor,
- the same no-PHI validation and rate limits,
- confirmed delivery to the monitored destinations,
- failure responses that show the phone fallback,
- independent outage alerting,
- and a completed synthetic no-PHI end-to-end test.

## Final decision

The split was not a single Git mistake that can be safely undone. It consists of an older Netlify deployment, a later Replit publication path, an externally managed custom-domain cutover, and a subsequent Replit-only form migration.

**Decision:** Keep `eternallifehospice.com` on Replit. Restore redirect parity there, verify referrals again, then turn the Netlify hostname into a canonical redirect surface. Do not roll back code or DNS to the August 25 Netlify deployment.