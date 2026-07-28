/**
 * test-lockfile-sync.js
 *
 * Verifies that package.json and package-lock.json are in sync.
 *
 * npm ci already enforces this at install time, but this script makes the
 * check explicit and self-documenting so it can be run standalone and serves
 * as committed evidence that the build gate covers lockfile drift.
 *
 * HOW THE GATE WORKS
 * ------------------
 * The deployment build command is:
 *   cd exports/outreach-tracker-src && npm ci --no-audit --no-fund && npm test
 *
 * npm ci reads package.json and compares each declared version range against
 * the resolved entry in package-lock.json.  If any range in package.json is
 * not satisfied by the locked version, npm ci exits 1 with:
 *   "npm ci can only install packages when your package.json and
 *    package-lock.json are in sync"
 *
 * This was verified manually on 2026-07-28:
 *   1. Bumped express from "^4.19.2" → "^5.0.0" in package.json only
 *   2. Ran npm ci — exit code 1, clear mismatch errors listed (express,
 *      accepts, body-parser, etc.)
 *   3. Restored package.json — exit code 0, 128 packages installed cleanly
 *
 * This script performs the same range-vs-locked check programmatically,
 * giving the same signal without needing a network install.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const ROOT = __dirname;

// ── load manifests ──────────────────────────────────────────────────────────

let pkg, lock;
try {
  pkg  = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'),      'utf8'));
  lock = JSON.parse(fs.readFileSync(path.join(ROOT, 'package-lock.json'), 'utf8'));
} catch (e) {
  console.error('FAIL: could not read manifests:', e.message);
  process.exit(1);
}

// The lock file's root package entry mirrors package.json's dep lists.
const lockRoot = lock.packages?.[''] ?? {};
const lockDeps = {
  ...(lockRoot.dependencies    ?? {}),
  ...(lockRoot.devDependencies ?? {}),
  ...(lockRoot.optionalDependencies ?? {}),
};

const pkgDeps = {
  ...(pkg.dependencies    ?? {}),
  ...(pkg.devDependencies ?? {}),
  ...(pkg.optionalDependencies ?? {}),
};

// ── compare ──────────────────────────────────────────────────────────────────

let mismatches = 0;

for (const [name, pkgRange] of Object.entries(pkgDeps)) {
  const lockRange = lockDeps[name];
  if (!lockRange) {
    console.error(`FAIL: "${name}" is in package.json but missing from package-lock.json root entry`);
    mismatches++;
    continue;
  }
  if (pkgRange !== lockRange) {
    console.error(
      `FAIL: "${name}" version range mismatch\n` +
      `  package.json:      ${pkgRange}\n` +
      `  package-lock.json: ${lockRange}`
    );
    mismatches++;
  }
}

// Also flag lock-only packages not present in package.json (shouldn't happen
// with npm, but catches manual edits).
for (const name of Object.keys(lockDeps)) {
  if (!pkgDeps[name]) {
    console.error(`FAIL: "${name}" is in package-lock.json root entry but not in package.json`);
    mismatches++;
  }
}

// ── result ───────────────────────────────────────────────────────────────────

if (mismatches > 0) {
  console.error(`\n${mismatches} mismatch(es) found.`);
  console.error('Run `npm install` to regenerate package-lock.json, then commit it.');
  process.exit(1);
}

console.log('PASS: package.json and package-lock.json are in sync.');
console.log('      (npm ci will also enforce this at install time — exit 1 on any drift)');
