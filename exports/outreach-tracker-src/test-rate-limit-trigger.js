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
function rateLimit({ max, windowMs, message, buckets = rlBuckets }) {
  return (req, res, next) => {
    const now = Date.now();
    const key = `${req.path}:${req.ip}`;
    let rec = buckets.get(key);
    if (!rec || now - rec.first > windowMs) {
      rec = { count: 0, first: now };
      buckets.set(key, rec);
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

/* ---------- DB-error (fail-closed) test ------------------------------------
 * Verifies that the real dbTriggerRateLimit middleware (from
 * db-trigger-rate-limit.js) blocks the request with 503 when the injected
 * query function throws — exercising the actual catch block, not a mirror.
 * --------------------------------------------------------------------------- */
const {
  makeTriggerRateLimit,
  TRIGGER_RL_DB_ERROR_MESSAGE: DB_ERROR_MESSAGE,
} = require("./db-trigger-rate-limit");

async function runDbErrorTest() {
  console.log("\n=== DB-error fail-closed test (real middleware) ===\n");

  /* Inject a query stub that always throws — simulates an unreachable DB */
  const throwingQuery = async () => {
    throw new Error("simulated DB error — trigger_rate_limit unreachable");
  };

  /* Use the real factory from db-trigger-rate-limit.js */
  const realMiddleware = makeTriggerRateLimit(throwingQuery);

  const app = express();
  app.use(express.json());
  app.post(
    "/api/backup/trigger",
    realMiddleware,
    (_req, res) => res.json({ ok: true, note: "stub — should never reach here" })
  );

  const srv = http.createServer(app);
  await new Promise((resolve) => srv.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${srv.address().port}`;

  try {
    /* Every request must be blocked — the "DB" always throws */
    for (let i = 1; i <= 2; i++) {
      const r = await post(base, "/api/backup/trigger");
      assert(
        r.status === 503,
        `DB-error request ${i}: real middleware blocks with 503 (got ${r.status})`
      );
      assert(
        r.data && r.data.error === DB_ERROR_MESSAGE,
        `DB-error request ${i}: error body is "${DB_ERROR_MESSAGE}" (got "${
          r.data && r.data.error
        }")`
      );
      /* No Retry-After header on a 503 — this is a transient infra error, not
         a rate-limit window; callers should not treat it as a countdown */
      const retryAfter = r.headers["retry-after"];
      assert(
        retryAfter === undefined,
        `DB-error request ${i}: no Retry-After header on 503 (got "${retryAfter}")`
      );
    }
  } finally {
    srv.close();
  }
}

/* ---------- client-side toast path test for 503 and 429 -------------------
 * Mirrors what triggerBackup()'s catch block does in public/app.js:
 *
 *   catch (err) {
 *     if (err.status === 429) {
 *       toast(err.message || "Please wait before running another backup.", true);
 *     } else {
 *       toast(err.message || "Backup failed.", true);   // ← 503 lands here
 *     }
 *   }
 *
 * We use simulateClientApiError() to build the Error object the same way the
 * real api() helper does, then check the message that toast() would receive.
 * --------------------------------------------------------------------------- */
function runClientSideToastTest() {
  console.log("\n=== client-side toast path test (503 + 429) ===\n");

  /* --- 503: DB unreachable --- */
  const err503 = simulateClientApiError(
    503,
    {},
    { error: DB_ERROR_MESSAGE }
  );

  assert(
    err503.message === DB_ERROR_MESSAGE,
    `503 client error message equals server string ("${err503.message}")`
  );
  assert(
    err503.status === 503,
    `503 client error.status is 503 (got ${err503.status})`
  );
  assert(
    err503.retryAfter === null,
    `503 client error.retryAfter is null — no countdown for a transient infra error (got "${err503.retryAfter}")`
  );

  /* Simulate the triggerBackup catch block for a non-429 error */
  const toastMsg503 = (err503 && err503.message) || "Backup failed.";
  assert(
    toastMsg503 === DB_ERROR_MESSAGE,
    `triggerBackup toast receives the exact server string for 503 ("${toastMsg503}")`
  );

  /* --- 429: rate-limited --- */
  const err429 = simulateClientApiError(
    429,
    { "retry-after": "3540" },
    { error: TRIGGER_MESSAGE }
  );

  assert(
    err429.message === TRIGGER_MESSAGE,
    `429 client error message equals server string ("${err429.message}")`
  );
  assert(
    err429.status === 429,
    `429 client error.status is 429 (got ${err429.status})`
  );
  assert(
    err429.retryAfter === "3540",
    `429 client error.retryAfter is populated (got "${err429.retryAfter}")`
  );

  /* Simulate the triggerBackup catch block for a 429 error */
  const toastMsg429 = (err429 && err429.message) || "Please wait before running another backup.";
  assert(
    toastMsg429 === TRIGGER_MESSAGE,
    `triggerBackup toast receives the exact server string for 429 ("${toastMsg429}")`
  );
}

/* ---------- window-reset test ----------------------------------------------
 * Verifies that the rate-limit window resets after it expires, so a user is
 * not permanently locked out after a single backup attempt.
 *
 * Uses a very short windowMs (200 ms) so the test completes quickly.
 * Steps:
 *   1. Spin up a server with max=1, windowMs=200.
 *   2. Make 1 allowed request (should succeed).
 *   3. Make a 2nd request immediately (should be blocked with 429).
 *   4. Wait 250 ms for the window to expire.
 *   5. Make a 3rd request (should succeed again — the window has reset).
 * --------------------------------------------------------------------------- */
async function runWindowResetTest() {
  console.log("\n=== window-reset test (short windowMs) ===\n");

  const SHORT_WINDOW_MS = 200;
  const SHORT_MESSAGE = "Too many backup requests. Please wait before trying again.";

  /* Use an isolated bucket map so prior test runs don't pollute this window */
  const shortLimiter = rateLimit({
    max: 1,
    windowMs: SHORT_WINDOW_MS,
    message: SHORT_MESSAGE,
    buckets: new Map(),
  });

  const app = express();
  app.use(express.json());
  app.post(
    "/api/backup/trigger",
    shortLimiter,
    (_req, res) => res.json({ ok: true, note: "stub" })
  );

  const srv = http.createServer(app);
  await new Promise((resolve) => srv.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${srv.address().port}`;

  try {
    /* Step 1 — first request must succeed (slot available) */
    const r1 = await post(base, "/api/backup/trigger");
    assert(
      r1.status >= 200 && r1.status < 300,
      `window-reset: first request succeeds (got ${r1.status})`
    );

    /* Step 2 — second request immediately: window still open, slot exhausted → 429 */
    const r2 = await post(base, "/api/backup/trigger");
    assert(
      r2.status === 429,
      `window-reset: second request (within window) is blocked with 429 (got ${r2.status})`
    );
    assert(
      r2.data && r2.data.error === SHORT_MESSAGE,
      `window-reset: second request error body is correct (got "${r2.data && r2.data.error}")`
    );

    /* Step 3 — wait for the window to expire */
    await new Promise((resolve) => setTimeout(resolve, SHORT_WINDOW_MS + 50));

    /* Step 4 — third request: window has reset, slot is available again → 200 */
    const r3 = await post(base, "/api/backup/trigger");
    assert(
      r3.status >= 200 && r3.status < 300,
      `window-reset: third request (after window expiry) succeeds (got ${r3.status})`
    );
    assert(
      r3.data && r3.data.ok === true,
      `window-reset: third request response body indicates success (got ${JSON.stringify(r3.data)})`
    );
  } finally {
    srv.close();
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

  await runWindowResetTest();

  await runDbErrorTest();

  runClientSideToastTest();

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
