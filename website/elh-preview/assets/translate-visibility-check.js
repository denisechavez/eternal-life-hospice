#!/usr/bin/env node
/**
 * translate-visibility-check.js
 *
 * Checks that the translate bar is not hidden by CSS on any site page.
 *
 * The existing translate-smoke-test.js confirms that every page carries the
 * translate.js script tag and the .ft-lang pill markup in its HTML source.
 * This script goes one step further: it scans CSS for rules that would hide
 * the translate bar elements and reports any page where such a rule exists.
 *
 * CSS sources scanned per page:
 *   1. Every inline <style>…</style> block embedded in the page HTML.
 *   2. Every external stylesheet referenced by a
 *      <link rel="stylesheet" href="…"> tag in that page.
 *   3. The canonical shared stylesheet assets/elh.css (always checked,
 *      because many pages use it even when the <link> tag is absent).
 *
 * Hiding patterns detected on translate-bar selectors:
 *   • display: none
 *   • visibility: hidden
 *   • opacity: 0
 *   • height: 0        ← clips bar away when ancestor has overflow:hidden
 *   • max-height: 0
 *
 * Selectors checked (the full translate bar element tree):
 *   .foot-translate   — outer wrapper in the footer
 *   .ft-label         — "Translate this page" label
 *   .ft-lang-btns     — pills container
 *   .ft-lang          — individual language pill
 *
 * Ancestor selectors also checked:
 *   footer            — the <footer> HTML element that wraps the bar
 *   #site-footer      — the id on that element in every elh-preview page
 *   If any hiding rule targets an ancestor the bar disappears even when
 *   none of its own CSS is flagged.  These use a token-aware match so
 *   a rule like ".footer-something" is not a false positive.
 *
 * CSS parser:
 *   Uses a brace-depth recursive parser (not a regex) so rules inside @media,
 *   @supports, and other nested at-rules are evaluated correctly. A rule like
 *   "@media (max-width:768px) { .ft-lang { display:none } }" is caught.
 *
 * HTML-level check:
 *   Any translate bar element carrying a `hidden` attribute is also flagged.
 *
 * Limitation: dynamic JavaScript mutations (e.g. a toggle that adds a class)
 * cannot be detected by static analysis. The bar's default state on first
 * page load is what matters for real-visitor visibility — exactly what this
 * checks.
 *
 * Runs as part of the Netlify deploy gate:
 *   netlify.toml → build.command includes "node assets/translate-visibility-check.js"
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const BASE = path.join(__dirname, '..');

// ── Target selectors ─────────────────────────────────────────────────────────
const TARGET_SELECTORS = [
  '.foot-translate',
  '.ft-label',
  '.ft-lang-btns',
  '.ft-lang',
];

// ── Ancestor selectors ────────────────────────────────────────────────────────
// A hiding rule on any of these makes the translate bar invisible even when
// none of its own selectors are touched.  In every elh-preview page the bar
// lives as a direct child of <footer id="site-footer">.
const ANCESTOR_SELECTORS = [
  'footer',
  '#site-footer',
];

// ── Hiding declarations to flag ───────────────────────────────────────────────
const HIDING_PATTERNS = [
  /\bdisplay\s*:\s*none\b/i,
  /\bvisibility\s*:\s*hidden\b/i,
  /\bopacity\s*:\s*0\b/,
  /\bmax-height\s*:\s*0\b/,
  /\bheight\s*:\s*0\b/,
];

// ── Pages excluded from the translate bar (mirrors translate-smoke-test.js) ──
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

// ── Shared stylesheet always scanned (relative to BASE) ──────────────────────
const ALWAYS_SCAN_CSS = ['assets/elh.css'];

// ── Brace-depth recursive CSS rule iterator ───────────────────────────────────
/**
 * Strip block comments (/* … *​/) from a CSS string before parsing so that
 * comment text never appears in the prelude and breaks the @-rule detection.
 */
function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

/**
 * Yield every { selector, declarations } pair found anywhere in the CSS text,
 * including rules nested inside @media, @supports, and other at-rules at any
 * depth.  This is more reliable than a flat regex because it correctly tracks
 * matching braces rather than assuming the first `}` closes the block.
 *
 * Call stripComments() on the input before this function to ensure comment
 * text does not corrupt the prelude of @-rules.
 *
 * Algorithm:
 *   Walk the text character-by-character.  When we hit `{`, the text before
 *   it is the "prelude" (selector or at-rule keyword).  We then find the
 *   matching `}` by counting depth.  If the prelude starts with `@` the block
 *   contains nested rules — recurse into its body.  Otherwise the body is a
 *   flat declaration list — yield it.
 *
 * @param {string} css   Comment-stripped stylesheet text (may be a fragment).
 * @yields {{ selector: string, declarations: string }}
 */
