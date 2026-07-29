#!/usr/bin/env node
/**
 * Pre-deploy guard: chat widget teaser must stay closed on first visit.
 *
 * The teaser auto-popup was deliberately disabled in maybeShowTeaser() — it is a
 * no-op that immediately returns.  A future edit accidentally re-enabling it
 * would show a greeting bubble to every new hospice visitor the moment they land.
 *
 * This script statically analyses chat.js and fails the deploy if:
 *   1. maybeShowTeaser() is no longer a no-op (contains code beyond "return;")
 *   2. The teaser element is not initialised hidden (display = "none")
 *   3. Any call to show the teaser (.style.display = "block", removeAttribute("hidden"),
 *      teaser.style.display = "") appears outside the open() / dismissTeaser() functions
 *      (i.e. at module initialisation time, where it would run on page load)
 *
 * Exits 0 when all checks pass, 1 on any failure.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const CHAT_JS = path.join(__dirname, 'chat.js');

let allPassed = true;

function pass(msg) { console.log('  ✓', msg); }
function fail(msg) { console.error('  ✗ FAIL:', msg); allPassed = false; }
function check(condition, message) { condition ? pass(message) : fail(message); }

// ── Read source ───────────────────────────────────────────────────────────────

if (!fs.existsSync(CHAT_JS)) {
  console.error('FATAL: chat.js not found at', CHAT_JS);
  process.exit(1);
}

const src = fs.readFileSync(CHAT_JS, 'utf8');

// ── 1. maybeShowTeaser must be a no-op ────────────────────────────────────────
//
// Extract everything between the opening brace and the closing brace of
// `function maybeShowTeaser() { ... }`.  We do a simple brace-depth walk so
// nested constructs don't confuse us.

console.log('\n── Check 1: maybeShowTeaser() is a no-op\n');

(function checkMaybeShowTeaser() {
  const startMarker = 'function maybeShowTeaser()';
  const startIdx    = src.indexOf(startMarker);

  if (startIdx === -1) {
    fail('maybeShowTeaser function not found in chat.js');
    return;
  }

  // Walk forward to find the opening brace.
  let braceStart = src.indexOf('{', startIdx);
  if (braceStart === -1) { fail('maybeShowTeaser: opening brace not found'); return; }

  // Walk until depth returns to 0 to find the closing brace.
  let depth = 0, i = braceStart, end = -1;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) { end = i; break; } }
  }

  if (end === -1) { fail('maybeShowTeaser: closing brace not found'); return; }

  const body = src.slice(braceStart + 1, end).trim();

  // Strip comments (single-line and block)
  const stripped = body
    .replace(/\/\*[\s\S]*?\*\//g, '')   // block comments
    .replace(/\/\/[^\n]*/g, '')          // line comments
    .trim();

  // A no-op body is empty or contains only "return;" (possibly with semicolons/whitespace)
  const isNoop = stripped === '' || /^[\s;]*return\s*;[\s;]*$/.test(stripped);

  check(isNoop,
    'maybeShowTeaser() body is a no-op (empty or bare "return;")'
  );

  if (!isNoop) {
    console.error('     Actual body (stripped):', JSON.stringify(stripped.slice(0, 200)));
  }
})();

// ── 2. Teaser element is initialised hidden ───────────────────────────────────
//
// The build() function must set teaser.style.display = "none" before the widget
// is ready.  Without this the element would flash briefly on insertion.

console.log('\n── Check 2: teaser element starts with display = "none"\n');

