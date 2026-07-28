-- Eternal Life Hospice — Field Outreach Tracker
-- Full database schema. Run once against a fresh Postgres database.
-- On Replit: enable the PostgreSQL integration first, then run:
--   psql $DATABASE_URL < schema.sql

-- Session store (required by connect-pg-simple)
CREATE TABLE IF NOT EXISTS session (
  sid    VARCHAR NOT NULL PRIMARY KEY,
  sess   JSON    NOT NULL,
  expire TIMESTAMP(6) NOT NULL
);
CREATE INDEX IF NOT EXISTS IDX_session_expire ON session (expire);

-- Outreach team users (max 2)
CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  name          TEXT        NOT NULL,
  phone         TEXT        NOT NULL UNIQUE,
  password_hash TEXT        NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Referral visit records
CREATE TABLE IF NOT EXISTS visits (
  id              SERIAL PRIMARY KEY,
  company         TEXT        NOT NULL,
  category        TEXT,
  address         TEXT,
  city            TEXT,
  county          TEXT,
  visit_date      DATE        NOT NULL DEFAULT CURRENT_DATE,
  contact_name    TEXT,
  contact_title   TEXT,
  contact_email   TEXT,
  contact_phone   TEXT,
  materials       JSONB       NOT NULL DEFAULT '[]',
  notes           TEXT,
  owner           TEXT,
  follow_up_due   DATE,
  followup_status TEXT        NOT NULL DEFAULT 'Not started',
  attested        BOOLEAN     NOT NULL DEFAULT TRUE,
  created_by      INTEGER     REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backup run log (populated by the scheduled backup task)
CREATE TABLE IF NOT EXISTS backup_log (
  id       SERIAL PRIMARY KEY,
  ran_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status   TEXT        NOT NULL,  -- 'ok' | 'error'
  note     TEXT
);

-- Visit photos (business cards + site photos stored as binary)
CREATE TABLE IF NOT EXISTS visit_photos (
  id         SERIAL PRIMARY KEY,
  visit_id   INTEGER     NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
  kind       TEXT        NOT NULL DEFAULT 'site',  -- 'card' | 'site'
  mime_type  TEXT        NOT NULL,
  data       BYTEA       NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
