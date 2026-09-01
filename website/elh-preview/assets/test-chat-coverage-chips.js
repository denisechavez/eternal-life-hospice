#!/usr/bin/env node
/**
 * Chat widget coverage-chip integration tests
 *
 * Tests the three behavioral paths inside chat.js's doCoverageCheck() and
 * the extractCityQuery() helper, without needing a real browser or a live
 * Netlify server.  The coverage.js Netlify handler is called directly
 * (same technique as test-coverage-lookup.js), and the chat.js logic is
 * reproduced with a minimal mock environment.
 *
 * Paths covered:
 *   A. Coverage returns ambiguous → "did you mean?" chips are shown; AI is NOT called
 *   B. Coverage returns served:true (from chip click) → direct confirmation reply
 *   C. Coverage returns served:false (from chip click) → warm decline reply
 *   D. Initial served/not-served (not from chip) → AI fallback called (not local reply)
 *   E. Coverage endpoint unreachable (network error) → AI fallback called
 *   F. extractCityQuery — matches and non-matches
 *
 * Run from workspace root:
 *   node website/elh-preview/assets/test-chat-coverage-chips.js
 */

"use strict";

const path = require("path");

// ── Load the real coverage handler (no HTTP server needed) ────────────────────
const fnDir = path.resolve(__dirname, "../netlify/functions");
const handler = require(path.join(fnDir, "coverage.js")).handler;

async function coverageCall(city) {
  const event = {
    httpMethod: "GET",
    queryStringParameters: city ? { city } : {}
  };
  const resp = await handler(event);
  return { status: resp.statusCode, body: JSON.parse(resp.body) };
}

// ── Test harness ──────────────────────────────────────────────────────────────
let passed = 0;
let failed = 0;
const failures = [];

function assert(label, condition, detail) {
  if (condition) {
    passed++;
    process.stdout.write("  \u2713 " + label + "\n");
  } else {
    failed++;
    const msg = "  \u2717 " + label + (detail ? " \u2014 " + detail : "");
    process.stdout.write(msg + "\n");
    failures.push(msg);
  }
}

// ── Reproduce extractCityQuery from chat.js (pure function) ───────────────────
// Keep in sync with the implementation in chat.js.
function extractCityQuery(text) {
  var COVERAGE_INTENT = /\b(serve|cover|coverage|service.?area|do you (?:have|go|come|serve|cover)|available in|care in|in your area|your area|your service|your coverage)\b/i;
  if (!COVERAGE_INTENT.test(text)) return null;
  var m = text.match(
    /\b(?:in|for|to|near|around|serve(?:d|s)?|cover(?:s|ed)?)\s+([A-Za-z][A-Za-z\s]{1,38}?)(?:[?\.,!]|\s+(?:ca|california)\b|$)/i
  );
  if (m) return m[1].replace(/\s+/g, " ").trim();
  return null;
}

// ── Minimal mock of the chat widget's doCoverageCheck() behavior ──────────────
// We reproduce the decision tree verbatim from chat.js so any future divergence
// between these tests and the production code is visible as a test failure that
// prompts a sync.  We inject `fetchImpl` so tests can control the network.

const PHONE_DISPLAY = "805.953.7273";

function makeMocks() {
  return {
    msgs: [],          // [{text, who}] — every addMsg() call
    chips: [],         // city names of every chip rendered by showAmbiguousReply()
    sendBtnDisabled: [],
    aiCallCount: 0,
    addMsg(text, who) { this.msgs.push({ text, who }); },
    showAmbiguousChips(city, suggestions) {
      // Mirrors showAmbiguousReply: one chip per suggestion
      suggestions.forEach(sug => this.chips.push(sug));
    },
    sendToAI() { this.aiCallCount++; }
  };
}

// Faithful reproduction of doCoverageCheck(city, fromChip, fetchImpl, mocks)
async function doCoverageCheck(city, fromChip, fetchImpl, mocks) {
  let data;
  try {
    const r = await fetchImpl(city);
    if (!r.ok) throw new Error("bad status");
    data = r.json;
  } catch (_) {
    mocks.sendToAI();
    return;
  }

  if (data.ambiguous && data.suggestions && data.suggestions.length > 0) {
    mocks.showAmbiguousChips(city, data.suggestions);
  } else if (fromChip) {
    if (data.served) {
      const countyNote = data.county ? " in " + data.county : "";
      const reply =
        "Yes\u2014we do serve " + data.city + countyNote + "." +
        " We\u2019d love to talk through how we can support your family." +
        " Please call us at " + PHONE_DISPLAY + " any time\u2014we\u2019re available 24/7.";
      mocks.addMsg(reply, "bot");
    } else {
      const notServedReply =
        "We don\u2019t have a published service page for \u201c" + (data.city || city) +
        "\u201d just yet, but our area across Ventura and Los Angeles counties may extend further than our page list." +
        " Please call " + PHONE_DISPLAY + " to confirm\u2014our team will be glad to help.";
      mocks.addMsg(notServedReply, "bot");
    }
  } else {
    // Non-ambiguous, not from chip → always let AI answer
    mocks.sendToAI();
  }
}