(function checkTeaserHidden() {
  // Look for the assignment that hides the teaser at construction time.
  // Accept both single and double quotes.
  const hiddenPattern = /teaser\.style\.display\s*=\s*["']none["']/;

  check(
    hiddenPattern.test(src),
    'teaser.style.display is set to "none" during build()'
  );
})();

// ── 3. No auto-show call at module initialisation time ────────────────────────
//
// We want to ensure the teaser is never made visible outside of a user
// interaction.  The allowed show-sites are:
//   • open()          — user clicks the launch button
//   • dismissTeaser() — sets display:none only (never shows)
//
// We detect any pattern that would reveal the teaser:
//   teaser.style.display = "block" / ""
//   teaser.removeAttribute("hidden")
//   teaser.style.visibility = "visible"
//
// …and confirm they only appear inside `open()` or `dismissTeaser()`, not at
// the top-level call to maybeShowTeaser() or anywhere that runs on page load.
//
// Because the static analysis is approximate, we use a conservative approach:
// extract the text of maybeShowTeaser() (already confirmed a no-op above) and
// additionally ensure no *top-level* setTimeout / setInterval in the module
// contains a teaser-show pattern.

console.log('\n── Check 3: no auto-show of teaser on page load\n');

(function checkNoAutoShow() {
  // Patterns that would make the teaser visible
  const showPatterns = [
    /teaser\.style\.display\s*=\s*["']block["']/,
    /teaser\.style\.display\s*=\s*["']["']/,          // display = ""  (resets to visible)
    /teaser\.removeAttribute\s*\(\s*["']hidden["']\s*\)/,
    /teaser\.style\.visibility\s*=\s*["']visible["']/,
  ];

  // Locate maybeShowTeaser body — we already checked it is a no-op, but let's
  // also confirm none of the show patterns appear inside it.
  const startMarker = 'function maybeShowTeaser()';
  const startIdx    = src.indexOf(startMarker);
  let teaserBody    = '';

  if (startIdx !== -1) {
    const braceStart = src.indexOf('{', startIdx);
    let depth = 0, i = braceStart, end = -1;
    for (; i < src.length; i++) {
      if (src[i] === '{') depth++;
      else if (src[i] === '}') { depth--; if (depth === 0) { end = i; break; } }
    }
    if (end !== -1) teaserBody = src.slice(braceStart + 1, end);
  }

  for (const pat of showPatterns) {
    const foundInTeaser = pat.test(teaserBody);
    check(
      !foundInTeaser,
      'maybeShowTeaser() does not contain a teaser-show call (' + pat + ')'
    );
  }

  // Broader check: confirm no setTimeout at module scope passes a show-pattern
  // callback.  We look for the pattern outside the known safe functions.
  //
  // Strategy: remove the open() function body from consideration (it is the
  // only legitimate place that calls dismissTeaser(true), which hides — not
  // shows — the teaser), then scan the remainder.
  //
  // We also remove dismissTeaser() itself since it only ever sets display:none.

  let remainder = src;
  for (const fnName of ['open', 'dismissTeaser', 'close']) {
    const marker = 'function ' + fnName + '(';
    const idx    = remainder.indexOf(marker);
    if (idx === -1) continue;
    const bStart = remainder.indexOf('{', idx);
    if (bStart === -1) continue;
    let d = 0, j = bStart, e = -1;
    for (; j < remainder.length; j++) {
      if (remainder[j] === '{') d++;
      else if (remainder[j] === '}') { d--; if (d === 0) { e = j; break; } }
    }
    if (e !== -1) {
      remainder = remainder.slice(0, idx) + remainder.slice(e + 1);
    }
  }

  for (const pat of showPatterns) {
    const foundOutside = pat.test(remainder);
    check(
      !foundOutside,
      'No auto-show of teaser outside user-triggered handlers (' + pat + ')'
    );
    if (foundOutside) {
      // Find and print the offending line for easier debugging
      const lines = remainder.split('\n');
      for (let li = 0; li < lines.length; li++) {
        if (pat.test(lines[li])) {
          console.error('     Line ~' + (li + 1) + ':', lines[li].trim().slice(0, 120));
        }
      }
    }
  }
})();

// ── Summary ───────────────────────────────────────────────────────────────────
console.log('\n' + '═'.repeat(60));
if (allPassed) {
  console.log('✅  All chat-teaser checks PASSED — teaser stays closed on first visit');
  process.exit(0);
} else {
  console.log('❌  One or more chat-teaser checks FAILED — see above');
  console.log('    To fix: ensure maybeShowTeaser() in assets/chat.js is a bare no-op.');
  process.exit(1);
}
