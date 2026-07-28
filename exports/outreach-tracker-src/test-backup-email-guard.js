/**
 * test-backup-email-guard.js
 *
 * Verifies that running test-backup-email.js WITHOUT BACKUP_EMAIL set
 * exits with a non-zero code and prints an "ERROR:" line to stderr/stdout —
 * i.e. the guard fails loudly rather than silently skipping.
 *
 * This test requires DATABASE_URL to be set (so the BACKUP_EMAIL guard is
 * reached), but deliberately omits BACKUP_EMAIL.
 *
 * Exit codes: 0 = guard behaves correctly, 1 = a failure occurred.
 */

"use strict";

const { spawnSync } = require("child_process");
const path = require("path");

// ---- assertion helper ----
let failures = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

console.log("=== BACKUP_EMAIL absence guard test ===\n");

if (!process.env.DATABASE_URL) {
  console.error(
    "ERROR: DATABASE_URL is not set — this guard test needs it to reach the BACKUP_EMAIL check.\n" +
    "       Set DATABASE_URL and re-run."
  );
  process.exit(1);
}

// Build a clean env that has DATABASE_URL but NOT BACKUP_EMAIL or BREVO_API,
// to confirm the BACKUP_EMAIL check fires (it comes before BREVO_API).
const guardEnv = Object.assign({}, process.env);
delete guardEnv.BACKUP_EMAIL;
delete guardEnv.BREVO_API;

const scriptPath = path.join(__dirname, "test-backup-email.js");

const result = spawnSync(process.execPath, [scriptPath], {
  env: guardEnv,
  encoding: "utf8",
  timeout: 15000,
});

const combinedOutput = (result.stdout || "") + (result.stderr || "");

// 1. Must exit non-zero
assert(
  result.status !== 0,
  `test-backup-email.js exits non-zero when BACKUP_EMAIL is absent (got exit code ${result.status})`
);

// 2. Output must contain "ERROR:" — not "SKIP:" or silence
assert(
  combinedOutput.includes("ERROR:"),
  `output contains "ERROR:" (got: ${JSON.stringify(combinedOutput.slice(0, 300))})`
);

// 3. Output must NOT contain "SKIP:" (we want loud failure, not silent skip)
assert(
  !combinedOutput.includes("SKIP:"),
  `output does NOT contain "SKIP:" — failure is visible, not silently skipped`
);

// 4. The error message should mention BACKUP_EMAIL so the cause is obvious
assert(
  combinedOutput.includes("BACKUP_EMAIL"),
  `error message mentions "BACKUP_EMAIL" so the cause is unambiguous`
);

console.log("\n=== Done (BACKUP_EMAIL guard test) ===");
process.exit(failures > 0 ? 1 : 0);
