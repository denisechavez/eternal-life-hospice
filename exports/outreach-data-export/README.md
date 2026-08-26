# Outreach Tracker — Data Export

**Re-verified:** 2026-08-26
**Source:** Main marketing-site Replit (this project)  
**Destination:** Standalone outreach-tracker Replit

---

## Finding: No visit records to migrate

The live source database was re-checked on **2026-08-26**. Both `visits` and
`visit_photos` were empty, so the migration is a verified zero-row import.

| Table | Rows |
|---|---|
| visits | 0 |
| visit_photos | 0 |

No user or visit payload needs to be copied. The standalone Replit can start
fresh from id = 1 after applying its canonical `schema.sql`.

The source schema has a legacy `follow_up_method` column that is not part of
the standalone schema. Because the source contains no rows, this produces no
loss; it is documented in the export mapping rather than added to the new app.

---

## How to use `visits-export.sql`

If visits are found in the retired source before access is removed, stop new
writes and re-run the export queries documented inside `visits-export.sql`.
Then:

1. In the new standalone Replit, apply `schema.sql` (included in `outreach-tracker-standalone.zip`).
2. Run `visits-export.sql` in the Replit database console (or via `psql $DATABASE_URL < visits-export.sql`).
3. Run the checks in `migration-verification.md`.

---

## Checklist for the new standalone Replit

- [x] Source counts re-verified: `visits = 0`, `visit_photos = 0`
- [x] Data-only export mapped to the standalone schema
- [x] Apply `schema.sql` and `visits-export.sql` to a fresh, isolated
      destination-equivalent PostgreSQL schema
- [x] Verify the fresh schema contains `visits = 0`, `visit_photos = 0`
- [x] Rebuild `outreach-tracker-standalone.zip` from the complete canonical
      source and verify fresh install, migration, tests, and server boot

The separate field-use deployment remains an operational follow-up:

- [ ] Set secrets: `SESSION_SECRET`, `REGISTRATION_CODE`
- [ ] Deploy and confirm the app boots and shows the empty visit log
- [ ] Log a test visit; confirm it saves, shows on the Follow-up tab, and exports via CSV

## Ownership after migration

- **Standalone outreach tracker:** owns all future visit records, visit photos,
  follow-up state, CSV exports, tracker users, sessions, and backups.
- **Main marketing site:** owns public pages and public referral intake only.
  It does not own, display, or write outreach visits.
- The old `visits` and `visit_photos` tables in the main project's database are
  retained as an empty migration source for auditability, but are not
  authoritative and must not receive new writes.

The full source-count, mapping, and destination verification record is in
`migration-verification.md`.
