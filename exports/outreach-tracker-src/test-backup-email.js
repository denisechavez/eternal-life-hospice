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
  console.error(
    "ERROR: BACKUP_EMAIL is not set — backup email test cannot run.\n" +
    "       Set BACKUP_EMAIL (and BREVO_API) to run the full integration test."
  );
  process.exit(1);
}
if (!process.env.BREVO_API) {
  // Allow any non-empty value — the fake https module never validates it.
  console.error(
    "ERROR: BREVO_API is not set — backup email test cannot run.\n" +
    "       Set BREVO_API (any non-empty value works; real sends are intercepted) to run."
  );
  process.exit(1);
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

  console.log("\n=== Done (full-backup test) ===");
}

// ---------------------------------------------------------------------------
// Incremental backup test
//
// Verifies that a normal (non-forced) runWeeklyBackup:
//   • includes only records whose updated_at is AFTER the last successful run
//   • excludes records that have not changed since then
//   • writes a backup_log row whose note starts with "Incremental backup"
//     and shows the correct record count
// ---------------------------------------------------------------------------
async function runIncrementalTest() {
  console.log("\n=== incremental backup integration test ===\n");

  const SENTINEL_PRE = "test-backup-incr-pre";   // unmodified record — must NOT appear
  const SENTINEL_NEW = "test-backup-incr-new";   // record changed after last backup — MUST appear

  // High-water mark so cleanup is surgical
  const hwmRes = await pool.query(
    "SELECT COALESCE(MAX(id), 0) AS hwm FROM backup_log"
  );
  const hwm = hwmRes.rows[0].hwm;

  // 1. Insert the "old" sentinel visit, then push its updated_at 2 hours into
  //    the past so it predates the simulated last successful backup.
  await pool.query(
    `INSERT INTO visits (company, attested, notes) VALUES ($1, false, 'incr-sentinel-pre')`,
    [SENTINEL_PRE]
  );
  await pool.query(
    `UPDATE visits SET updated_at = NOW() - INTERVAL '2 hours'
     WHERE company = $1`,
    [SENTINEL_PRE]
  );

  // 2. Seed a successful backup_log row dated 1 hour ago.  This becomes
  //    lastSuccessfulAt for the incremental query (updated_at > lastSuccessfulAt).
  await pool.query(
    `INSERT INTO backup_log (ran_at, status, note)
     VALUES (NOW() - INTERVAL '1 hour', 'ok',
             'Seeded by incremental test — safe to delete')`,
  );

  // 3. Insert the "new" sentinel visit.  Its updated_at = NOW(), which is
  //    after the seeded backup, so the incremental query must pick it up.
  await pool.query(
    `INSERT INTO visits (company, attested, notes) VALUES ($1, false, 'incr-sentinel-new')`,
    [SENTINEL_NEW]
  );

  // 4. Run the incremental backup (forceFullBackup defaults to false).
  const fakeHttps2 = makeFakeHttps();
  await runWeeklyBackup({ forceFullBackup: false, _httpsOverride: fakeHttps2 });

  // ---- A. backup_log row ----
  const logRes = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );
  assert(logRes.rows.length >= 1, "incremental: backup_log received at least 1 new row");
  if (logRes.rows.length) {
    const { status, note } = logRes.rows[0];
    assert(status === "ok", `incremental: backup_log row status = 'ok' (got '${status}')`);
    assert(
      note && note.startsWith("Incremental backup"),
      `incremental: backup_log note starts with "Incremental backup" (got: "${note}")`
    );
    // The note embeds the record count: "Incremental backup: N record(s) …"
    // Assert ≥ 1 rather than exactly 1: other records in a live DB may also
    // have been updated recently and will legitimately appear in the window.
    const match = note && note.match(/^Incremental backup:\s+(\d+)\s+record/);
    assert(
      match !== null,
      `incremental: backup_log note contains a record count (got: "${note}")`
    );
    if (match) {
      assert(
        parseInt(match[1], 10) >= 1,
        `incremental: backup_log note reports at least 1 changed record (got ${match[1]})`
      );
    }
  }

  // ---- B. Brevo request was made ----
  const { options: incrOpts, parsed: incrParsed } = fakeHttps2.captured;
  assert(incrOpts !== null, "incremental: Brevo https.request was called");

  if (incrParsed) {
    // ---- C. Filename contains 'Incremental' ----
    const attachments = incrParsed.attachment || [];
    assert(attachments.length === 1, `incremental: 1 attachment present (got ${attachments.length})`);

    if (attachments.length) {
      const att = attachments[0];
      assert(
        att.name && att.name.includes("Incremental"),
        `incremental: attachment filename contains 'Incremental' (got '${att.name}')`
      );

      // ---- D. Decode CSV and check row counts ----
      let csv = "";
      try { csv = Buffer.from(att.content, "base64").toString("utf8"); } catch (_) {}
      assert(csv.length > 0, "incremental: attachment decodes to non-empty string");

      const lines = csv.split(/\r?\n/).filter(Boolean);
      const dataRowCount = lines.length - 1; // subtract header
      // Assert ≥ 1 rather than exactly 1: other records updated within the
      // cutoff window in a live DB will also appear legitimately.
      assert(
        dataRowCount >= 1,
        `incremental: CSV contains at least 1 data row (got ${dataRowCount})`
      );

      // ---- E. Updated sentinel IS in the CSV ----
      const csvBody = lines.slice(1).join("\n");
      assert(
        csvBody.includes(SENTINEL_NEW),
        `incremental: updated sentinel ('${SENTINEL_NEW}') appears in CSV`
      );

      // ---- F. Unmodified sentinel is NOT in the CSV ----
      assert(
        !csvBody.includes(SENTINEL_PRE),
        `incremental: unmodified sentinel ('${SENTINEL_PRE}') does NOT appear in CSV`
      );
    }
  }

  // --- Cleanup ---
  await pool.query("DELETE FROM visits WHERE company = $1", [SENTINEL_PRE]);
  await pool.query("DELETE FROM visits WHERE company = $1", [SENTINEL_NEW]);
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm]);

  const cleanPre = await pool.query(
    "SELECT COUNT(*)::int AS n FROM visits WHERE company = $1", [SENTINEL_PRE]
  );
  assert(cleanPre.rows[0].n === 0, "incremental: SENTINEL_PRE visits cleaned up");

  const cleanNew = await pool.query(
    "SELECT COUNT(*)::int AS n FROM visits WHERE company = $1", [SENTINEL_NEW]
  );
  assert(cleanNew.rows[0].n === 0, "incremental: SENTINEL_NEW visits cleaned up");

  const cleanL = await pool.query(
    "SELECT COUNT(*)::int AS n FROM backup_log WHERE id > $1", [hwm]
  );
  assert(cleanL.rows[0].n === 0, "incremental: test backup_log rows cleaned up");

  console.log("\n=== Done (incremental backup test) ===");
}

