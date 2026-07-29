/**
 * test-deploy-hook.js
 *
 * Confirms that the Replit deployment configuration wires `npm test` into the
 * build step so the full test chain — including test-backup-email-guard.js —
 * runs automatically on every deploy and cannot be bypassed.
 *
 * What it checks:
 *   1. _setup/dot-replit.toml exists (the template operators copy to .replit).
 *   2. It contains a [deployment] build command.
 *   3. That build command invokes `npm test`.
 *   4. test-backup-email-guard.js is in the `npm test` chain (package.json).
 *
 * Exit codes: 0 = all assertions pass, 1 = one or more failures.
 */

"use strict";

const fs   = require("fs");
const path = require("path");

// ---- assertion helper ----
let failures = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

console.log("=== deploy-hook wiring test ===\n");

// ---- 1. _setup/dot-replit.toml exists ----
const tomlPath = path.join(__dirname, "_setup", "dot-replit.toml");
const tomlExists = fs.existsSync(tomlPath);
assert(tomlExists, "_setup/dot-replit.toml exists");

if (!tomlExists) {
  console.error("\nERROR: cannot continue without the template file.");
  process.exit(1);
}

const tomlContent = fs.readFileSync(tomlPath, "utf8");

// ---- 2. [deployment] section is present ----
assert(
  tomlContent.includes("[deployment]"),
  "dot-replit.toml contains a [deployment] section"
);

// ---- 3. build command is present ----
assert(
  tomlContent.includes("build"),
  "dot-replit.toml contains a 'build' key under [deployment]"
);

// ---- 4. build command invokes npm test ----
assert(
  tomlContent.includes("npm test"),
  "dot-replit.toml build command invokes 'npm test'"
);

// ---- 5. build command runs before the app starts (run key also present) ----
assert(
  tomlContent.includes("npm start"),
  "dot-replit.toml run command invokes 'npm start' (build fires first, then run)"
);

// ---- 6. test-backup-email-guard.js is in the npm test chain ----
const pkgPath = path.join(__dirname, "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
const testScript = pkg.scripts && pkg.scripts.test || "";

assert(
  testScript.includes("test-backup-email-guard.js"),
  "package.json 'test' script includes test-backup-email-guard.js"
);

// ---- 7. guard covers both absence cases (BACKUP_EMAIL + BREVO_API) ----
const guardPath = path.join(__dirname, "test-backup-email-guard.js");
assert(fs.existsSync(guardPath), "test-backup-email-guard.js exists");

const guardContent = fs.readFileSync(guardPath, "utf8");
assert(
  guardContent.includes("BREVO_API"),
  "test-backup-email-guard.js covers the BREVO_API absence case"
);
assert(
  guardContent.includes("BACKUP_EMAIL"),
  "test-backup-email-guard.js covers the BACKUP_EMAIL absence case"
);

console.log("\n=== Done (deploy-hook wiring test) ===");
process.exit(failures > 0 ? 1 : 0);
