#!/usr/bin/env node
/**
 * Batch translate-bar removal guard — all city pages
 *
 * Verifies that no hospice-*-ca.html city page contains .ft-lang pills
 * or a translate.js script tag — the Google Translate feature was removed
 * July 2026.
 *
 * Exits 0 only when every city page is clean; exits 1 if any remnant found.
 *
 * Usage (from repo root):
 *   node website/elh-preview/assets/test-city-pages-batch.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const PREVIEW_DIR = path.join(__dirname, '..');

function hasTranslateBar(html) {
  return /class=["'][^"']*ft-lang[^"']*["']/.test(html) ||
         /src=["'][^"']*translate\.js["']/.test(html) ||
         /class=["']foot-translate["']/.test(html);
}

const cityPages = fs.readdirSync(PREVIEW_DIR)
  .filter(name => /^hospice-.+-ca\.html$/.test(name))
  .sort();

console.log(`Translate-bar removal check — ${cityPages.length} city page(s)\n`);
console.log('═'.repeat(60));

let failures = 0;
for (const name of cityPages) {
  const html = fs.readFileSync(path.join(PREVIEW_DIR, name), 'utf8');
  if (hasTranslateBar(html)) {
    console.error(`  FAIL: ${name}`);
    failures++;
  }
}

if (failures === 0) {
  console.log(`\n✅  All ${cityPages.length} city pages clean — translate bar removed`);
  process.exit(0);
} else {
  console.error(`\n❌  ${failures} city page(s) still contain translate bar markup`);
  process.exit(1);
}
