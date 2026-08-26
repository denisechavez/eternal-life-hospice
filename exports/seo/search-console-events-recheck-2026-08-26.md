# Search Console Events report recheck

**Checked:** August 26, 2026  
**Property:** `https://eternallifehospice.com/`

## Search Console result

The Events report supplied by the property owner shows:

- **Valid:** 3
- **Invalid:** 0
- **Last detected:** August 25, 2026

The three reported items are:

| URL | Event item | Last detected |
|---|---|---|
| `https://eternallifehospice.com/events` | Caregiver Support Workshop | August 25, 2026 |
| `https://eternallifehospice.com/events` | Community Grief Circle | August 25, 2026 |
| `https://eternallifehospice.com/events/community-grief-circle` | Community Grief Circle | August 25, 2026 |

The report also shows appearance-improvement warnings for the retained historical items:

- Missing field `offers` — 3 items
- Missing field `performer` — 3 items
- Missing field `url` in `organizer` — 2 items

These are not current production errors. The events are retired, so adding placeholder fields would be incorrect.

## Live verification

The owner’s URL Inspection screenshot for
`https://eternallifehospice.com/events` shows the Live Test result:

> URL doesn't have this enhancement

Independent production checks on August 26, 2026 confirmed:

- `/events` returns HTTP 404.
- `/events/` returns HTTP 404.
- `/events/caregiver-support-workshop` returns HTTP 404.
- `/events/community-grief-circle` returns HTTP 404.
- None of those responses contains Event JSON-LD or other Event structured-data markers.
- The current published static source contains no Event JSON-LD and no `/events` route references.

These checks are reproducible with:

```text
python3 website/check-retired-events.py
```

The check covers both slash and non-slash forms of the events index and both
retired detail routes. It requires every response to be HTTP 404 or 410 and
rejects any response containing an Event JSON-LD item.

Observed output on August 26, 2026:

```text
PASS /events status=404 event_json_ld=False
PASS /events/ status=404 event_json_ld=False
PASS /events/caregiver-support-workshop status=404 event_json_ld=False
PASS /events/caregiver-support-workshop/ status=404 event_json_ld=False
PASS /events/community-grief-circle status=404 event_json_ld=False
PASS /events/community-grief-circle/ status=404 event_json_ld=False
All retired event routes return 404/410 without Event JSON-LD.
```

## Decision

The stale Event markup has been removed from the actual serving source, and the live result is correct. The three valid items shown in Search Console are residual results from Google’s August 25 crawl, not markup currently served by the site.

Search Console does not show a **Validate Fix** control because there are no invalid items; it only shows valid items with optional appearance warnings. Do not add `offers`, `performer`, or organizer data to retired events, and do not request indexing for the retired 404 URLs. Recheck the report after Google’s next crawl to confirm the residual items disappear.