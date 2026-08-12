#!/usr/bin/env node
/**
 * test-a11y-coverage.js — Verify every public content page has:
 *   1. A skip link pointing to #main-content
 *   2. A <main id="main-content"> landmark (with or without tabindex)
 *
 * Pages intentionally excluded (redirect stubs, card pages, booklet):
 *   see EXCLUDED_FILES below.
 *
 * Usage:
 *   node website/elh-preview/assets/test-a11y-coverage.js
 */
'use strict';

const fs   = require('fs');
const path = require('path');

const BASE = path.join(__dirname, '..');

// Pages that legitimately omit the pattern (redirect stubs, single-purpose micro-pages)
const EXCLUDED_FILES = new Set([
  'resources/index.html',
  'blog/index.html',
  'care-brief/index.html',
  'card-aleksandra-dubina.html',
  'card-denise-chavez.html',
  'aleksandradubina.html',
  'family-guide.html',       // booklet: <main> wraps stage div, no site header
  'sitemap.html',            // custom footer, translation bar excluded by design
  'referral-card.html',      // print-preview card
  'blog/index.html',
]);

const EXCLUDED_PREFIXES = ['assets/', 'es/'];

function walkHtml(dir, baseLen, results = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkHtml(full, baseLen, results);
    } else if (entry.name.endsWith('.html')) {
      results.push(full.slice(baseLen + 1));
    }
  }
  return results;
}

const allHtml = walkHtml(BASE, BASE.length);
const pages = allHtml.filter(f => {
  if (EXCLUDED_PREFIXES.some(p => f.startsWith(p))) return false;
  if (EXCLUDED_FILES.has(f)) return false;
  return true;
});

let passed = 0;
const failed = [];

for (const rel of pages) {
  const html = fs.readFileSync(path.join(BASE, rel), 'utf8');
  const hasSkipLink = /class=["'][^"']*skip-link[^"']*["'][^>]+href=["']#main-content["']/i.test(html);
  const hasMain     = /<main\b[^>]*id=["']main-content["']/i.test(html);

  if (hasSkipLink && hasMain) {
    passed++;
  } else {
    const reasons = [];
    if (!hasSkipLink) reasons.push('no .skip-link→#main-content');
    if (!hasMain)     reasons.push('no <main id="main-content">');
    failed.push(`${rel}: ${reasons.join(', ')}`);
  }
}

console.log(`\nA11y coverage check — ${pages.length} pages scanned\n`);
if (failed.length === 0) {
  console.log(`✅  All ${passed} pages have skip link and main landmark.`);
  process.exit(0);
} else {
  console.error(`❌  ${failed.length} page(s) missing skip link or main landmark:`);
  failed.forEach(f => console.error('   ', f));
  process.exit(1);
}
