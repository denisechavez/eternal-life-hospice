# _setup — environment bootstrap helpers

## Database schema

`schema.sql` (one level up) is the single source of truth for the Postgres schema.
Every statement uses `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`, so
applying it to an already-provisioned database is safe.

### Automatic (npm pretest hook)

`npm test` runs `node migrate.js` automatically before the test suite starts.
A freshly provisioned Replit environment will have the correct schema without any
manual steps.

### Manual (new Replit project or CI bootstrap)

```bash
# Option A — Node helper (same logic as the pretest hook):
node migrate.js

# Option B — psql one-liner:
psql "$DATABASE_URL" < schema.sql

# Option C — shell helper in this directory:
bash _setup/bootstrap-db.sh
```

All three options are idempotent — safe to re-run at any time.

### Prerequisites

- The Replit **PostgreSQL** integration must be enabled so that `DATABASE_URL`
  is exported into the environment automatically.
- If `DATABASE_URL` is not set, `migrate.js` exits cleanly with a notice (it does
  not block pure-JS tests that don't touch the database).
