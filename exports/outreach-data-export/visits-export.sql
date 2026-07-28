-- =============================================================================
-- Eternal Life Hospice — Field Outreach Tracker
-- Data export from the original Replit (main marketing-site project)
-- Exported: 2026-07-28
-- =============================================================================
-- HOW TO USE
-- ----------
-- 1. In your standalone tracker Replit, apply schema.sql first (creates the
--    tables, indexes, and sequences).
-- 2. Then run this file to import visit data.
-- 3. If visits rows exist below, the INSERT statements will load them.
--    If this file only contains the schema stubs, there was no data to migrate.
-- =============================================================================

-- ── Schema reference (matches schema.sql in the standalone zip) ──────────────
-- Included here for completeness; schema.sql in the standalone app is canonical.

CREATE TABLE IF NOT EXISTS visits (
    id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    company     TEXT NOT NULL,
    address     TEXT,
    visit_date  DATE DEFAULT CURRENT_DATE,
    contact_name   TEXT,
    contact_email  TEXT,
    contact_phone  TEXT,
    notes          TEXT,
    followup_status TEXT NOT NULL DEFAULT 'Not started',
    created_by  INTEGER,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    category    TEXT,
    city        TEXT,
    county      TEXT,
    contact_title TEXT,
    materials   JSONB NOT NULL DEFAULT '[]',
    owner       TEXT,
    follow_up_due DATE,
    attested    BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS visit_photos (
    id        INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    visit_id  INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    kind      TEXT NOT NULL DEFAULT 'visit',
    mime_type TEXT NOT NULL,
    data      BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_visits_status  ON visits (followup_status);
CREATE INDEX IF NOT EXISTS idx_photos_visit   ON visit_photos (visit_id);

-- ── Data ─────────────────────────────────────────────────────────────────────
-- STATUS: No visit records were found in the source database as of the export
-- date (2026-07-28). The app was set up and one user account was created on
-- 2026-07-09, but no field visits had been logged yet.
--
-- When the first real visits are added in the new standalone Replit, they will
-- start from id = 1. No sequence reset is needed.
--
-- If visits ARE added to the old project before the move is complete, re-run
-- the export query below against the OLD Replit's database and paste the
-- generated INSERT block here:
--
--   SELECT 'INSERT INTO visits (company,address,visit_date,contact_name,' ||
--          'contact_email,contact_phone,notes,followup_status,created_by,' ||
--          'created_at,updated_at,category,city,county,contact_title,' ||
--          'materials,owner,follow_up_due,attested) OVERRIDING SYSTEM VALUE VALUES (' ||
--          quote_nullable(company) || ',' || quote_nullable(address) || ',' ||
--          quote_nullable(visit_date::text) || ',' || quote_nullable(contact_name) || ',' ||
--          quote_nullable(contact_email) || ',' || quote_nullable(contact_phone) || ',' ||
--          quote_nullable(notes) || ',' || quote_nullable(followup_status) || ',' ||
--          quote_nullable(created_by::text) || ',' ||
--          quote_nullable(created_at::text) || ',' || quote_nullable(updated_at::text) || ',' ||
--          quote_nullable(category) || ',' || quote_nullable(city) || ',' ||
--          quote_nullable(county) || ',' || quote_nullable(contact_title) || ',' ||
--          materials::text || ',' || quote_nullable(owner) || ',' ||
--          quote_nullable(follow_up_due::text) || ',' || attested || ');'
--   FROM visits ORDER BY id;
--
--   -- Then for photos (BYTEA → base64 round-trip via psql \copy or pg_dump):
--   SELECT 'INSERT INTO visit_photos (visit_id,kind,mime_type,data,created_at)' ||
--          ' OVERRIDING SYSTEM VALUE VALUES (' ||
--          visit_id || ',' || quote_literal(kind) || ',' ||
--          quote_literal(mime_type) || ',' ||
--          'decode(' || quote_literal(encode(data,''base64'')) || ',''base64''),' ||
--          quote_literal(created_at::text) || ');'
--   FROM visit_photos ORDER BY id;

-- (No INSERT statements — source tables were empty at export time.)

-- ── Sequence sync (run AFTER all inserts) ────────────────────────────────────
-- Uncomment and adjust the values if you inserted rows with explicit ids above.
-- SELECT setval('visits_id_seq',     (SELECT MAX(id) FROM visits),     true);
-- SELECT setval('visit_photos_id_seq',(SELECT MAX(id) FROM visit_photos),true);
