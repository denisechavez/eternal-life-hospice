import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { verifyStudioBuild } from "./verify-studio-build.mjs";

function fixture(run) {
  const directory = mkdtempSync(join(tmpdir(), "studio-build-check-"));
  mkdirSync(join(directory, ".vite"));
  mkdirSync(join(directory, "assets"));
  const manifest = {
    "index.html": {file: "assets/login.js", isEntry: true, dynamicImports: ["review"]},
    review: {file: "assets/review.js", css: ["assets/review.css"]},
  };
  writeFileSync(join(directory, "index.html"), '<script src="/studio/assets/login.js"></script>');
  writeFileSync(join(directory, ".vite/manifest.json"), JSON.stringify(manifest));
  for (const name of ["login.js", "review.js", "review.css"]) {
    writeFileSync(join(directory, "assets", name), "/* fixture */");
  }
  try { run(directory, manifest); }
  finally { rmSync(directory, {recursive: true, force: true}); }
}

test("complete login and private review assets are accepted", () => fixture(directory => {
  assert.equal(verifyStudioBuild(directory), 2);
}));
test("missing Studio entry fails validation", () => fixture(directory => {
  rmSync(join(directory, "index.html"));
  assert.throws(() => verifyStudioBuild(directory));
}));
test("missing private review chunks fail validation", () => fixture(directory => {
  rmSync(join(directory, "assets/review.js"));
  assert.throws(() => verifyStudioBuild(directory));
}));
test("missing stylesheet fails validation", () => fixture(directory => {
  rmSync(join(directory, "assets/review.css"));
  assert.throws(() => verifyStudioBuild(directory));
}));
test("wrong asset base fails validation", () => fixture(directory => {
  writeFileSync(join(directory, "index.html"), '<script src="/assets/login.js"></script>');
  assert.throws(() => verifyStudioBuild(directory), /asset base/);
}));
test("broken manifest dependencies fail validation", () => fixture((directory, manifest) => {
  manifest["index.html"].dynamicImports.push("missing");
  writeFileSync(join(directory, ".vite/manifest.json"), JSON.stringify(manifest));
  assert.throws(() => verifyStudioBuild(directory), /dependency/);
}));
test("publish exclusions must not remove the required Studio app", () => {
  const ignored = readFileSync(new URL("../.replitignore", import.meta.url), "utf8");
  assert.ok(!ignored.split(/\r?\n/).some(line => line.trim() === "/website/studio-build/"));
});
