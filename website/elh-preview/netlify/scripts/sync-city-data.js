#!/usr/bin/env node
/**
 * sync-city-data.js
 * ──────────────────────────────────────────────────────────────────────────────
 * Regenerates city-data.json from the published city-page HTML files
 * (hospice-*-ca.html) so the /coverage?list=true endpoint is always in sync
 * with whatever pages have actually been deployed.
 *
 * Run automatically via the Netlify build command before every deploy.
 *
 * Usage
 *   node netlify/scripts/sync-city-data.js          # sync & write
 *   node netlify/scripts/sync-city-data.js --check  # CI mode — exit 1 if stale
 *
 * The script is pure Node.js with no npm dependencies so it works
 * in Netlify's build environment with no install step.
 *
 * How data is sourced
 *   · canonicalUrl  — <link rel="canonical">
 *   · title         — <title>
 *   · metaDesc      — <meta name="description">
 *   · h1            — first <h1> text
 *   · heroEyebrow   — .eyebrow div text (→ county + subregion extraction)
 *   · lat/lng       — JSON-LD MedicalOrganization.geo (if present)
 *   · faqItems      — JSON-LD FAQPage.mainEntity
 *   · dateModified  — JSON-LD WebPage.dateModified
 *   · publishStatus — "published" for every page that exists on disk
 *                     (pages with <meta name="robots" content="noindex"> → "draft")
 *
 * Existing city-data.json entries are merged rather than overwritten, so any
 * hand-curated fields (atAGlanceSummary, localIntroduction, etc.) are preserved.
 * New entries are appended with whatever can be extracted automatically.
 */

"use strict";

const fs   = require("fs");
const path = require("path");

// ── Paths ─────────────────────────────────────────────────────────────────────
const CHECK_MODE    = process.argv.includes("--check");
const SCRIPT_DIR    = __dirname;                                         // netlify/scripts/
const SITE_DIR      = path.resolve(SCRIPT_DIR, "..", "..");              // website/elh-preview/
const CITY_DATA     = path.resolve(SITE_DIR, "..", "city-data.json");   // website/city-data.json

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Strip HTML tags, decode common entities, collapse whitespace. */
function stripHtml(html) {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&middot;/gi, "·")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&nbsp;/gi, " ")
    .replace(/&#\d+;/g, (m) => {
      const code = parseInt(m.slice(2, -1), 10);
      return String.fromCodePoint(code);
    })
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Extract all JSON-LD script blocks from an HTML string.
 * Returns an array of parsed objects (invalid JSON is silently skipped).
 */
function extractJsonLd(html) {
  const results = [];
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    try { results.push(JSON.parse(m[1])); } catch (_) { /* skip invalid */ }
  }
  return results;
}

/**
 * Parse the .eyebrow text ("Serving CITY · SUBREGION · COUNTY") and return
 * { county, subregion }.  County is normalised to "Los Angeles County" or
 * "Ventura County".
 */
function parseEyebrow(raw) {
  const text = raw
    .replace(/&middot;/gi, "·")
    .replace(/·/g, "·")      // normalise fancy bullets
    .replace(/\s+/g, " ")
    .trim();

  const withoutServing = text.replace(/^Serving\s+/i, "");
  const parts = withoutServing.split("·").map((p) => p.trim()).filter(Boolean);

  if (parts.length === 0) return { county: "", subregion: "" };

  // Last segment containing "County" → county name
  const lastPart = parts[parts.length - 1];
  let countyRaw = "";
  let subregionParts = [];

  if (lastPart.includes("County")) {
    countyRaw = lastPart;
    subregionParts = parts.slice(1, -1); // skip city (idx 0) and county (last)
  } else {
    // No explicit county in eyebrow — treat remaining parts as subregion
    subregionParts = parts.slice(1);
  }

  // Normalise county to one of the two known values
  let county = "";
  if (countyRaw.includes("Los Angeles")) county = "Los Angeles County";
  else if (countyRaw.includes("Ventura"))  county = "Ventura County";

  // Subregion: joined middle parts, fallback to the raw county text
  const subregion = subregionParts.length
    ? subregionParts.join(" · ")
    : countyRaw || "";

  return { county, subregion };
}

/**
 * Parse one city HTML file and return a partial city-data record.
 * Fields that cannot be reliably extracted are omitted (caller merges them
 * from the existing city-data.json entry).
 */