function* iterRules(css) {
  let i = 0;
  while (i < css.length) {
    // Find the next opening brace.
    const open = css.indexOf('{', i);
    if (open === -1) break;

    const prelude = css.slice(i, open).trim();

    // Find the matching closing brace using depth counting.
    let depth = 1;
    let j = open + 1;
    while (j < css.length && depth > 0) {
      if (css[j] === '{') depth++;
      else if (css[j] === '}') depth--;
      j++;
    }

    const body = css.slice(open + 1, j - 1);

    if (prelude.startsWith('@')) {
      // At-rule (e.g. @media, @supports, @keyframes, @page).
      // Recurse into its body to find any nested selector rules.
      // @keyframes bodies contain step selectors (from/to/%), not real rules —
      // those selectors never target .ft-lang so they are harmless to recurse.
      //
      // Skip @media print blocks: hiding elements for print output is
      // intentional and does not affect screen visibility for real visitors.
      if (/^@media\s*print\b/i.test(prelude)) {
        i = j;
        continue;
      }
      yield* iterRules(body);
    } else if (prelude.length > 0) {
      // Regular rule: the prelude is the selector list, body is declarations.
      yield { selector: prelude, declarations: body };
    }

    i = j;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function walkHtml(dir, baseLen) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkHtml(full, baseLen));
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      results.push(full.slice(baseLen + 1));
    }
  }
  return results;
}

/** Return all inline <style>…</style> block text concatenated. */
function extractInlineStyles(html) {
  const blocks = [];
  const re = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  let m;
  while ((m = re.exec(html)) !== null) blocks.push(m[1]);
  return blocks.join('\n');
}

/**
 * Return hrefs of every <link rel="stylesheet" href="…"> in the HTML,
 * resolved to paths relative to BASE.
 * Absolute https:// / CDN hrefs are skipped — unreadable at build time and
 * the site ships no CDN stylesheets that reference .ft-lang.
 */
