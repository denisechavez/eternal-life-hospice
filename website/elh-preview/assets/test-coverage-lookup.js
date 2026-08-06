#!/usr/bin/env node
/**
 * Coverage lookup regression test
 *
 * Calls the coverage.js handler directly (no HTTP server needed) and
 * verifies correct results across four categories:
 *
 *   1. All 145 published cities resolve to served:true with the right city name
 *   2. Exact-match priority — "Bell" must not collide with "Bell Gardens" / "Bellflower"
 *   3. Normalisation — diacritics, case, extra whitespace
 *   4. Non-served cities and edge inputs return the right negative responses
 *
 * Run from workspace root:
 *   node website/elh-preview/assets/test-coverage-lookup.js
 */

"use strict";

// coverage.js uses require("../../../city-data.json") relative to its own
// location.  We need the module resolver to start from the functions dir.
const path = require("path");
const Module = require("module");

// Temporarily override require so the relative path inside coverage.js
// is resolved correctly from its actual file location.
const fnDir = path.resolve(__dirname, "../netlify/functions");
const origLoad = Module._resolveFilename.bind(Module);
const patchedLoad = function (request, parent, isMain, options) {
  if (parent && parent.filename && parent.filename.includes("coverage.js") && request.startsWith(".")) {
    return origLoad(request, parent, isMain, options);
  }
  return origLoad(request, parent, isMain, options);
};

// Load handler with its cwd-independent require path
const handler = require(path.join(fnDir, "coverage.js")).handler;
const cityData = require(path.resolve(__dirname, "../../city-data.json"));

// ── Helpers ────────────────────────────────────────────────────────────────────

async function query(city) {
  const event = {
    httpMethod: "GET",
    queryStringParameters: city === null ? {} : { city }
  };
  const resp = await handler(event);
  return { status: resp.statusCode, body: JSON.parse(resp.body) };
}

async function queryList() {
  const event = {
    httpMethod: "GET",
    queryStringParameters: { list: "true" }
  };
  const resp = await handler(event);
  return { status: resp.statusCode, body: JSON.parse(resp.body) };
}

let passed = 0;
let failed = 0;
const failures = [];

function assert(label, condition, detail) {
  if (condition) {
    passed++;
    process.stdout.write("  ✓ " + label + "\n");
  } else {
    failed++;
    const msg = "  ✗ " + label + (detail ? " — " + detail : "");
    process.stdout.write(msg + "\n");
    failures.push(msg);
  }
}

// ── Test suite ─────────────────────────────────────────────────────────────────

