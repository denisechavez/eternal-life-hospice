/**
 * test-nav-scroll.js
 *
 * Static guard for the hamburger nav overflow rules.
 *
 * What it checks
 * --------------
 * 1. `#hdr.nav-open nav` in assets/elh.css declares `max-height` containing
 *    `calc(100vh - 74px)` — the nav panel is height-capped on small screens.
 * 2. `#hdr.nav-open nav` in elh.css declares `overflow-y:auto` (or `scroll`) —
 *    items below the viewport are reachable by scrolling.
 * 3. Every HTML file under website/elh-preview/ that contains an inline
 *    `#hdr.nav-open nav` rule also declares both of the above properties —
 *    inline <style> blocks cannot silently override and drop the scroll cap.
 * 4. The nav in index.html has at least MIN_NAV_LINKS links — enough to fill a
 *    375 px viewport and make the scroll guard meaningful.
 *
 * Why a static check?
 * -------------------
 * The rules are a CSS guarantee: removing `max-height` makes bottom links
 * unreachable on short phones; removing `overflow-y:auto` silently clips them.
 * Both regressions are caught here without needing a live browser.
 *
 * Usage:
 *   node test-nav-scroll.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const fs   = require("fs");
const path = require("path");

// Paths relative to this script (exports/outreach-tracker-src/)
const REPO_ROOT   = path.resolve(__dirname, "..", "..");
const ELH_CSS     = path.join(REPO_ROOT, "website", "elh-preview", "assets", "elh.css");
const PREVIEW_DIR = path.join(REPO_ROOT, "website", "elh-preview");

const MIN_NAV_LINKS = 5; // minimum links to make the scroll cap meaningful

// ─── helpers ────────────────────────────────────────────────────────────────

/**
 * Walk a directory tree recursively and return all file paths whose names
 * satisfy the predicate.  Follows directories but not symlinks.
 */
function walkHtmlFiles(dir, results = []) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (_) {
    return results;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkHtmlFiles(full, results);
    } else if (entry.isFile() && entry.name.endsWith(".html")) {
      results.push(full);
    }
  }
  return results;
}

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

function readFile(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (err) {
    console.error(`ERROR: Could not read ${filePath}:`, err.message);
    process.exit(1);
  }
}

/**
 * Extract all rule-blocks for a given selector from a CSS string.
 * Returns an array of declaration strings (the content between { and }).
 * Handles minified CSS (no whitespace around braces).
 */
function extractRuleBlocks(css, selector) {
  // Escape special regex chars in selector
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Match selector followed by { ... } — non-greedy, handles minified CSS
  const pattern = new RegExp(escaped + "\\s*\\{([^}]*)\\}", "g");
  const blocks = [];
  let m;
  while ((m = pattern.exec(css)) !== null) {
    blocks.push(m[1]);
  }
  return blocks;
}

/**
 * Return all inline <style> block contents from an HTML string.
 */
function extractStyleBlocks(html) {
  const blocks = [];
  const re = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    blocks.push(m[1]);
  }
  return blocks;
}

/**
 * Count <a href= occurrences inside the first <nav>…</nav> block.
 */
function countNavLinks(html) {
  const navMatch = html.match(/<nav[\s>]([\s\S]*?)<\/nav>/i);
  if (!navMatch) return 0;
  return (navMatch[1].match(/<a\s+href=/gi) || []).length;
}

// ─── run ────────────────────────────────────────────────────────────────────

function run() {
  console.log("=== hamburger nav scroll-overflow static check ===\n");

  // ── 1. Check shared stylesheet ──────────────────────────────────────────
  console.log("[ elh.css — shared stylesheet ]");
  const sharedCss = readFile(ELH_CSS);
  const sharedBlocks = extractRuleBlocks(sharedCss, "#hdr.nav-open nav");

  assert(
    sharedBlocks.length > 0,
    "#hdr.nav-open nav rule exists in assets/elh.css"
  );

  if (sharedBlocks.length > 0) {
    const combined = sharedBlocks.join(" ");

    assert(
      /max-height\s*:\s*calc\(100vh\s*-\s*74px\)/.test(combined),
      "#hdr.nav-open nav in elh.css has max-height:calc(100vh - 74px)"
    );

    assert(
      /overflow-y\s*:\s*(auto|scroll)/.test(combined),
      "#hdr.nav-open nav in elh.css has overflow-y:auto (or scroll)"
    );
  }

  console.log();

  // ── 2. Check every HTML file with an inline #hdr.nav-open nav rule ──────
  console.log("[ inline <style> blocks in HTML files ]");

  // Collect all .html files under website/elh-preview/ recursively so that
  // standalone pages added in sub-folders are automatically covered.
  const htmlFiles = walkHtmlFiles(PREVIEW_DIR);

  let inlineChecked = 0;

  for (const htmlFile of htmlFiles) {
    const html = readFile(htmlFile);
    const styleBlocks = extractStyleBlocks(html);
    const rel = path.relative(REPO_ROOT, htmlFile);

    for (const block of styleBlocks) {
      const ruleBlocks = extractRuleBlocks(block, "#hdr.nav-open nav");
      if (ruleBlocks.length === 0) continue; // this style block doesn't define the rule

      const combined = ruleBlocks.join(" ");
      inlineChecked++;

      assert(
        /max-height\s*:\s*calc\(100vh\s*-\s*74px\)/.test(combined),
        `${rel} inline CSS: #hdr.nav-open nav has max-height:calc(100vh - 74px)`
      );

      assert(
        /overflow-y\s*:\s*(auto|scroll)/.test(combined),
        `${rel} inline CSS: #hdr.nav-open nav has overflow-y:auto (or scroll)`
      );
    }
  }

  if (inlineChecked === 0) {
    console.log("  INFO: no inline #hdr.nav-open nav rules found in any HTML file under elh-preview/");
  }

  console.log();

  // ── 3. Nav link count — index.html ──────────────────────────────────────
  console.log("[ nav link count — index.html ]");
  const indexHtml = readFile(path.join(PREVIEW_DIR, "index.html"));
  const linkCount = countNavLinks(indexHtml);

  assert(
    linkCount >= MIN_NAV_LINKS,
    `index.html nav has at least ${MIN_NAV_LINKS} links (found ${linkCount}) — scroll guard is meaningful`
  );

  console.log();

  if (process.exitCode === 1) {
    console.error("=== FAILED — one or more assertions did not pass ===");
  } else {
    console.log("=== all checks passed ===");
  }
}

run();
