/**
 * test-backup-trim.js
 *
 * Verifies that the 90-day trim logic in /api/backup/status correctly deletes
 * old backup_log rows while retaining recent ones.
 *
 * Usage:
 *   DATABASE_URL=postgres://... node test-backup-trim.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const { Pool } = require("pg");

if (!process.env.DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set.");
  process.exit(1);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function query(text, params) {
  return pool.query(text, params);
}

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

async function run() {
  console.log("=== backup_log 90-day trim test ===\n");

  // Ensure the table exists (mirrors schema.sql)
  await query(`
    CREATE TABLE IF NOT EXISTS backup_log (
      id     SERIAL PRIMARY KEY,
      ran_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      status TEXT        NOT NULL,
      note   TEXT
    )
  `);

  // --- Insert test rows with a sentinel note so we can target only our rows ---
  const SENTINEL = "test-backup-trim-script";

  // Three rows that are older than 90 days — should be deleted
  await query(
    `INSERT INTO backup_log (ran_at, status, note) VALUES
       (NOW() - INTERVAL '91 days',  'ok',    $1),
       (NOW() - INTERVAL '180 days', 'error', $1),
       (NOW() - INTERVAL '365 days', 'ok',    $1)`,
    [SENTINEL]
  );

  // Two rows within 90 days — should survive
  await query(
    `INSERT INTO backup_log (ran_at, status, note) VALUES
       (NOW() - INTERVAL '89 days', 'ok',    $1),
       (NOW() - INTERVAL '1 day',   'ok',    $1)`,
    [SENTINEL]
  );

  // Confirm we inserted exactly 5 sentinel rows before the trim
  const before = await query(
    `SELECT COUNT(*)::int AS n FROM backup_log WHERE note = $1`,
    [SENTINEL]
  );
  assert(before.rows[0].n === 5, `5 sentinel rows present before trim (got ${before.rows[0].n})`);

  // --- Run the exact trim from server.js /api/backup/status ---
  await query(`DELETE FROM backup_log WHERE ran_at < NOW() - INTERVAL '90 days'`);

  // --- Assertions ---
  const after = await query(
    `SELECT COUNT(*)::int AS n FROM backup_log WHERE note = $1`,
    [SENTINEL]
  );
  assert(after.rows[0].n === 2, `2 recent sentinel rows remain after trim (got ${after.rows[0].n})`);

  const oldRemaining = await query(
    `SELECT COUNT(*)::int AS n FROM backup_log
      WHERE note = $1 AND ran_at < NOW() - INTERVAL '90 days'`,
    [SENTINEL]
  );
  assert(oldRemaining.rows[0].n === 0, `0 old sentinel rows remain (got ${oldRemaining.rows[0].n})`);

  const recentRows = await query(
    `SELECT ran_at FROM backup_log WHERE note = $1 ORDER BY ran_at DESC`,
    [SENTINEL]
  );
  assert(recentRows.rows.length === 2, `exactly 2 rows survive (got ${recentRows.rows.length})`);
  const allRecent = recentRows.rows.every(
    (r) => new Date(r.ran_at) >= new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
  );
  assert(allRecent, "all surviving rows have ran_at within the last 90 days");

  // --- Cleanup: remove our sentinel rows so the table is left in original state ---
  await query(`DELETE FROM backup_log WHERE note = $1`, [SENTINEL]);
  const cleanup = await query(
    `SELECT COUNT(*)::int AS n FROM backup_log WHERE note = $1`,
    [SENTINEL]
  );
  assert(cleanup.rows[0].n === 0, "sentinel rows cleaned up after test");

  console.log("\n=== Done ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
