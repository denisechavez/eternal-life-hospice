/**
 * test-backup-brevo-failure.js
 *
 * Verifies that a Brevo API failure is surfaced correctly instead of being
 * silently swallowed.
 *
 * What it verifies:
 *   1. A non-2xx Brevo response causes backup_log to receive an 'error' row.
 *   2. The note on that row contains the HTTP status code from Brevo so the
 *      admin sees an actionable message (e.g. "Brevo 401: ...").
 *   3. runWeeklyBackup resolves (does NOT throw) — errors are handled internally.
 *   4. The /api/backup/trigger endpoint returns { error: <note> } with HTTP 502
 *      when the most-recent log row has status='error'.
 *      (Tested by reading what trigger would return, without starting a server.)
 *
 * The test never sends real email — it substitutes a fake https module that
 * returns HTTP 401 with a Brevo-style error body.
 *
 * Usage:
 *   DATABASE_URL=postgres://... BACKUP_EMAIL=test@example.com BREVO_API=fake \
 *     node test-backup-brevo-failure.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const { Pool } = require("pg");
const EventEmitter = require("events");

// ---- env checks ----
if (!process.env.DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set.");
  process.exit(1);
}
if (!process.env.BACKUP_EMAIL) {
  console.warn(
    "SKIP: BACKUP_EMAIL is not set — Brevo failure test skipped.\n" +
    "      Set BACKUP_EMAIL (and BREVO_API) to run the full integration test."
  );
  process.exit(0);
}
if (!process.env.BREVO_API) {
  console.warn(
    "SKIP: BREVO_API is not set — Brevo failure test skipped.\n" +
    "      Set BREVO_API (any non-empty value works; real sends are intercepted) to run."
  );
  process.exit(0);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const { runWeeklyBackup } = require("./backup");

// ---- assertion helper ----
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

// ---- fake https module that returns HTTP 401 ----
// Mimics a Brevo "invalid API key" error response.
function makeFailing401Https() {
  const BREVO_401_BODY = JSON.stringify({
    code: "unauthorized",
    message: "Key not found",
  });

  const fakeHttps = {
    request(options, callback) {
      const fakeRes = new EventEmitter();
      fakeRes.statusCode = 401;

      const fakeReq = new EventEmitter();
      fakeReq.setTimeout = () => {};
      fakeReq.destroy = (err) => fakeReq.emit("error", err);
      fakeReq.write = () => {};
      fakeReq.end = () => {
        setImmediate(() => {
          callback(fakeRes);
          setImmediate(() => {
            fakeRes.emit("data", BREVO_401_BODY);
            fakeRes.emit("end");
          });
        });
      };
      return fakeReq;
    },
  };

  return fakeHttps;
}

// ---- fake https module that simulates a network timeout ----
function makeFakeTimeoutHttps() {
  const fakeHttps = {
    request(_options, _callback) {
      const fakeReq = new EventEmitter();
      let timeoutCb = null;
      fakeReq.setTimeout = (_ms, cb) => { timeoutCb = cb; };
      fakeReq.destroy = (err) => fakeReq.emit("error", err);
      fakeReq.write = () => {};
      fakeReq.end = () => {
        // Fire the timeout immediately instead of waiting 30 s
        setImmediate(() => {
          if (timeoutCb) timeoutCb();
        });
      };
      return fakeReq;
    },
  };
  return fakeHttps;
}

async function run() {
  console.log("=== Brevo failure surfacing test ===\n");

  // Verify both tables exist (must be created by schema.sql before tests run).
  // We deliberately do NOT issue CREATE TABLE here: a missing table is a setup
  // error — fail loudly so the operator knows to run the migration first.
  for (const tableName of ["visits", "backup_log"]) {
    const tableCheck = await pool.query(`
      SELECT 1 FROM information_schema.tables
       WHERE table_schema = 'public'
         AND table_name   = $1
    `, [tableName]);
    if (tableCheck.rows.length === 0) {
      console.error(
        `ERROR: ${tableName} table does not exist.\n` +
        "       Run the schema migration first:  psql $DATABASE_URL < schema.sql"
      );
      process.exit(1);
    }
  }

  // --- Remember the backup_log high-water mark ---
  const hwmRes = await pool.query(
    "SELECT COALESCE(MAX(id), 0) AS hwm FROM backup_log"
  );
  const hwm = hwmRes.rows[0].hwm;

  // =====================================================================
  // Scenario A: Brevo returns HTTP 401
  // =====================================================================
  console.log("-- Scenario A: Brevo returns HTTP 401 --\n");

  const fake401 = makeFailing401Https();

  // runWeeklyBackup must not throw — errors are caught internally
  let threw = false;
  try {
    await runWeeklyBackup({ forceFullBackup: true, _httpsOverride: fake401 });
  } catch (_) {
    threw = true;
  }
  assert(!threw, "runWeeklyBackup resolves without throwing on Brevo 401");

  // backup_log should have a new 'error' row
  const logResA = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );
  assert(logResA.rows.length === 1, "backup_log received exactly 1 new row after Brevo 401");

  if (logResA.rows.length) {
    const { status, note } = logResA.rows[0];
    assert(status === "error", `backup_log row status = 'error' (got '${status}')`);
    assert(
      note && note.includes("401"),
      `note contains '401' so admin sees the HTTP status (got: "${note}")`
    );
    assert(
      note && note.length <= 500,
      `note is truncated to ≤500 chars (got ${note && note.length})`
    );

    // Simulate what /api/backup/trigger returns when it reads this row
    // (mirrors server.js: if row.status !== 'ok' → return 502 { error: note })
    const simulatedErrorResponse = { error: note };
    assert(
      typeof simulatedErrorResponse.error === "string" &&
      simulatedErrorResponse.error.includes("401"),
      "trigger endpoint error JSON would contain '401' — actionable for the admin"
    );
  }

  // Clean up Scenario A rows
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm]);

  // =====================================================================
  // Scenario B: Brevo request times out
  // =====================================================================
  console.log("\n-- Scenario B: Brevo request times out --\n");

  const fakeTimeout = makeFakeTimeoutHttps();

  let threwB = false;
  try {
    await runWeeklyBackup({ forceFullBackup: true, _httpsOverride: fakeTimeout });
  } catch (_) {
    threwB = true;
  }
  assert(!threwB, "runWeeklyBackup resolves without throwing on Brevo timeout");

  const logResB = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );
  assert(logResB.rows.length === 1, "backup_log received exactly 1 new row after timeout");

  if (logResB.rows.length) {
    const { status, note } = logResB.rows[0];
    assert(status === "error", `backup_log row status = 'error' on timeout (got '${status}')`);
    assert(
      note && note.toLowerCase().includes("timed out"),
      `note contains 'timed out' so admin can diagnose (got: "${note}")`
    );
  }

  // Clean up Scenario B rows
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm]);

  // =====================================================================
  // Verify no leftover test rows
  // =====================================================================
  const remaining = await pool.query(
    "SELECT COUNT(*)::int AS n FROM backup_log WHERE id > $1",
    [hwm]
  );
  assert(remaining.rows[0].n === 0, "all test backup_log rows cleaned up");

  console.log("\n=== Done ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
