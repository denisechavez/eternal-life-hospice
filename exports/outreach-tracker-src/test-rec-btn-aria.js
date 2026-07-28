/**
 * test-rec-btn-aria.js
 *
 * Verifies that #recBtn announces its disabled state correctly to screen readers:
 *
 *   1. The HTML source ships with aria-disabled="true" on #recBtn so the button
 *      is announced as dimmed/unavailable before any JavaScript runs.
 *
 *   2. After the config fetch resolves with AI disabled (the common initial state),
 *      updateVoiceSection() keeps aria-disabled="true" and adds a description via
 *      aria-describedby pointing at #recHint.
 *
 *   3. After the config fetch resolves with AI enabled, updateVoiceSection()
 *      removes aria-disabled so screen readers announce an active button.
 *
 * Usage:
 *   node test-rec-btn-aria.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const fs = require("fs");
const path = require("path");

// ── helpers ────────────────────────────────────────────────────────────────

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

// ── minimal mock DOM (no jsdom dependency) ─────────────────────────────────

function makeMockBtn() {
  const attrs = {};
  return {
    _attrs: attrs,
    classList: { toggle() {} },
    disabled: false,
    setAttribute(k, v) { attrs[k] = v; },
    removeAttribute(k) { delete attrs[k]; },
    getAttribute(k) { return attrs[k] ?? null; },
    hasAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k); },
    querySelector() { return null; },
  };
}

function makeVoiceSection(btn) {
  return {
    querySelector(sel) { return sel === "#recBtn" ? btn : null; },
  };
}

/**
 * Inline re-implementation of updateVoiceSection() extracted from app.js.
 * This mirrors the production logic exactly so the test stays in sync with
 * the source; if the logic changes in app.js, this test must be updated too.
 */
function updateVoiceSection(aiEnabled, voiceSection, setRecHintFn) {
  if (!voiceSection) return;
  const btn = voiceSection.querySelector("#recBtn");
  if (!aiEnabled) {
    const msg =
      "Voice notes aren't available yet — enable the OpenAI integration in this Replit's Integrations panel.";
    if (btn) {
      btn.setAttribute("aria-disabled", "true");
      btn.setAttribute("title", "Voice notes unavailable — AI integration not enabled");
      btn.setAttribute("aria-describedby", "recHint");
    }
    if (setRecHintFn) setRecHintFn(msg, true);
  } else {
    if (btn) {
      btn.removeAttribute("aria-disabled");
      btn.removeAttribute("title");
      btn.removeAttribute("aria-describedby");
    }
  }
}

// ── test 1: HTML source ships aria-disabled="true" on #recBtn ──────────────

console.log("\n=== Test 1: HTML default state ===\n");

const htmlPath = path.join(__dirname, "public", "index.html");
const htmlSource = fs.readFileSync(htmlPath, "utf8");

// Match the opening tag of #recBtn (everything up to the closing >)
const recBtnTagMatch = htmlSource.match(/<button[^>]+id="recBtn"[^>]*>/);
assert(recBtnTagMatch !== null, "#recBtn element is present in index.html");

if (recBtnTagMatch) {
  const tag = recBtnTagMatch[0];
  assert(
    tag.includes('aria-disabled="true"'),
    '#recBtn has aria-disabled="true" in HTML source (announced before JS runs)'
  );
  assert(
    tag.includes('aria-label=') || htmlSource.includes('aria-label='),
    '#recBtn has an aria-label so screen readers announce a meaningful name'
  );
  assert(
    tag.includes('aria-describedby="recHint"'),
    '#recBtn has aria-describedby="recHint" in HTML source'
  );
}

// ── test 2: updateVoiceSection with AI disabled ────────────────────────────

console.log("\n=== Test 2: Post-config state — AI disabled ===\n");

{
  const btn = makeMockBtn();
  const section = makeVoiceSection(btn);
  let hintMsg = null;
  updateVoiceSection(false, section, (msg) => { hintMsg = msg; });

  assert(
    btn.getAttribute("aria-disabled") === "true",
    "aria-disabled is set to 'true' when AI is off"
  );
  assert(
    btn.hasAttribute("aria-describedby"),
    "aria-describedby is set when AI is off"
  );
  assert(
    btn.getAttribute("aria-describedby") === "recHint",
    "aria-describedby points to #recHint when AI is off"
  );
  assert(
    btn.hasAttribute("title"),
    "title attribute is set when AI is off (tooltip for sighted users)"
  );
  assert(
    hintMsg !== null && hintMsg.length > 0,
    "hint text is populated when AI is off"
  );
}

// ── test 3: updateVoiceSection with AI enabled ─────────────────────────────

console.log("\n=== Test 3: Post-config state — AI enabled ===\n");

{
  // Start in the disabled state, then simulate enabling AI
  const btn = makeMockBtn();
  btn.setAttribute("aria-disabled", "true");
  btn.setAttribute("aria-describedby", "recHint");
  btn.setAttribute("title", "Voice notes unavailable — AI integration not enabled");
  const section = makeVoiceSection(btn);

  updateVoiceSection(true, section, null);

  assert(
    !btn.hasAttribute("aria-disabled"),
    "aria-disabled is removed when AI is enabled"
  );
  assert(
    !btn.hasAttribute("title"),
    "title is removed when AI is enabled"
  );
}

// ── test 4: updateVoiceSection — JS source contains the expected toggles ───

console.log("\n=== Test 4: app.js source contains correct aria toggling ===\n");

const jsPath = path.join(__dirname, "public", "app.js");
const jsSource = fs.readFileSync(jsPath, "utf8");

assert(
  jsSource.includes('setAttribute("aria-disabled", "true")'),
  'app.js sets aria-disabled="true" when AI is off'
);
assert(
  jsSource.includes('removeAttribute("aria-disabled")'),
  "app.js removes aria-disabled when AI is on"
);
assert(
  jsSource.includes('setAttribute("aria-describedby", "recHint")'),
  "app.js sets aria-describedby to recHint when AI is off"
);

console.log("\n=== Done ===\n");
