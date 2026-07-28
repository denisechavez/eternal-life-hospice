/**
 * test-timer-resume.js
 *
 * Verifies that the "Last checked" interval (_backupCheckedAtTimer) starts
 * exactly once after the following sequence:
 *
 *   1. Navigate to Export tab  → timer starts
 *   2. Hide browser tab        → timer cleared (visibilitychange: hidden)
 *   3. Switch to Log tab       → timer was already null; stays null
 *   4. Switch back to Export   → timer starts again (while tab still hidden)
 *   5. Foreground browser tab  → visibilitychange: visible fires; guard
 *      `!_backupCheckedAtTimer` prevents a second interval from starting
 *
 * Only one interval must be live at the end of step 5.
 *
 * Uses jsdom + a setInterval/clearInterval spy injected BEFORE app.js runs.
 * No server or database required.
 * Exit codes: 0 = all assertions passed, 1 = one or more failures.
 */

"use strict";

const { JSDOM } = require("jsdom");
const fs   = require("fs");
const path = require("path");

const APP_JS = fs.readFileSync(path.join(__dirname, "public", "app.js"), "utf8");

// ── minimal HTML matching what app.js binds listeners to at load ──────────────
const MINIMAL_HTML = `<!DOCTYPE html><html><body>
  <div id="auth"></div>
  <div id="app">
    <div id="autherr"    class="hidden"></div>
    <div id="regClosed"  class="hidden"></div>
    <div id="codeWrap"   class="hidden"></div>
    <span id="meName"></span>
    <button id="toReg"></button>
    <button id="toLogin"></button>
    <button id="toLogin2"></button>
    <form id="loginForm">
      <input id="li-phone"><input id="li-pass">
    </form>
    <form id="regForm">
      <input id="re-name"><input id="re-phone">
      <input id="re-pass"><input id="re-code">
    </form>
    <button id="logoutBtn"></button>
    <div id="aiModelBanner" class="hidden">
      <span id="aiModelBannerMsg"></span>
      <button id="aiModelBannerDismiss"></button>
    </div>
    <div id="toast"></div>
    <input id="org">
    <input id="date" type="date">
    <textarea id="notes"></textarea>
    <input id="addr"><input id="cname"><input id="ctitle">
    <input id="cemail"><input id="cphone"><input id="city">
    <select id="cat"><option>Hospital</option></select>
    <select id="county"><option>Ventura</option></select>
    <select id="owner"><option>Unassigned</option></select>
    <select id="due"><option value="5">5 days</option></select>
    <div id="mats"></div>
    <input id="attest" type="checkbox">
    <button id="saveBtn"></button>
    <button id="clearBtn"></button>
    <div id="guard"><b></b></div>
    <div id="hasCard">
      <button class="segbtn" data-val="yes"></button>
      <button class="segbtn" data-val="no"></button>
    </div>
    <div id="cardScan">
      <button id="scanBtn"></button>
      <p class="scanhint"></p>
      <input id="fCard" type="file">
      <div id="dropCard"></div>
    </div>
    <div id="manualHint"></div>
    <input id="fSite" type="file">
    <div id="dropSite"></div>
    <div id="thumbs"></div>
    <div class="voice">
      <button id="recBtn"><span class="reclabel">Record</span></button>
      <p id="recHint"></p>
    </div>
    <div id="queue"></div>
    <span id="qcount">0</span>
    <span id="sVisits">0</span>
    <span id="sOrgs">0</span>
    <span id="sOpen">0</span>
    <span id="sWon">0</span>
    <div id="bar" class="hidden"></div>
    <button id="csv"></button>
    <button id="triggerBackup">Send full backup now</button>
    <div   id="triggerBackupStatus" class="hidden"></div>
    <button id="runBackupBtn"></button>
    <div id="backupWarn"    class="hidden"><span id="backupWarnMsg"></span></div>
    <div id="backupHistory" class="hidden"></div>
    <span id="backupCheckedAt" class="hidden"></span>
    <button class="tab" data-view="log"    aria-selected="true"></button>
    <button class="tab" data-view="queue"></button>
    <button class="tab" data-view="export"></button>
    <div id="view-log"></div>
    <div id="view-queue"  class="hidden"></div>
    <div id="view-export" class="hidden"></div>
  </div>
</body></html>`;

