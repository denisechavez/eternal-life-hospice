/**
 * test-nav-scroll-regression.js
 *
 * Regression-mode proof for test-nav-scroll.js.
 *
 * What it does
 * ------------
 * Runs TWO mutation passes against test-nav-scroll.js to confirm both
 * assertions in the guard are independently exercised:
 *
 *   Pass 1 — strips `max-height` from the `#hdr.nav-open nav` rule.
 *   Pass 2 — strips `overflow-y` from the `#hdr.nav-open nav` rule.
 *
 * Each pass:
 *   1. Reads the real elh.css.
 *   2. Removes the target property, writing the result to a temp file.
 *   3. Spawns `test-nav-scroll.js` with ELH_CSS_OVERRIDE pointing at that
 *      temp file.
 *   4. Asserts the child process exits with code 1 — proving the guard
 *      catches the regression.
 *   5. Cleans up the temp file.
 *
 * Exit codes: 0 = both regressions were caught (guard works),
 *             1 = at least one mutation was NOT detected (assertion logic broken).
 */

"use strict";

const fs            = require("fs");
const path          = require("path");
const os            = require("os");
const { spawnSync } = require("child_process");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const ELH_CSS   = path.join(REPO_ROOT, "website", "elh-preview", "assets", "elh.css");

if (!fs.existsSync(ELH_CSS)) {
  console.log("SKIP: marketing-site nav assets are not included in the standalone tracker package.");
  process.exit(0);
}

// ── Read the real stylesheet once ────────────────────────────────────────────
let realCss;
try {
  realCss = fs.readFileSync(ELH_CSS, "utf8");
} catch (err) {
  console.error("ERROR: Could not read elh.css:", err.message);
  process.exit(1);
}

/**
 * Run one mutation pass.
 *
 * @param {object} opts
 * @param {string} opts.label       - human-readable name for the mutation
 * @param {RegExp} opts.presentRe   - regex that must match the real CSS
 * @param {string} opts.presentMsg  - error when property is already absent
 * @param {RegExp} opts.stripRe     - regex to remove from the CSS
 * @param {string} opts.passMsg     - logged on success
 * @param {string} opts.failMsg     - logged on failure
 * @returns {boolean} true = mutation was caught (guard works)
 */
function runMutationPass(opts) {
  console.log(`=== nav scroll regression proof (${opts.label}) ===\n`);

  // Verify the property we are about to remove is actually present — if it is
  // already absent, the regression is already in the codebase and this test
  // would give a false pass.
  if (!opts.presentRe.test(realCss)) {
    console.error(
      `FAIL: ${opts.presentMsg}\n` +
      "      The property is already missing — fix the stylesheet first."
    );
    return false;
  }

  // Produce a mutated copy with the target property removed.
  const mutatedCss = realCss.replace(opts.stripRe, "");

  const tmpFile = path.join(os.tmpdir(), `elh-nav-regression-${opts.label}-${process.pid}.css`);
  try {
    fs.writeFileSync(tmpFile, mutatedCss, "utf8");
  } catch (err) {
    console.error("ERROR: Could not write temp CSS:", err.message);
    return false;
  }

  console.log(`  INFO: mutated CSS written to ${tmpFile}`);
  console.log(`  INFO: spawning test-nav-scroll.js with ${opts.label} absent…\n`);

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
    try { fs.unlinkSync(tmpFile); } catch (_) { /* best-effort */ }
  }

  console.log("\n=== regression-mode result ===");

  if (exitCode === 1) {
    console.log(`  PASS: ${opts.passMsg}`);
    return true;
  } else {
    console.error(
      `  FAIL: test-nav-scroll.js exited ${exitCode} instead of 1.\n` +
      `        ${opts.failMsg}`
    );
    return false;
  }
}

// ── Pass 1: strip max-height ──────────────────────────────────────────────────
const pass1 = runMutationPass({
  label:      "max-height removed",
  presentRe:  /max-height\s*:\s*calc\(100vh\s*-\s*74px\)/,
  presentMsg: "max-height:calc(100vh - 74px) not found in elh.css.",
  stripRe:    /max-height\s*:\s*calc\(100vh\s*-\s*74px\)\s*;?/g,
  passMsg:    "test-nav-scroll.js exited 1 — the max-height regression was caught correctly.",
  failMsg:    "The guard did NOT catch the missing max-height — the assertion logic is broken.",
});

console.log();

// ── Pass 2: strip overflow-y ──────────────────────────────────────────────────
const pass2 = runMutationPass({
  label:      "overflow-y removed",
  presentRe:  /overflow-y\s*:\s*(auto|scroll)/,
  presentMsg: "overflow-y:auto (or scroll) not found in elh.css.",
  stripRe:    /overflow-y\s*:\s*(auto|scroll)\s*;?/g,
  passMsg:    "test-nav-scroll.js exited 1 — the overflow-y regression was caught correctly.",
  failMsg:    "The guard did NOT catch the missing overflow-y — the assertion logic is broken.",
});

console.log();

// ── Overall result ────────────────────────────────────────────────────────────
if (pass1 && pass2) {
  console.log("=== all regression passes PASSED — both guard assertions are verified ===");
  process.exitCode = 0;
} else {
  console.error("=== FAILED — one or more regression passes did not catch their mutation ===");
  process.exitCode = 1;
}
