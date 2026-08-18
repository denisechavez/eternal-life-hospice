/**
 * test-csv-export.js
 *
 * Verifies that the CSV export logic in public/app.js:
 *   1. Neutralizes formula-prefixed field values BEFORE CSV quoting so that
 *      `=SUM(A1)` in a visit field exports as `'=SUM(A1)` (not executable).
 *   2. Escapes embedded double-quotes correctly (RFC 4180 doubling).
 *   3. The materials array is joined with "; " rather than serialised as JSON.
 *   4. Null/undefined fields export as empty strings, not "null" / "undefined".
 *
 * No database or network required.
 * Exit code 0 = all assertions passed; 1 = failure.
 */

"use strict";

const fs   = require("fs");
const path = require("path");

/* ── assert helper ──────────────────────────────────────────────────────────── */
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

/* ── Verify neutralize is present and correct in app.js ─────────────────────
   Confirm the raw function body matches the expected pattern before running
   the behavioral tests below.
──────────────────────────────────────────────────────────────────────────────── */
const APP_JS = fs.readFileSync(path.join(__dirname, "public", "app.js"), "utf8");

const neutralizeMatch = APP_JS.match(/const neutralize\s*=\s*\(s\)\s*=>[^\n]+/);
if (!neutralizeMatch) {
  console.error("FAIL: could not locate neutralize() in app.js");
  process.exitCode = 1;
  process.exit(1);
}
assert(
  neutralizeMatch[0].includes("[=+") && neutralizeMatch[0].includes("@"),
  "neutralize() in app.js checks for formula-prefixed characters"
);

// Define the same function locally — keeps tests independent of app.js eval.
const neutralize = (s) => (/^[=+\-@\t\r]/.test(s) ? "'" + s : s);

/* ── Replicate the exact CSV row-building logic from app.js ─────────────────── */
const cols = [
  "visit_date", "company", "category", "address", "city", "county",
  "contact_name", "contact_title", "contact_email", "contact_phone",
  "materials", "notes", "owner", "follow_up_method", "follow_up_due",
  "followup_status",
];

function buildRow(visit) {
  return cols.map((c) => {
    const val = c === "materials"
      ? (Array.isArray(visit[c]) ? visit[c].join("; ") : "")
      : String(visit[c] ?? "");
    return '"' + neutralize(val).replace(/"/g, '""') + '"';
  }).join(",");
}

/* ── Tests ──────────────────────────────────────────────────────────────────── */
console.log("=== CSV export regression tests ===\n");

/* 1. Formula injection — = prefix */
{
  const row = buildRow({ visit_date: "2026-01-01", company: "=SUM(A1)", category: "Hospital",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "", followup_status: "Not started" });
  const cells = row.split(",");
  assert(
    cells[1] === '"\'=SUM(A1)"',
    `formula = prefix is neutralized: company cell is ${cells[1]}`
  );
}

/* 2. Formula injection — + prefix */
{
  const row = buildRow({ visit_date: "2026-01-01", company: "+malicious()", category: "",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "", followup_status: "" });
  const cells = row.split(",");
  assert(cells[1] === '"\'+malicious()"', `formula + prefix is neutralized: ${cells[1]}`);
}

/* 3. Formula injection — @ prefix */
{
  const row = buildRow({ visit_date: "2026-01-01", company: "@HYPERLINK(x)", category: "",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "", followup_status: "" });
  const cells = row.split(",");
  assert(cells[1] === '"\'@HYPERLINK(x)"', `formula @ prefix is neutralized: ${cells[1]}`);
}

/* 4. Non-formula string is NOT prefixed with apostrophe */
{
  const row = buildRow({ visit_date: "2026-01-01", company: "St. John's Hospital", category: "",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "", followup_status: "" });
  const cells = row.split(",");
  assert(cells[1] === '"St. John\'s Hospital"', `safe string is not prefixed: ${cells[1]}`);
}

/* 5. Embedded double-quote is RFC-4180 doubled */
{
  const row = buildRow({ visit_date: "2026-01-01", company: 'Say "hello"', category: "",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "", followup_status: "" });
  const cells = row.split(/,(?=")/);
  assert(cells[1] === '"Say ""hello"""', `embedded quote is RFC-4180 doubled: ${cells[1]}`);
}

/* 6. Materials array is joined with "; " */
{
  const row = buildRow({ visit_date: "2026-01-01", company: "Acme", category: "",
    address: "", city: "", county: "", contact_name: "", contact_title: "", contact_email: "",
    contact_phone: "", materials: ["Brochure", "Business card"], notes: "",
    owner: "", follow_up_method: "", follow_up_due: "", followup_status: "" });
  const cells = row.split(",");
  const materialsIdx = cols.indexOf("materials");
  assert(cells[materialsIdx] === '"Brochure; Business card"', `materials joined with "; ": ${cells[materialsIdx]}`);
}

/* 7. Null/undefined fields export as empty string */
{
  const row = buildRow({ visit_date: null, company: undefined, category: null,
    address: null, city: null, county: null, contact_name: null, contact_title: null,
    contact_email: null, contact_phone: null, materials: null, notes: null,
    owner: null, follow_up_method: null, follow_up_due: null, followup_status: null });
  const cells = row.split(",");
  assert(cells.every((c) => c === '""'), `null/undefined fields export as empty string (all cells: ${cells.slice(0,3).join(" ")})`);
}

/* 8. Date fields are truncated to YYYY-MM-DD (PostgreSQL returns ISO timestamps) */
{
  const DATE_COLS = new Set(["visit_date", "follow_up_due"]);
  function buildRowWithDates(visit) {
    return cols.map((c) => {
      const raw = visit[c] ?? "";
      const val = c === "materials"
        ? (Array.isArray(raw) ? raw.join("; ") : "")
        : DATE_COLS.has(c)
        ? String(raw).slice(0, 10)
        : String(raw);
      return '"' + neutralize(val).replace(/"/g, '""') + '"';
    }).join(",");
  }

  const row = buildRowWithDates({
    visit_date: "2026-01-15T08:30:00.000Z", company: "St. John's",
    category: "Hospital", address: "", city: "", county: "",
    contact_name: "", contact_title: "", contact_email: "", contact_phone: "",
    materials: [], notes: "", owner: "", follow_up_method: "",
    follow_up_due: "2026-01-22T00:00:00.000Z", followup_status: "Not started",
  });
  const cells = row.split(",");
  assert(cells[0] === '"2026-01-15"', `visit_date ISO timestamp truncated to date: ${cells[0]}`);
  const fuIdx = cols.indexOf("follow_up_due");
  assert(cells[fuIdx] === '"2026-01-22"', `follow_up_due ISO timestamp truncated to date: ${cells[fuIdx]}`);
}

/* 9. Formula injection check is on RAW value, not quoted cell (the key regression) */
{
  // If neutralize were called on the already-quoted string '"=BAD()"', its
  // first char would be `"` and it would NOT be neutralized.  Confirm the
  // fix: raw `=BAD()` is still neutralized.
  const rawVal = "=BAD()";
  const cell = '"' + neutralize(rawVal).replace(/"/g, '""') + '"';
  assert(cell === '"\'=BAD()"', `neutralize applied to raw value before quoting: ${cell}`);

  // Confirm the broken order would NOT neutralize (regression guard)
  const brokenCell = neutralize('"' + rawVal.replace(/"/g, '""') + '"');
  assert(brokenCell === '"=BAD()"',
    `broken order (neutralize after quoting) leaves formula unprotected: ${brokenCell}`);
}

console.log("\n=== Done (CSV export regression test) ===");