(async function main() {
  console.log("\n=== Coverage lookup regression tests ===\n");

  // ── 1. All published cities ──────────────────────────────────────────────────
  console.log("1. All published cities resolve to served:true");

  const published = cityData.filter(c => c.publishStatus === "published");
  assert(
    `city-data.json has 145 published entries`,
    published.length === 145,
    `found ${published.length}`
  );

  for (const entry of published) {
    const { status, body } = await query(entry.city);
    assert(
      `${entry.city} → served`,
      status === 200 && body.served === true,
      body.served === false ? "served:false" : `status ${status}`
    );
    assert(
      `${entry.city} → correct city name`,
      body.city === entry.city,
      `got "${body.city}"`
    );
  }

  // ── 2. Exact-match priority (ambiguous prefix pairs) ────────────────────────
  console.log("\n2. Exact-match priority — prefixes must not collide");

  // "Bell" is a real city; Bell Gardens and Bellflower share its prefix.
  const bell = await query("Bell");
  assert(
    '"Bell" → city is Bell (exact), not Bell Gardens or Bellflower',
    bell.body.served && bell.body.city === "Bell",
    `got "${bell.body.city}"`
  );

  const bellGardens = await query("Bell Gardens");
  assert(
    '"Bell Gardens" → city is Bell Gardens',
    bellGardens.body.served && bellGardens.body.city === "Bell Gardens",
    `got "${bellGardens.body.city}"`
  );

  const bellflower = await query("Bellflower");
  assert(
    '"Bellflower" → city is Bellflower',
    bellflower.body.served && bellflower.body.city === "Bellflower",
    `got "${bellflower.body.city}"`
  );

  // "El Monte" must not be confused with "South El Monte"
  const elMonte = await query("El Monte");
  assert(
    '"El Monte" → city is El Monte (not South El Monte)',
    elMonte.body.served && elMonte.body.city === "El Monte",
    `got "${elMonte.body.city}"`
  );

  const southElMonte = await query("South El Monte");
  assert(
    '"South El Monte" → city is South El Monte',
    southElMonte.body.served && southElMonte.body.city === "South El Monte",
    `got "${southElMonte.body.city}"`
  );

  // "West Hollywood", "West Hills", "West Covina" — each must be independent
  for (const w of ["West Hollywood", "West Hills", "West Covina"]) {
    const r = await query(w);
    assert(
      `"${w}" → exact`,
      r.body.served && r.body.city === w,
      `got "${r.body.city}"`
    );
  }

  // "Signal Hill" must not partially match a bare "Hill" (non-served)
  const hill = await query("Hill");
  assert(
    '"Hill" (non-served partial) → served:false',
    !hill.body.served,
    `got served:${hill.body.served}, city="${hill.body.city}"`
  );

  // "North Hollywood" vs "Hollywood"
  const hollywood = await query("Hollywood");
  assert(
    '"Hollywood" → city is Hollywood (exact)',
    hollywood.body.served && hollywood.body.city === "Hollywood",
    `got "${hollywood.body.city}"`
  );
  const northHollywood = await query("North Hollywood");
  assert(
    '"North Hollywood" → city is North Hollywood',
    northHollywood.body.served && northHollywood.body.city === "North Hollywood",
    `got "${northHollywood.body.city}"`
  );

  // "South Pasadena" vs "Pasadena"
  const pasadena = await query("Pasadena");
  assert(
    '"Pasadena" → city is Pasadena (exact)',
    pasadena.body.served && pasadena.body.city === "Pasadena",
    `got "${pasadena.body.city}"`
  );
  const southPasadena = await query("South Pasadena");
  assert(
    '"South Pasadena" → city is South Pasadena',
    southPasadena.body.served && southPasadena.body.city === "South Pasadena",
    `got "${southPasadena.body.city}"`
  );

  // "Oak Park" vs "Oak View"
  const oakPark = await query("Oak Park");
  assert(
    '"Oak Park" → city is Oak Park',
    oakPark.body.served && oakPark.body.city === "Oak Park",
    `got "${oakPark.body.city}"`
  );
  const oakView = await query("Oak View");
  assert(
    '"Oak View" → city is Oak View',
    oakView.body.served && oakView.body.city === "Oak View",
    `got "${oakView.body.city}"`
  );

  // "San Fernando" vs "San Gabriel" vs "San Marino" vs "San Dimas" vs "San Pedro"
  for (const c of ["San Fernando", "San Gabriel", "San Marino", "San Dimas", "San Pedro"]) {
    const r = await query(c);
    assert(
      `"${c}" → exact`,
      r.body.served && r.body.city === c,
      `got "${r.body.city}"`
    );
  }

  // ── 3. Normalisation ─────────────────────────────────────────────────────────
  console.log("\n3. Normalisation — diacritics, case, whitespace");

  // Diacritics: "La Canada Flintridge" (no ñ) should resolve to La Cañada Flintridge
  const lacaNada = await query("La Canada Flintridge");
  assert(
    '"La Canada Flintridge" (no diacritic) → La Cañada Flintridge',
    lacaNada.body.served && lacaNada.body.city === "La Cañada Flintridge",
    `got "${lacaNada.body.city}"`
  );

  // Uppercase
  const upper = await query("PASADENA");
  assert(
    '"PASADENA" (uppercase) → Pasadena',
    upper.body.served && upper.body.city === "Pasadena",
    `got "${upper.body.city}"`
  );

  // Mixed case
  const mixed = await query("thousand oaks");
  assert(
    '"thousand oaks" (lowercase) → Thousand Oaks',
    mixed.body.served && mixed.body.city === "Thousand Oaks",
    `got "${mixed.body.city}"`
  );

  // Leading/trailing whitespace
  const whitespace = await query("  Glendale  ");
  assert(
    '"  Glendale  " (extra whitespace) → Glendale',
    whitespace.body.served && whitespace.body.city === "Glendale",
    `got "${whitespace.body.city}"`
  );

  // ── 4. Non-served cities and edge inputs ─────────────────────────────────────
  console.log("\n4. Non-served cities and edge inputs → correct negatives");

  const nonServed = [
    "San Francisco",
    "San Diego",
    "Orange",
    "Sacramento",
    "Irvine",
    "San Jose",
    "Bakersfield",
    "Fresno",
    "Oakland",
    "Riverside"
  ];
  for (const city of nonServed) {
    const r = await query(city);
    assert(
      `"${city}" → served:false`,
      r.status === 200 && !r.body.served,
      `got served:${r.body.served}`
    );
  }

  // Missing city param → 400
  const missing = await query(null);
  assert(
    "missing ?city param → 400",
    missing.status === 400 && missing.body.error != null,
    `got status ${missing.status}`
  );

  // Empty string → 400
  const empty = await query("");
  assert(
    'empty city "" → 400',
    empty.status === 400,
    `got status ${empty.status}`
  );

  // ── 5. Ambiguous prefix queries → suggestions, not a wrong served:true ────────
  console.log("\n5. Ambiguous prefix queries → served:false + suggestions");

  // "West" matches West Covina, West Hills, West Hollywood → ambiguous
  const westAmbig = await query("West");
  assert(
    '"West" (ambiguous prefix) → served:false with ambiguous:true',
    !westAmbig.body.served && westAmbig.body.ambiguous === true,
    `got served:${westAmbig.body.served}, ambiguous:${westAmbig.body.ambiguous}`
  );
  assert(
    '"West" → suggestions includes West Covina, West Hills, West Hollywood',
    Array.isArray(westAmbig.body.suggestions) &&
      westAmbig.body.suggestions.includes("West Covina") &&
      westAmbig.body.suggestions.includes("West Hills") &&
      westAmbig.body.suggestions.includes("West Hollywood"),
    `got suggestions: ${JSON.stringify(westAmbig.body.suggestions)}`
  );

  // "North" matches North Hills + North Hollywood → ambiguous
  const northAmbig = await query("North");
  assert(
    '"North" (ambiguous prefix) → served:false with ambiguous:true',
    !northAmbig.body.served && northAmbig.body.ambiguous === true,
    `got served:${northAmbig.body.served}, ambiguous:${northAmbig.body.ambiguous}`
  );
  assert(
    '"North" → suggestions includes North Hills and North Hollywood',
    Array.isArray(northAmbig.body.suggestions) &&
      northAmbig.body.suggestions.includes("North Hills") &&
      northAmbig.body.suggestions.includes("North Hollywood"),
    `got suggestions: ${JSON.stringify(northAmbig.body.suggestions)}`
  );

  // Very short queries (< 4 chars) below minimum length → served:false, no ambiguous flag
  const shortQuery = await query("We");
  assert(
    '"We" (2 chars, below minimum) → served:false without ambiguous flag',
    !shortQuery.body.served && shortQuery.body.ambiguous == null,
    `got served:${shortQuery.body.served}, ambiguous:${shortQuery.body.ambiguous}`
  );

  const threeChar = await query("San");
  assert(
    '"San" (3 chars, below minimum) → served:false without ambiguous flag',
    !threeChar.body.served && threeChar.body.ambiguous == null,
    `got served:${threeChar.body.served}, ambiguous:${threeChar.body.ambiguous}`
  );

  // A unique 4-char prefix still resolves to served:true (single match)
  // "Thou" → only Thousand Oaks starts with "thou"
  const thou = await query("Thou");
  assert(
    '"Thou" (unique 4-char prefix) → served:true as Thousand Oaks',
    thou.body.served && thou.body.city === "Thousand Oaks",
    `got served:${thou.body.served}, city="${thou.body.city}"`
  );

  // "Thousand" prefix (unique) → still resolves correctly
  const thousand = await query("Thousand");
  assert(
    '"Thousand" (unique prefix) → served:true as Thousand Oaks',
    thousand.body.served && thousand.body.city === "Thousand Oaks",
    `got served:${thousand.body.served}, city="${thousand.body.city}"`
  );

  // Full city names that share prefixes still resolve via step 1 (exact match), unaffected
  const westCovina = await query("West Covina");
  assert(
    '"West Covina" (full name) → served:true, exact match unaffected',
    westCovina.body.served && westCovina.body.city === "West Covina",
    `got served:${westCovina.body.served}, city="${westCovina.body.city}"`
  );

  // ── 6. List mode sanity check ────────────────────────────────────────────────
  console.log("\n6. List mode (?list=true)");

  const list = await queryList();
  assert(
    "?list=true → 200",
    list.status === 200,
    `got ${list.status}`
  );
  assert(
    "?list=true → total matches published count",
    list.body.total === published.length,
    `got total=${list.body.total}, expected ${published.length}`
  );
  assert(
    "?list=true → cities array has correct length",
    Array.isArray(list.body.cities) && list.body.cities.length === published.length,
    `got ${list.body.cities && list.body.cities.length}`
  );
  assert(
    "?list=true → counties array present and non-empty",
    Array.isArray(list.body.counties) && list.body.counties.length > 0,
    `got ${list.body.counties}`
  );

  // ── Summary ──────────────────────────────────────────────────────────────────
  console.log(`\n${"─".repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  if (failures.length) {
    console.log("\nFailures:");
    failures.forEach(f => console.log(f));
  }
  console.log("");
  process.exit(failed > 0 ? 1 : 0);
})();
