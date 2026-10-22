import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync, chmodSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { verifyStudioBuild } from "./verify-studio-build.mjs";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

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

function publishGateFixture(env, check) {
  const directory=mkdtempSync(join(tmpdir(),"studio-gate-check-"));
  try {
    for(const [command,contents] of [
      ["python3", 'echo "SENTINEL: test-studio-access.py protected access checks OK"\nexit "${FIXTURE_PYTHON_EXIT:-0}"'],
      ["node", 'echo "BROWSER_FIXTURE_CALLED"\nif [ "${FIXTURE_MISSING_SENTINEL:-0}" = 0 ]; then echo "SENTINEL: test-studio-entry-ui.mjs authenticated checks OK"; fi\nexit "${FIXTURE_NODE_EXIT:-0}"'],
    ]){
      const path=join(directory,command);
      writeFileSync(path,"#!/usr/bin/env bash\n"+contents+"\n");chmodSync(path,0o755);
    }
    const result=spawnSync("bash",[fileURLToPath(new URL("./check-studio-regressions.sh",import.meta.url))],
      {cwd:tmpdir(),encoding:"utf8",env:{...process.env,PATH:directory+":"+process.env.PATH,...env}});
    check(result);
  }finally{rmSync(directory,{recursive:true,force:true});}
}

test("publish gate runs from any directory and requires both completed regressions",()=>{
  publishGateFixture({},result=>assert.equal(result.status,0,result.stdout+result.stderr));
  const script=readFileSync(new URL("./build-published-site.sh",import.meta.url),"utf8");
  assert.ok(script.indexOf("bash website/check-studio-regressions.sh")>
    script.indexOf("node website/build-studio.mjs --published"));
});
test("failed server checks stop publishing before the browser check",()=>{
  publishGateFixture({FIXTURE_PYTHON_EXIT:"17"},result=>{
    assert.equal(result.status,17);
    assert.ok(!result.stdout.includes("BROWSER_FIXTURE_CALLED"));
  });
});
test("browser failures and empty successful check scripts block publishing",()=>{
  publishGateFixture({FIXTURE_NODE_EXIT:"19"},result=>assert.equal(result.status,19));
  publishGateFixture({FIXTURE_MISSING_SENTINEL:"1"},result=>{
    assert.equal(result.status,1);
    assert.match(result.stderr,/missing SENTINEL/);
  });
});
