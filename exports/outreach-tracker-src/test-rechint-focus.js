/**
 * test-rechint-focus.js
 *
 * Static-analysis guard for the #recHint focus-ring rules.
 *
 * What it checks
 * --------------
 * 1. `#recHint` has `tabindex="0"` in index.html — the element is reachable
 *    by keyboard Tab navigation.
 * 2. `#recHint:focus-visible` in styles.css declares a visible `outline` —
 *    keyboard focus will show the ring.
 * 3. No bare `#recHint:focus` rule exists in styles.css that adds a visible
 *    outline — mouse clicks (which don't satisfy :focus-visible) will NOT show
 *    a ring.
 *
 * Why a static check?
 * -------------------
 * The :focus-visible pseudo-class is a CSS guarantee.  The risk is a future
 * edit replacing `:focus-visible` with plain `:focus` (mouse ring reappears) or
 * removing `tabindex="0"` (keyboard users can no longer reach the hint at all).
 * Both regressions are caught here without needing a browser.
 *
 * For live browser verification see test-rechint-focus-manual.md.
 *
 * Usage:
 *   node test-rechint-focus.js
 *
 * Flags:
 *   --skip-regression   Run only the forward checks (used internally by the
 *                       regression-proof section to avoid infinite recursion).
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const fs            = require("fs");
const path          = require("path");
const { spawnSync } = require("child_process");

const CSS_PATH  = path.join(__dirname, "public", "styles.css");
const HTML_PATH = path.join(__dirname, "public", "index.html");

// When this script runs itself as a subprocess to prove the regression check
// works, it passes --skip-regression so the subprocess only runs the forward
// checks and does not mutate the CSS a second time.
const SKIP_REGRESSION = process.argv.includes("--skip-regression");

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

function run() {
  console.log("=== #recHint focus-ring static check ===\n");

  const html = readFile(HTML_PATH);
  const css  = readFile(CSS_PATH);

  // ── 1. #recHint must have tabindex="0" so keyboard Tab can reach it ────────
  // Match the opening tag of the element, allowing attributes in any order.
  const recHintTag = html.match(/<[^>]+id=["']recHint["'][^>]*>/);
  assert(
    recHintTag !== null,
    "#recHint element is present in index.html"
  );
  if (recHintTag) {
    assert(
      /tabindex=["']0["']/.test(recHintTag[0]),
      '#recHint has tabindex="0" — keyboard Tab navigation can reach it'
    );
  }

  // ── 2. :focus-visible rule must exist and declare a visible outline ────────
  const focusVisibleBlock = css.match(/#recHint\s*:\s*focus-visible\s*\{([^}]*)\}/);
  assert(
    focusVisibleBlock !== null,
    "#recHint:focus-visible rule is present in styles.css"
  );
  if (focusVisibleBlock) {
    const decls = focusVisibleBlock[1];
    assert(
      /outline\s*:/.test(decls),
      "#recHint:focus-visible block contains an outline declaration"
    );
    assert(
      !/outline\s*:\s*none/.test(decls),
      "#recHint:focus-visible outline is not set to none"
    );
  }

  // ── 3. No bare :focus rule that would show an outline on mouse clicks ───────
  const focusBareBlock = css.match(/#recHint\s*:\s*focus(?!-visible)\s*\{([^}]*)\}/);
  if (focusBareBlock) {
    const decls = focusBareBlock[1];
    const hasVisibleOutline =
      /outline\s*:/.test(decls) &&
      !/outline\s*:\s*(none|0)\b/.test(decls);
    assert(
      !hasVisibleOutline,
      "No bare #recHint:focus rule that would force an outline on mouse clicks"
    );
  } else {
    console.log("  PASS: No bare #recHint:focus rule found (expected)");
  }

  console.log("\n=== Done ===");
}

// ── Regression proof ────────────────────────────────────────────────────────
// Temporarily injects a bare `#recHint:focus { outline: 2px solid red; }` rule
// into styles.css, spawns this same script with --skip-regression, and asserts
// that it exits with code 1.  The CSS file is always restored, even on error.
//
// This section is skipped when the script is called with --skip-regression so
// that the subprocess used for the proof doesn't recurse.
function runRegressionCheck() {
  console.log("\n=== Regression proof: bare :focus swap ===\n");

  const originalCss = fs.readFileSync(CSS_PATH, "utf8");
  // Inject a bare :focus rule that the check should flag.
  const mutatedCss =
    originalCss + "\n/* regression-probe */\n#recHint:focus { outline: 2px solid red; }\n";

  try {
    fs.writeFileSync(CSS_PATH, mutatedCss, "utf8");

    const result = spawnSync(process.execPath, [__filename, "--skip-regression"], {
      encoding: "utf8",
    });

    const exitCode = result.status;
    assert(
      exitCode === 1,
      `check exits 1 when a bare #recHint:focus outline rule is present (got ${exitCode})`
    );

    if (exitCode !== 1) {
      // Surface subprocess output to aid debugging when the proof fails.
      if (result.stdout) process.stdout.write("  [subprocess stdout]\n" + result.stdout);
      if (result.stderr) process.stderr.write("  [subprocess stderr]\n" + result.stderr);
    }
  } finally {
    // Always restore the original CSS — even if the spawn threw.
    fs.writeFileSync(CSS_PATH, originalCss, "utf8");
    console.log("  INFO: styles.css restored to original state");
  }

  console.log("\n=== Regression proof done ===");
}

// ── Regression proof: tabindex removal ──────────────────────────────────────
// Temporarily removes `tabindex="0"` from the #recHint tag in index.html,
// spawns this same script with --skip-regression, and asserts that it exits
// with code 1.  The HTML file is always restored, even on error.
//
// This section is skipped when the script is called with --skip-regression so
// that the subprocess used for the proof doesn't recurse.
function runTabindexRegressionCheck() {
  console.log("\n=== Regression proof: tabindex removal ===\n");

  const originalHtml = fs.readFileSync(HTML_PATH, "utf8");
  // Remove tabindex="0" (or tabindex='0') from the #recHint tag.
  const mutatedHtml = originalHtml.replace(
    /(<[^>]+id=["']recHint["'][^>]*)\s+tabindex=["']0["']/,
    "$1"
  );

  if (mutatedHtml === originalHtml) {
    // Safety net: if the substitution didn't change anything the proof is
    // meaningless — fail loudly rather than silently passing.
    console.error(
      "  FAIL: Could not remove tabindex=\"0\" from #recHint — pattern not found"
    );
    process.exitCode = 1;
    return;
  }

  try {
    fs.writeFileSync(HTML_PATH, mutatedHtml, "utf8");

    const result = spawnSync(process.execPath, [__filename, "--skip-regression"], {
      encoding: "utf8",
    });

    const exitCode = result.status;
    assert(
      exitCode === 1,
      `check exits 1 when tabindex="0" is absent from #recHint (got ${exitCode})`
    );

    if (exitCode !== 1) {
      // Surface subprocess output to aid debugging when the proof fails.
      if (result.stdout) process.stdout.write("  [subprocess stdout]\n" + result.stdout);
      if (result.stderr) process.stderr.write("  [subprocess stderr]\n" + result.stderr);
    }
  } finally {
    // Always restore the original HTML — even if the spawn threw.
    fs.writeFileSync(HTML_PATH, originalHtml, "utf8");
    console.log("  INFO: index.html restored to original state");
  }

  console.log("\n=== Regression proof done ===");
}

run();

if (!SKIP_REGRESSION) {
  runRegressionCheck();
  runTabindexRegressionCheck();
}
