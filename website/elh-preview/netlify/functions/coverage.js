/**
 * Eternal Life Hospice — coverage lookup (Netlify Function)
 *
 * Lets AI agents and other callers check whether ELH serves a given city
 * with a structured yes/no answer rather than inferring from page text.
 *
 *   GET /.netlify/functions/coverage?city=Pasadena
 *
 * Response (served):
 *   { "served": true, "city": "Pasadena", "county": "Los Angeles County",
 *     "subregion": "San Gabriel Valley", "pageUrl": "https://...", "phone": "..." }
 *
 * Response (not served / unknown):
 *   { "served": false, "city": "San Francisco", "message": "..." }
 *
 * No auth required — this is public read-only data with no PII.
 * city-data.json is bundled at deploy time by esbuild, so the cold-start
 * cost is a single require() from the bundle, not a filesystem read.
 */

/* eslint-disable @typescript-eslint/no-var-requires */
const cities = require("../../../city-data.json");

const PHONE = "805.953.7273";

// ── Normalise a city name for comparison ──────────────────────────────────────
// Strips accents (ñ→n, é→e), lowercases, removes punctuation.
// "La Cañada Flintridge" and "La Canada Flintridge" both become
// "la canada flintridge", so callers don't need to type diacritics.
function normalise(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip combining diacritics
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "") // drop punctuation
    .replace(/\s+/g, " ")
    .trim();
}

// ── Build lookup index once at cold-start ─────────────────────────────────────
const index = cities
  .filter(function (c) { return c.publishStatus === "published"; })
  .map(function (c) {
    return {
      city: c.city,
      county: c.county,
      subregion: c.subregion,
      canonicalUrl: c.canonicalUrl,
      // pre-computed normalised forms for fast matching
      _normCity: normalise(c.city),
      _normSlug: c.slug.replace(/-/g, " ")  // slug is already ASCII-safe
    };
  });

// ── Handler ───────────────────────────────────────────────────────────────────
exports.handler = async function (event) {
  const headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Cache-Control": "public, max-age=3600" // 1 hour; data changes infrequently
  };

  // CORS pre-flight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: headers, body: "" };
  }

  if (event.httpMethod !== "GET") {
    return {
      statusCode: 405,
      headers: headers,
      body: JSON.stringify({ error: "Method not allowed. Use GET /.netlify/functions/coverage?city=CityName" })
    };
  }

  const params = event.queryStringParameters || {};

  // ── List mode: ?list=true returns all published cities in one payload ─────────
  if (params.list === "true") {
    const listHeaders = Object.assign({}, headers, {
      "Cache-Control": "public, max-age=86400" // 1 day; list changes only on new city-page publish
    });
    const counties = Array.from(new Set(index.map(function (c) { return c.county; }))).sort();
    return {
      statusCode: 200,
      headers: listHeaders,
      body: JSON.stringify({
        cities: index.map(function (c) {
          return {
            city: c.city,
            county: c.county,
            subregion: c.subregion,
            pageUrl: c.canonicalUrl
          };
        }),
        total: index.length,
        counties: counties,
        phone: PHONE
      })
    };
  }

  const raw = params.city || "";
  const trimmed = raw.trim();

  if (!trimmed) {
    return {
      statusCode: 400,
      headers: headers,
      body: JSON.stringify({
        error: "Missing required query parameter: city",
        example: "/.netlify/functions/coverage?city=Pasadena",
        tip: "To fetch all published cities at once use: /.netlify/functions/coverage?list=true"
      })
    };
  }

  const q = normalise(trimmed);

  // 1. Exact match on city name or slug-derived name
  let match = index.find(function (c) {
    return c._normCity === q || c._normSlug === q;
  });

  // 2. Prefix / contained match — only fires when the normalised query is at
  //    least 4 characters (guards against very-short inputs like "W" or "San"
  //    returning a confidently-wrong result).
  //    When multiple cities share the same prefix the query is ambiguous: we
  //    return served:false + a suggestions list instead of picking the first.
  if (!match && q.length >= 4) {
    const prefixMatches = index.filter(function (c) {
      return c._normCity.startsWith(q) || q.startsWith(c._normCity);
    });
    if (prefixMatches.length === 1) {
      match = prefixMatches[0];
    } else if (prefixMatches.length > 1) {
      return {
        statusCode: 200,
        headers: headers,
        body: JSON.stringify({
          served: false,
          city: trimmed,
          ambiguous: true,
          message:
            "\u201c" + trimmed + "\u201d matches multiple cities. " +
            "Please use the full city name so we can give you an accurate answer.",
          suggestions: prefixMatches.map(function (c) { return c.city; })
        })
      };
    }
  }

  if (match) {
    return {
      statusCode: 200,
      headers: headers,
      body: JSON.stringify({
        served: true,
        city: match.city,
        county: match.county,
        subregion: match.subregion,
        pageUrl: match.canonicalUrl,
        phone: PHONE
      })
    };
  }

  // Not found in published city list
  return {
    statusCode: 200,
    headers: headers,
    body: JSON.stringify({
      served: false,
      city: trimmed,
      message:
        "Eternal Life Hospice does not have a published service-area page for \u201c" +
        trimmed +
        "\u201d. Please call " +
        PHONE +
        " to confirm coverage \u2014 our service area across Ventura and Los Angeles counties may extend beyond our published city pages."
    })
  };
};