// ── assertion helper ──────────────────────────────────────────────────────────
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

// ── boot jsdom, install interval spy, then load app.js ───────────────────────
async function bootApp() {
  const dom = new JSDOM(MINIMAL_HTML, {
    runScripts: "dangerously",
    url: "http://localhost/",
  });
  const w = dom.window;

  // Minimal fetch mock so app.js boot sequence completes without errors.
  // /api/backup/status is called by loadBackupStatus() on every switchTab("export").
  w.fetch = async (url) => {
    if (url.includes("/api/me")) {
      return { ok: false, json: async () => ({ error: "not logged in" }) };
    }
    if (url.includes("/api/config")) {
      return { ok: true, json: async () => ({ registrationOpen: true, requiresCode: false, aiEnabled: false }) };
    }
    if (url.includes("/api/backup/status")) {
      return { ok: true, json: async () => ({ lastBackupAt: null, checkedAt: null }) };
    }
    return { ok: true, json: async () => ({}) };
  };

  // ── interval spy: wraps setInterval/clearInterval BEFORE app.js runs ─────
  // Tracks only renderCheckedAt-related intervals by watching the interval IDs
  // that are created after the spy is installed.  We count all live intervals
  // (app.js uses setInterval only for the "Last checked" ticker and the backup
  // cooldown countdown; the cooldown one is managed separately and is not
  // running during this test sequence).
  const spy = {
    active: new Set(),   // IDs of currently-live intervals
    created: 0,          // total ever created (after spy installed)
    cleared: 0,          // total ever cleared
  };

  const _realSetInterval   = w.setInterval.bind(w);
  const _realClearInterval = w.clearInterval.bind(w);

  w.setInterval = (fn, ms, ...args) => {
    const id = _realSetInterval(fn, ms, ...args);
    spy.active.add(id);
    spy.created++;
    return id;
  };
  w.clearInterval = (id) => {
    if (id !== null && id !== undefined && spy.active.has(id)) {
      spy.active.delete(id);
      spy.cleared++;
    }
    _realClearInterval(id);
  };

  // Load the real app.js
  const script = w.document.createElement("script");
  script.textContent = APP_JS;
  w.document.body.appendChild(script);

  // Wait for the async boot (api/me → api/config) to settle
  await new Promise((resolve) => setTimeout(resolve, 50));

  // Bridge: expose switchTab and document.hidden control into test scope.
  // jsdom does not implement document.visibilityState/hidden natively in a
  // way we can set from outside, so we define a writable hidden property and
  // a helper to fire the event manually.
  const bridge = w.document.createElement("script");
  bridge.textContent = `
    window.__spy = null; // filled in from Node scope below

    // Helper: simulate browser-tab hide/show and fire visibilitychange.
    window.__setHidden = function(isHidden) {
      Object.defineProperty(document, 'hidden', { value: isHidden, writable: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    };

    // Expose switchTab so we can call it directly from the test.
    window.__switchTab = function(view) { switchTab(view); };

    // Expose the raw _backupCheckedAtTimer value for inspection.
    window.__getTimerId = function() { return _backupCheckedAtTimer; };
  `;
  w.document.body.appendChild(bridge);

  // Give bridge script time to register
  await new Promise((resolve) => setTimeout(resolve, 10));

  return { dom, w, spy };
}

