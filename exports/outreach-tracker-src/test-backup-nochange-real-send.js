/**
 * test-backup-nochange-real-send.js
 *
 * One-time deliverability verification for the no-change incremental backup.
 *
 * What it does:
 *   1. Seeds a backup_log row at NOW() — so every visit in the DB is "old"
 *      (updated_at <= NOW()) and the incremental query returns 0 rows.
 *   2. Calls runWeeklyBackup({ forceFullBackup: false }) WITHOUT the fake-https
 *      override so the email goes through Brevo for real.
 *   3. Confirms Brevo accepted the send (backup_log status='ok', note reports
 *      "Incremental backup: 0 record(s)").
 *   4. Cleans up the seeded log row.
 *
 * The recipient (BACKUP_EMAIL) should check their inbox for:
 *   - Subject: "ELH Field Log Incremental Backup — YYYY-MM-DD"
 *   - Attachment: ELH_Field_Log_Incremental_Backup_YYYY-MM-DD.csv
 *     containing only the header row (no data rows).
 *
 * Usage:
 *   DATABASE_URL=... BACKUP_EMAIL=... BREVO_API=... node test-backup-nochange-real-send.js
 *
 * ⚠️  Brevo IP allowlist:
 *   Brevo rejects requests from unrecognised IP addresses with HTTP 401.
 *   Run this script from a machine (or the deployed server) whose outbound IP
 *   is already added under Brevo → My Account → Security → Authorized IPs.
 *   If you see "unrecognised IP address", add the egress IP and rerun.
 *
 * Exit codes: 0 = Brevo accepted the send, 1 = failure.
 */

"use strict";

const { Pool } = require("pg");

if (!process.env.DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set.");
  process.exit(1);
}
if (!process.env.BACKUP_EMAIL) {
  console.error("ERROR: BACKUP_EMAIL is not set.");
  process.exit(1);
}
if (!process.env.BREVO_API) {
  console.error("ERROR: BREVO_API is not set — real send requires a valid Brevo API key.");
  process.exit(1);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

const { runWeeklyBackup } = require("./backup");

async function run() {
  console.log("=== no-change incremental backup — REAL SEND verification ===\n");
  console.log(`  BACKUP_EMAIL : ${process.env.BACKUP_EMAIL}`);
  console.log(`  DATABASE_URL : ${process.env.DATABASE_URL.replace(/:([^@]+)@/, ':***@')}\n`);

  // Seed a successful backup_log row at NOW().
  // All existing visits have updated_at <= NOW(), so the incremental query
  // (updated_at > lastSuccessfulAt) will return 0 rows → header-only CSV.
  const seedRes = await pool.query(
    `INSERT INTO backup_log (ran_at, status, note)
     VALUES (NOW(), 'ok', 'Seeded by no-change real-send test — safe to delete')
     RETURNING id`
  );
  const seededLogId = seedRes.rows[0].id;
  console.log(`  Seeded backup_log row id=${seededLogId} at NOW() — incremental query will return 0 rows.\n`);

  // Real send — no _httpsOverride, so backup.js calls api.brevo.com directly.
  console.log("  Calling runWeeklyBackup (real Brevo send) ...");
  await runWeeklyBackup({ forceFullBackup: false });

  // Check backup_log for the result row.
  const logRes = await pool.query(
    `SELECT status, note FROM backup_log WHERE id > $1 ORDER BY id DESC LIMIT 1`,
    [hwm]
  );

  assert(logRes.rows.length >= 1, "backup_log received at least 1 new row after the real send");

  if (logRes.rows.length) {
    const { status, note } = logRes.rows[0];
    assert(
      status === "ok",
      `backup_log status = 'ok' — Brevo accepted the send (got '${status}')`
    );
    assert(
      note && note.startsWith("Incremental backup"),
      `backup_log note starts with "Incremental backup" (got: "${note}")`
    );

    const match = note && note.match(/^Incremental backup:\s+(\d+)\s+record/);
    assert(match !== null, `backup_log note contains a record count (got: "${note}")`);
    if (match) {
      assert(
        parseInt(match[1], 10) === 0,
        `backup_log note reports 0 changed records — CSV is header-only (got ${match[1]})`
      );
    }

    if (status === "ok") {
      console.log(`\n  >>> Email sent to ${process.env.BACKUP_EMAIL}.`);
      console.log("  >>> Check the inbox for subject:");
      console.log(`      "ELH Field Log Incremental Backup — ${new Date().toISOString().slice(0, 10)}"`);
      console.log("  >>> The CSV attachment should contain only the header row (no data rows).\n");
    } else {
      console.log(`\n  Note: ${note}\n`);
    }
  }

  // Cleanup: remove only the rows this script inserted (seeded row + result row
  // from runWeeklyBackup). Using specific IDs avoids deleting any legitimate
  // backup_log rows that another process may have written concurrently.
  const resultRes = await pool.query(
    `SELECT id FROM backup_log WHERE id > $1 ORDER BY id DESC`,
    [seededLogId]
  );
  const resultIds = resultRes.rows.map(r => r.id);
  const allIds = [seededLogId, ...resultIds];

  await pool.query(
    `DELETE FROM backup_log WHERE id = ANY($1::int[])`,
    [allIds]
  );

  const cleanL = await pool.query(
    `SELECT COUNT(*)::int AS n FROM backup_log WHERE id = ANY($1::int[])`,
    [allIds]
  );
  assert(cleanL.rows[0].n === 0, "seeded/result backup_log rows cleaned up by specific IDs");

  console.log("\n=== Done (no-change real-send verification) ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
