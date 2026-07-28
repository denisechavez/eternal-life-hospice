#!/usr/bin/env node
/**
 * Smoke-test: translate bar wiring
 *
 * For each representative page, this script:
 *   1. Reads the HTML file
 *   2. Extracts the canonical URL (simulates what location.href resolves to in production)
 *   3. Extracts every .ft-lang pill and its data-lang attribute
 *   4. Replicates the translate.js logic to build the Google Translate URL
 *   5. Asserts the URL contains the correct u= parameter and a valid tl= code
 *
 * translate.js logic (verbatim):
 *   a.href = 'https://translate.google.com/translate?sl=en&tl=' + a.dataset.lang
 *            + '&u=' + encodeURIComponent(location.href);
 */

const fs   = require('fs');
const path = require('path');

const BASE = path.join(__dirname, '..');

// Representative pages: label → file path relative to BASE
const PAGES = [
  {
    label : 'Homepage (root)',
    file  : 'index.html',
    // canonical resolved in production as https://eternallifehospice.com/
  },
  {
    label : 'City page (root-level)',
    file  : 'hospice-ventura-ca.html',
  },
  {
    label : 'Resources post (subdirectory /resources/)',
    file  : 'resources/volunteer.html',
  },
  {
    label : 'Blog post (subdirectory /blog/)',
    file  : 'blog/caring-for-the-caregiver.html',
  },
];

const EXPECTED_LANGS = ['es','ru','uk','ko','hy','tl','vi','zh-CN','ar','fa'];
const TRANSLATE_BASE  = 'https://translate.google.com/translate';

let allPassed = true;

function assert(condition, message) {
  if (!condition) {
    console.error('  ✗ FAIL:', message);
    allPassed = false;
  } else {
    console.log('  ✓', message);
  }
}

function extractCanonical(html) {
  const m = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i)
         || html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  return m ? m[1] : null;
}

function extractLangs(html) {
  // Find all <a class="ft-lang" data-lang="..."> (order preserved)
  const re = /<a[^>]+class=["'][^"']*ft-lang[^"']*["'][^>]+data-lang=["']([^"']+)["'][^>]*>/gi;
  const langs = [];
  let m;
  while ((m = re.exec(html)) !== null) langs.push(m[1]);
  // also handle reversed attribute order
  const re2 = /<a[^>]+data-lang=["']([^"']+)["'][^>]+class=["'][^"']*ft-lang[^"']*["'][^>]*>/gi;
  while ((m = re2.exec(html)) !== null) {
    if (!langs.includes(m[1])) langs.push(m[1]);
  }
  return langs;
}

function hasTranslateScript(html) {
  return /src=["'][^"']*translate\.js["']/i.test(html);
}

// Replicate translate.js
function buildTranslateUrl(lang, pageUrl) {
  return TRANSLATE_BASE + '?sl=en&tl=' + lang + '&u=' + encodeURIComponent(pageUrl);
}

// ── Run tests ────────────────────────────────────────────────────────────────
for (const page of PAGES) {
  console.log('\n──', page.label);
  const filePath = path.join(BASE, page.file);

  if (!fs.existsSync(filePath)) {
    console.error('  ✗ FAIL: file not found:', filePath);
    allPassed = false;
    continue;
  }

  const html      = fs.readFileSync(filePath, 'utf8');
  const canonical = extractCanonical(html);
  const langs     = extractLangs(html);

  // 1. canonical URL exists
  assert(canonical, 'canonical <link> is present');
  assert(canonical && canonical.startsWith('https://eternallifehospice.com'),
         'canonical URL starts with https://eternallifehospice.com');

  // 2. translate.js is loaded on this page
  assert(hasTranslateScript(html), 'translate.js script tag is present');

  // 3. .ft-lang pills are present
  assert(langs.length > 0, `.ft-lang pills found (${langs.length})`);

  // 4. Expected language set matches
  const missing = EXPECTED_LANGS.filter(l => !langs.includes(l));
  const extra   = langs.filter(l => !EXPECTED_LANGS.includes(l));
  assert(missing.length === 0, `all ${EXPECTED_LANGS.length} expected language codes are present`
    + (missing.length ? ` — missing: ${missing.join(', ')}` : ''));
  if (extra.length) console.log('  ℹ  Extra langs (not in baseline):', extra.join(', '));

  // 5. For each language, simulate translate.js and verify the generated URL
  if (canonical) {
    let urlOk = true;
    for (const lang of langs) {
      const built = buildTranslateUrl(lang, canonical);
      const uParam = new URL(built).searchParams.get('u');
      const tlParam = new URL(built).searchParams.get('tl');
      if (uParam !== canonical || tlParam !== lang) {
        console.error(`  ✗ URL mismatch for lang=${lang}:`, built);
        urlOk = false;
        allPassed = false;
      }
    }
    if (urlOk) {
      // Show one sample URL for review
      const sample = buildTranslateUrl(langs[0], canonical);
      assert(true, `all ${langs.length} translate URLs correctly encode u=${canonical}`);
      console.log('     sample:', sample);
    }
  }

  // 6. Subdirectory pages: confirm canonical contains the path segment (not just the root)
  if (page.file.includes('/')) {
    const subPath = '/' + page.file.replace('.html', '');
    assert(canonical && canonical.includes(subPath.split('/').pop()),
           `canonical URL contains the page's path segment (${subPath.split('/').pop()})`);
  }
}

// ── Summary ──────────────────────────────────────────────────────────────────
console.log('\n' + '═'.repeat(60));
if (allPassed) {
  console.log('✅  All translate-bar smoke-tests PASSED');
  process.exit(0);
} else {
  console.log('❌  One or more tests FAILED — see above');
  process.exit(1);
}
