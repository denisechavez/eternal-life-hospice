/**
 * test-backup-cooldown-session.js
 *
 * Verifies that the Run Backup button cooldown survives a mid-cooldown page
 * refresh via sessionStorage, using jsdom to execute the real public/app.js.
 *
 * What it verifies:
 *   1. Clicking #runBackupBtn when the server returns 429 writes the deadline
 *      to sessionStorage under the real RUN_BACKUP_COOLDOWN_KEY and disables
 *      the button with a countdown label.
 *   2. A simulated page refresh (new jsdom instance with sessionStorage
 *      pre-populated with the deadline from step 1) still finds the button
 *      disabled with the countdown showing the correct remaining time.
 *   3. Once the cooldown expires, sessionStorage removes the key and the
 *      button reverts to "Run backup now" and becomes enabled.
 *
 * No database or network required.
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const { JSDOM } = require("jsdom");
const fs   = require("fs");
const path = require("path");

const APP_JS = fs.readFileSync(path.join(__dirname, "public", "app.js"), "utf8");

/* ── minimal HTML — every element app.js touches at load time ─────────────── */
const MINIMAL_HTML = `<!DOCTYPE html><html><body>
  <div id="auth"></div>
  <div id="app">
    <div id="autherr" class="hidden"></div>
    <div id="regClosed" class="hidden"></div>
    <div id="codeWrap"  class="hidden"></div>
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
    <button id="runBackupBtn">Run backup now</button>
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

/* ── assert helper ──────────────────────────────────────────────────────────── */
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

/* ── boot a fresh jsdom instance with optional pre-seeded sessionStorage ────── */
async function bootApp({ sessionStorageData = {}, backupRunResponse = null, throwingStorage = false } = {}) {
  const dom = new JSDOM(MINIMAL_HTML, {
    runScripts: "dangerously",
    url: "http://localhost/",
  });
  const w = dom.window;

  if (throwingStorage) {
    // Replace sessionStorage with an object whose every method throws, simulating
    // a browser that blocks storage (e.g. Private Browsing with strict settings).
    const alwaysThrows = () => { throw new DOMException("Storage is disabled", "SecurityError"); };
    Object.defineProperty(w, "sessionStorage", {
      configurable: true,
      get: () => ({
        getItem:    alwaysThrows,
        setItem:    alwaysThrows,
        removeItem: alwaysThrows,
        clear:      alwaysThrows,
        key:        alwaysThrows,
        length:     0,
      }),
    });
  } else {
    // Pre-populate sessionStorage BEFORE app.js runs so the boot IIFE
    // → enterApp() → resume-cooldown block sees it immediately.
    for (const [k, v] of Object.entries(sessionStorageData)) {
      w.sessionStorage.setItem(k, v);
    }
  }

  // Build a mutable fetch mock so individual scenarios can control each route.
  // Wrap in an object so callers can swap `backupRunResponse` after boot.
  const mockState = { backupRunResponse };

  w.fetch = async (url, opts) => {
    // /api/me — simulate a logged-in user so enterApp() is called
    if (url.includes("/api/me")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ user: { id: 1, name: "Test User", role: "user" } }),
      };
    }
    // /api/config
    if (url.includes("/api/config")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ registrationOpen: true, requiresCode: false, aiEnabled: false }),
      };
    }
    // /api/visits
    if (url.includes("/api/visits")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ visits: [] }),
      };
    }
    // /api/backup/status
    if (url.includes("/api/backup/status")) {
      return {
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ rows: [] }),
      };
    }
    // /api/backup/run — controlled per test
    if (url.includes("/api/backup/run")) {
      const resp = mockState.backupRunResponse;
      if (resp) return resp;
      // Default: 429
      return {
        ok: false,
        status: 429,
        headers: { get: (h) => (h === "Retry-After" ? "300" : null) },
        json: async () => ({ error: "Rate limit — try again later." }),
      };
    }
    // Fallback
    return {
      ok: true,
      status: 200,
      headers: { get: () => null },
      json: async () => ({}),
    };
  };

  // Execute the real app.js in this window context
  const script = w.document.createElement("script");
  script.textContent = APP_JS;
  w.document.body.appendChild(script);

  // Give the async boot IIFE (/api/me → enterApp → /api/visits, /api/config,
  // /api/backup/status) time to resolve.
  await new Promise((resolve) => setTimeout(resolve, 60));

  return { dom, w, mockState };
}

/* ── wait for a DOM condition, polling every 20 ms up to `maxMs` ───────────── */
function waitFor(fn, maxMs = 2000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const id = setInterval(() => {
      if (fn()) { clearInterval(id); resolve(); }
      else if (Date.now() - start > maxMs) { clearInterval(id); reject(new Error("waitFor timed out")); }
    }, 20);
  });
}

/* ── main test runner ───────────────────────────────────────────────────────── */
async function runTests() {
  console.log("=== backup-button cooldown sessionStorage test (real app.js) ===\n");

  /* ── Scenario 1: 429 writes sessionStorage key and disables button ─────────── */
  console.log("--- Scenario 1: 429 writes deadline to sessionStorage ---");
  {
    const { w } = await bootApp();
    const btn = w.document.getElementById("runBackupBtn");
    assert(btn !== null, "#runBackupBtn exists in DOM");
    assert(btn.disabled === false, "button starts enabled");

    // Click the real backup button — fetch mock returns 429
    btn.click();

    // Wait for the async handler to finish and the cooldown to start
    await waitFor(() => btn.disabled === true);

    const KEY = "runBackupCooldownUntil";
    const stored = parseInt(w.sessionStorage.getItem(KEY) || "0", 10);
    assert(btn.disabled === true, "button is disabled after 429");
    assert(stored > Date.now(), "sessionStorage deadline is in the future");
    assert(
      stored >= Date.now() + 290_000,
      `deadline is ~300 s away (${stored - Date.now()} ms from now)`
    );
    assert(
      btn.textContent.startsWith("Try again in"),
      `button shows countdown label (got "${btn.textContent}")`
    );
    console.log();
  }

  /* ── Scenario 2: simulated page refresh mid-cooldown ─────────────────────── */
  console.log("--- Scenario 2: button still disabled after simulated page refresh ---");
  {
    // First "page": 429 triggers cooldown, we capture the deadline
    const { w: w1 } = await bootApp();
    const btn1 = w1.document.getElementById("runBackupBtn");
    btn1.click();
    await waitFor(() => btn1.disabled === true);

    const KEY = "runBackupCooldownUntil";
    const deadline = w1.sessionStorage.getItem(KEY);
    assert(deadline !== null, "deadline was written to sessionStorage by the first page");

    // Advance fake time by 60 s: produce a deadline 240 s in the future
    const adjustedDeadline = String(parseInt(deadline, 10));  // same deadline, ~240 s left after 60 s

    // Second "page": fresh jsdom, sessionStorage pre-seeded with the deadline
    // (We subtract 60 s to simulate 60 s having elapsed on the real clock.)
    const simulatedDeadline = String(parseInt(deadline, 10) - 60_000);
    // Sanity: should still be in the future (deadline was ~300 s out; minus 60 s = ~240 s left)
    const { w: w2 } = await bootApp({
      sessionStorageData: { [KEY]: simulatedDeadline },
    });

    // enterApp() has now run — give it time to read sessionStorage and resume cooldown
    const btn2 = w2.document.getElementById("runBackupBtn");
    await waitFor(() => btn2.disabled === true, 500);

    assert(btn2.disabled === true, "button is disabled on fresh page (mid-cooldown)");
    assert(
      btn2.textContent.startsWith("Try again in"),
      `countdown label present on fresh page (got "${btn2.textContent}")`
    );

    // Remaining time shown should be roughly the remaining seconds
    const remaining = Math.ceil((parseInt(simulatedDeadline, 10) - Date.now()) / 1000);
    const labelMatch = btn2.textContent.match(/Try again in (?:(\d+):(\d+)|(\d+)s)/);
    assert(labelMatch !== null, "button text matches countdown format");
    if (labelMatch) {
      const shownSec = labelMatch[3] !== undefined
        ? parseInt(labelMatch[3], 10)
        : parseInt(labelMatch[1], 10) * 60 + parseInt(labelMatch[2], 10);
      // Allow ±3 s tolerance for timing jitter
      assert(
        Math.abs(shownSec - remaining) <= 3,
        `countdown shows ~${remaining}s remaining (got ${shownSec}s)`
      );
    }
    assert(
      w2.sessionStorage.getItem(KEY) !== null,
      "sessionStorage key still present mid-cooldown on fresh page"
    );
    console.log();
  }

  /* ── Scenario 3: key removed and button re-enabled after expiry ────────────── */
  console.log("--- Scenario 3: key removed and button re-enabled after expiry ---");
  {
    const KEY = "runBackupCooldownUntil";
    // Pre-seed a deadline 2 seconds in the future so we don't wait 300 s
    const shortDeadline = String(Date.now() + 2000);

    const { w } = await bootApp({ sessionStorageData: { [KEY]: shortDeadline } });
    const btn = w.document.getElementById("runBackupBtn");

    // enterApp resume block should have picked up the short deadline
    await waitFor(() => btn.disabled === true, 500);
    assert(btn.disabled === true, "button is disabled when short cooldown resumes");
    assert(w.sessionStorage.getItem(KEY) !== null, "key present before expiry");

    // Wait for the 2-second cooldown to tick through (allow 3.5 s to be safe)
    await waitFor(() => btn.disabled === false, 3500);

    assert(btn.disabled === false, "button re-enabled after cooldown expires");
    assert(
      btn.textContent === "Run backup now",
      `button label restored to "Run backup now" (got "${btn.textContent}")`
    );
    assert(
      w.sessionStorage.getItem(KEY) === null,
      "sessionStorage key removed after expiry"
    );
    console.log();
  }

  /* ── Scenario 4: mid-cooldown refresh then expiry ──────────────────────────── */
  console.log("--- Scenario 4: button re-enables after expiry following a refresh ---");
  {
    const KEY = "runBackupCooldownUntil";
    // 3 seconds total; "refresh" happens at 1 second elapsed → 2 seconds remain
    const shortDeadline = String(Date.now() + 3000);

    // First "page": boot with 3-second deadline
    const { w: w1 } = await bootApp({ sessionStorageData: { [KEY]: shortDeadline } });
    const btn1 = w1.document.getElementById("runBackupBtn");
    await waitFor(() => btn1.disabled === true, 500);
    assert(btn1.disabled === true, "button disabled on first page (3 s deadline)");

    // Wait 1 second — 2 seconds remain
    await new Promise((r) => setTimeout(r, 1000));

    // The deadline in sessionStorage was overwritten by _startRunBackupCooldown
    // when it resumed; read the current stored value (should still be ~2 s out)
    const currentDeadline = w1.sessionStorage.getItem(KEY);
    assert(currentDeadline !== null, "key still in sessionStorage after 1 s");

    // Second "page": pre-seed with the current deadline
    const { w: w2 } = await bootApp({ sessionStorageData: { [KEY]: currentDeadline } });
    const btn2 = w2.document.getElementById("runBackupBtn");
    await waitFor(() => btn2.disabled === true, 500);
    assert(btn2.disabled === true, "button disabled on refreshed page (~2 s remaining)");

    // Wait for expiry (allow 4 s)
    await waitFor(() => btn2.disabled === false, 4000);

    assert(btn2.disabled === false, "button re-enabled after expiry post-refresh");
    assert(
      w2.sessionStorage.getItem(KEY) === null,
      "sessionStorage key removed after post-refresh expiry"
    );
    console.log();
  }

  /* ── Scenario 5: stale (already-expired) key on load — button stays enabled ── */
  //
  // This covers the case where a user dismissed a 429, closed the tab, and
  // returns hours later after the server-side 5-minute window has already reset.
  // The enterApp cooldown-resume guard is:
  //   if (_cooldownUntil > Date.now()) { … }
  // A past deadline is NOT greater than Date.now(), so the cooldown is skipped
  // and the button must remain enabled.  The stale key is left harmlessly in
  // sessionStorage (not re-used; the `> Date.now()` guard prevents it).
  //
  console.log("--- Scenario 5: stale (already-expired) key on load — button stays enabled ---");
  {
    const KEY = "runBackupCooldownUntil";
    // Deadline was 60 seconds in the past (server-side limit has fully reset)
    const staleDeadline = String(Date.now() - 60_000);

    const { w } = await bootApp({ sessionStorageData: { [KEY]: staleDeadline } });
    const btn = w.document.getElementById("runBackupBtn");

    // Give enterApp() a moment to finish running (it is async)
    await new Promise((r) => setTimeout(r, 80));

    assert(btn.disabled === false, "button stays enabled when stored deadline is already past");
    assert(
      btn.textContent === "Run backup now",
      `button label unchanged (got "${btn.textContent}")`
    );
    // The stale key is left in storage — it is harmless because the guard
    // (`> Date.now()`) will skip it on every subsequent enterApp() call too.
    // This documents the chosen behaviour: no cleanup on load, no re-use.
    assert(
      w.sessionStorage.getItem(KEY) === staleDeadline,
      "stale key is left in sessionStorage (not re-used, not cleared on load)"
    );
    console.log();
  }

  /* ── Scenario 6: stale key is left harmlessly after a successful backup run ── */
  //
  // After the user successfully triggers a backup (server returns 200), the
  // success path in the click handler does NOT call _ssRemove — it only
  // restores btn.disabled = false and btn.textContent.  The stale key therefore
  // remains in sessionStorage, which is fine: the `> Date.now()` guard in
  // enterApp() will still skip it on any subsequent page load.
  //
  console.log("--- Scenario 6: stale key remains harmlessly after a successful backup run ---");
  {
    const KEY = "runBackupCooldownUntil";
    const staleDeadline = String(Date.now() - 300_000); // 5 minutes ago

    // Boot with a successful /api/backup/run response
    const { w, mockState } = await bootApp({
      sessionStorageData: { [KEY]: staleDeadline },
      backupRunResponse: {
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ rows: [] }),
      },
    });
    const btn = w.document.getElementById("runBackupBtn");

    // Let enterApp() settle
    await new Promise((r) => setTimeout(r, 80));

    // Button must be enabled before the click (stale key was skipped)
    assert(btn.disabled === false, "button enabled before run (stale key skipped)");

    // Click — success path executes
    btn.click();
    // Wait for the async handler to complete and restore the button
    await waitFor(() => btn.textContent === "Run backup now", 2000);

    assert(btn.disabled === false, "button re-enabled after successful run");
    assert(
      btn.textContent === "Run backup now",
      `button label restored to "Run backup now" (got "${btn.textContent}")`
    );
    // Documented behaviour: success path does not clean up the stale key;
    // the key is left in storage and remains harmless on future loads.
    assert(
      w.sessionStorage.getItem(KEY) === staleDeadline,
      "stale key still in sessionStorage after successful run (left harmlessly — guard skips it on next load)"
    );
    console.log();
  }

  /* ── Scenario 7: storage unavailable — cooldown still runs in-memory ──────── */
  console.log("--- Scenario 7: sessionStorage blocked — no uncaught error, button still disables ---");
  {
    let uncaughtError = null;

    const { w } = await bootApp({ throwingStorage: true });

    // Capture any uncaught error the window emits (would indicate a missing try/catch)
    w.addEventListener("error", (e) => { uncaughtError = e.error || e.message; });

    const btn = w.document.getElementById("runBackupBtn");
    assert(btn !== null, "#runBackupBtn exists in DOM");
    assert(btn.disabled === false, "button starts enabled with throwing storage");

    // Click — fetch mock returns 429, cooldown logic runs with broken sessionStorage
    btn.click();

    await waitFor(() => btn.disabled === true);

    assert(uncaughtError === null, "no uncaught error when sessionStorage always throws");
    assert(btn.disabled === true, "button is disabled (in-memory cooldown) despite broken storage");
    assert(
      btn.textContent.startsWith("Try again in"),
      `countdown label present despite broken storage (got "${btn.textContent}")`
    );
    console.log();
  }

  console.log("=== Done ===");
}

runTests()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => {
    // jsdom setInterval timers keep the Node event loop alive; force exit so
    // the test runner (npm test chain) is not blocked waiting for them to clear.
    process.exit(process.exitCode || 0);
  });