// ── main test runner ──────────────────────────────────────────────────────────
async function runTests() {
  console.log("=== timer-resume: visibility-then-tab-switch sequence ===\n");

  // ── Scenario 1: the core edge case ──────────────────────────────────────────
  {
    console.log("Scenario 1: hide → switch-to-log → switch-to-export → foreground");
    const { dom, w, spy } = await bootApp();

    // Reset spy counters after boot (boot may have created intervals unrelated
    // to the export timer, e.g. the cooldown; start clean).
    spy.active.clear();
    spy.created = 0;
    spy.cleared = 0;

    // Step 1: navigate to Export tab → switchTab starts the interval
    w.__switchTab("export");
    await new Promise((r) => setTimeout(r, 20));   // let loadBackupStatus settle
    const afterExport = spy.active.size;
    assert(afterExport === 1, `step 1 (switch to export): 1 interval live, got ${afterExport}`);
    assert(w.__getTimerId() !== null, "step 1: _backupCheckedAtTimer is non-null");

    // Step 2: hide the browser tab → visibilitychange fires, timer cleared
    w.__setHidden(true);
    const afterHide = spy.active.size;
    assert(afterHide === 0, `step 2 (hide tab): 0 intervals live, got ${afterHide}`);
    assert(w.__getTimerId() === null, "step 2: _backupCheckedAtTimer is null after hide");

    // Step 3: switch to Log tab while still hidden → must NOT start a timer
    w.__switchTab("log");
    const afterLogSwitch = spy.active.size;
    assert(afterLogSwitch === 0, `step 3 (switch to log while hidden): 0 intervals live, got ${afterLogSwitch}`);
    assert(w.__getTimerId() === null, "step 3: _backupCheckedAtTimer still null after log-switch");

    // Step 4: switch back to Export tab while still hidden → timer should start
    // (switchTab always starts the timer when view==="export", regardless of
    // document.hidden — the visibilitychange handler guards against duplication
    // when the tab is later foregrounded)
    w.__switchTab("export");
    await new Promise((r) => setTimeout(r, 20));
    const afterExport2 = spy.active.size;
    assert(afterExport2 === 1, `step 4 (switch to export while hidden): 1 interval live, got ${afterExport2}`);
    assert(w.__getTimerId() !== null, "step 4: _backupCheckedAtTimer is non-null after re-export");

    // Step 5: foreground browser → visibilitychange fires with hidden=false
    // The guard `!_backupCheckedAtTimer` must prevent a second interval.
    w.__setHidden(false);
    const afterForeground = spy.active.size;
    assert(afterForeground === 1, `step 5 (foreground): still exactly 1 interval live, got ${afterForeground}`);
    assert(w.__getTimerId() !== null, "step 5: _backupCheckedAtTimer remains non-null");

    // Total intervals ever created: step 1 + step 4 = 2 (step 5 must NOT add a 3rd)
    assert(spy.created === 2, `total intervals ever created = 2 (no phantom 3rd), got ${spy.created}`);

    // Teardown: clear all live intervals then close the jsdom window so Node exits cleanly.
    for (const id of spy.active) w.clearInterval(id);
    dom.window.close();
    console.log();
  }

  // ── Scenario 2: simpler path — hide then foreground without tab switch ───────
  {
    console.log("Scenario 2: hide then immediately foreground (no in-app tab change)");
    const { dom, w, spy } = await bootApp();

    spy.active.clear();
    spy.created = 0;
    spy.cleared = 0;

    // Start on Export
    w.__switchTab("export");
    await new Promise((r) => setTimeout(r, 20));
    assert(spy.active.size === 1, `baseline: 1 interval after switching to export`);

    // Hide then foreground
    w.__setHidden(true);
    assert(spy.active.size === 0, "hide clears the interval");

    w.__setHidden(false);
    assert(spy.active.size === 1, "foreground while on export restarts exactly one interval");
    assert(spy.created === 2, `total intervals created = 2 (one per start), got ${spy.created}`);

    for (const id of spy.active) w.clearInterval(id);
    dom.window.close();
    console.log();
  }

  // ── Scenario 3: foreground while on a non-export tab must NOT start timer ───
  {
    console.log("Scenario 3: foreground while on Log tab must NOT start the timer");
    const { dom, w, spy } = await bootApp();

    spy.active.clear();
    spy.created = 0;
    spy.cleared = 0;

    // Start on Export, hide, switch to Log, then foreground
    w.__switchTab("export");
    await new Promise((r) => setTimeout(r, 20));
    w.__setHidden(true);
    w.__switchTab("log");
    w.__setHidden(false);

    assert(spy.active.size === 0, "foreground while on Log: 0 intervals live");
    assert(w.__getTimerId() === null, "foreground while on Log: _backupCheckedAtTimer is null");

    for (const id of spy.active) w.clearInterval(id);
    dom.window.close();
    console.log();
  }

  console.log("=== Done ===");
}

runTests()
  .then(() => {
    process.exit(process.exitCode || 0);
  })
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exit(1);
  });
