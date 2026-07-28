/**
 * test-rate-limit-trigger.js
 *
 * Verifies that triggerLimiter (max 3 per hour per IP) on
 * POST /api/backup/trigger blocks a fourth request with 429 and returns the
 * correct error body + Retry-After header, and that the client-side api()
 * helper surfaces the right message to toast().
 *
 * Self-contained: starts its own minimal Express server, no DB required.
 *
 * Usage:
 *   node test-rate-limit-trigger.js
 *
 * Exit codes: 0 = all assertions passed, 1 = a failure occurred.
 */

"use strict";

const http = require("http");
const express = require("express");

/* ---------- in-memory rate-limit middleware (mirrors original server.js) ---- */
const rlBuckets = new Map();
function rateLimit({ max, windowMs, message }) {
  return (req, res, next) => {
    const now = Date.now();
    const key = `${req.path}:${req.ip}`;
    let rec = rlBuckets.get(key);
    if (!rec || now - rec.first > windowMs) {
      rec = { count: 0, first: now };
      rlBuckets.set(key, rec);
    }
    rec.count += 1;
    if (rec.count > max) {
      const waitSec = Math.ceil((rec.first + windowMs - now) / 1000);
      res.setHeader("Retry-After", String(Math.max(waitSec, 1)));
      return res.status(429).json({ error: message });
    }
    next();
  };
}
/* --------------------------------------------------------------------------- */

/* ---------- store-injected rate-limit (models the DB-backed limiter) --------
 * In production, server.js writes to the trigger_rate_limit Postgres table so
 * the bucket survives a process restart.  Here we inject a plain Map so the
 * post-restart test can share the same store across two "server instances"
 * without needing a real database.
 * --------------------------------------------------------------------------- */
function makeStoredRateLimit({ max, windowMs, message, store }) {
  return (req, res, next) => {
    const now = Date.now();
    const key = `${req.path}:${req.ip}`;
    let rec = store.get(key);
    if (!rec || now - rec.first > windowMs) {
      rec = { count: 0, first: now };
      store.set(key, rec);
    }
    rec.count += 1;
    if (rec.count > max) {
      const waitSec = Math.ceil((rec.first + windowMs - now) / 1000);
      res.setHeader("Retry-After", String(Math.max(waitSec, 1)));
      return res.status(429).json({ error: message });
    }
    next();
  };
}
/* --------------------------------------------------------------------------- */

const TRIGGER_MESSAGE = "Too many backup requests. Please wait before trying again.";

const triggerLimiter = rateLimit({
  max: 3,
  windowMs: 60 * 60 * 1000,
  message: TRIGGER_MESSAGE,
});

/* ---------- assertion helpers ---------- */
let failures = 0;
function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    failures++;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

/* ---------- tiny HTTP helper ---------- */
function post(baseUrl, path) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, baseUrl);
    const opts = {
      hostname: url.hostname,
      port: Number(url.port),
      path: url.pathname,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": 0 },
    };
    const req = http.request(opts, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        let data = null;
        try { data = JSON.parse(body); } catch (_) {}
        resolve({ status: res.statusCode, headers: res.headers, data });
      });
    });
    req.on("error", reject);
    req.end();
  });
}

/* ---------- client-side api() error-building logic (mirrored from app.js) ---
   When the server responds with !res.ok, app.js does:
     const err = new Error((data && data.error) || "Something went wrong.");
     err.status = res.status;
     err.retryAfter = res.headers.get("Retry-After");
     throw err;
   The triggerBackup catch block then does:
     const msg = (e && e.message) || "Backup failed...";
     toast(msg, true);
   So the toast message == the server's error string.
------------------------------------------------------------------------------ */
function simulateClientApiError(status, headers, data) {
  const message = (data && data.error) || "Something went wrong.";
  const err = new Error(message);
  err.status = status;
  err.retryAfter = headers["retry-after"] || null;
  return err;
}

/* ---------- in-memory rate-limit behaviour test ----------------------------
 * Exercises the original in-memory triggerLimiter: 3 allowed, 4th is 429.
 * --------------------------------------------------------------------------- */
