/**
 * test-scanhint-reset.js
 *
 * Verifies that the scan-hint text and "busy" class reset correctly when the
 * card-photo thumbnail × button is clicked after a scan has run, while
 * hasCard === "yes" and scanning === false.
 *
 * Uses jsdom to load and execute the real public/app.js, so regressions in
 * the actual remove handler are caught.
 *
 * No server or database required.
 * Exit codes: 0 = all assertions passed, 1 = one or more failures.
 */

"use strict";

const { JSDOM } = require("jsdom");
const fs   = require("fs");
const path = require("path");

const APP_JS = fs.readFileSync(path.join(__dirname, "public", "app.js"), "utf8");

// ── minimal HTML: every element app.js binds a listener to at load time ───────
const MINIMAL_HTML = `<!DOCTYPE html><html><body>
  <!-- auth views -->
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
    <!-- AI banner -->
    <div id="aiModelBanner" class="hidden">
      <span id="aiModelBannerMsg"></span>
      <button id="aiModelBannerDismiss"></button>
    </div>
    <div id="toast"></div>
    <!-- log form fields -->
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
    <!-- card scanning -->
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
    <!-- voice -->
    <div class="voice">
      <button id="recBtn"><span class="reclabel">Record</span></button>
      <p id="recHint"></p>
    </div>
    <!-- queue / stats -->
    <div id="queue"></div>
    <span id="qcount">0</span>
    <span id="sVisits">0</span>
    <span id="sOrgs">0</span>
    <span id="sOpen">0</span>
    <span id="sWon">0</span>
    <!-- export tab -->
    <div id="bar" class="hidden"></div>
    <button id="csv"></button>
    <button id="triggerBackup">Send full backup now</button>
    <div   id="triggerBackupStatus" class="hidden"></div>
    <button id="runBackupBtn"></button>
    <div id="backupWarn"    class="hidden"><span id="backupWarnMsg"></span></div>
    <div id="backupHistory" class="hidden"></div>
    <span id="backupCheckedAt" class="hidden"></span>
    <!-- tabs -->
    <button class="tab" data-view="log"    aria-selected="true"></button>
    <button class="tab" data-view="queue"></button>
    <button class="tab" data-view="export"></button>
    <div id="view-log"></div>
    <div id="view-queue"  class="hidden"></div>
    <div id="view-export" class="hidden"></div>
  </div>
</body></html>`;

// ── assert helper ──────────────────────────────────────────────────────────────
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

// ── boot a fresh jsdom instance with app.js loaded ────────────────────────────
async function bootApp({ aiEnabled = true } = {}) {
  const dom = new JSDOM(MINIMAL_HTML, {
    runScripts: "dangerously",
    url: "http://localhost/",
  });
  const w = dom.window;

  // Provide a minimal fetch mock: /api/me fails (unauthenticated),
  // /api/config resolves so initAuthScreen() completes without errors.
  w.fetch = async (url) => {
    if (url.includes("/api/me")) {
      return { ok: false, json: async () => ({ error: "not logged in" }) };
    }
    if (url.includes("/api/config")) {
      return {
        ok: true,
        json: async () => ({ registrationOpen: true, requiresCode: false, aiEnabled }),
      };
    }
    // Any other endpoint (backup, etc.) — return empty ok response
    return { ok: true, json: async () => ({}) };
  };

  // Execute the real app.js in this window context
  const script = w.document.createElement("script");
  script.textContent = APP_JS;
  w.document.body.appendChild(script);

  // Wait for the async boot IIFE (/api/me → /api/config) to settle
  await new Promise((resolve) => setTimeout(resolve, 30));

  // Inject a bridge script in the same global lexical scope so the test can
  // read and write app.js's top-level `let` variables (which are NOT on window).
  const bridge = w.document.createElement("script");
  bridge.textContent = `
    window.__app = {
      get photos()    { return photos;    },
      set photos(v)   { photos = v;       },
      get hasCard()   { return hasCard;   },
      set hasCard(v)  { hasCard = v;      },
      get scanning()  { return scanning;  },
      set scanning(v) { scanning = v;     },
      get aiEnabled() { return aiEnabled; },
      set aiEnabled(v){ aiEnabled = v;    },
      SCAN_HINT,
      SCAN_HINT_NO_AI,
      drawThumbs: () => drawThumbs(),
      onCardPhotoSet: (d) => onCardPhotoSet(d),
    };
  `;
  w.document.body.appendChild(bridge);

  return { dom, w };
}

// ── helpers to drive the real app state via the bridge ───────────────────────

/** Put a fake card photo into app state and call the real drawThumbs() */
function loadFakeCardPhoto(w) {
  w.__app.photos = { card: "data:image/jpeg;base64,/9j/fake", site: null };
  w.__app.drawThumbs();
}