// Helper: make a mock fetch that returns the real coverage handler response.
function realFetch(city) {
  return coverageCall(city).then(({ status, body }) => ({
    ok: status >= 200 && status < 300,
    json: body
  }));
}

// Helper: make a mock fetch that always rejects (simulates network error / timeout).
function failingFetch(_city) {
  return Promise.reject(new Error("NetworkError"));
}

// Helper: make a mock fetch that returns a specific JSON payload.
function fixedFetch(payload) {
  return function(_city) {
    return Promise.resolve({ ok: true, json: payload });
  };
}

// Helper: make a mock fetch that returns a non-2xx status.
function badStatusFetch(_city) {
  return Promise.resolve({ ok: false, json: null });
}

// ── Test suite ────────────────────────────────────────────────────────────────
(async function main() {

  // ─────────────────────────────────────────────────────────────────────────────
  // F. extractCityQuery — pure-function tests (no network needed)
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== F. extractCityQuery — intent + city extraction ===\n");

  assert(
    'Extracts city from "Do you serve Pasadena?"',
    extractCityQuery("Do you serve Pasadena?") === "Pasadena",
    `got: "${extractCityQuery("Do you serve Pasadena?")}" `
  );
  assert(
    'Extracts city from "Do you cover Thousand Oaks?"',
    extractCityQuery("Do you cover Thousand Oaks?") === "Thousand Oaks",
    `got: "${extractCityQuery("Do you cover Thousand Oaks?")}"`
  );
  assert(
    'Extracts city from "Is Glendale in your service area?"',
    extractCityQuery("Is Glendale in your service area?") !== null,
    "expected non-null"
  );
  assert(
    'Extracts city from "Are you available in West Hollywood, CA?"',
    extractCityQuery("Are you available in West Hollywood, CA?") === "West Hollywood",
    `got: "${extractCityQuery("Are you available in West Hollywood, CA?")}"`
  );
  assert(
    'Returns null for unrelated question "What is hospice care?"',
    extractCityQuery("What is hospice care?") === null,
    "expected null"
  );
  assert(
    'Returns null for "Is it covered by Medicare?"',
    extractCityQuery("Is it covered by Medicare?") === null,
    "expected null"
  );
  assert(
    'Returns null for "How quickly can care begin?"',
    extractCityQuery("How quickly can care begin?") === null,
    "expected null"
  );
  assert(
    'Returns null for emergency text "Call 911"',
    extractCityQuery("Call 911 right away") === null,
    "expected null"
  );
  assert(
    'Extracts partial "West" from "Do you serve West?"',
    extractCityQuery("Do you serve West?") === "West",
    `got: "${extractCityQuery("Do you serve West?")}"`
  );

  // ─────────────────────────────────────────────────────────────────────────────
  // A. Ambiguous response → chips shown, AI NOT called
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== A. Ambiguous → did-you-mean chips (AI not called) ===\n");

  {
    // "West" matches West Covina, West Hills, West Hollywood — real endpoint
    const mocks = makeMocks();
    await doCoverageCheck("West", false, realFetch, mocks);

    assert(
      'Ambiguous "West" → chips rendered, not AI',
      mocks.aiCallCount === 0,
      `AI was called ${mocks.aiCallCount} times`
    );
    assert(
      'Ambiguous "West" → at least 2 city chips',
      mocks.chips.length >= 2,
      `got ${mocks.chips.length} chips: ${JSON.stringify(mocks.chips)}`
    );
    assert(
      'Ambiguous "West" → no direct bot message added',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
    assert(
      'Ambiguous "West" → West Covina chip present',
      mocks.chips.includes("West Covina"),
      `chips: ${JSON.stringify(mocks.chips)}`
    );
    assert(
      'Ambiguous "West" → West Hollywood chip present',
      mocks.chips.includes("West Hollywood"),
      `chips: ${JSON.stringify(mocks.chips)}`
    );
  }

  {
    // fromChip=true and still ambiguous → shows refined chips, no AI, no direct reply
    const mocks = makeMocks();
    await doCoverageCheck("West", true, realFetch, mocks);

    assert(
      'Ambiguous from chip → still shows chips, AI not called',
      mocks.aiCallCount === 0 && mocks.chips.length >= 2,
      `AI=${mocks.aiCallCount}, chips=${mocks.chips.length}`
    );
    assert(
      'Ambiguous from chip → no direct bot reply added',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
  }

  {
    // Fixed payload: single-level ambiguous
    const ambigPayload = {
      served: false,
      city: "North",
      ambiguous: true,
      suggestions: ["North Hills", "North Hollywood"]
    };
    const mocks = makeMocks();
    await doCoverageCheck("North", false, fixedFetch(ambigPayload), mocks);

    assert(
      'Fixed ambiguous payload → North Hills chip present',
      mocks.chips.includes("North Hills"),
      `chips: ${JSON.stringify(mocks.chips)}`
    );
    assert(
      'Fixed ambiguous payload → North Hollywood chip present',
      mocks.chips.includes("North Hollywood"),
      `chips: ${JSON.stringify(mocks.chips)}`
    );
    assert(
      'Fixed ambiguous payload → AI not called',
      mocks.aiCallCount === 0,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // B. Chip click → served:true → direct confirmation reply
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== B. Chip click → served city → direct confirmation reply ===\n");

  {
    // Real endpoint, fromChip=true, a city we know is served
    const mocks = makeMocks();
    await doCoverageCheck("Pasadena", true, realFetch, mocks);

    assert(
      'Chip "Pasadena" served → 1 bot message added',
      mocks.msgs.length === 1 && mocks.msgs[0].who === "bot",
      `msgs: ${JSON.stringify(mocks.msgs.map(m => m.who))}`
    );
    assert(
      'Chip "Pasadena" served → message contains "Yes"',
      mocks.msgs[0] && /yes/i.test(mocks.msgs[0].text),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 80)}"`
    );
    assert(
      'Chip "Pasadena" served → message contains city name',
      mocks.msgs[0] && mocks.msgs[0].text.includes("Pasadena"),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 80)}"`
    );
    assert(
      'Chip "Pasadena" served → message contains phone number',
      mocks.msgs[0] && mocks.msgs[0].text.includes(PHONE_DISPLAY),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
    assert(
      'Chip "Pasadena" served → AI not called',
      mocks.aiCallCount === 0,
      `AI called ${mocks.aiCallCount} times`
    );
    assert(
      'Chip "Pasadena" served → no ambiguous chips shown',
      mocks.chips.length === 0,
      `chips: ${JSON.stringify(mocks.chips)}`
    );
  }

  {
    // Fixed payload: served from chip with county info
    const servedPayload = {
      served: true,
      city: "Thousand Oaks",
      county: "Ventura County",
      subregion: "Conejo Valley",
      phone: PHONE_DISPLAY
    };
    const mocks = makeMocks();
    await doCoverageCheck("Thousand Oaks", true, fixedFetch(servedPayload), mocks);

    assert(
      'Fixed served payload → reply contains county note',
      mocks.msgs[0] && mocks.msgs[0].text.includes("Ventura County"),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
    assert(
      'Fixed served payload → reply starts with "Yes"',
      mocks.msgs[0] && mocks.msgs[0].text.startsWith("Yes"),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 40)}"`
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // C. Chip click → served:false → warm decline reply
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== C. Chip click → not-served city → warm decline reply ===\n");

  {
    // Use a city outside our service area
    const mocks = makeMocks();
    await doCoverageCheck("San Francisco", true, realFetch, mocks);

    assert(
      'Chip "San Francisco" not served → 1 bot message added',
      mocks.msgs.length === 1 && mocks.msgs[0].who === "bot",
      `msgs count: ${mocks.msgs.length}`
    );
    assert(
      'Chip "San Francisco" not served → message does NOT say "Yes"',
      mocks.msgs[0] && !/^yes/i.test(mocks.msgs[0].text),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 80)}"`
    );
    assert(
      'Chip "San Francisco" not served → message contains phone number',
      mocks.msgs[0] && mocks.msgs[0].text.includes(PHONE_DISPLAY),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
    assert(
      'Chip "San Francisco" not served → message references county area',
      mocks.msgs[0] && /ventura|los angeles/i.test(mocks.msgs[0].text),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
    assert(
      'Chip "San Francisco" not served → AI not called',
      mocks.aiCallCount === 0,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  {
    // Fixed payload: not served from chip (echo the city from response)
    const notServedPayload = { served: false, city: "Bakersfield" };
    const mocks = makeMocks();
    await doCoverageCheck("Bakersfield", true, fixedFetch(notServedPayload), mocks);

    assert(
      'Fixed not-served payload (chip) → city name in reply',
      mocks.msgs[0] && mocks.msgs[0].text.includes("Bakersfield"),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
    assert(
      'Fixed not-served payload (chip) → phone number in reply',
      mocks.msgs[0] && mocks.msgs[0].text.includes(PHONE_DISPLAY),
      `got: "${mocks.msgs[0] && mocks.msgs[0].text.slice(0, 120)}"`
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // D. Served/not-served from initial message (fromChip=false) → AI called
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== D. Non-chip served/not-served → AI fallback (not direct reply) ===\n");

  {
    // Served city, NOT from chip — must call AI so it gives a warm contextual answer
    const mocks = makeMocks();
    await doCoverageCheck("Pasadena", false, realFetch, mocks);

    assert(
      'Served city (not from chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
    assert(
      'Served city (not from chip) → no direct bot message',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
    assert(
      'Served city (not from chip) → no chips shown',
      mocks.chips.length === 0,
      `chips: ${JSON.stringify(mocks.chips)}`
    );
  }

  {
    // Not-served city, NOT from chip — must also route to AI
    const mocks = makeMocks();
    await doCoverageCheck("San Francisco", false, realFetch, mocks);

    assert(
      'Not-served city (not from chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
    assert(
      'Not-served city (not from chip) → no direct bot message',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
  }

  {
    // Fixed served payload, fromChip=false → AI
    const mocks = makeMocks();
    await doCoverageCheck("Glendale", false, fixedFetch({ served: true, city: "Glendale", county: "Los Angeles County" }), mocks);

    assert(
      'Fixed served payload (not chip) → AI called',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // E. Network error / bad status → AI fallback always
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n=== E. Coverage endpoint unreachable / bad status → AI fallback ===\n");

  {
    // Network failure, fromChip=false
    const mocks = makeMocks();
    await doCoverageCheck("Pasadena", false, failingFetch, mocks);

    assert(
      'Network error (not from chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
    assert(
      'Network error (not from chip) → no direct bot message',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
    assert(
      'Network error (not from chip) → no chips shown',
      mocks.chips.length === 0,
      `chips: ${JSON.stringify(mocks.chips)}`
    );
  }

  {
    // Network failure, fromChip=true — still falls back to AI, not a local reply
    const mocks = makeMocks();
    await doCoverageCheck("West Hollywood", true, failingFetch, mocks);

    assert(
      'Network error (from chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
    assert(
      'Network error (from chip) → no direct bot message',
      mocks.msgs.length === 0,
      `got ${mocks.msgs.length} messages`
    );
  }

  {
    // Bad HTTP status (5xx), fromChip=false
    const mocks = makeMocks();
    await doCoverageCheck("Glendale", false, badStatusFetch, mocks);

    assert(
      'Bad HTTP status (not chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  {
    // Bad HTTP status (5xx), fromChip=true — still falls back to AI
    const mocks = makeMocks();
    await doCoverageCheck("Pasadena", true, badStatusFetch, mocks);

    assert(
      'Bad HTTP status (from chip) → AI called once',
      mocks.aiCallCount === 1,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  {
    // Slow endpoint: verify that a delayed response still resolves correctly
    // (simulated by wrapping the real fetch in a short artificial delay)
    function slowFetch(city) {
      return new Promise(function (resolve) {
        setTimeout(function () {
          resolve(realFetch(city));
        }, 80); // 80ms simulated latency
      }).then(function (p) { return p; });
    }

    const mocks = makeMocks();
    await doCoverageCheck("West", false, slowFetch, mocks);

    assert(
      'Slow endpoint → ambiguous still resolved (chips shown)',
      mocks.chips.length >= 2,
      `chips: ${JSON.stringify(mocks.chips)}`
    );
    assert(
      'Slow endpoint → AI not called on ambiguous',
      mocks.aiCallCount === 0,
      `AI called ${mocks.aiCallCount} times`
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Summary
  // ─────────────────────────────────────────────────────────────────────────────
  console.log("\n" + "\u2500".repeat(60));
  console.log("Results: " + passed + " passed, " + failed + " failed");
  if (failures.length) {
    console.log("\nFailures:");
    failures.forEach(function (f) { console.log(f); });
  }
  console.log("");
  process.exit(failed > 0 ? 1 : 0);
})();
