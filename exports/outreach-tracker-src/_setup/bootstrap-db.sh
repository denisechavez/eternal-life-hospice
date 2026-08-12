#!/usr/bin/env bash
# bootstrap-db.sh — apply schema.sql to the Postgres database
#
# Run once when provisioning a new environment, or any time you want to make
# sure the schema is current.  Every statement is idempotent (IF NOT EXISTS),
# so it is safe to re-run against an existing database.
#
# Prerequisites: DATABASE_URL must be set in the environment (the Replit
# PostgreSQL integration exports it automatically).
#
# Usage:
#   bash _setup/bootstrap-db.sh

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set." >&2
  echo "Enable the PostgreSQL integration in your Replit project and re-run." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="$SCRIPT_DIR/../schema.sql"

echo "[bootstrap-db] Applying schema.sql …"
psql "$DATABASE_URL" < "$SCHEMA"
echo "[bootstrap-db] Done — schema is up to date."
