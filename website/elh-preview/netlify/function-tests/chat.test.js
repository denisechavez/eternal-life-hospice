/**
 * Tests for chat.js — API-key expiry paths (401 / 403) and model-discovery
 * failure paths (Task 394: no silent hang when discovery also fails).
 *
 * Run with:
 *   node website/elh-preview/netlify/function-tests/chat.test.js
 *
 * Uses only Node built-ins — no extra packages needed.
 * global.fetch is monkey-patched per test; no real network calls are made.
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

/**
 * Build a fetch stub that replays `responses` in order.
 * Each entry:
 *   { throws: "msg" }            — fetch itself throws (network error)
 *   { ok, status, json?, text? } — returns a Response-like object
 */
function makeFetchStub(responses) {
  const queue = responses.slice();
  return async function stubFetch(url) {
    const spec = queue.shift();
    if (!spec) throw new Error("Unexpected extra fetch call to: " + url);
    if (spec.throws !== undefined) throw new Error(spec.throws);
    return {
      ok: spec.ok,
      status: spec.status,
      json: async () => (spec.json !== undefined ? spec.json : {}),
      text: async () => (spec.text !== undefined ? spec.text : "")
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

/**
 * Wrap a promise with a hard timeout so a hanging handler fails promptly
 * rather than waiting for an external CI timeout.
 */
function withTimeout(ms, promise) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Test timed out after " + ms + "ms")), ms)
    )
  ]);
}

/** Load (or reload) the handler from the functions directory. */
function loadHandler() {
  delete require.cache[require.resolve("../functions/chat")];
  return require("../functions/chat");
}

/** Clear the handler from the require cache after a test. */
function unloadHandler() {
  delete require.cache[require.resolve("../functions/chat")];
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
    const chat = loadHandler();
    await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-401" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    response = await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-401" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-403" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    response = await withEnv(
      { ANTHROPIC_API_KEY: undefined, OPENAI_API_KEY: "sk-test-403" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-401", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-401", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-403", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
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
    const chat = loadHandler();
    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-test-403", OPENAI_API_KEY: undefined },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");
  assert.strictEqual(body.reply, "", "Expected reply to be empty string");
});

// ─── Tests: Both keys expired simultaneously ──────────────────────────────────

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
    const chat = loadHandler();
    response = await withEnv(
      { ANTHROPIC_API_KEY: "sk-ant-expired", OPENAI_API_KEY: "sk-expired" },
      () => chat.handler(makeEvent())
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502, "Expected HTTP 502");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "Expected a non-empty fallback message");

  const hasAnthropic = captured.some(m => m.includes("ANTHROPIC_API_KEY invalid or revoked"));
  const hasOpenAI    = captured.some(m => m.includes("OPENAI_API_KEY invalid or revoked"));
  assert.ok(hasAnthropic, `Missing Anthropic error log. Got: ${JSON.stringify(captured)}`);
  assert.ok(hasOpenAI,    `Missing OpenAI error log. Got: ${JSON.stringify(captured)}`);
});

// ─── Tests: Model-discovery failure (Task 394 — no silent hang) ───────────────
//
// These tests verify that when the primary Claude POST returns 404 and the
// subsequent model-list GET also fails (network throw or non-ok), the handler
// completes promptly rather than hanging. Each test is wrapped in withTimeout
// so a future regression fails fast instead of blocking CI indefinitely.

test("Claude 404 + model-discovery network error → 502 (no OpenAI, no hang)", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = makeFetchStub([
    { ok: false, status: 404, text: "model_not_found" },   // Claude POST
    { throws: "fetch failed: network error" }               // model-list GET
  ]);
  let response;

  try {
    const chat = loadHandler();
    response = await withTimeout(
      5000,
      withEnv(
        { ANTHROPIC_API_KEY: "test-key", OPENAI_API_KEY: undefined },
        () => chat.handler(makeEvent())
      )
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502, "should return 502 when both Claude and discovery fail");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0, "should include a fallback message");
  assert.strictEqual(body.reply, "");
});

test("Claude 404 + model-discovery non-ok (503) → 502 (no OpenAI, no hang)", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = makeFetchStub([
    { ok: false, status: 404, text: "model_not_found" },   // Claude POST
    { ok: false, status: 503, text: "service unavailable" } // model-list GET
  ]);
  let response;

  try {
    const chat = loadHandler();
    response = await withTimeout(
      5000,
      withEnv(
        { ANTHROPIC_API_KEY: "test-key", OPENAI_API_KEY: undefined },
        () => chat.handler(makeEvent())
      )
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502, "should return 502 when discovery returns non-ok");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0);
  assert.strictEqual(body.reply, "");
});

test("Claude 404 + model-discovery throws → falls through to OpenAI (no hang)", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = makeFetchStub([
    { ok: false, status: 404, text: "model_not_found" },    // Claude POST
    { throws: "fetch failed: network error" },               // model-list GET
    {                                                        // OpenAI POST — succeeds
      ok: true, status: 200,
      json: { choices: [{ message: { content: "Hospice care focuses on comfort." } }] }
    }
  ]);
  let response;

  try {
    const chat = loadHandler();
    response = await withTimeout(
      5000,
      withEnv(
        { ANTHROPIC_API_KEY: "test-key", OPENAI_API_KEY: "oai-test-key" },
        () => chat.handler(makeEvent())
      )
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 200, "should return 200 when OpenAI succeeds");
  const body = JSON.parse(response.body);
  assert.ok(body.reply && body.reply.length > 0, "should have a non-empty reply from OpenAI");
  assert.strictEqual(body.configured, true);
});

test("Claude 404 + discovery throws + OpenAI throws → 502 (no hang)", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = makeFetchStub([
    { ok: false, status: 404, text: "model_not_found" }, // Claude POST
    { throws: "network error" },                          // model-list GET
    { throws: "openai network error" }                    // OpenAI POST
  ]);
  let response;

  try {
    const chat = loadHandler();
    response = await withTimeout(
      5000,
      withEnv(
        { ANTHROPIC_API_KEY: "test-key", OPENAI_API_KEY: "oai-test-key" },
        () => chat.handler(makeEvent())
      )
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502, "should return 502 when all providers fail");
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0);
});

test("Claude 404 + discovery returns empty model list → 502 (no OpenAI, no hang)", async () => {
  const { restore } = captureErrors();
  const originalFetch = global.fetch;
  global.fetch = makeFetchStub([
    { ok: false, status: 404, text: "model_not_found" }, // Claude POST
    { ok: true, status: 200, json: { data: [] } }         // model-list GET — empty
  ]);
  let response;

  try {
    const chat = loadHandler();
    response = await withTimeout(
      5000,
      withEnv(
        { ANTHROPIC_API_KEY: "test-key", OPENAI_API_KEY: undefined },
        () => chat.handler(makeEvent())
      )
    );
  } finally {
    restore();
    global.fetch = originalFetch;
    unloadHandler();
  }

  assert.strictEqual(response.statusCode, 502);
  const body = JSON.parse(response.body);
  assert.ok(body.fallback && body.fallback.length > 0);
});

// ─── Run ──────────────────────────────────────────────────────────────────────

console.log("\nchat.js — API key expiry + model-discovery failure tests\n");
runAll();
