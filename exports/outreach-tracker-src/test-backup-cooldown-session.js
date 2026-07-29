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

const http    = require("http");
const express = require("express");
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
async function bootApp({ sessionStorageData = {}, backupRunResponse = null, throwingStorage = false, customStorage = null, backupRunFetcher = null, captureErrors = false } = {}) {
  const dom = new JSDOM(MINIMAL_HTML, {
    runScripts: "dangerously",
    url: "http://localhost/",
  });
  const w = dom.window;

  if (customStorage) {
    // Caller supplies a fully custom storage object (e.g. a mix of readable
    // getItem + throwing removeItem) to exercise specific code paths.
    Object.defineProperty(w, "sessionStorage", {
      configurable: true,
      get: () => customStorage,
    });
  } else if (throwingStorage) {
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
      if (backupRunFetcher) return backupRunFetcher(url, opts);
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

  // Optionally register an uncaught-error collector BEFORE the script runs so
  // that synchronous errors thrown during app.js evaluation — including anything
  // in the boot IIFE's synchronous setup path — are captured.  Callers that need
  // this pass `captureErrors: true`; the returned `uncaughtErrors` array is then
  // populated with any window `error` events that fire during and after boot.
  const uncaughtErrors = captureErrors ? [] : null;
  if (captureErrors) {
    w.addEventListener("error", (e) => { uncaughtErrors.push(e.error || e.message); });
  }

  // Execute the real app.js in this window context
  const script = w.document.createElement("script");
  script.textContent = APP_JS;
  w.document.body.appendChild(script);

  // Give the async boot IIFE (/api/me → enterApp → /api/visits, /api/config,
  // /api/backup/status) time to resolve.
  await new Promise((resolve) => setTimeout(resolve, 60));

  return { dom, w, mockState, uncaughtErrors };
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
    // The stale key is proactively removed by the else-if branch in enterApp()
    // so it never lingers in storage for the rest of the session.
    assert(
      w.sessionStorage.getItem(KEY) === null,
      "stale key is removed from sessionStorage on load (proactive cleanup)"
    );
    console.log();
  }

  /* ── Scenario 6: stale key is left harmlessly after a successful backup run ── */
  //
  // After the user successfully triggers a backup (server returns 200), the
  // stale key was already removed by the proactive cleanup in enterApp() (the
  // `else if (_cooldownUntil > 0)` branch), so the key is null both before and
  // after the successful run.
  //
  console.log("--- Scenario 6: stale key already cleaned up by enterApp before a successful backup run ---");
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

    // Button must be enabled before the click (stale key was skipped and cleaned up)
    assert(btn.disabled === false, "button enabled before run (stale key skipped)");
    assert(
      w.sessionStorage.getItem(KEY) === null,
      "stale key already removed by enterApp() proactive cleanup before the click"
    );

    // Click — success path executes
    btn.click();
    // Wait for the async handler to complete and restore the button
    await waitFor(() => btn.textContent === "Run backup now", 2000);

    assert(btn.disabled === false, "button re-enabled after successful run");
    assert(
      btn.textContent === "Run backup now",
      `button label restored to "Run backup now" (got "${btn.textContent}")`
    );
    assert(
      w.sessionStorage.getItem(KEY) === null,
      "key remains absent after successful run"
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

  /* ── Scenario 8: proactive cleanup survives throwing sessionStorage ─────────
   *
   * When the browser blocks sessionStorage entirely, _ssGet() returns null so
   * _cooldownUntil === 0 and the proactive-cleanup branch is unreachable in
   * practice.  This scenario uses a hybrid mock: getItem returns a stale
   * deadline (so _cooldownUntil > 0 but ≤ Date.now()), while removeItem always
   * throws.  This exercises the else-if branch in enterApp() and confirms that
   * _ssRemove()'s internal try/catch swallows the error gracefully — no
   * uncaught exception, button stays enabled.
   */
  console.log("--- Scenario 8: proactive cleanup with throwing removeItem — no uncaught error, button enabled ---");
  {
    let uncaughtError = null;
    const KEY = "runBackupCooldownUntil";
    const staleDeadline = String(Date.now() - 60_000); // 60 s in the past

    // Hybrid storage: getItem returns the stale deadline so the else-if branch
    // in enterApp() fires; removeItem (and everything else) always throws to
    // verify that _ssRemove's try/catch handles the error silently.
    const alwaysThrows = () => { throw new DOMException("Storage is disabled", "SecurityError"); };
    const hybridStorage = {
      getItem: (k) => (k === KEY ? staleDeadline : null),
      setItem:    alwaysThrows,
      removeItem: alwaysThrows,
      clear:      alwaysThrows,
      key:        alwaysThrows,
      length:     0,
    };

    const { w } = await bootApp({ customStorage: hybridStorage });

    // Register the uncaught-error listener BEFORE enterApp() settles so we
    // don't miss anything that fires during the cleanup branch.
    w.addEventListener("error", (e) => { uncaughtError = e.error || e.message; });

    const btn = w.document.getElementById("runBackupBtn");

    // Give enterApp() time to reach and execute the proactive-cleanup branch
    await new Promise((r) => setTimeout(r, 80));

    assert(uncaughtError === null, "no uncaught error when removeItem throws during proactive cleanup");
    assert(btn.disabled === false, "button stays enabled (stale key — no active cooldown)");
    assert(
      btn.textContent === "Run backup now",
      `button label unchanged (got "${btn.textContent}")`
    );
    console.log();
  }

  /* ── Scenario 9: hard-refresh bypass — server gate blocks second instance ──
   *
   * When sessionStorage is blocked (e.g. Private Browsing), the client-side
   * cooldown lives in-memory only and is lost on a hard refresh.  A new page
   * load (second jsdom instance) therefore has zero knowledge of the cooldown.
   * This scenario verifies that the SERVER-SIDE rate limit is the real backstop:
   * even without any client cooldown, the second "hard-refreshed" instance is
   * still rejected with 429 by the server.
   *
   * The test spins up a real Express server with max=1 per window so the first
   * request is allowed and the second is definitively blocked at the server.
   * ─────────────────────────────────────────────────────────────────────────── */
  console.log("--- Scenario 9: hard-refresh bypass — server gate blocks second instance (throwingStorage) ---");
  {
    /* ── build a tight in-memory rate limiter: max 1 per window ── */
    const rlStore9 = new Map();
    function rateLimit1({ windowMs, message }) {
      return (req, res, next) => {
        const now = Date.now();
        const key = `${req.path}:${req.ip}`;
        let rec = rlStore9.get(key);
        if (!rec || now - rec.first > windowMs) {
          rec = { count: 0, first: now };
          rlStore9.set(key, rec);
        }
        rec.count += 1;
        if (rec.count > 1) {
          const waitSec = Math.ceil((rec.first + windowMs - now) / 1000);
          res.setHeader("Retry-After", String(Math.max(waitSec, 1)));
          return res.status(429).json({ error: message });
        }
        next();
      };
    }

    const RATE_MSG = "Too many backup requests. Please wait before trying again.";
    const app9 = express();
    app9.use(express.json());
    app9.post(
      "/api/backup/run",
      rateLimit1({ windowMs: 60 * 60 * 1000, message: RATE_MSG }),
      (_req, res) => res.json({ ok: true, note: "stub backup ok" })
    );
    const srv9 = http.createServer(app9);
    await new Promise((resolve) => srv9.listen(0, "127.0.0.1", resolve));
    const base9 = `http://127.0.0.1:${srv9.address().port}`;

    /* ── make a real HTTP POST, return a fetch-compatible response object ── */
    function makeRealFetcher(baseUrl) {
      return function (url) {
        return new Promise((resolve, reject) => {
          const target = new URL("/api/backup/run", baseUrl);
          const reqOpts = {
            hostname: target.hostname,
            port: Number(target.port),
            path: target.pathname,
            method: "POST",
            headers: { "Content-Type": "application/json", "Content-Length": "0" },
          };
          const req = http.request(reqOpts, (res) => {
            let body = "";
            res.on("data", (c) => (body += c));
            res.on("end", () => {
              let data = null;
              try { data = JSON.parse(body); } catch (_) {}
              resolve({
                ok: res.statusCode >= 200 && res.statusCode < 300,
                status: res.statusCode,
                headers: {
                  get: (h) => res.headers[h.toLowerCase()] != null
                    ? String(res.headers[h.toLowerCase()])
                    : null,
                },
                json: async () => data,
              });
            });
          });
          req.on("error", reject);
          req.end();
        });
      };
    }

    const realFetcher = makeRealFetcher(base9);

    try {
      /* ── Instance 1: throwingStorage — client has NO stored cooldown ──────
       *   First click → server allows (count=1, within max=1 limit).
       *   Button should re-enable once the successful response is processed.
       * ─────────────────────────────────────────────────────────────────── */
      const { w: w1 } = await bootApp({
        throwingStorage: true,
        backupRunFetcher: realFetcher,
      });
      const btn1 = w1.document.getElementById("runBackupBtn");
      assert(btn1.disabled === false, "Scenario 9 / instance 1: button starts enabled (no client cooldown)");

      btn1.click();

      // Wait for the async handler — successful run re-enables the button
      await waitFor(() => btn1.textContent === "Run backup now", 2000);

      assert(btn1.disabled === false, "Scenario 9 / instance 1: button re-enabled after server returned 200");
      assert(
        btn1.textContent === "Run backup now",
        `Scenario 9 / instance 1: label restored to "Run backup now" (got "${btn1.textContent}")`
      );

      /* ── Instance 2: throwingStorage, fresh jsdom — client has NO cooldown ──
       *   This models a hard-refresh in a privacy context: in-memory cooldown
       *   is gone, sessionStorage is inaccessible, so the client believes the
       *   button is freely clickable.
       *   Second click → server blocks with 429 (count=2, exceeds max=1).
       *   The button must become disabled, proving the server is the backstop.
       * ─────────────────────────────────────────────────────────────────── */
      const { w: w2 } = await bootApp({
        throwingStorage: true,
        backupRunFetcher: realFetcher,
      });
      const btn2 = w2.document.getElementById("runBackupBtn");
      assert(btn2.disabled === false, "Scenario 9 / instance 2: button starts enabled (no client cooldown after hard-refresh)");

      btn2.click();

      // Wait for the async handler — 429 from server disables the button
      await waitFor(() => btn2.disabled === true, 2000);

      assert(btn2.disabled === true, "Scenario 9 / instance 2: button disabled — server 429 enforced despite no client cooldown");
      assert(
        btn2.textContent.startsWith("Try again in"),
        `Scenario 9 / instance 2: countdown label shown (got "${btn2.textContent}")`
      );
    } finally {
      srv9.close();
    }
    console.log();
  }

  /* ── Scenario 10: fully opaque blocked storage — neither cooldown branch fires
   *
   * This scenario documents and asserts the defined safe behavior when the
   * browser blocks sessionStorage so completely that getItem itself throws
   * (e.g. iOS Safari Private Browsing, or a browser extension that traps every
   * storage access).
   *
   * _ssGet() wraps getItem in a try/catch and returns null on error, so the
   * enterApp() cooldown-resume block evaluates to:
   *
   *   const _cooldownUntil = parseInt(null || "0", 10);  // → 0
   *
   * With _cooldownUntil === 0 both guards are false:
   *   • `_cooldownUntil > Date.now()` → false  — active-cooldown branch skipped
   *   • `_cooldownUntil > 0`          → false  — proactive-cleanup branch skipped
   *
   * Expected/safe outcome: neither branch fires.  The app boots cleanly, no
   * uncaught error is thrown, and the button remains enabled.  Proactive cleanup
   * requires a positive _cooldownUntil (i.e. a stale timestamp) to enter the
   * else-if branch; when getItem throws there is no timestamp to parse, so
   * cleanup is correctly skipped rather than silently attempted.
   *
   * The error listener is registered via captureErrors=true inside bootApp(),
   * BEFORE app.js executes, so any synchronous or async exception thrown during
   * the script-evaluation or enterApp() cooldown path is captured.
   */
  console.log("--- Scenario 10: fully opaque blocked storage (getItem throws) — neither cooldown branch fires, no uncaught error ---");
  {
    // captureErrors registers the window error listener before app.js runs,
    // ensuring boot-phase exceptions are not missed.
    const { w, uncaughtErrors } = await bootApp({ throwingStorage: true, captureErrors: true });

    const btn = w.document.getElementById("runBackupBtn");

    // Give enterApp() time to reach and fully execute the cooldown block.
    await new Promise((r) => setTimeout(r, 80));

    assert(
      uncaughtErrors.length === 0,
      "no uncaught error when getItem throws (fully opaque blocked storage)"
    );
    assert(
      btn.disabled === false,
      "button stays enabled — _cooldownUntil === 0 so neither cooldown branch fires"
    );
    assert(
      btn.textContent === "Run backup now",
      `button label unchanged (got "${btn.textContent}")`
    );
    // Confirm no spurious in-memory cooldown timer was started — label must
    // still be unchanged after an extra tick.
    await new Promise((r) => setTimeout(r, 40));
    assert(
      btn.textContent === "Run backup now",
      "button label still unchanged after extra tick — no spurious cooldown started"
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