/** Simulate extractCard's "reading" phase — adds "busy" and sets in-progress text */
function simulateScanInProgress(w) {
  const hint = w.document.querySelector(".scanhint");
  if (hint) { hint.textContent = "Reading the card\u2026"; hint.classList.add("busy"); }
}

/** Simulate extractCard's success — sets post-scan text, removes "busy" */
function simulateScanSuccess(w) {
  const hint = w.document.querySelector(".scanhint");
  if (hint) { hint.textContent = "Card read \u2014 please check every detail is right."; hint.classList.remove("busy"); }
}

// ─────────────────────────────────────────────────────────────────────────────

async function runTests() {
  console.log("=== scan-hint reset on card-photo removal (app.js) ===\n");

  // ── Scenario 1: aiEnabled=true — post-scan hint resets on remove ────────────
  {
    console.log("Scenario 1: aiEnabled=true — full path through drawThumbs remove handler");
    const { w } = await bootApp({ aiEnabled: true });

    // Set state: card toggle "yes", AI on, photo loaded
    // (aiEnabled stays false until enterApp() runs; set it explicitly since we skip login)
    w.__app.aiEnabled = true;
    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);

    // Simulate a completed scan: hint shows post-scan text, no "busy"
    simulateScanSuccess(w);

    // Find and click the real × remove button rendered by drawThumbs()
    const rmBtn = w.document.querySelector("#thumbs .rm[data-slot='card']");
    assert(rmBtn !== null, "remove button is rendered in #thumbs after photo load");
    rmBtn && rmBtn.click();

    const hint = w.document.querySelector(".scanhint");
    assert(hint !== null, ".scanhint element exists");
    assert(hint.textContent === w.__app.SCAN_HINT, "hint text resets to SCAN_HINT");
    assert(!hint.classList.contains("busy"),        "'busy' class is absent after reset");
    console.log();
  }

  // ── Scenario 2: aiEnabled=false — hint resets to SCAN_HINT_NO_AI ───────────
  {
    console.log("Scenario 2: aiEnabled=false — hint resets to SCAN_HINT_NO_AI on remove");
    const { w } = await bootApp({ aiEnabled: false });

    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);

    // Simulate a scan that failed (busy removed, error text shown)
    const hint = w.document.querySelector(".scanhint");
    if (hint) { hint.textContent = "Couldn't read the card. Please type the details by hand."; hint.classList.remove("busy"); }

    const rmBtn = w.document.querySelector("#thumbs .rm[data-slot='card']");
    assert(rmBtn !== null, "remove button is rendered in #thumbs");
    rmBtn && rmBtn.click();

    assert(hint.textContent === w.__app.SCAN_HINT_NO_AI, "hint text resets to SCAN_HINT_NO_AI");
    assert(!hint.classList.contains("busy"),              "'busy' class is absent after reset");
    console.log();
  }

  // ── Scenario 3: scanning=true — guard prevents reset ─────────────────────────
  {
    console.log("Scenario 3: scanning=true — remove must NOT reset the hint");
    const { w } = await bootApp({ aiEnabled: true });

    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);
    simulateScanInProgress(w);    // sets in-progress text + busy on the DOM hint

    // Set the app-level scanning flag so the guard fires in the real handler
    w.__app.scanning = true;

    const hint = w.document.querySelector(".scanhint");
    const textBefore = hint ? hint.textContent : "";

    const rmBtn = w.document.querySelector("#thumbs .rm[data-slot='card']");
    assert(rmBtn !== null, "remove button is rendered in #thumbs");
    rmBtn && rmBtn.click();

    assert(hint.textContent === textBefore, "hint text unchanged while scan in progress");
    assert(hint.classList.contains("busy"), "'busy' class retained while scan in progress");
    console.log();
  }

  // ── Scenario 4: hasCard="no" — remove handler guard prevents reset ───────────
  {
    console.log("Scenario 4: hasCard='no' — remove must NOT reset the hint");
    const { w } = await bootApp({ aiEnabled: true });

    // Load a photo with hasCard still "no" (photo loaded before toggle)
    w.__app.hasCard = "no";
    loadFakeCardPhoto(w);

    const hint = w.document.querySelector(".scanhint");
    if (hint) { hint.textContent = "some other text"; hint.classList.add("busy"); }

    const rmBtn = w.document.querySelector("#thumbs .rm[data-slot='card']");
    assert(rmBtn !== null, "remove button is rendered in #thumbs");
    rmBtn && rmBtn.click();

    assert(hint.textContent === "some other text", "hint text unchanged when hasCard is 'no'");
    assert(hint.classList.contains("busy"),         "'busy' class retained when hasCard is 'no'");
    console.log();
  }

  // ── Scenario 5: removing a site photo leaves card hint untouched ─────────────
  {
    console.log("Scenario 5: removing site photo must NOT affect card hint");
    const { w } = await bootApp({ aiEnabled: true });

    w.__app.hasCard = "yes";
    w.__app.photos = { card: "data:image/jpeg;base64,/9j/card", site: "data:image/jpeg;base64,/9j/site" };
    w.__app.drawThumbs();

    simulateScanSuccess(w);

    const hint = w.document.querySelector(".scanhint");
    const textBefore = hint ? hint.textContent : "";

    // Click the site remove button specifically
    const siteBtn = w.document.querySelector("#thumbs .rm[data-slot='site']");
    assert(siteBtn !== null, "site remove button is rendered in #thumbs");
    siteBtn && siteBtn.click();

    assert(hint.textContent === textBefore,  "card hint text unchanged when site photo removed");
    assert(!hint.classList.contains("busy"), "'busy' still absent after site photo removed");
    console.log();
  }

  // ── Scenario 6: aiEnabled=true — hint resets when photo is swapped (no remove) ─
  //
  // extractCard is called by onCardPhotoSet and would immediately overwrite the hint
  // with "Reading the card…".  Stub it out so we can observe the reset state cleanly.
  {
    console.log("Scenario 6: aiEnabled=true — swap card photo resets hint via afterSet callback");
    const { w } = await bootApp({ aiEnabled: true });

    w.__app.aiEnabled = true;
    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);

    // Simulate a completed scan: post-scan text shown, busy absent
    simulateScanSuccess(w);

    const hint = w.document.querySelector(".scanhint");
    assert(hint !== null, ".scanhint element exists");
    assert(hint.textContent !== w.__app.SCAN_HINT, "hint text shows post-scan text before swap");

    // Stub extractCard so it does not overwrite the hint during this test
    const stubScript6 = w.document.createElement("script");
    stubScript6.textContent = "extractCard = function() {};";
    w.document.body.appendChild(stubScript6);

    // Simulate choosing a new file — the real onCardPhotoSet callback
    w.__app.onCardPhotoSet("data:image/jpeg;base64,/9j/newphoto");

    assert(hint.textContent === w.__app.SCAN_HINT, "hint text resets to SCAN_HINT after swap");
    assert(!hint.classList.contains("busy"),        "'busy' class is absent after swap reset");
    console.log();
  }

  // ── Scenario 7: aiEnabled=false — swap resets hint to SCAN_HINT_NO_AI ──────────
  {
    console.log("Scenario 7: aiEnabled=false — swap card photo resets hint to SCAN_HINT_NO_AI");
    const { w } = await bootApp({ aiEnabled: false });

    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);

    // Simulate a failed scan: error text shown, busy absent
    const hint = w.document.querySelector(".scanhint");
    if (hint) { hint.textContent = "Couldn't read the card. Please type the details by hand."; hint.classList.remove("busy"); }

    assert(hint !== null, ".scanhint element exists");
    assert(hint.textContent !== w.__app.SCAN_HINT_NO_AI, "hint shows error text before swap");

    // Stub extractCard so it does not overwrite the hint during this test
    const stubScript7 = w.document.createElement("script");
    stubScript7.textContent = "extractCard = function() {};";
    w.document.body.appendChild(stubScript7);

    // Simulate choosing a new file — real onCardPhotoSet callback
    w.__app.onCardPhotoSet("data:image/jpeg;base64,/9j/newphoto2");

    assert(hint.textContent === w.__app.SCAN_HINT_NO_AI, "hint resets to SCAN_HINT_NO_AI after swap");
    assert(!hint.classList.contains("busy"),              "'busy' class is absent after swap reset");
    console.log();
  }

  // ── Scenario 8: scanning=true — swap must NOT reset the hint ────────────────────
  {
    console.log("Scenario 8: scanning=true — swap must NOT reset the hint while scan in progress");
    const { w } = await bootApp({ aiEnabled: true });

    w.__app.aiEnabled = true;
    w.__app.hasCard = "yes";
    loadFakeCardPhoto(w);
    simulateScanInProgress(w);
    w.__app.scanning = true;

    const hint = w.document.querySelector(".scanhint");
    const textBefore = hint ? hint.textContent : "";

    // Stub extractCard — scanning=true causes onCardPhotoSet to skip both the reset
    // and the extractCard call, but stub anyway for safety
    const stubScript8 = w.document.createElement("script");
    stubScript8.textContent = "extractCard = function() {};";
    w.document.body.appendChild(stubScript8);

    // Simulate swap — afterSet should skip reset because scanning=true
    w.__app.onCardPhotoSet("data:image/jpeg;base64,/9j/newphoto3");

    assert(hint.textContent === textBefore, "hint text unchanged when scanning=true during swap");
    assert(hint.classList.contains("busy"), "'busy' class retained when scanning=true during swap");
    console.log();
  }

  console.log("=== Done ===");
}

runTests().catch((err) => {
  console.error("Unexpected error:", err);
  process.exitCode = 1;
});
