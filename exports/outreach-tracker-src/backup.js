/**
 * backup.js
 *
 * Weekly / on-demand backup logic for the ELH Outreach Tracker.
 * Extracted from server.js so it can be unit-tested independently.
 *
 * Exports:
 *   runWeeklyBackup(opts?)  – opts.forceFullBackup (bool), opts._httpsOverride (module, tests only)
 *   scheduleNextBackup()    – schedules the next automated run
 *
 * Both functions share the module-level backupRunning guard and
 * nextBackupTimer handle so concurrent invocations are safe.
 */

"use strict";

const { query } = require("./db");

const BACKUP_INTERVAL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const BACKUP_RETRY_MS   = 60 * 60 * 1000;            // 1 h on failure
const BREVO_TIMEOUT_MS  = 30 * 1000;                 // 30 s HTTP timeout

let backupRunning = false;
let nextBackupTimer = null; // always cleared before a new timer is set

// opts.forceFullBackup  — when true, exports all records regardless of prior runs
//                         (used by the on-demand "Send full backup now" button).
// opts._httpsOverride   — inject a fake https module (tests only).
async function runWeeklyBackup({ forceFullBackup = false, _httpsOverride } = {}) {
  if (backupRunning) {
    console.log("Weekly backup: already running, skipping duplicate trigger.");
    return { busy: true };
  }
  backupRunning = true;
  const runLabel = forceFullBackup ? "On-demand full backup" : "Weekly backup";
  console.log(`${runLabel}: starting at`, new Date().toISOString());
  try {
    const to = process.env.BACKUP_EMAIL;
    if (!to) {
      console.warn(`${runLabel}: BACKUP_EMAIL not set.`);
      await query("INSERT INTO backup_log (status, note) VALUES ($1, $2)", [
        "error",
        "BACKUP_EMAIL environment variable is not set.",
      ]);
      return;
    }

    const brevoKey = process.env.BREVO_API;
    if (!brevoKey) {
      console.warn(`${runLabel}: BREVO_API not set.`);
      await query("INSERT INTO backup_log (status, note) VALUES ($1, $2)", [
        "error",
        "BREVO_API environment variable is not set.",
      ]);
      return;
    }

    // Determine the cutoff: timestamp of the last SUCCESSFUL backup.
    // No prior success OR forceFullBackup → full backup.
    const lastOkRes = await query(
      `SELECT ran_at FROM backup_log WHERE status = 'ok' ORDER BY ran_at DESC LIMIT 1`
    );
    const lastSuccessfulAt = lastOkRes.rows.length ? lastOkRes.rows[0].ran_at : null;
    const isFullBackup = forceFullBackup || !lastSuccessfulAt;

    // Fetch visits: all records on first run, only new/changed records thereafter.
    const visitQuery = isFullBackup
      ? `SELECT id, company, category, address, city, county, visit_date,
                contact_name, contact_title, contact_email, contact_phone,
                materials, notes, owner, follow_up_due, followup_status,
                attested, created_at, updated_at
         FROM visits ORDER BY created_at DESC`
      : `SELECT id, company, category, address, city, county, visit_date,
                contact_name, contact_title, contact_email, contact_phone,
                materials, notes, owner, follow_up_due, followup_status,
                attested, created_at, updated_at
         FROM visits WHERE updated_at > $1 ORDER BY updated_at DESC`;
    const visitParams = isFullBackup ? [] : [lastSuccessfulAt];
    const { rows: visits } = await query(visitQuery, visitParams);

    // Build CSV (always include header row even when visits is empty so the
    // recipient gets a well-formed file that confirms continuity).
    const fields = [
      "id", "company", "category", "address", "city", "county", "visit_date",
      "contact_name", "contact_title", "contact_email", "contact_phone",
      "materials", "notes", "owner", "follow_up_due", "followup_status",
      "attested", "created_at", "updated_at",
    ];
    const csvEsc = (v) => {
      if (v === null || v === undefined) return "";
      const s = Array.isArray(v) ? JSON.stringify(v) : String(v);
      return /[,"\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const csv = [
      fields.join(","),
      ...visits.map((r) => fields.map((f) => csvEsc(r[f])).join(",")),
    ].join("\r\n");

    const dateStr = new Date().toISOString().slice(0, 10);
    const backupKind = isFullBackup ? "Full" : "Incremental";
    const sinceStr = isFullBackup
      ? "all records"
      : `records updated since ${new Date(lastSuccessfulAt).toISOString().slice(0, 10)}`;
    const filename = `ELH_Field_Log_${backupKind}_Backup_${dateStr}.csv`;

    const noteText = isFullBackup
      ? `${forceFullBackup ? "On-demand full" : "Full"} backup: ${visits.length} record(s) emailed to ${to}`
      : `Incremental backup: ${visits.length} record(s) updated since ${new Date(lastSuccessfulAt).toISOString().slice(0, 10)}, emailed to ${to}`;

    // Send via Brevo transactional email API
    const payload = JSON.stringify({
      sender: { name: "ELH Outreach Tracker", email: "no-reply@eternallifehospice.com" },
      to: [{ email: to }],
      subject: `ELH Field Log ${backupKind} Backup — ${dateStr}`,
      textContent:
        `${backupKind} automated backup of the ELH Outreach Tracker field log.\n\n` +
        `Records included: ${visits.length} (${sinceStr})\nDate: ${dateStr}\n\n` +
        `The CSV file is attached.`,
      attachment: [
        { name: filename, content: Buffer.from(csv).toString("base64") },
      ],
    });

    const https = _httpsOverride || require("https");
    await new Promise((resolve, reject) => {
      const req = https.request(
        {
          hostname: "api.brevo.com",
          path: "/v3/smtp/email",
          method: "POST",
          headers: {
            "api-key": brevoKey,
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(payload),
          },
        },
        (res) => {
          let body = "";
          res.on("data", (c) => (body += c));
          res.on("end", () => {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve();
            } else {
              reject(new Error(`Brevo ${res.statusCode}: ${body.slice(0, 200)}`));
            }
          });
        }
      );
      req.setTimeout(BREVO_TIMEOUT_MS, () => {
        req.destroy(new Error(`Brevo request timed out after ${BREVO_TIMEOUT_MS / 1000} s`));
      });
      req.on("error", reject);
      req.write(payload);
      req.end();
    });

    await query("INSERT INTO backup_log (status, note) VALUES ($1, $2)", [
      "ok",
      noteText,
    ]);
    console.log(`Weekly backup: ${noteText}`);
  } catch (e) {
    const note = String((e && e.message) || "Unknown error").slice(0, 500);
    console.error("Weekly backup failed:", note);
    try {
      await query("INSERT INTO backup_log (status, note) VALUES ($1, $2)", [
        "error",
        note,
      ]);
    } catch (dbErr) {
      console.error("Weekly backup: could not write to backup_log:", dbErr);
    }
  } finally {
    backupRunning = false;
    scheduleNextBackup();
  }
}

