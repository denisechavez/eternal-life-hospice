# Outreach Tracker — Data Export

**Export date:** 2026-07-28  
**Source:** Main marketing-site Replit (this project)  
**Destination:** Standalone outreach-tracker Replit

---

## Finding: No visit records to migrate

Both `visits` and `visit_photos` tables were **empty** at the time of export.

| Table | Rows |
|---|---|
| visits | 0 |
| visit_photos | 0 |

One user account was created on **2026-07-09**, confirming the app was set up and accessible, but no field visits had been logged before the tracker was moved.

**No data migration is required.** The new standalone Replit can start fresh from id = 1.

---

## How to use `visits-export.sql`

If visits ARE added to the old project before the standalone Replit is fully live, re-run the export queries documented inside `visits-export.sql` and paste the generated `INSERT` statements back in. Then:

1. In the new standalone Replit, apply `schema.sql` (already included in `outreach-tracker-standalone.zip`).
2. Run `visits-export.sql` in the Replit database console (or via `psql $DATABASE_URL < visits-export.sql`).
3. Un-comment and run the `setval` lines at the bottom to sync the sequences.

---

## Checklist for the new standalone Replit

- [ ] Apply `schema.sql` from `outreach-tracker-standalone.zip`
- [ ] Run `visits-export.sql` (no-op if still empty; adds rows if data was added)
- [ ] Set secrets: `SESSION_SECRET`, `REGISTRATION_CODE`
- [ ] Deploy and confirm the app boots and shows the empty visit log
- [ ] Log a test visit; confirm it saves, shows on the Follow-up tab, and exports via CSV
