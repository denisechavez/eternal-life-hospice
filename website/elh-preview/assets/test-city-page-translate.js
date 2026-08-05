#!/usr/bin/env node
/**
 * Pre-commit guard: translate bar presence on a city page
 *
 * Usage:
 *   node website/elh-preview/assets/test-city-page-translate.js \
 *        website/elh-preview/hospice-CITY-ca.html
 *
 * Exits 0 when all checks pass, 1 on any failure.
 * Run this as the final step before committing a new or updated city page.
 *
 * Checks:
 *   1. foot-translate wrapper div is present
 *   2. All 10 expected .ft-lang pills are present
 *   3. The translate.js <script> tag is present
 *   4. Canonical URL is present and starts with https://eternallifehospice.com
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ── helpers ───────────────────────────────────────────────────────────────────

const EXPECTED_LANGS = ['es','ru','uk','ko','hy','tl','vi','zh-CN','ar','fa'];

let allPassed = true;

function pass(msg)  { console.log('  ✓', msg); }
function fail(msg)  { console.error('  ✗ FAIL:', msg); allPassed = false; }

function check(condition, message) {
  condition ? pass(message) : fail(message);
}

function extractLangs(html) {
  const re  = /<a[^>]+class=["'][^"']*ft-lang[^"']*["'][^>]+data-lang=["']([^"']+)["'][^>]*>/gi;
  const re2 = /<a[^>]+data-lang=["']([^"']+)["'][^>]+class=["'][^"']*ft-lang[^"']*["'][^>]*>/gi;
  const langs = [];
  let m;
  while ((m = re.exec(html))  !== null) langs.push(m[1]);
  while ((m = re2.exec(html)) !== null) { if (!langs.includes(m[1])) langs.push(m[1]); }
  return langs;
}

function extractCanonical(html) {
  const m = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i)
           || html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  return m ? m[1] : null;
}

// ── main ─────────────────────────────────────────────────────────────────────

const [,, filePath] = process.argv;

if (!filePath) {
  console.error('Usage: node test-city-page-translate.js <path/to/hospice-CITY-ca.html>');
  process.exit(1);
}

const absPath = path.resolve(filePath);
if (!fs.existsSync(absPath)) {
  console.error(`File not found: ${absPath}`);
  process.exit(1);
}

console.log(`\nChecking translate bar: ${path.basename(absPath)}\n`);

const html = fs.readFileSync(absPath, 'utf8');

// 1. foot-translate wrapper
check(/class=["'][^"']*foot-translate[^"']*["']/.test(html),
      'foot-translate wrapper div is present');

// 2. translate.js script tag
check(/src=["'][^"']*translate\.js[^"']*["']/i.test(html),
      'translate.js script tag is present');

// 3. .ft-lang pills — all expected languages
const langs   = extractLangs(html);
const missing = EXPECTED_LANGS.filter(l => !langs.includes(l));
const extra   = langs.filter(l => !EXPECTED_LANGS.includes(l));

check(langs.length > 0,
      `.ft-lang pills found (${langs.length})`);
check(missing.length === 0,
      `all ${EXPECTED_LANGS.length} expected language codes present`
      + (missing.length ? ` — missing: ${missing.join(', ')}` : ''));

if (extra.length) {
  console.log('  ℹ  Extra langs (not in baseline):', extra.join(', '));
}

// 4. Canonical URL
const canonical = extractCanonical(html);
check(!!canonical,
      'canonical <link> is present');
check(!!(canonical && canonical.startsWith('https://eternallifehospice.com')),
      'canonical URL starts with https://eternallifehospice.com');

// ── summary ───────────────────────────────────────────────────────────────────
console.log('');
if (allPassed) {
  console.log('✅  Translate bar OK — safe to commit');
  process.exit(0);
} else {
  console.error('❌  Translate bar checks FAILED — do NOT commit until fixed');
  console.error('    Copy the foot-translate block from any existing city page,');
  console.error('    e.g. website/elh-preview/hospice-ventura-ca.html lines 199-213,');
  console.error('    and add <script defer src="/assets/translate.js"></script> before </body>.');
  process.exit(1);
}
