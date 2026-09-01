#!/usr/bin/env node
/**
 * update-sitemap-dates.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Refreshes every <lastmod> in sitemap.xml to match the date of the last Git
 * commit that touched the corresponding HTML source file.
 *
 * Why Git commit dates, not filesystem mtimes
 *   Netlify (and most CI systems) use a shallow Git clone, so all files get
 *   the same checkout timestamp. Filesystem mtime is therefore meaningless in
 *   CI — every entry would show today's date regardless of whether the page
 *   actually changed. Git's own commit history is the canonical source of
 *   per-file change dates.
 *
 * Why lastmod accuracy matters for this site
 *   Google uses lastmod as a freshness signal. When city pages receive content
 *   updates (neighborhood keywords, nav changes, schema edits) but the sitemap
 *   still shows a stale batch date, Googlebot deprioritises recrawling — which
 *   causes pages to linger as "Discovered – currently not indexed" in Search
 *   Console long after they have been updated.
 *
 * Prerequisite
 *   The Netlify build command must run `git fetch --unshallow 2>/dev/null || true`
 *   before this script so that shallow clones are converted to full history.
 *   Without full history, `git log -1` only looks back one commit and will
 *   return empty for any file that was not touched in the most-recent commit.
 *
 * How it works
 *   1. Reads sitemap.xml
 *   2. For each <url>, maps the pathname to an HTML file under elh-preview/
 *      (e.g. /hospice-malibu-ca → hospice-malibu-ca.html)
 *   3. Runs `git log --date=short --format=%ad -1 -- <file>` to get the
 *      last-commit date (YYYY-MM-DD) for that file
 *   4. Replaces <lastmod> with that date
 *   5. If git returns nothing (file not in history) or the file doesn't exist,
 *      the existing <lastmod> is preserved — no silent breakage
 *   6. Writes sitemap.xml back in-place
 *
 * Usage
 *   node website/elh-preview/assets/update-sitemap-dates.js
 *
 * Wired into netlify.toml so it runs automatically before every deploy.
 */

'use strict';

const fs            = require('fs');
const path          = require('path');
const { execSync }  = require('child_process');

// ── Paths ────────────────────────────────────────────────────────────────────
const SITE_ROOT = path.resolve(__dirname, '..');          // website/elh-preview/
const SITEMAP   = path.resolve(SITE_ROOT, 'sitemap.xml');
const BASE_URL  = 'https://eternallifehospice.com';

// ── URL → relative file path (relative to SITE_ROOT) ─────────────────────────
/**
 * Given a full sitemap URL, returns the relative file path within SITE_ROOT
 * that Netlify would serve for that URL, or null if no file is found.
 *
 * Resolution order (mirrors Netlify pretty-URL precedence):
 *   1. {pathname}.html          e.g. hospice-malibu-ca.html
 *   2. {pathname}/index.html    e.g. blog/index.html
 *   3. index.html               for the root URL
 */
function urlToRelPath(url) {
  let pathname = url.replace(BASE_URL, '').replace(/\/$/, '');

  if (pathname === '' || pathname === '/') {
    return fs.existsSync(path.join(SITE_ROOT, 'index.html')) ? 'index.html' : null;
  }

  const rel = pathname.slice(1);  // strip leading slash

  const direct = rel + '.html';
  if (fs.existsSync(path.join(SITE_ROOT, direct))) return direct;

  const dirIndex = rel + '/index.html';
  if (fs.existsSync(path.join(SITE_ROOT, dirIndex))) return dirIndex;

  return null;
}

// ── Git last-commit date ──────────────────────────────────────────────────────
/**
 * Returns the YYYY-MM-DD date of the most recent commit that touched `relPath`
 * (relative to SITE_ROOT), or null when git cannot find a commit.
 */
function gitLastModDate(relPath) {
  try {
    const date = execSync(
      // %ad = author date, --date=short → YYYY-MM-DD, -1 = most recent commit
      `git log --date=short --format=%ad -1 -- "${relPath}"`,
      {
        cwd:      SITE_ROOT,
        encoding: 'utf8',
        stdio:    ['pipe', 'pipe', 'pipe'],
      }
    ).trim();
    // git returns empty string when no commit history found for the path
    return date || null;
  } catch {
    return null;
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
function main() {
  let xml;
  try {
    xml = fs.readFileSync(SITEMAP, 'utf8');
  } catch (err) {
    console.error(`[sitemap] ERROR: Could not read sitemap.xml — ${err.message}`);
    process.exit(1);
  }

  let updated = 0;
  let kept    = 0;   // entries where git returned no date (existing date preserved)
  let missing = 0;   // entries with no matching HTML file

  const result = xml.replace(/<url>([\s\S]*?)<\/url>/g, (block) => {
    const locMatch = block.match(/<loc>([^<]+)<\/loc>/);
    if (!locMatch) return block;

    const loc     = locMatch[1].trim();
    const relPath = urlToRelPath(loc);

    if (!relPath) {
      // No HTML file found on disk — keep existing lastmod unchanged.
      missing++;
      return block;
    }

    const date = gitLastModDate(relPath);

    if (!date) {
      // File exists but has no git history (e.g. untracked) — keep existing date.
      kept++;
      return block;
    }

    const replaced = block.replace(/<lastmod>[^<]+<\/lastmod>/, `<lastmod>${date}</lastmod>`);
    if (replaced !== block) updated++;
    return replaced;
  });

  fs.writeFileSync(SITEMAP, result, 'utf8');

  const parts = [`[sitemap] Done. ${updated} lastmod date(s) updated`];
  if (kept)    parts.push(`${kept} kept (no git history)`);
  if (missing) parts.push(`${missing} kept (no matching file)`);
  console.log(parts.join(', ') + '.');
}

main();