// ---------------------------------------------------------------------------
// Incremental backup — no-change test
//
// Verifies that when nothing has changed since the last successful backup
// the backup still:
//   • sends an email (Brevo request is made)
//   • attaches a well-formed CSV that contains ONLY the header row (0 data rows)
//   • writes a backup_log note reporting "Incremental backup: 0 record(s)…"
// ---------------------------------------------------------------------------
async function runIncrementalNoChangeTest() {
  console.log("\n=== incremental backup — no-change test ===\n");

  // High-water mark so cleanup is surgical
  const hwmRes = await pool.query(
    "SELECT COALESCE(MAX(id), 0) AS hwm FROM backup_log"
  );
  const hwm = hwmRes.rows[0].hwm;

  // Seed a successful backup_log row at NOW().
  // All visits already in the DB have updated_at <= NOW(), so the incremental
  // query (updated_at > lastSuccessfulAt) will return 0 rows.
  await pool.query(
    `INSERT INTO backup_log (ran_at, status, note)
     VALUES (NOW(), 'ok',
             'Seeded by no-change incremental test — safe to delete')`
  );

  // Run the incremental backup — nothing has changed since NOW().
  const fakeHttps3 = makeFakeHttps();
  await runWeeklyBackup({ forceFullBackup: false, _httpsOverride: fakeHttps3 });

  // ---- A. backup_log row ----
  const logRes = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );
  assert(logRes.rows.length >= 1, "no-change: backup_log received at least 1 new row");
  if (logRes.rows.length) {
    const { status, note } = logRes.rows[0];
    assert(status === "ok", `no-change: backup_log row status = 'ok' (got '${status}')`);
    assert(
      note && note.startsWith("Incremental backup"),
      `no-change: backup_log note starts with "Incremental backup" (got: "${note}")`
    );
    const match = note && note.match(/^Incremental backup:\s+(\d+)\s+record/);
    assert(
      match !== null,
      `no-change: backup_log note contains a record count (got: "${note}")`
    );
    if (match) {
      assert(
        parseInt(match[1], 10) === 0,
        `no-change: backup_log note reports 0 changed records (got ${match[1]})`
      );
    }
  }

  // ---- B. Brevo request was still made ----
  const { options: noChangeOpts, parsed: noChangeParsed } = fakeHttps3.captured;
  assert(noChangeOpts !== null, "no-change: Brevo https.request was called");

  if (noChangeParsed) {
    // ---- C. Attachment present ----
    const attachments = noChangeParsed.attachment || [];
    assert(
      attachments.length === 1,
      `no-change: 1 attachment present (got ${attachments.length})`
    );

    if (attachments.length) {
      const att = attachments[0];

      // ---- D. Filename contains 'Incremental' ----
      assert(
        att.name && att.name.includes("Incremental"),
        `no-change: attachment filename contains 'Incremental' (got '${att.name}')`
      );

      // ---- E. Decode CSV — header only, 0 data rows ----
      let csv = "";
      try { csv = Buffer.from(att.content, "base64").toString("utf8"); } catch (_) {}
      assert(
        csv.length > 0,
        "no-change: attachment decodes to non-empty string (header row is present)"
      );

      const lines = csv.split(/\r?\n/).filter(Boolean);
      assert(lines.length >= 1, "no-change: CSV has at least the header row");

      const dataRowCount = lines.length - 1; // subtract header
      assert(
        dataRowCount === 0,
        `no-change: CSV contains exactly 0 data rows (got ${dataRowCount})`
      );

      // ---- F. Header is still well-formed ----
      const EXPECTED_FIELDS = [
        "id", "company", "category", "address", "city", "county", "visit_date",
        "contact_name", "contact_title", "contact_email", "contact_phone",
        "materials", "notes", "owner", "follow_up_due", "followup_status",
        "attested", "created_at", "updated_at",
      ];
      const headerCols = (lines[0] || "").split(",");
      assert(
        headerCols.length === EXPECTED_FIELDS.length,
        `no-change: CSV header has ${EXPECTED_FIELDS.length} columns (got ${headerCols.length})`
      );
      EXPECTED_FIELDS.forEach((col, i) => {
        assert(
          headerCols[i] === col,
          `no-change: CSV column[${i}] = '${col}' (got '${headerCols[i]}')`
        );
      });
    }
  }

  // --- Cleanup ---
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm]);

  const cleanL = await pool.query(
    "SELECT COUNT(*)::int AS n FROM backup_log WHERE id > $1", [hwm]
  );
  assert(cleanL.rows[0].n === 0, "no-change: test backup_log rows cleaned up");

  console.log("\n=== Done (incremental no-change test) ===");
}

