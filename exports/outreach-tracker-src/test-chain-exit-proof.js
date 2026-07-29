/**
 * test-chain-exit-proof.js
 *
 * Automated proof that the npm test chain halts and exits non-zero when any
 * script in the chain exits 1.
 *
 * It works by spawning two temporary Node.js one-liners connected with &&:
 *
 *   node -e "process.exit(1)" && node -e "process.exit(0)"
 *
 * The shell && operator stops as soon as the first command exits non-zero, so
 * the second command never runs.  The overall child process exits 1, which is
 * exactly the behaviour that prevents a failing test from being silently
 * swallowed in the CI chain.
 *
 * A second scenario confirms the positive path: when the first command exits 0
 * the chain continues and the overall exit code is 0.
 *
 * Usage:
 *   node test-chain-exit-proof.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const { spawnSync } = require("child_process");

let failures = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

function runChain(cmd) {
  return spawnSync(cmd, { shell: true, encoding: "utf8" });
}

console.log("=== chain exit-code propagation proof ===\n");

// ── Scenario A: first script exits 1 → chain must halt with exit code 1 ──────
console.log("[ Scenario A: first script exits 1 ]");

// The marker string is written by the SECOND command.  If it appears the
// chain did NOT stop — a definitive sign of silent failure swallowing.
const markerA = "__SECOND_RAN__";
const resultA = runChain(
  `node -e "process.exit(1)" && node -e "process.stdout.write('${markerA}')"`
);

assert(
  resultA.status === 1,
  `chain exits 1 when first script exits 1 (got ${resultA.status})`
);
assert(
  !resultA.stdout.includes(markerA),
  "second script never ran after first exited 1"
);

console.log();

// ── Scenario B: first script exits 0 → chain continues, overall exit 0 ───────
console.log("[ Scenario B: first script exits 0 ]");

const markerB = "__SECOND_RAN_OK__";
const resultB = runChain(
  `node -e "process.exit(0)" && node -e "process.stdout.write('${markerB}')"`
);

assert(
  resultB.status === 0,
  `chain exits 0 when all scripts exit 0 (got ${resultB.status})`
);
assert(
  resultB.stdout.includes(markerB),
  "second script ran after first exited 0"
);

console.log();

// ── Scenario C: middle script exits 1 → scripts after it must not run ─────────
console.log("[ Scenario C: middle script exits 1, third must not run ]");

const markerC = "__THIRD_RAN__";
const resultC = runChain(
  `node -e "process.exit(0)" && node -e "process.exit(1)" && node -e "process.stdout.write('${markerC}')"`
);

assert(
  resultC.status === 1,
  `chain exits 1 when middle script exits 1 (got ${resultC.status})`
);
assert(
  !resultC.stdout.includes(markerC),
  "third script never ran after middle exited 1"
);

console.log();

// ── Summary ────────────────────────────────────────────────────────────────────
if (failures > 0) {
  console.error(`=== FAILED — ${failures} assertion(s) did not pass ===`);
  process.exit(1);
} else {
  console.log("=== all chain exit-code proof checks passed ===");
}
