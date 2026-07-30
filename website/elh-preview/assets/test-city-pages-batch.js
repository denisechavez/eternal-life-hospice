#!/usr/bin/env node
/**
 * Batch translate-bar guard — all city pages
 *
 * Runs test-city-page-translate.js on every hospice-*-ca.html file under
 * website/elh-preview/.  Exits 0 only when every page passes; exits 1 as
 * soon as any page fails so the deploy is blocked.
 *
 * Usage (from repo root):
 *   node website/elh-preview/assets/test-city-pages-batch.js
 *
 * This script is registered as the "translate-bar-city-pages" validation step
 * and is the automated counterpart to the per-file pre-commit guard (step 7 in
 * the elh-city-pages skill).
 */

'use strict';

const fs           = require('fs');
const path         = require('path');
const { execFileSync } = require('child_process');

const PREVIEW_DIR  = path.join(__dirname, '..');
const GUARD_SCRIPT = path.join(__dirname, 'test-city-page-translate.js');

// ── collect all hospice-*-ca.html files ───────────────────────────────────────

const cityPages = fs.readdirSync(PREVIEW_DIR)
  .filter(name => /^hospice-.+-ca\.html$/.test(name))
  .sort()
  .map(name => path.join(PREVIEW_DIR, name));

if (cityPages.length === 0) {
  console.error('No hospice-*-ca.html files found under', PREVIEW_DIR);
  process.exit(1);
}

console.log(`\nTranslate-bar batch check — ${cityPages.length} city page(s)\n`);

// ── run the per-file guard on each page ───────────────────────────────────────

const failed = [];

for (const filePath of cityPages) {
  try {
    execFileSync(process.execPath, [GUARD_SCRIPT, filePath], {
      stdio: 'pipe',   // suppress per-file output on success
    });
  } catch (err) {
    // Guard exited non-zero — print its output and record the failure
    const stdout = err.stdout ? err.stdout.toString() : '';
    const stderr = err.stderr ? err.stderr.toString() : '';
    console.error(`\n── FAIL: ${path.basename(filePath)}`);
    if (stdout) process.stdout.write(stdout);
    if (stderr) process.stderr.write(stderr);
    failed.push(path.basename(filePath));
  }
}

// ── summary ───────────────────────────────────────────────────────────────────

console.log('\n' + '═'.repeat(60));

if (failed.length === 0) {
  console.log(`✅  All ${cityPages.length} city pages passed the translate-bar check`);
  process.exit(0);
} else {
  console.error(`❌  ${failed.length} of ${cityPages.length} city page(s) failed:`);
  for (const name of failed) {
    console.error(`     ${name}`);
  }
  console.error('\n    Fix each page before deploying.');
  console.error('    Copy the foot-translate block from any passing city page');
  console.error('    and add <script defer src="/assets/translate.js"></script> before </body>.');
  process.exit(1);
}
