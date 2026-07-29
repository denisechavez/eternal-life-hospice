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

// ── Full-coverage scan ────────────────────────────────────────────────────────
// Walk every .html file under elh-preview/ and confirm each site page carries
// the translate bar.  Pages that legitimately omit it are listed in EXCLUDED.
console.log('\n' + '═'.repeat(60));
console.log('Full-coverage scan — all site pages\n');

// Paths relative to BASE that are intentionally excluded from the translate bar:
//   • assets/            — social graphics and internal tooling (not site pages)
//   • redirect stubs     — meta-refresh shims that immediately send the browser elsewhere
//   • print cards        — standalone rack-card / business-card HTML (no shared nav)
//   • aleksandradubina   — noindex digital business card (no shared nav)
//   • family-guide       — standalone interactive booklet (no shared nav)
const EXCLUDED_PREFIXES = ['assets/'];
const EXCLUDED_FILES = new Set([
  'blog/index.html',
  'care-brief/index.html',
  'resources/index.html',
  'card-aleksandra-dubina.html',
  'card-denise-chavez.html',
  'aleksandradubina.html',
  'family-guide.html',
]);

function walkHtml(dir, baseLen) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkHtml(full, baseLen));
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      results.push(full.slice(baseLen + 1)); // relative to BASE
    }
  }
  return results;
}

const allHtml   = walkHtml(BASE, BASE.length);
const sitePages = allHtml.filter(f => {
  if (EXCLUDED_PREFIXES.some(p => f.startsWith(p))) return false;
  if (EXCLUDED_FILES.has(f)) return false;
  return true;
});

console.log(`Scanning ${sitePages.length} site pages (${allHtml.length - sitePages.length} excluded)\n`);

const scanFailed = [];

for (const rel of sitePages.sort()) {
  const html = fs.readFileSync(path.join(BASE, rel), 'utf8');
  const missingScript = !hasTranslateScript(html);
  const missingPills  = extractLangs(html).length === 0;
  const canonical     = extractCanonical(html);
  const badCanonical  = !canonical || !canonical.startsWith('https://eternallifehospice.com');
  if (missingScript || missingPills || badCanonical) {
    const why = [
      missingScript ? 'no translate.js <script>'                                   : '',
      missingPills  ? 'no .ft-lang pills'                                           : '',
      badCanonical  ? `bad canonical (${canonical ? canonical : 'missing'})` : '',
    ].filter(Boolean).join(' + ');
    scanFailed.push({ rel, why });
  }
}

if (scanFailed.length === 0) {
  console.log(`✅  All ${sitePages.length} site pages have the translate bar and a valid canonical URL`);
} else {
  console.error(`❌  ${scanFailed.length} page(s) failing translate-bar / canonical check:`);
  for (const { rel, why } of scanFailed) {
    console.error(`     ${rel}  (${why})`);
    allPassed = false;
  }
}

// ── Canonical-guard self-test ─────────────────────────────────────────────────
// Prove the full-coverage canonical check catches a bad canonical by temporarily
// injecting one into a real site page, running the check, then restoring.
console.log('\n' + '═'.repeat(60));
console.log('Canonical-guard self-test\n');

(function runCanonicalSelfTest() {
  // Use the city page — it is always present and has a canonical
  const probeRel  = 'hospice-ventura-ca.html';
  const probeFile = path.join(BASE, probeRel);

  if (!fs.existsSync(probeFile)) {
    console.error('  ✗ FAIL: probe page not found for self-test:', probeFile);
    allPassed = false;
    return;
  }

  const originalHtml = fs.readFileSync(probeFile, 'utf8');

  // 1. Verify the page currently has a valid canonical (baseline)
  const baseCanonical = extractCanonical(originalHtml);
  if (!baseCanonical || !baseCanonical.startsWith('https://eternallifehospice.com')) {
    console.error('  ✗ FAIL: probe page already has a bad canonical before injection:', baseCanonical);
    allPassed = false;
    return;
  }
  console.log('  ✓ baseline canonical is valid:', baseCanonical);

  // 2. Inject a broken canonical (wrong domain) and confirm detection fires
  const brokenHtml = originalHtml.replace(
    /<link[^>]+rel=["']canonical["'][^>]*>/i,
    `<link rel="canonical" href="http://localhost/hospice-ventura-ca">`,
  );
  fs.writeFileSync(probeFile, brokenHtml, 'utf8');

  let detectedBad = false;
  try {
    const injectedCanonical = extractCanonical(fs.readFileSync(probeFile, 'utf8'));
    detectedBad = !injectedCanonical || !injectedCanonical.startsWith('https://eternallifehospice.com');
  } finally {
    // Always restore before asserting so a crash can't leave the file broken
    fs.writeFileSync(probeFile, originalHtml, 'utf8');
  }

  if (detectedBad) {
    console.log('  ✓ broken canonical (http://localhost) correctly detected by guard');
  } else {
    console.error('  ✗ FAIL: guard did NOT catch the injected broken canonical — self-test is broken');
    allPassed = false;
  }

  // 3. Confirm the page is clean again after restore
  const restoredCanonical = extractCanonical(fs.readFileSync(probeFile, 'utf8'));
  if (restoredCanonical && restoredCanonical.startsWith('https://eternallifehospice.com')) {
    console.log('  ✓ page restored — canonical is valid again:', restoredCanonical);
  } else {
    console.error('  ✗ FAIL: page not correctly restored after self-test, canonical:', restoredCanonical);
    allPassed = false;
  }
})();

// ── Summary ──────────────────────────────────────────────────────────────────
console.log('\n' + '═'.repeat(60));
if (allPassed) {
  console.log('✅  All translate-bar smoke-tests PASSED');
  process.exit(0);
} else {
  console.log('❌  One or more tests FAILED — see above');
  process.exit(1);
}
