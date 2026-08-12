#!/usr/bin/env node
/**
 * migrate.js — idempotent schema bootstrap
 *
 * Reads schema.sql and applies it to the Postgres database identified by
 * DATABASE_URL.  Every statement uses CREATE TABLE IF NOT EXISTS / CREATE INDEX
 * IF NOT EXISTS, so running this against an already-provisioned database is
 * safe.
 *
 * Called automatically by the `pretest` npm hook so a freshly provisioned
 * environment always has the right schema before tests run.
 *
 * Usage (manual):
 *   node migrate.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');
const { Client } = require('pg');

const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  console.log('[migrate] DATABASE_URL not set — skipping schema migration.');
  process.exit(0);
}

const schemaPath = path.join(__dirname, 'schema.sql');
const sql = fs.readFileSync(schemaPath, 'utf8');

(async () => {
  const client = new Client({ connectionString: DATABASE_URL });
  try {
    await client.connect();
    console.log('[migrate] Applying schema.sql …');
    await client.query(sql);
    console.log('[migrate] Schema is up to date.');
  } catch (err) {
    console.error('[migrate] Failed to apply schema:', err.message);
    process.exit(1);
  } finally {
    await client.end();
  }
})();
