import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const source = await readFile(new URL("./elh-preview/assets/contact-fields.js", import.meta.url), "utf8");
const {validPhone, formatPhone} = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));
for (const [raw, expected] of [
  ["2", "2"], ["2025", "202.5"], ["2025550", "202.555.0"],
  ["2025550190", "202.555.0190"], ["(202) 555-0190", "202.555.0190"],
  ["12025550190", "+1 202.555.0190"], ["+1 (202) 555-0190", "+1 202.555.0190"],
  ["+442079460123", "+442079460123"], ["call2025550190", "call2025550190"],
  ["2025550190123456", "2025550190123456"]
]) assert.equal(formatPhone(raw), expected, raw);
for (const value of ["202.555.0190", "+1 202.555.0190", "+442079460123", "805-555-0100"])
  assert.equal(validPhone(value), true, value);
for (const value of ["", "2025550", "call2025550190", "22025550190", "+1 202555019", "+120255501901", "+2025550190123456"])
  assert.equal(validPhone(value), false, value);
console.log("PASS partial formatting, pasted numbers, country codes and incomplete/invalid numbers");
