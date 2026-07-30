#!/usr/bin/env node
/**
 * Smoke-test: translate bar REMOVED
 *
 * Verifies that no HTML page contains .ft-lang pills or translate.js —
 * the Google Translate feature was removed July 2026.
 *
 * Exits 0 when all pages are clean; exits 1 if any remnant is found.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const BASE      = path.join(__dirname, '..');
const SITE_DIR  = BASE;

function hasTranslateBar(html) {
  return /class=["'][^"']*ft-lang[^"']*["']/.test(html) ||
         /src=["'][^"']*translate\.js["']/.test(html) ||
         /class=["']foot-translate["']/.test(html);
}

function collectHtmlFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // skip social/internal previews
      if (['assets', 'node_modules'].includes(entry.name)) continue;
      results.push(...collectHtmlFiles(full));
    } else if (entry.name.endsWith('.html')) {
      results.push(full);
    }
  }
  return results;
}

const pages = collectHtmlFiles(SITE_DIR);
let failures = 0;

console.log(`Checking ${pages.length} pages for translate bar remnants...\n`);

for (const p of pages) {
  const html = fs.readFileSync(p, 'utf8');
  if (hasTranslateBar(html)) {
    console.error(`  FAIL: translate bar found in ${path.relative(BASE, p)}`);
    failures++;
  }
}

if (failures === 0) {
  console.log(`✅  All ${pages.length} pages clean — no translate bar remnants found`);
  process.exit(0);
} else {
  console.error(`\n❌  ${failures} page(s) still contain translate bar markup`);
  process.exit(1);
}
