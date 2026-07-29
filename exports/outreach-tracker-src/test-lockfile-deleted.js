/**
 * test-lockfile-deleted.js
 *
 * Regression proof: the deployment build gate (npm ci) must exit non-zero with
 * a clear error when package-lock.json is absent entirely — not silently pass
 * or fall back to a loose install.
 *
 * HOW THE GATE WORKS
 * ------------------
 * The deployment build command is:
 *   cd exports/outreach-tracker-src && npm ci --no-audit --no-fund && npm test
 *
 * npm ci requires package-lock.json to be present.  If it is missing, npm ci
 * exits 1 with a message such as:
 *   "npm ci can only install packages with an existing package-lock.json"
 *
 * WHAT THIS TEST DOES
 * -------------------
 * 1. Rename package-lock.json → package-lock.json.bak (simulate deletion).
 * 2. Run `npm ci --no-audit --no-fund` as a child process.
 * 3. Assert: exit code is non-zero AND output contains a clear error phrase.
 * 4. Restore package-lock.json.bak → package-lock.json.
 * 5. Run `npm ci --no-audit --no-fund` again.
 * 6. Assert: exit code is 0 (normal install succeeds once the file is back).
 *
 * A try/finally block guarantees the lock file is always restored even if the
 * assertions throw.
 *
 * Exit codes: 0 = gate behaves correctly, 1 = a failure occurred.
 */

'use strict';

const { spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');

const ROOT     = __dirname;
const LOCKFILE = path.join(ROOT, 'package-lock.json');
const LOCKBAK  = path.join(ROOT, 'package-lock.json.bak');

let failures = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

function runNpmCi() {
  return spawnSync(
    'npm',
    ['ci', '--no-audit', '--no-fund'],
    {
      cwd:      ROOT,
      env:      process.env,
      encoding: 'utf8',
      timeout:  120_000,
    }
  );
}

console.log('=== package-lock.json deleted — build gate test ===\n');

// Sanity-check: lock file must exist before we start.
if (!fs.existsSync(LOCKFILE)) {
  console.error(
    'ERROR: package-lock.json does not exist in exports/outreach-tracker-src/.\n' +
    '       Run `npm install` to regenerate it, then commit it.'
  );
  process.exit(1);
}

// Also make sure there is no leftover .bak from a previous crashed run.
if (fs.existsSync(LOCKBAK)) {
  console.warn(
    'WARN: package-lock.json.bak already exists — removing stale backup before test.'
  );
  fs.unlinkSync(LOCKBAK);
}

// ── Phase 1: lock file absent → npm ci must fail ──────────────────────────

console.log('Phase 1: rename package-lock.json away and run npm ci …');
fs.renameSync(LOCKFILE, LOCKBAK);

let missingResult;
try {
  missingResult = runNpmCi();
} finally {
  // Always restore, even if spawnSync throws.
  if (!fs.existsSync(LOCKFILE) && fs.existsSync(LOCKBAK)) {
    fs.renameSync(LOCKBAK, LOCKFILE);
  }
}

const missingOutput = (missingResult.stdout || '') + (missingResult.stderr || '');

assert(
  missingResult.status !== 0,
  `npm ci exits non-zero when package-lock.json is absent (got exit code ${missingResult.status})`
);

// npm ci prints variants of this message across npm versions:
//   "can only install packages with an existing package-lock.json"
//   "requires a lockfile"
//   "package-lock.json"   ← minimum: the filename must appear
const errorPhrases = [
  'package-lock.json',
  'lockfile',
];
const mentionsLockFile = errorPhrases.some(p =>
  missingOutput.toLowerCase().includes(p.toLowerCase())
);
assert(
  mentionsLockFile,
  `npm ci error output mentions lockfile (got: ${JSON.stringify(missingOutput.slice(0, 400))})`
);

// ── Phase 2: lock file restored → npm ci must succeed ────────────────────

console.log('\nPhase 2: package-lock.json restored — run npm ci again …');

const restoredResult = runNpmCi();

assert(
  restoredResult.status === 0,
  `npm ci exits 0 after package-lock.json is restored (got exit code ${restoredResult.status})`
);

// ── Result ────────────────────────────────────────────────────────────────

console.log('\n=== Done ===');
if (failures > 0) {
  process.exit(1);
}