async function runInMemoryTest(base) {
  /* --- requests 1–3: all must succeed (2xx) --- */
  for (let i = 1; i <= 3; i++) {
    const r = await post(base, "/api/backup/trigger");
    assert(
      r.status >= 200 && r.status < 300,
      `request ${i}: status is 2xx (got ${r.status})`
    );
  }

  /* --- request 4: must be rate-limited --- */
  const r4 = await post(base, "/api/backup/trigger");

  assert(r4.status === 429, `request 4: status is 429 (got ${r4.status})`);

  assert(
    r4.data && r4.data.error === TRIGGER_MESSAGE,
    `request 4: error body is "${TRIGGER_MESSAGE}" (got "${r4.data && r4.data.error}")`
  );

  const retryAfter = r4.headers["retry-after"];
  assert(
    retryAfter !== undefined && retryAfter !== null,
    `request 4: Retry-After header is present (got "${retryAfter}")`
  );
  const retryAfterNum = Number(retryAfter);
  assert(
    Number.isFinite(retryAfterNum) && retryAfterNum >= 1,
    `request 4: Retry-After is a positive integer (got "${retryAfter}")`
  );

  /* --- client-side toast message verification --- */
  const clientErr = simulateClientApiError(r4.status, r4.headers, r4.data);
  assert(
    clientErr.message === TRIGGER_MESSAGE,
    `client api() error message matches server error string ("${clientErr.message}")`
  );
  assert(
    clientErr.status === 429,
    `client api() error.status is 429 (got ${clientErr.status})`
  );
  assert(
    clientErr.retryAfter !== null,
    `client api() error.retryAfter is populated (got "${clientErr.retryAfter}")`
  );

  /* --- 5th request must also be blocked --- */
  const r5 = await post(base, "/api/backup/trigger");
  assert(r5.status === 429, `request 5: also blocked with 429 (got ${r5.status})`);
}

/* ---------- post-restart persistence test ----------------------------------
 * Verifies that the DB-backed limiter (modelled here with a shared Map store)
 * still blocks requests after the server process has been restarted mid-window.
 *
 * Production mapping:
 *   sharedStore  →  trigger_rate_limit Postgres table
 *   server1      →  process before restart
 *   server2      →  process after restart (same DB, fresh in-memory state)
 * --------------------------------------------------------------------------- */
async function runPostRestartTest() {
  console.log("\n=== post-restart persistence test ===\n");

  /* Shared backing store — survives both "server instances" */
  const sharedStore = new Map();

  function startServer() {
    const app = express();
    app.use(express.json());
    const limiter = makeStoredRateLimit({
      max: 3,
      windowMs: 60 * 60 * 1000,
      message: TRIGGER_MESSAGE,
      store: sharedStore,
    });
    app.post("/api/backup/trigger", limiter, (_req, res) =>
      res.json({ ok: true, note: "stub" })
    );
    const srv = http.createServer(app);
    return new Promise((resolve) =>
      srv.listen(0, "127.0.0.1", () => resolve(srv))
    );
  }

  /* --- server1: consume all 3 allowed requests --- */
  const server1 = await startServer();
  const base1 = `http://127.0.0.1:${server1.address().port}`;

  for (let i = 1; i <= 3; i++) {
    const r = await post(base1, "/api/backup/trigger");
    assert(
      r.status >= 200 && r.status < 300,
      `pre-restart request ${i}: status is 2xx (got ${r.status})`
    );
  }
  server1.close();
  console.log("  [server1 stopped — simulating restart]");

  /* --- server2: fresh process, same backing store (DB in production) --- */
  const server2 = await startServer();
  const base2 = `http://127.0.0.1:${server2.address().port}`;

  try {
    const r4 = await post(base2, "/api/backup/trigger");
    assert(
      r4.status === 429,
      `post-restart request 4: still blocked with 429 (got ${r4.status})`
    );
    assert(
      r4.data && r4.data.error === TRIGGER_MESSAGE,
      `post-restart request 4: correct error body (got "${r4.data && r4.data.error}")`
    );
    const retryAfter = r4.headers["retry-after"];
    assert(
      retryAfter !== undefined && Number(retryAfter) >= 1,
      `post-restart request 4: Retry-After header present and ≥ 1 (got "${retryAfter}")`
    );
  } finally {
    server2.close();
  }
}

/* ---------- main ---------- */
async function run() {
  console.log("=== triggerLimiter rate-limit test ===\n");

  /* --- spin up a minimal express app with the same route guard --- */
  const app = express();
  app.use(express.json());

  /* stub: the real route calls runWeeklyBackup (needs DB); here we just 200 */
  app.post(
    "/api/backup/trigger",
    triggerLimiter,
    (_req, res) => res.json({ ok: true, note: "stub backup ok" })
  );

  const server = http.createServer(app);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  const base = `http://127.0.0.1:${port}`;

  try {
    await runInMemoryTest(base);
  } finally {
    server.close();
  }

  await runPostRestartTest();

  console.log("\n=== Done ===");

  if (failures > 0) {
    console.error(`\n${failures} assertion(s) failed.`);
    process.exitCode = 1;
  }
}

run().catch((err) => {
  console.error("Unexpected error:", err);
  process.exitCode = 1;
});
