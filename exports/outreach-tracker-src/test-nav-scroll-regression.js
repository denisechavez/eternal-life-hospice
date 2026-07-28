/**
 * test-nav-scroll-regression.js
 *
 * Regression-mode proof for test-nav-scroll.js.
 *
 * What it does
 * ------------
 * 1. Reads the real elh.css.
 * 2. Strips `max-height` from the `#hdr.nav-open nav` rule, writing the
 *    result to a temp file.
 * 3. Spawns `test-nav-scroll.js` with ELH_CSS_OVERRIDE pointing at that
 *    temp file.
 * 4. Asserts the child process exits with code 1 — proving the guard
 *    catches the regression.
 * 5. Cleans up the temp file.
 *
 * Exit codes: 0 = regression was caught (guard works), 1 = guard failed to
 * detect the regression (the assertion logic is broken).
 */

"use strict";

const fs            = require("fs");
const path          = require("path");
const os            = require("os");
const { spawnSync } = require("child_process");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const ELH_CSS   = path.join(REPO_ROOT, "website", "elh-preview", "assets", "elh.css");

console.log("=== nav scroll regression proof (max-height removed) ===\n");

// ── 1. Read real stylesheet ──────────────────────────────────────────────────
let realCss;
try {
  realCss = fs.readFileSync(ELH_CSS, "utf8");
} catch (err) {
  console.error("ERROR: Could not read elh.css:", err.message);
  process.exit(1);
}

// Verify the property we are about to remove is actually present — if it is
// already absent, the regression is already in the codebase and this test
// would give a false pass.
if (!/max-height\s*:\s*calc\(100vh\s*-\s*74px\)/.test(realCss)) {
  console.error(
    "FAIL: max-height:calc(100vh - 74px) not found in elh.css.\n" +
    "      The property is already missing — fix the stylesheet first."
  );
  process.exit(1);
}

// ── 2. Produce a mutated copy with max-height removed ───────────────────────
// Remove every `max-height:calc(100vh - 74px)` declaration (with optional
// whitespace variants) so the copy simulates the regression.
const mutatedCss = realCss.replace(
  /max-height\s*:\s*calc\(100vh\s*-\s*74px\)\s*;?/g,
  ""
);

const tmpFile = path.join(os.tmpdir(), `elh-nav-regression-${process.pid}.css`);
try {
  fs.writeFileSync(tmpFile, mutatedCss, "utf8");
} catch (err) {
  console.error("ERROR: Could not write temp CSS:", err.message);
  process.exit(1);
}

console.log(`  INFO: mutated CSS written to ${tmpFile}`);
console.log("  INFO: spawning test-nav-scroll.js with max-height absent…\n");

// ── 3. Spawn the guard with the mutated CSS ──────────────────────────────────
let exitCode;
try {
  const result = spawnSync(
    process.execPath,
    [path.join(__dirname, "test-nav-scroll.js")],
    {
      env: { ...process.env, ELH_CSS_OVERRIDE: tmpFile },
      encoding: "utf8",
    }
  );

  // Echo child output so the CI log shows exactly which assertions failed.
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);

  exitCode = result.status;
} finally {
  // ── 4. Clean up ─────────────────────────────────────────────────────────
  try { fs.unlinkSync(tmpFile); } catch (_) { /* best-effort */ }
}

// ── 5. Assert the guard detected the regression ──────────────────────────────
console.log("\n=== regression-mode result ===");

if (exitCode === 1) {
  console.log(
    "  PASS: test-nav-scroll.js exited 1 — " +
    "the max-height regression was caught correctly."
  );
  process.exitCode = 0;
} else {
  console.error(
    `  FAIL: test-nav-scroll.js exited ${exitCode} instead of 1.\n` +
    "        The guard did NOT catch the missing max-height — " +
    "the assertion logic is broken."
  );
  process.exitCode = 1;
}
