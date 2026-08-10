/**
 * Tests for chat.js — API-key expiry paths (401 / 403).
 *
 * Verifies that when Anthropic or OpenAI returns 401/403:
 *   1. The expected operator console.error message is emitted.
 *   2. The error propagates so the handler returns the graceful 502 fallback.
 *
 * Run with:  node website/elh-preview/netlify/functions/chat.test.js
 */

"use strict";

const assert = require("assert");

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Build a minimal Netlify function event that passes guard-rails. */
function makeEvent(overrides) {
  return Object.assign(
    {
      httpMethod: "POST",
      body: JSON.stringify({ messages: [{ role: "user", content: "What is hospice care?" }] }),
      queryStringParameters: {}
    },
    overrides
  );
}

/** Stub console.error and collect messages; restore automatically via the returned teardown fn. */
function captureErrors() {
  const captured = [];
  const original = console.error;
  console.error = function (...args) { captured.push(args.join(" ")); };
  return {
    captured,
    restore() { console.error = original; }
  };
}

/**
 * Build a fetch stub that returns the given status for the FIRST call and a
 * valid empty-but-ok response for any subsequent calls (e.g. model-discovery).
 */
function fetchStub(firstStatus, subsequentOk) {
  let callCount = 0;
  return async function fakeFetch(url, opts) {
    callCount++;
    if (callCount === 1) {
      return {
        ok: firstStatus < 400,
        status: firstStatus,
        text: async () => '{"error":"test"}',
        json: async () => ({ error: "test" })
      };
    }
    // Subsequent calls (model-discovery, retry) succeed with an empty list so
    // the function falls through without hanging.
    if (subsequentOk === "models-empty") {
      return {
        ok: true,
        status: 200,
        text: async () => "{}",
        json: async () => ({ data: [] })
      };
    }
    return {
      ok: true,
      status: 200,
      text: async () => "{}",
      json: async () => ({
        content: [{ type: "text", text: "" }],
        stop_reason: "end_turn"
      })
    };
  };
}

/** Isolate env vars for a single test then restore them. */
function withEnv(vars, fn) {
  const saved = {};
  for (const k of Object.keys(vars)) {
    saved[k] = process.env[k];
    if (vars[k] === undefined) {
      delete process.env[k];
    } else {
      process.env[k] = vars[k];
    }
  }
  const restore = () => {
    for (const k of Object.keys(saved)) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  };
  // Run — may return a promise
  let result;
  try {
    result = fn();
  } catch (e) {
    restore();
    throw e;
  }
  if (result && typeof result.then === "function") {
    return result.then(v => { restore(); return v; }, e => { restore(); throw e; });
  }
  restore();
  return result;
}

// ─── Test runner ──────────────────────────────────────────────────────────────

const tests = [];
let passed = 0;
let failed = 0;

function test(name, fn) {
  tests.push({ name, fn });
}

async function runAll() {
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log("  ✓", name);
      passed++;
    } catch (err) {
      console.error("  ✗", name);
      console.error("    ", err.message || err);
      failed++;
    }
  }
  console.log(`\n${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

// ─── Tests: OpenAI 401 ────────────────────────────────────────────────────────

test("callOpenAI — 401 logs the expected operator message", async () => {
  const { captured, restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(401);

  try {
    // Re-require so env changes are picked up cleanly
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-401" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  const matched = captured.some(
    m => m.includes("OPENAI_API_KEY invalid or revoked") && m.includes("401")
  );
  assert.ok(matched, `Expected an operator error log for 401 but got: ${JSON.stringify(captured)}`);
});

test("callOpenAI — 401 causes handler to return 502 with graceful fallback", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(401);
  let response;

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    response = await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-401" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");
  assert.strictEqual(body.reply, "", "Expected reply to be empty string");
});

// ─── Tests: OpenAI 403 ────────────────────────────────────────────────────────

test("callOpenAI — 403 logs the expected operator message", async () => {
  const { captured, restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(403);

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-403" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  const matched = captured.some(
    m => m.includes("OPENAI_API_KEY invalid or revoked") && m.includes("403")
  );
  assert.ok(matched, `Expected an operator error log for 403 but got: ${JSON.stringify(captured)}`);
});

test("callOpenAI — 403 causes handler to return 502 with graceful fallback", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(403);
  let response;

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    response = await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-403" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");
  assert.strictEqual(body.reply, "", "Expected reply to be empty string");
});

// ─── Tests: Anthropic 401 ─────────────────────────────────────────────────────

test("callClaude — 401 logs the expected operator message", async () => {
  const { captured, restore } = captureErrors();
  const originalFetch = global.fetch;
  // Stub: first call = 401, subsequent = empty model list so auto-discovery exits
  global.fetch = fetchStub(401, "models-empty");

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-401", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  const matched = captured.some(
    m => m.includes("ANTHROPIC_API_KEY invalid or revoked") && m.includes("401")
  );
  assert.ok(matched, `Expected an operator error log for 401 but got: ${JSON.stringify(captured)}`);
});

test("callClaude — 401 causes handler to return 502 with graceful fallback", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(401, "models-empty");
  let response;

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-401", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");
  assert.strictEqual(body.reply, "", "Expected reply to be empty string");
});

// ─── Tests: Anthropic 403 ─────────────────────────────────────────────────────

test("callClaude — 403 logs the expected operator message", async () => {
  const { captured, restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(403, "models-empty");

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-403", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  const matched = captured.some(
    m => m.includes("ANTHROPIC_API_KEY invalid or revoked") && m.includes("403")
  );
  assert.ok(matched, `Expected an operator error log for 403 but got: ${JSON.stringify(captured)}`);
});

test("callClaude — 403 causes handler to return 502 with graceful fallback", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = fetchStub(403, "models-empty");
  let response;

  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-403", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");
  assert.strictEqual(body.reply, "", "Expected reply to be empty string");
});

// ─── Both keys expired simultaneously ─────────────────────────────────────────

test("both keys 401 — handler returns 502 with graceful fallback (no crash)", async () => {
  const { captured, restore } = captureErrors();
  const originalFetch = global.fetch;

  // Every call returns 401 (Anthropic primary, Anthropic model-list, OpenAI)
  global.fetch = async () => ({
    ok: false,
    status: 401,
    text: async () => '{"error":"unauthorized"}',
    json: async () => ({ error: "unauthorized" })
  });

  let response;
  try {
    delete require.cache[require.resolve("./chat")];
    const chat = require("./chat");

    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-expired", OPENAI_API_KEY: "sk-expired" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    delete require.cache[require.resolve("./chat")];
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");

  const hasAnthropic = captured.some(m => m.includes("ANTHROPIC_API_KEY invalid or revoked"));
  const hasOpenAI    = captured.some(m => m.includes("OPENAI_API_KEY invalid or revoked"));
  assert.ok(hasAnthropic, `Missing Anthropic error log. Got: ${JSON.stringify(captured)}`);
  assert.ok(hasOpenAI,    `Missing OpenAI error log. Got: ${JSON.stringify(captured)}`);
});

// ─── Run ──────────────────────────────────────────────────────────────────────

console.log("\nchat.js — API key expiry tests\n");
runAll();
