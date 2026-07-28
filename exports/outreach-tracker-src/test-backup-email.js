/**
 * test-backup-email.js
 *
 * Integration test for the on-demand full-backup flow.
 *
 * What it verifies:
 *   1. runWeeklyBackup({ forceFullBackup: true }) completes without error.
 *   2. backup_log receives a new row with status='ok' and note starting with
 *      "On-demand full backup".
 *   3. The Brevo request carries a well-formed CSV attachment:
 *        a. Header row contains all 19 expected column names in the right order.
 *        b. Data-row count equals the total visits in the DB at run time.
 *        c. The attachment content round-trips cleanly through base64.
 *   4. The Brevo request is addressed to BACKUP_EMAIL.
 *
 * The test never sends real email — it substitutes a fake https module that
 * returns HTTP 201 and captures the outbound request body.
 *
 * Usage:
 *   DATABASE_URL=postgres://... BACKUP_EMAIL=test@example.com BREVO_API=fake \
 *     node test-backup-email.js
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
    "SKIP: BACKUP_EMAIL is not set — backup email test skipped.\n" +
    "      Set BACKUP_EMAIL (and BREVO_API) to run the full integration test."
  );
  process.exit(0);
}
if (!process.env.BREVO_API) {
  // Allow any non-empty value — the fake https module never validates it.
  console.warn(
    "SKIP: BREVO_API is not set — backup email test skipped.\n" +
    "      Set BREVO_API (any non-empty value works; real sends are intercepted) to run."
  );
  process.exit(0);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Override the module-level pool used by backup.js's db.js require.
// backup.js calls require("./db") which returns a singleton pool from db.js.
// We don't re-pool here; we just reuse the same DATABASE_URL via the env.

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

// ---- fake https module ----
// Returns a mock that:
//   • accepts https.request(options, callback)
//   • calls callback with a fake IncomingMessage (statusCode 201)
//   • captures everything written via req.write() into capturedBody
//   • exposes capturedOptions (the request options object)
function makeFakeHttps() {
  let capturedBody = "";
  let capturedOptions = null;

  const fakeHttps = {
    request(options, callback) {
      capturedOptions = options;

      // Build a fake response that fires the 'end' event synchronously
      // after the test calls req.end().
      const fakeRes = new EventEmitter();
      fakeRes.statusCode = 201;

      const fakeReq = new EventEmitter();
      fakeReq.setTimeout = () => {};
      fakeReq.destroy = (err) => fakeReq.emit("error", err);
      fakeReq.write = (chunk) => { capturedBody += chunk; };
      fakeReq.end = () => {
        // Simulate async response
        setImmediate(() => {
          callback(fakeRes);
          setImmediate(() => fakeRes.emit("end"));
        });
      };
      return fakeReq;
    },

    get captured() {
      return {
        options: capturedOptions,
        body: capturedBody,
        parsed: capturedBody ? JSON.parse(capturedBody) : null,
      };
    },
  };

  return fakeHttps;
}

// ---- test ----
async function run() {
  console.log("=== on-demand backup email integration test ===\n");

  const SENTINEL = "test-backup-email-script";

  // Ensure tables exist (mirrors schema.sql)
  await pool.query(`
    CREATE TABLE IF NOT EXISTS visits (
      id              SERIAL PRIMARY KEY,
      company         TEXT NOT NULL,
      category        TEXT,
      address         TEXT,
      city            TEXT,
      county          TEXT,
      visit_date      DATE,
      contact_name    TEXT,
      contact_title   TEXT,
      contact_email   TEXT,
      contact_phone   TEXT,
      materials       JSONB DEFAULT '[]',
      notes           TEXT,
      owner           TEXT,
      follow_up_due   DATE,
      followup_status TEXT DEFAULT 'Not started',
      attested        BOOLEAN DEFAULT FALSE,
      created_by      INTEGER,
      created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS backup_log (
      id     SERIAL PRIMARY KEY,
      ran_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      status TEXT        NOT NULL,
      note   TEXT
    )
  `);

  // --- Count existing visits so we know what a full backup should include ---
  const beforeCount = await pool.query("SELECT COUNT(*)::int AS n FROM visits");
  const existingVisitCount = beforeCount.rows[0].n;

  // --- Insert 2 sentinel visits ---
  await pool.query(
    `INSERT INTO visits (company, attested, notes) VALUES
       ($1, true, 'sentinel-A'),
       ($1, true, 'sentinel-B')`,
    [SENTINEL]
  );
  const expectedRowCount = existingVisitCount + 2;

  // --- Remember the backup_log high-water mark so we can isolate our new row ---
  const hwmRes = await pool.query(
    "SELECT COALESCE(MAX(id), 0) AS hwm FROM backup_log"
  );
  const hwm = hwmRes.rows[0].hwm;

  // --- Run the backup with a fake https module ---
  const fakeHttps = makeFakeHttps();
  await runWeeklyBackup({ forceFullBackup: true, _httpsOverride: fakeHttps });

  // ---- 1. backup_log row ----
  const logRes = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );
  assert(logRes.rows.length === 1, "backup_log received exactly 1 new row");
  if (logRes.rows.length) {
    const { status, note } = logRes.rows[0];
    assert(status === "ok", `backup_log row status = 'ok' (got '${status}')`);
    assert(
      note && note.startsWith("On-demand full backup"),
      `backup_log note starts with "On-demand full backup" (got: "${note}")`
    );
  }

  // ---- 2. Brevo request was made ----
  const { options, parsed } = fakeHttps.captured;
  assert(options !== null, "Brevo https.request was called");
  assert(
    options && options.hostname === "api.brevo.com",
    `Brevo hostname is api.brevo.com (got '${options && options.hostname}')`
  );

  if (parsed) {
    // ---- 3. Recipient ----
    const toEmail =
      parsed.to && parsed.to[0] && parsed.to[0].email;
    assert(
      toEmail === process.env.BACKUP_EMAIL,
      `Email addressed to BACKUP_EMAIL (${process.env.BACKUP_EMAIL}) — got '${toEmail}'`
    );

    // ---- 4. Attachment present ----
    const attachments = parsed.attachment || [];
    assert(attachments.length === 1, `1 attachment present (got ${attachments.length})`);

    if (attachments.length) {
      const att = attachments[0];

      // ---- 5. Filename contains 'Full' ----
      assert(
        att.name && att.name.includes("Full"),
        `attachment filename contains 'Full' (got '${att.name}')`
      );

      // ---- 6. Decode CSV ----
      let csv = "";
      try {
        csv = Buffer.from(att.content, "base64").toString("utf8");
      } catch (_) {}
      assert(csv.length > 0, "attachment content decodes from base64 to non-empty string");

      const lines = csv.split(/\r?\n/).filter(Boolean);
      const headerLine = lines[0] || "";

      // ---- 7. Header columns (order matters) ----
      const EXPECTED_FIELDS = [
        "id", "company", "category", "address", "city", "county", "visit_date",
        "contact_name", "contact_title", "contact_email", "contact_phone",
        "materials", "notes", "owner", "follow_up_due", "followup_status",
        "attested", "created_at", "updated_at",
      ];
      const headerCols = headerLine.split(",");
      assert(
        headerCols.length === EXPECTED_FIELDS.length,
        `CSV header has ${EXPECTED_FIELDS.length} columns (got ${headerCols.length})`
      );
      EXPECTED_FIELDS.forEach((col, i) => {
        assert(
          headerCols[i] === col,
          `CSV column[${i}] = '${col}' (got '${headerCols[i]}')`
        );
      });

      // ---- 8. Data row count matches DB ----
      const dataRowCount = lines.length - 1; // subtract header
      assert(
        dataRowCount === expectedRowCount,
        `CSV data rows = total visits in DB (${expectedRowCount}), got ${dataRowCount}`
      );

      // ---- 9. Sentinel rows are in the CSV ----
      const csvBody = lines.slice(1).join("\n");
      assert(
        csvBody.includes(SENTINEL),
        "sentinel company name appears in CSV data rows"
      );
    }
  }

  // --- Cleanup: remove sentinel visits and the backup_log row we created ---
  await pool.query("DELETE FROM visits WHERE company = $1", [SENTINEL]);
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm]);

  const cleanV = await pool.query(
    "SELECT COUNT(*)::int AS n FROM visits WHERE company = $1",
    [SENTINEL]
  );
  assert(cleanV.rows[0].n === 0, "sentinel visits cleaned up");

  const cleanL = await pool.query(
    "SELECT COUNT(*)::int AS n FROM backup_log WHERE id > $1",
    [hwm]
  );
  assert(cleanL.rows[0].n === 0, "test backup_log rows cleaned up");

  console.log("\n=== Done ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
