/**
 * test-syntax-check.js
 *
 * Runs `node --check` on every test-*.js file in this directory.
 * Catches undefined-variable / syntax errors before they reach runtime.
 *
 * Exit codes: 0 = all files pass, 1 = at least one file has a syntax error.
 */

"use strict";

const { execFileSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const dir = __dirname;
const files = fs
  .readdirSync(dir)
  .filter((f) => f.startsWith("test-") && f.endsWith(".js"))
  .sort();

let failed = 0;

console.log(`=== syntax check (node --check) for ${files.length} test file(s) ===\n`);

for (const file of files) {
  const full = path.join(dir, file);
  try {
    execFileSync(process.execPath, ["--check", full], { stdio: "pipe" });
    console.log(`  PASS: ${file}`);
  } catch (err) {
    const detail = (err.stderr || err.stdout || "").toString().trim();
    console.error(`  FAIL: ${file}`);
    if (detail) console.error(`        ${detail}`);
    failed++;
  }
}

console.log(`\n${failed === 0 ? "All files pass syntax check." : `${failed} file(s) failed syntax check.`}`);

if (failed > 0) process.exit(1);