function extractLinkedStylesheets(html, pageRel) {
  const hrefs = [];
  const patterns = [
    /<link[^>]+rel=["']stylesheet["'][^>]+href=["']([^"']+)["'][^>]*>/gi,
    /<link[^>]+href=["']([^"']+)["'][^>]+rel=["']stylesheet["'][^>]*>/gi,
  ];
  for (const re of patterns) {
    let m;
    while ((m = re.exec(html)) !== null) {
      const h = m[1];
      if (h.startsWith('http://') || h.startsWith('https://') || h.startsWith('//')) continue;
      hrefs.push(h);
    }
  }
  const pageDir = path.dirname(path.join(BASE, pageRel));
  return hrefs.map(h =>
    h.startsWith('/')
      ? h.slice(1)                                      // root-relative
      : path.relative(BASE, path.join(pageDir, h))      // page-relative
  );
}

/**
 * Returns true if an ancestor selector token appears as the **subject** of
 * the CSS rule (i.e. the rightmost compound selector), not merely as a
 * scoping context.
 *
 * Examples:
 *   "footer { display:none }"          → selector="footer"     → TRUE  ✓
 *   "#hdr, #site-footer, .btn"         → contains "#site-footer" at subject → TRUE  ✓
 *   "#site-footer .foot-social .child" → "#site-footer" is scoping, not subject → FALSE ✓
 *   ".footer-link { display:none }"    → different token → FALSE ✓
 *
 * The key rule: after the ancestor token must come ONLY end-of-string, a
 * comma (next selector in the list), or a pseudo/attribute/class modifier
 * that stays on the same compound selector (: [ . #).  A space, >, +, or ~
 * after the token means the ancestor is a scoping context — skip it.
 */
function selectorMatchesAncestor(selector, ancestor) {
  const esc = ancestor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(
    '(?:^|[\\s,>+~])' + esc + '(?=[,:{\\[.#]|$)'
  ).test(selector);
}

/**
 * Returns true if the CSS selector targets any translate-bar element OR any
 * known ancestor element (footer / #site-footer).  Translate-bar selectors
 * use a substring match; ancestor selectors use the token-aware matcher above
 * to avoid false positives like ".footer-link".
 */
function targetsTranslateBar(selector) {
  if (TARGET_SELECTORS.some(t => selector.includes(t))) return true;
  return ANCESTOR_SELECTORS.some(a => selectorMatchesAncestor(selector, a));
}

/** Returns the first matching hiding pattern description, or null. */
function findHidingDeclaration(declarations) {
  for (const pat of HIDING_PATTERNS) {
    if (pat.test(declarations)) return pat.source;
  }
  return null;
}

/**
 * Scan a CSS string using the recursive rule iterator.
 * Strips block comments first so @-rule preludes are clean.
 * Returns an array of { selector, hiding } findings.
 */
function scanCss(css) {
  const findings = [];
  for (const { selector, declarations } of iterRules(stripComments(css))) {
    if (!targetsTranslateBar(selector)) continue;
    const hiding = findHidingDeclaration(declarations);
    if (hiding) findings.push({ selector, hiding });
  }
  return findings;
}

// ── Cache external CSS content ────────────────────────────────────────────────
const cssCache = new Map();
function readCss(relPath) {
  if (cssCache.has(relPath)) return cssCache.get(relPath);
  const full = path.join(BASE, relPath);
  const content = fs.existsSync(full) ? fs.readFileSync(full, 'utf8') : '';
  cssCache.set(relPath, content);
  return content;
}

// ── Self-test ─────────────────────────────────────────────────────────────────
/**
 * Sanity checks run before any real pages are scanned:
 *
 *   1. Parser catches translate-bar hiding nested inside @media / @supports.
 *   2. Ancestor hiding: `footer { display:none }` is flagged even though the
 *      translate bar's own selectors are untouched.
 *   3. False-positive guard: `.footer-link { display:none }` must NOT be
 *      flagged (token-boundary check on the ancestor matcher).
 */
function selfTest() {
  // ── check 1: nested at-rule hiding on bar selectors ─────────────────────
  const syntheticCss = `
    /* normal rule */
    .ft-lang { display: inline-flex; color: red; }

    /* hiding inside @media — must be caught */
    @media (max-width: 768px) {
      .ft-lang { display: none; }
    }

    /* hiding inside nested @supports > @media */
    @supports (display: flex) {
      @media screen {
        .foot-translate { visibility: hidden; }
      }
    }
  `;

  const found = scanCss(syntheticCss);

  const displayNone  = found.some(f => f.selector.includes('.ft-lang')       && /display.*none/i.test(f.hiding));
  const visHidden    = found.some(f => f.selector.includes('.foot-translate') && /visibility.*hidden/i.test(f.hiding));
  const normalMissed = found.some(f => /inline-flex/.test(f.hiding)); // must NOT flag this

  if (!displayNone || !visHidden || normalMissed) {
    console.error('❌  Self-test FAILED — CSS parser is not detecting nested at-rule hiding');
    console.error('   findings:', JSON.stringify(found, null, 2));
    process.exit(2);
  }

  // ── check 2: ancestor hiding — footer { display:none } must be caught ───
  // This is the regression case: the bar's own CSS is fine but its containing
  // <footer> is hidden, so the bar disappears from the page.
  const ancestorCss = `
    footer { display: none; }
    #site-footer { visibility: hidden; }
  `;

  const ancestorFound = scanCss(ancestorCss);
  const footerCaught     = ancestorFound.some(f => /footer/.test(f.selector) && /display.*none/i.test(f.hiding));
  const siteFooterCaught = ancestorFound.some(f => /#site-footer/.test(f.selector) && /visibility.*hidden/i.test(f.hiding));

  if (!footerCaught || !siteFooterCaught) {
    console.error('❌  Self-test FAILED — ancestor hiding (footer/site-footer) not detected');
    console.error('   findings:', JSON.stringify(ancestorFound, null, 2));
    process.exit(2);
  }

  // ── check 3: false-positive guards ─────────────────────────────────────
  // 3a. ".footer-link" must NOT match the "footer" token (different selector)
  // 3b. "#site-footer .child" must NOT flag #site-footer (scoping context, not subject)
  // 3c. "@media print { #site-footer { display:none } }" must NOT be flagged
  //     (print hiding is intentional and irrelevant to screen visitors)
  const fp3a = scanCss(`.footer-link { display: none; }`);
  const fp3b = scanCss(`#site-footer .foot-social .fs-invite { display: none; }`);
  const fp3c = scanCss(`@media print { #site-footer { display: none; } }`);

  if (fp3a.length > 0) {
    console.error('❌  Self-test FAILED — false positive 3a: ".footer-link" matched as ancestor');
    console.error('   findings:', JSON.stringify(fp3a, null, 2));
    process.exit(2);
  }
  if (fp3b.length > 0) {
    console.error('❌  Self-test FAILED — false positive 3b: "#site-footer .child" matched as ancestor subject');
    console.error('   findings:', JSON.stringify(fp3b, null, 2));
    process.exit(2);
  }
  if (fp3c.length > 0) {
    console.error('❌  Self-test FAILED — false positive 3c: @media print hiding incorrectly flagged');
    console.error('   findings:', JSON.stringify(fp3c, null, 2));
    process.exit(2);
  }

  // All self-tests passed — continue silently.
}

// ── Main ──────────────────────────────────────────────────────────────────────

selfTest();

const allHtml   = walkHtml(BASE, BASE.length);
const sitePages = allHtml.filter(f => {
  if (EXCLUDED_PREFIXES.some(p => f.startsWith(p))) return false;
  if (EXCLUDED_FILES.has(f)) return false;
  return true;
});

// Pre-scan the always-checked stylesheets once and cache results.
const sharedFindings = {};
for (const rel of ALWAYS_SCAN_CSS) {
  const css = readCss(rel);
  if (css) sharedFindings[rel] = scanCss(css);
}

console.log('Translate-bar CSS visibility check');
console.log('═'.repeat(60));
console.log(`Scanning ${sitePages.length} site pages for hiding CSS rules\n`);
console.log('CSS sources  : inline <style> blocks + linked stylesheets + assets/elh.css');
console.log('CSS parser   : recursive brace-depth (handles @media/@supports nesting)');
console.log('Bar targets  :', TARGET_SELECTORS.join(', '));
console.log('Ancestors    :', ANCESTOR_SELECTORS.join(', '), ' ← hidden ancestor = hidden bar');
console.log('Hiding props : display:none · visibility:hidden · opacity:0 · height:0 · max-height:0\n');

let allPassed = true;
const failures = [];

for (const rel of sitePages.sort()) {
  const html = fs.readFileSync(path.join(BASE, rel), 'utf8');

  // 1. Inline <style> blocks.
  for (const f of scanCss(extractInlineStyles(html))) {
    failures.push({ rel, source: 'inline <style>', ...f });
    allPassed = false;
  }

  // 2. Linked external stylesheets.
  const linked = extractLinkedStylesheets(html, rel);
  for (const cssRel of linked) {
    for (const f of scanCss(readCss(cssRel))) {
      failures.push({ rel, source: cssRel, ...f });
      allPassed = false;
    }
  }

  // 3. Always-checked shared stylesheets (skip if already covered above).
  for (const [cssRel, findings] of Object.entries(sharedFindings)) {
    if (linked.includes(cssRel)) continue;
    for (const f of findings) {
      failures.push({ rel, source: cssRel, ...f });
      allPassed = false;
    }
  }

  // 4. HTML `hidden` attribute on any translate bar element.
  const hiddenRe = /<(?:div|span|a)[^>]+class="[^"]*(?:foot-translate|ft-label|ft-lang-btns|ft-lang)[^"]*"[^>]*\bhidden\b[^>]*>/gi;
  let m;
  while ((m = hiddenRe.exec(html)) !== null) {
    failures.push({ rel, source: 'HTML hidden attribute', selector: '(element)', hiding: m[0].slice(0, 80) });
    allPassed = false;
  }
}

// ── Report ────────────────────────────────────────────────────────────────────

if (failures.length === 0) {
  console.log(`✅  No hiding CSS rules found across all ${sitePages.length} site pages`);
  console.log('    (inline styles, linked stylesheets, and assets/elh.css all checked)\n');
} else {
  console.error(`❌  ${failures.length} hiding rule(s) detected:\n`);
  for (const { rel, source, selector, hiding } of failures) {
    console.error(`  Page     : ${rel}`);
    console.error(`  CSS src  : ${source}`);
    console.error(`  Selector : ${selector}`);
    console.error(`  Hides via: ${hiding}`);
    console.error('');
  }
}

console.log('═'.repeat(60));
if (allPassed) {
  console.log('✅  translate-visibility-check PASSED');
  process.exit(0);
} else {
  console.error('❌  translate-visibility-check FAILED — translate bar is hidden on one or more pages');
  process.exit(1);
}
