/**
 * test-trim-guard.js
 *
 * Regression proof: test-backup-trim.js must exit with code 1 and print a
 * clear "ERROR:" message when the backup_log table does not exist — rather
 * than crashing on a permissions error or silently passing.
 *
 * Strategy: temporarily rename backup_log → backup_log_guard_tmp, spawn
 * test-backup-trim.js as a child process, assert the expected failure, then
 * rename the table back.  try/finally guarantees the rename is always
 * reversed even if the assertions throw.
 *
 * Requires: DATABASE_URL (needs SELECT on information_schema and ALTER TABLE
 * on backup_log — i.e. the same role used by the app).
 *
 * Exit codes: 0 = guard behaves correctly, 1 = a failure occurred.
 */

"use strict";

const { spawnSync } = require("child_process");
const path = require("path");
const { Pool } = require("pg");

if (!process.env.DATABASE_URL) {
  console.error(
    "ERROR: DATABASE_URL is not set.\n" +
    "       Set DATABASE_URL and re-run."
  );
  process.exit(1);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

let failures = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

async function run() {
  console.log("=== backup_log missing-table guard test ===\n");

  // Confirm backup_log exists before we hide it; skip gracefully if absent
  // (another test may have already dropped it — don't double-fault).
  const check = await pool.query(`
    SELECT 1 FROM information_schema.tables
     WHERE table_schema = 'public'
       AND table_name   = 'backup_log'
  `);
  if (check.rows.length === 0) {
    console.error(
      "ERROR: backup_log table does not exist in the database.\n" +
      "       Run schema.sql first, then re-run this guard test."
    );
    process.exitCode = 1;
    return;
  }

  // Hide the table so test-backup-trim.js sees a missing table.
  await pool.query("ALTER TABLE backup_log RENAME TO backup_log_guard_tmp");

  let result;
  try {
    const scriptPath = path.join(__dirname, "test-backup-trim.js");
    result = spawnSync(process.execPath, [scriptPath], {
      env: process.env,
      encoding: "utf8",
      timeout: 15000,
    });
  } finally {
    // Always restore the table, even if spawnSync throws.
    await pool.query("ALTER TABLE backup_log_guard_tmp RENAME TO backup_log");
  }

  const combined = (result.stdout || "") + (result.stderr || "");

  // 1. Must exit non-zero
  assert(
    result.status !== 0,
    `test-backup-trim.js exits non-zero when backup_log is absent (got exit code ${result.status})`
  );

  // 2. Output must contain "ERROR:" — not a silent pass or an unhandled crash
  assert(
    combined.includes("ERROR:"),
    `output contains "ERROR:" (got: ${JSON.stringify(combined.slice(0, 300))})`
  );

  // 3. Output must NOT contain "PASS:" — no assertions should have run
  assert(
    !combined.includes("PASS:"),
    `output does NOT contain "PASS:" — test should have aborted before any assertions`
  );

  // 4. Error message must mention backup_log so the cause is unambiguous
  assert(
    combined.includes("backup_log"),
    `error message mentions "backup_log" so the cause is unambiguous (got: ${JSON.stringify(combined.slice(0, 300))})`
  );

  // 5. Error message must mention schema.sql so the operator knows the fix
  assert(
    combined.includes("schema.sql"),
    `error message mentions "schema.sql" so the operator knows what to run (got: ${JSON.stringify(combined.slice(0, 300))})`
  );

  console.log("\n=== Done ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end())
  .then(() => {
    if (failures > 0) process.exit(1);
  });
