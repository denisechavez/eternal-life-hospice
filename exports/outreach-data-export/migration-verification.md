---
name: Outreach tracker migration verification
description: Auditable source counts, field mapping, and destination checks for the visit-history move.
---

# Outreach tracker migration verification

**Migration type:** verified zero-row import  
**Source:** main marketing-site Replit development database  
**Destination:** standalone outreach-tracker Replit database  
**Verified:** 2026-08-26

## Source verification

The source database was queried before preparing the destination export:

| Check | Result |
|---|---:|
| `visits` row count | 0 |
| `visit_photos` row count | 0 |
| `visits` minimum/maximum id | none |
| `visits` earliest/latest visit date | none |
| distinct visits with photos | 0 |

Because both source tables are empty, there are no representative row values
or binary photo payloads to copy. The export is intentionally a data-only
no-op rather than a second copy of the destination DDL.

## Mapping verification

All standalone `visits` fields have a direct source counterpart:

| Standalone field | Source field | Handling |
|---|---|---|
| `id` | `visits.id` | preserve if rows appear |
| `company`, `category`, `address`, `city`, `county` | same | direct |
| `visit_date` | same | direct date |
| `contact_name`, `contact_title`, `contact_email`, `contact_phone` | same | direct |
| `materials` | same | preserve as JSONB |
| `notes`, `owner`, `follow_up_due`, `followup_status`, `attested` | same | direct |
| `created_by`, `created_at`, `updated_at` | same | preserve audit fields |
| `visit_photos.*` | same | preserve FK and binary data if rows appear |

The source-only `follow_up_method` column is intentionally excluded. It has no
rows to map in this export and is not part of the standalone application
contract.

## Destination verification

On 2026-08-26, the canonical `schema.sql` and the data-only
`visits-export.sql` were executed together against a fresh, isolated
PostgreSQL schema. The verification transaction was rolled back afterward, so
the source database was not altered. This checks the same schema and import
path used by a new standalone Replit.

The following count queries were then run in that isolated schema:

```sql
SELECT COUNT(*) AS visit_count,
       MIN(id) AS min_id,
       MAX(id) AS max_id,
       MIN(visit_date) AS earliest_visit,
       MAX(visit_date) AS latest_visit
FROM visits;

SELECT COUNT(*) AS photo_count,
       COUNT(DISTINCT visit_id) AS visits_with_photos
FROM visit_photos;
```

Verified zero-row result:

| `visit_count` | `min_id` | `max_id` | `earliest_visit` | `latest_visit` |
|---:|---|---|---|---|
| 0 | null | null | null | null |

| `photo_count` | `visits_with_photos` |
|---:|---:|
| 0 | 0 |

The rebuilt standalone ZIP was also extracted into a clean directory and
verified for file parity with `exports/outreach-tracker-src`. Its dependencies
were installed from the packaged lockfile, the migration and full test chain
passed, and the server returned the Eternal Field Log page over HTTP.

The separate deployed Replit should repeat the count queries as its field-use
gate. It may contain later real visits after the team begins using it; those
are new destination-owned records, not migrated history.

## Ownership decision

After the schema is applied, the standalone tracker is the sole owner of
outreach visits and photos. The main marketing-site database tables remain
empty historical source tables only; no application path should write to them.
Public referral submissions remain owned by the marketing site and are not
visit-history records.