#!/usr/bin/env node
/**
 * build-search-index.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Regenerates website/elh-preview/assets/search-index.json from the HTML
 * source files so new pages appear in site search automatically.
 *
 * What it does
 *   • Walks all HTML files under website/elh-preview/
 *   • Extracts <title>, <meta name="description">, and <link rel="canonical">
 *   • Strips the " | Eternal Life Hospice" site-name suffix from titles
 *   • Skips utility/noindex/internal pages (see SKIP_FILES / noindex check)
 *   • Preserves hand-authored `kw` and `cat` fields for URLs already in index
 *   • Infers `cat` for brand-new pages from their URL pattern
 *   • Keeps existing entry order; appends newly discovered pages at the end
 *   • Idempotent — safe to run on every deploy
 *
 * Usage
 *   node website/elh-preview/assets/build-search-index.js
 *
 * It is wired into the Netlify build command in netlify.toml so it runs
 * automatically before every production deploy.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ── Paths ────────────────────────────────────────────────────────────────────
const SITE_ROOT  = path.resolve(__dirname, '..');          // website/elh-preview/
const INDEX_PATH = path.resolve(__dirname, 'search-index.json');

// ── Pages to exclude from the index ─────────────────────────────────────────
// Directories whose HTML files are not public site pages.
const SKIP_DIRS = new Set(['assets', 'es']);

// Individual filenames (basename only) to always exclude.
const SKIP_FILES = new Set([
  '404.html',
  'aleksandradubina.html',
  'card-aleksandra-dubina.html',
  'card-denise-chavez.html',
  'referral-card.html',
  'sitemap.html',
  'privacy-policy.html',
  'terms.html',
]);

// ── City keyword auto-generator ───────────────────────────────────────────────
/**
 * Builds a baseline `kw` string for a city page from its title and description.
 * Only used when the existing index entry has an empty kw field.
 *
 * Extracts:
 *   - City name  from title  e.g. "Hospice Care in Long Beach, CA" → "long beach"
 *   - Subregion  from desc   e.g. "… — South Bay, Los Angeles County. …" → "south bay"
 *   - County     from desc   e.g. "Los Angeles County" → "los angeles county"
 */
function generateCityKw(title, desc) {
  const parts = [];

  // City name
  const cityMatch = title && title.match(/Hospice Care in (.+?),?\s*CA\b/i);
  if (cityMatch) parts.push(cityMatch[1].trim().toLowerCase());

  // Subregion + county from the em-dash clause: "— Subregion, County."
  const regionMatch = desc && desc.match(/—\s*(.+?),\s*((Los Angeles|Ventura|Orange|San Bernardino|Riverside)\s+County)/i);
  if (regionMatch) {
    const subregion = regionMatch[1].trim().toLowerCase();
    const county    = regionMatch[2].trim().toLowerCase();
    if (subregion && !parts.includes(subregion)) parts.push(subregion);
    if (county    && !parts.includes(county))    parts.push(county);
  }

  return parts.join(', ');
}

// ── Category inference from URL ───────────────────────────────────────────────
function inferCat(url) {
  if (url === '/')                         return 'Home';
  if (url === '/refer')                    return 'Provider';
  if (url === '/resources')                return 'Resource';
  if (url === '/blog')                     return 'Journal';
  if (url === '/care-brief')               return 'Newsletter';
  if (url === '/sound-bath')               return 'Therapy';
  if (url === '/family-guide')             return 'Guide';
  if (url === '/careers')                  return 'Career';
  if (url === '/volunteer')                return 'Volunteer';
  if (url === '/media-kit')                return 'Press';
  if (url === '/hospice-care')             return 'Guide';
  if (url === '/services')                 return 'Service';
  if (url.startsWith('/services/'))        return 'Service';
  if (url.startsWith('/resources/'))       return 'Resource';
  if (url.startsWith('/blog/'))            return 'Journal';
  if (url.startsWith('/care-brief/'))      return 'Article';
  if (/^\/hospice-.+-ca$/.test(url))      return 'City';
  return 'Page';
}