// ---------------------------------------------------------------------------
// Boundary-timestamp test
//
// The incremental WHERE clause is:  updated_at > $1  (strict greater-than).
// A record whose updated_at equals the cutoff exactly is intentionally
// excluded — the assumption is that it was already captured by the backup
// that produced that ran_at timestamp.
//
// This test pins that contract so any future change to ">=" is caught.
// ---------------------------------------------------------------------------
async function runBoundaryTest() {
  console.log("\n=== incremental backup boundary-timestamp test ===\n");
  console.log(
    "  (Documents intentional behaviour: updated_at = ran_at is excluded by strict >)"
  );

  const SENTINEL_BOUNDARY = "test-backup-boundary";

  // High-water mark for surgical cleanup
  const hwmRes2 = await pool.query(
    "SELECT COALESCE(MAX(id), 0) AS hwm FROM backup_log"
  );
  const hwm2 = hwmRes2.rows[0].hwm;

  // 1. Seed a successful backup_log row 5 seconds in the future so it is
  //    guaranteed to be the latest 'ok' row regardless of any pre-existing
  //    rows in the database.  Capture its exact ran_at so we can align
  //    the sentinel visit's updated_at to the same microsecond.
  const logInsert = await pool.query(
    `INSERT INTO backup_log (ran_at, status, note)
     VALUES (NOW() + INTERVAL '5 seconds', 'ok',
             'Seeded by boundary test — safe to delete')
     RETURNING ran_at`
  );
  const cutoff = logInsert.rows[0].ran_at; // exact timestamp as JS Date

  // Verify this row is indeed the effective cutoff that runWeeklyBackup will use.
  const effectiveCutoffRes = await pool.query(
    `SELECT ran_at FROM backup_log WHERE status = 'ok' ORDER BY ran_at DESC LIMIT 1`
  );
  assert(
    effectiveCutoffRes.rows.length === 1 &&
      effectiveCutoffRes.rows[0].ran_at.getTime() === cutoff.getTime(),
    `boundary: seeded log row IS the effective cutoff (ran_at=${cutoff.toISOString()})`
  );

  // 2. Insert a sentinel visit and set its updated_at to the EXACT cutoff.
  //    With strict ">", this record must not appear in the incremental backup.
  await pool.query(
    `INSERT INTO visits (company, attested, notes) VALUES ($1, false, 'boundary-sentinel')`,
    [SENTINEL_BOUNDARY]
  );
  await pool.query(
    `UPDATE visits SET updated_at = $1 WHERE company = $2`,
    [cutoff, SENTINEL_BOUNDARY]
  );

  // Confirm the update took effect at the exact cutoff microsecond.
  const sentinelTsRes = await pool.query(
    `SELECT updated_at FROM visits WHERE company = $1`, [SENTINEL_BOUNDARY]
  );
  assert(
    sentinelTsRes.rows.length === 1 &&
      sentinelTsRes.rows[0].updated_at.getTime() === cutoff.getTime(),
    `boundary: sentinel updated_at = cutoff exactly (${cutoff.toISOString()})`
  );

  // 3. Run the incremental backup (no force-full).
  const fakeHttps4 = makeFakeHttps();
  await runWeeklyBackup({ forceFullBackup: false, _httpsOverride: fakeHttps4 });

  // ---- A. backup_log row produced ----
  const logRes2 = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm2]
  );
  assert(logRes2.rows.length >= 1, "boundary: backup_log received at least 1 new row");
  if (logRes2.rows.length) {
    const { status, note } = logRes2.rows[0];
    assert(status === "ok", `boundary: backup_log row status = 'ok' (got '${status}')`);
    assert(
      note && note.startsWith("Incremental backup"),
      `boundary: backup_log note starts with "Incremental backup" (got: "${note}")`
    );
  }

  // ---- B. Brevo request was made ----
  const { options: bndOpts, parsed: bndParsed } = fakeHttps4.captured;
  assert(bndOpts !== null, "boundary: Brevo https.request was called");

  if (bndParsed) {
    const attachments = bndParsed.attachment || [];
    assert(attachments.length === 1, `boundary: 1 attachment present (got ${attachments.length})`);

    if (attachments.length) {
      let csv = "";
      try { csv = Buffer.from(attachments[0].content, "base64").toString("utf8"); } catch (_) {}
      assert(csv.length > 0, "boundary: attachment decodes to non-empty string");

      const lines = csv.split(/\r?\n/).filter(Boolean);
      const csvBody = lines.slice(1).join("\n");

      // ---- C. Boundary record is NOT in the CSV (strict > intentional) ----
      assert(
        !csvBody.includes(SENTINEL_BOUNDARY),
        `boundary: record with updated_at = cutoff is excluded (strict > is intentional)`
      );
    }
  }

  // --- Cleanup ---
  await pool.query("DELETE FROM visits WHERE company = $1", [SENTINEL_BOUNDARY]);
  await pool.query("DELETE FROM backup_log WHERE id > $1", [hwm2]);

  const cleanV = await pool.query(
    "SELECT COUNT(*)::int AS n FROM visits WHERE company = $1", [SENTINEL_BOUNDARY]
  );
  assert(cleanV.rows[0].n === 0, "boundary: sentinel visit cleaned up");

  const cleanL2 = await pool.query(
    "SELECT COUNT(*)::int AS n FROM backup_log WHERE id > $1", [hwm2]
  );
  assert(cleanL2.rows[0].n === 0, "boundary: test backup_log rows cleaned up");

  console.log("\n=== Done (boundary-timestamp test) ===");
}

run()
  .then(() => runIncrementalTest())
  .then(() => runIncrementalNoChangeTest())
  .then(() => runBoundaryTest())
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