function parseCityPage(filePath) {
  const html = fs.readFileSync(filePath, "utf8");
  const filename = path.basename(filePath);                        // hospice-agoura-hills-ca.html
  const slug = filename.replace(/^hospice-/, "").replace(/-ca\.html$/, "");

  // publishStatus — noindex pages are "draft"
  const publishStatus = /name=["']robots["'][^>]+content=["'][^"']*noindex/i.test(html)
    ? "draft"
    : "published";

  // canonicalUrl
  const canonMatch = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i)
    || html.match(/<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["']/i);
  const canonicalUrl = canonMatch ? canonMatch[1] : "";

  // title
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  const title = titleMatch ? titleMatch[1].trim() : "";

  // metaDescription
  const descMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i)
    || html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+name=["']description["']/i);
  const metaDescription = descMatch ? descMatch[1].trim() : "";

  // h1
  const h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  const h1 = h1Match ? stripHtml(h1Match[1]) : "";

  // City name: strip "Hospice Care in " prefix and ", California" suffix from h1
  const city = h1
    .replace(/^Hospice Care in\s+/i, "")
    .replace(/,\s*California$/i, "")
    .trim();

  // heroEyebrow — first .eyebrow div
  const eyebrowMatch = html.match(/class=["'][^"']*eyebrow[^"']*["'][^>]*>([\s\S]*?)<\/div>/i);
  const heroEyebrow = eyebrowMatch ? stripHtml(eyebrowMatch[1]) : "";
  let { county, subregion } = parseEyebrow(heroEyebrow);

  // JSON-LD blocks
  const jsonLdBlocks = extractJsonLd(html);

  // lat/lng from MedicalOrganization.geo
  let latitude  = null;
  let longitude = null;
  for (const block of jsonLdBlocks) {
    const types = [].concat(block["@type"] || []);
    if (types.includes("MedicalOrganization") || types.includes("LocalBusiness")) {
      if (block.geo) {
        latitude  = block.geo.latitude  ?? null;
        longitude = block.geo.longitude ?? null;
      }
      // County fallback from areaServed if eyebrow parse was inconclusive
      if (!county && Array.isArray(block.areaServed)) {
        const adminArea = block.areaServed.find(
          (a) => a["@type"] === "AdministrativeArea" && String(a.name || "").includes("County")
        );
        if (adminArea) {
          const raw = adminArea.name;
          if (raw.includes("Los Angeles")) county = "Los Angeles County";
          else if (raw.includes("Ventura")) county = "Ventura County";
        }
      }
    }
  }

  // dateModified from WebPage JSON-LD
  let lastMaterialUpdate = "";
  for (const block of jsonLdBlocks) {
    if (block["@type"] === "WebPage" && block.dateModified) {
      lastMaterialUpdate = block.dateModified;
      break;
    }
  }

  // faqItems from FAQPage JSON-LD
  let faqItems = [];
  for (const block of jsonLdBlocks) {
    if (block["@type"] === "FAQPage" && Array.isArray(block.mainEntity)) {
      faqItems = block.mainEntity.map((q) => ({
        q: q.name || "",
        a: q.acceptedAnswer ? q.acceptedAnswer.text : ""
      }));
      break;
    }
  }

  const record = {
    slug,
    city,
    county,
    subregion,
    canonicalUrl,
    title,
    metaDescription,
    h1,
    heroEyebrow,
    publishStatus,
    lastMaterialUpdate,
    faqItems
  };

  if (latitude  !== null) record.latitude  = latitude;
  if (longitude !== null) record.longitude = longitude;

  return record;
}

// ── Main ──────────────────────────────────────────────────────────────────────

// 1. Load existing city-data.json
const existingRaw = JSON.parse(fs.readFileSync(CITY_DATA, "utf8"));
const existingBySlug = {};
for (const entry of existingRaw) existingBySlug[entry.slug] = entry;

// 2. Find all city HTML pages (exclude the county hub page)
const htmlFiles = fs.readdirSync(SITE_DIR)
  .filter((f) => /^hospice-.+-ca\.html$/.test(f) && !f.includes("county"))
  .map((f)    => path.join(SITE_DIR, f))
  .sort();

if (htmlFiles.length === 0) {
  console.error("ERROR: No hospice-*-ca.html files found in", SITE_DIR);
  process.exit(1);
}

// 3. Parse each HTML file and merge with existing data
const newEntries = [];
let addedCount   = 0;
let updatedCount = 0;

for (const file of htmlFiles) {
  const parsed  = parseCityPage(file);
  const existing = existingBySlug[parsed.slug];

  if (existing) {
    // Merge: HTML-sourced fields win for structural data, but preserve
    // rich hand-curated prose fields that are NOT easily extracted from HTML.
    const merged = Object.assign({}, existing, {
      // Always refresh from HTML
      slug:             parsed.slug,
      canonicalUrl:     parsed.canonicalUrl || existing.canonicalUrl,
      title:            parsed.title        || existing.title,
      metaDescription:  parsed.metaDescription || existing.metaDescription,
      h1:               parsed.h1           || existing.h1,
      heroEyebrow:      parsed.heroEyebrow  || existing.heroEyebrow,
      publishStatus:    parsed.publishStatus,
      lastMaterialUpdate: parsed.lastMaterialUpdate || existing.lastMaterialUpdate,
      faqItems:         parsed.faqItems.length ? parsed.faqItems : existing.faqItems,
      // Refresh coordinates only when found in HTML (don't clobber existing)
      ...(parsed.latitude  !== undefined ? { latitude:  parsed.latitude  } : {}),
      ...(parsed.longitude !== undefined ? { longitude: parsed.longitude } : {}),
      // Refresh city/county/subregion from HTML only if the existing values
      // look like they were auto-generated (i.e. match the HTML value exactly
      // or the existing JSON has an empty value).
      city:      parsed.city      || existing.city,
      county:    parsed.county    || existing.county,
      subregion: parsed.subregion || existing.subregion,
    });
    newEntries.push(merged);
    // Only count as "updated" if the merged record actually changed
    if (JSON.stringify(merged) !== JSON.stringify(existing)) updatedCount++;
  } else {
    // Brand-new city page not yet in city-data.json
    // Build a complete record with auto-extracted fields and empty prose stubs
    const newEntry = {
      slug:              parsed.slug,
      city:              parsed.city,
      county:            parsed.county,
      subregion:         parsed.subregion,
      latitude:          parsed.latitude  ?? null,
      longitude:         parsed.longitude ?? null,
      canonicalUrl:      parsed.canonicalUrl,
      title:             parsed.title,
      metaDescription:   parsed.metaDescription,
      h1:                parsed.h1,
      heroEyebrow:       parsed.heroEyebrow,
      atAGlanceSummary:  "",
      localIntroduction: "",
      localNearbyParagraph: "",
      nearbyCityPages:   [],
      faqItems:          parsed.faqItems,
      lastMaterialUpdate: parsed.lastMaterialUpdate,
      publishStatus:     parsed.publishStatus
    };
    newEntries.push(newEntry);
    addedCount++;
    console.log("  + NEW:", parsed.city, `(${parsed.slug})`);
  }
}

// 4. Sort alphabetically by city name (case-insensitive)
newEntries.sort((a, b) => a.city.localeCompare(b.city, "en"));

// 5. Compare with existing to detect drift
const newJson     = JSON.stringify(newEntries, null, 2);
const existingJson = JSON.stringify(
  existingRaw.slice().sort((a, b) => a.city.localeCompare(b.city, "en")),
  null,
  2
);

const changed = newJson !== existingJson;

if (CHECK_MODE) {
  // ── CI / check mode ──────────────────────────────────────────────────────
  if (changed) {
    console.error(
      "FAIL: city-data.json is out of sync with the city page HTML files."
    );
    if (addedCount)   console.error(`  ${addedCount} page(s) in HTML but missing from city-data.json`);
    if (updatedCount) console.error(`  ${updatedCount} existing entries would be updated`);
    console.error(
      "\nRun `node netlify/scripts/sync-city-data.js` to regenerate."
    );
    process.exit(1);
  } else {
    console.log("OK: city-data.json is in sync with all city page HTML files.");
    process.exit(0);
  }
}

// ── Write mode ───────────────────────────────────────────────────────────────
if (!changed) {
  console.log(
    `city-data.json is already up to date (${newEntries.length} cities).`
  );
  process.exit(0);
}

fs.writeFileSync(CITY_DATA, newJson + "\n", "utf8");
console.log(
  `city-data.json regenerated: ${newEntries.length} cities` +
  (addedCount   ? `, ${addedCount} new`     : "") +
  (updatedCount ? `, ${updatedCount} updated` : "")
);