// ── HTML mini-parser helpers ──────────────────────────────────────────────────
function extractMeta(html, name) {
  // Handles both name= and property= forms; value in content=
  const re = new RegExp(
    `<meta[^>]+(?:name|property)=["']${name}["'][^>]+content=["']([^"']*?)["']` +
    `|<meta[^>]+content=["']([^"']*?)["'][^>]+(?:name|property)=["']${name}["']`,
    'i'
  );
  const m = html.match(re);
  return m ? decodeHtmlEntities((m[1] || m[2] || '').trim()) : null;
}

function extractTitle(html) {
  const m = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (!m) return null;
  let t = decodeHtmlEntities(m[1].trim());
  // Strip common site-name suffixes
  t = t.replace(/\s*[\|–—]\s*Eternal Life Hospice.*$/i, '').trim();
  return t || null;
}

function extractCanonical(html) {
  const m = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i)
         || html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  if (!m) return null;
  try {
    return new URL(m[1]).pathname.replace(/\/$/, '') || '/';
  } catch {
    return null;
  }
}

function hasNoIndex(html) {
  return /<meta[^>]+name=["']robots["'][^>]+content=["'][^"']*noindex/i.test(html);
}

function decodeHtmlEntities(str) {
  return str
    .replace(/&amp;/g,  '&')
    .replace(/&lt;/g,   '<')
    .replace(/&gt;/g,   '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g,  "'")
    .replace(/&mdash;/g,'—')
    .replace(/&ndash;/g,'–')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n, 10)));
}

// ── File walker ───────────────────────────────────────────────────────────────
function findHtmlFiles(dir, results = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) {
        findHtmlFiles(path.join(dir, entry.name), results);
      }
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      if (!SKIP_FILES.has(entry.name)) {
        results.push(path.join(dir, entry.name));
      }
    }
  }
  return results;
}

// ── Main ──────────────────────────────────────────────────────────────────────
function main() {
  // 1. Load existing index; build lookup by URL (preserves kw + cat).
  let existing = [];
  try {
    existing = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
  } catch {
    console.warn('[search-index] No existing index found; starting fresh.');
  }

  const existingByUrl = new Map();
  for (const entry of existing) {
    existingByUrl.set(entry.url, entry);
  }

  // 2. Scan HTML files.
  const htmlFiles = findHtmlFiles(SITE_ROOT);
  const discovered = new Map(); // url → { title, desc, cat, kw }

  for (const filePath of htmlFiles) {
    let html;
    try {
      html = fs.readFileSync(filePath, 'utf8');
    } catch {
      continue;
    }

    if (hasNoIndex(html)) continue;

    const canonical = extractCanonical(html);
    if (!canonical) continue;  // No canonical = don't index

    const title = extractTitle(html);
    const desc  = extractMeta(html, 'description');

    if (!title && !desc) continue;  // Nothing useful

    const prev         = existingByUrl.get(canonical);
    const resolvedTitle = title || prev?.title || '';
    const resolvedDesc  = desc  || prev?.desc  || '';
    const cat           = prev?.cat ?? inferCat(canonical);
    // Preserve any hand-authored kw; auto-generate for city pages with blank kw.
    const autoKw        = (cat === 'City') ? generateCityKw(resolvedTitle, resolvedDesc) : '';
    const kw            = prev?.kw || autoKw;

    discovered.set(canonical, {
      url:   canonical,
      title: resolvedTitle,
      desc:  resolvedDesc,
      cat,
      kw,
    });
  }

  // 3. Rebuild index: existing order first, then new entries appended.
  const output = [];
  const seen   = new Set();

  // Preserve all existing entries (updated with fresh title/desc if found).
  for (const entry of existing) {
    const fresh = discovered.get(entry.url);
    if (fresh) {
      output.push(fresh);
    } else {
      // Keep entries for pages we couldn't scan (e.g. redirects, hand-curated).
      output.push(entry);
    }
    seen.add(entry.url);
  }

  // Append newly discovered pages (not previously in the index).
  let added = 0;
  for (const [url, entry] of discovered) {
    if (!seen.has(url)) {
      output.push(entry);
      seen.add(url);
      added++;
      console.log(`[search-index] + new page: ${url}`);
    }
  }

  // 4. Write output.
  const json = JSON.stringify(output, null, 2);
  fs.writeFileSync(INDEX_PATH, json, 'utf8');

  console.log(
    `[search-index] Done. ${output.length} entries total` +
    (added ? `, ${added} new.` : ', no new pages.')
  );
}

main();