// Reads the LATEST backup_log row (any status) to decide when to next fire:
//   - No rows yet        → fire immediately (first ever run)
//   - Last row = 'ok'    → fire in (7 days − elapsed); or immediately if overdue
//   - Last row = 'error' → fire in (BACKUP_RETRY_MS − elapsed); or immediately
//                          if the retry window has already passed
// This prevents the tight-loop where a failed run keeps rescheduling as
// "overdue" because only ok rows were checked.
function scheduleNextBackup() {
  // Defer DB check so it never blocks the startup path.
  setImmediate(async () => {
    try {
      const r = await query(
        `SELECT status, ran_at FROM backup_log ORDER BY ran_at DESC LIMIT 1`
      );
      const now = Date.now();

      if (!r.rows.length) {
        console.log("Weekly backup scheduler: no prior attempt, firing now.");
        runWeeklyBackup().catch((e) => console.error("Weekly backup unexpected error:", e));
        return;
      }

      const { status, ran_at } = r.rows[0];
      const elapsed = now - new Date(ran_at).getTime();
      const window = status === "ok" ? BACKUP_INTERVAL_MS : BACKUP_RETRY_MS;
      const delay  = Math.max(0, window - elapsed);

      if (delay === 0) {
        const reason = status === "ok"
          ? `overdue by ${Math.floor(elapsed / 3_600_000)} h`
          : `retry window elapsed`;
        console.log(`Weekly backup scheduler: ${reason}, firing now.`);
        runWeeklyBackup().catch((e) => console.error("Weekly backup unexpected error:", e));
      } else {
        const hh = Math.floor(delay / 3_600_000);
        const mm = Math.floor((delay % 3_600_000) / 60_000);
        console.log(
          `Weekly backup scheduler: next ${status === "ok" ? "run" : "retry"} in ${hh} h ${mm} min.`
        );
        if (nextBackupTimer) clearTimeout(nextBackupTimer);
        nextBackupTimer = setTimeout(
          () => runWeeklyBackup().catch((e) => console.error("Weekly backup unexpected error:", e)),
          delay
        );
        nextBackupTimer.unref();
      }
    } catch (e) {
      console.error("Weekly backup scheduler: DB check failed, retrying in 1 h:", e);
      setTimeout(scheduleNextBackup, BACKUP_RETRY_MS).unref();
    }
  });
}

module.exports = { runWeeklyBackup, scheduleNextBackup };
