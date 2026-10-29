// Real served landing pages, production headers, synthetic providers only.
// node --experimental-websocket website/test-landing-consent-browser.mjs
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";

assert.notEqual(process.env.REPLIT_DEPLOYMENT, "1", "Never run fixtures in production");
assert.equal(typeof WebSocket, "function", "Node 20 needs --experimental-websocket");
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const profile = await mkdtemp(join(tmpdir(), "elh-landing-consent-"));
let server, browser, ws, origin, sequence = 0, serverLog = "", browserLog = "";
const pending = new Map(), errors = [], requests = [], documents = [];
const essentialWidget = "https://cdn.userway.org/widget.js";
// Hubs and representative detail pages use distinct public rendering paths.
// Keep this explicit and independent of the fixture's server-side allowlist.
const publicPages = [
  "/", "/refer", "/services", "/services/in-home-hospice-care",
  "/resources", "/resources/when-is-it-time"
];
try {
  server = spawn("python3", [new URL("./landing-consent-fixture.py", import.meta.url).pathname],
    {stdio:["pipe", "pipe", "pipe"]});
  server.stderr.on("data", chunk => { serverLog = (serverLog + chunk).slice(-4000); });
  origin = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Fixture timeout: " + serverLog)), 15000);
    server.once("error", error => { clearTimeout(timer); reject(error); });
    server.once("exit", code => { clearTimeout(timer); reject(new Error(`Fixture exited ${code}: ${serverLog}`)); });
    let output = "";
    server.stdout.on("data", chunk => {
      output += chunk;
      if (!output.includes("\n")) return;
      clearTimeout(timer);
      try { resolve(`http://127.0.0.1:${JSON.parse(output.split("\n")[0]).port}`); }
      catch (error) { reject(error); }
    });
  });
  // Verify the server-side guard independently of browser interception.
  for (const [path, method] of [
    ["/api/form-submit", "POST"], ["/api/chat", "POST"],
    ["/api/form-security", "GET"], ["/", "POST"], ["/api/coverage", "GET"],
    ["/api/newsletter-subscribe", "POST"], ["/api/unlisted", "GET"],
    ["/services/not-allowlisted", "GET"], ["/resources/not-allowlisted", "GET"],
    ["/__service-preview-assets/hero.webp", "GET"]
  ]) {
    assert.equal((await fetch(origin + path, {method})).status, 405, `${method} ${path} denied`);
  }
  for (const path of publicPages) {
    for (const method of ["HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]) {
      assert.equal((await fetch(origin + path, {method})).status, 405, `${method} ${path} denied`);
    }
  }
  browser = spawn(process.env.CHROMIUM_BIN || "chromium", [
    "--headless", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--disable-component-update", "--no-proxy-server",
    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
    "--no-first-run", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"
  ], {stdio:["ignore", "ignore", "pipe"]});
  browser.stderr.on("data", chunk => { browserLog = (browserLog + chunk).slice(-4000); });
  let port;
  for (let i = 0; i < 300; i++) {
    if (browser.exitCode !== null) throw new Error("Chromium exited: " + browserLog);
    try { port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]); break; }
    catch { await sleep(50); }
  }
  assert.ok(port, browserLog);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, {once:true});
    ws.addEventListener("error", reject, {once:true});
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id); reject(new Error("CDP timeout: " + method));
    }, 10000);
    pending.set(id, {resolve, reject, timer});
    ws.send(JSON.stringify({id, method, params}));
  });
  ws.addEventListener("message", event => {
    const m = JSON.parse(event.data), p = pending.get(m.id);
    if (p) {
      clearTimeout(p.timer); pending.delete(m.id);
      m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result);
    }
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails);
    if (m.method === "Network.responseReceived" && m.params.type === "Document")
      documents.push(m.params.response);
    if (m.method !== "Fetch.requestPaused") return;
    const {requestId, request, resourceType} = m.params;
    requests.push({url:request.url, method:request.method, resourceType});
    const url = new URL(request.url), local = url.origin === origin;
    const allowed = local && request.method === "GET" && (
      publicPages.includes(url.pathname) || url.pathname === "/api/google-reviews" ||
      url.pathname.startsWith("/assets/")
    );
    // Every provider response is synthetic, including the sole permitted
    // essential widget. Unknown providers are recorded (and fail the check),
    // never forwarded. All other local APIs and all mutations fail closed.
    const response = allowed ? call("Fetch.continueRequest", {requestId}) :
      local ? call("Fetch.failRequest", {requestId, errorReason:"BlockedByClient"}) :
      call("Fetch.fulfillRequest", {
        requestId, responseCode:200,
        responseHeaders:[{name:"Content-Type", value:resourceType === "Script" ?
          "text/javascript" : "text/plain"}, {name:"Access-Control-Allow-Origin", value:origin}],
        body:Buffer.from(resourceType === "Script" ?
          "window.__syntheticProviderExecutions=(window.__syntheticProviderExecutions||0)+1;" : "").toString("base64")
      });
    response.catch(error => errors.push(String(error)));
    if (local && !allowed && url.pathname !== "/favicon.ico")
      errors.push({unexpectedLocalRequest:request.url, method:request.method});
  });
  const evaluate = async expression => {
    const r = await call("Runtime.evaluate", {expression, returnByValue:true, awaitPromise:true});
    assert.ok(!r.exceptionDetails, JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  const until = async expression => {
    for (let i = 0; i < 200; i++) {
      if (await evaluate(expression)) return;
      await sleep(40);
    }
    throw new Error("Timed out: " + expression);
  };
  await call("Page.enable"); await call("Runtime.enable"); await call("Network.enable");
  await call("Network.setCacheDisabled", {cacheDisabled:true});
  await call("Network.setBypassServiceWorker", {bypass:true});
  await call("Fetch.enable", {patterns:[{urlPattern:"*"}]});
  await call("Page.addScriptToEvaluateOnNewDocument", {source:`
    window.__consentPolicyViolations = [];
    document.addEventListener('securitypolicyviolation', e => {
      window.__consentPolicyViolations.push({directive:e.effectiveDirective, blocked:e.blockedURI});
    });
  `});

  const visit = async path => {
    requests.length = 0;
    const previousDocuments = documents.length;
    await call("Page.navigate", {url:origin + path});
    await until("document.readyState==='complete' && typeof elhCookieSettings==='function'");
    // Exercise lazy/scroll-triggered page-specific tags too, without touching
    // forms, chat, phone links or any actual attribution verification.
    await evaluate("window.scrollTo(0, document.body.scrollHeight)");
    await sleep(1400);
    assert.equal(documents.length, previousDocuments + 1);
    const response = documents.at(-1);
    assert.equal(response.status, 200);
    const headers = Object.fromEntries(Object.entries(response.headers).map(([k,v]) => [k.toLowerCase(),v]));
    const scriptPolicy = headers["content-security-policy"]?.split(";")
      .find(directive => directive.trim().startsWith("script-src ")).split(/\s+/);
    assert.ok(["'self'", "'unsafe-inline'", "'unsafe-eval'"].every(token => scriptPolicy?.includes(token)),
      "Real production CSP must reach each document without test relaxations");
    assert.equal(headers["permissions-policy"], "geolocation=(), microphone=(), camera=()");
    assert.equal(headers["x-content-type-options"], "nosniff");
    assert.match(headers["content-type"], /text\/html/);
    assert.equal(await evaluate("document.querySelectorAll('h1').length"), 1, "Full public page");
    assert.equal(await evaluate("document.querySelectorAll('link[rel=canonical]').length"), 1);
    assert.equal(await evaluate("document.querySelector('link[rel=canonical]').href"),
      "https://eternallifehospice.com" + new URL(path, origin).pathname,
      "Expected public landing page, not a redirect or fallback");
    assert.equal(await evaluate("document.documentElement.outerHTML.includes('/__service-preview-assets/')"),
      false, "Public rendering must not inject workspace preview assets");
    assert.ok(requests.some(r => new URL(r.url).pathname === "/assets/analytics.js"), "Real shared loader served");
  };
  const assertNoTracking = async () => {
    assert.deepEqual(requests.filter(r => new URL(r.url).origin !== origin &&
      r.url !== essentialWidget), [], "No optional third-party request before consent");
    assert.equal(await evaluate(`!!(window.__elhAnalyticsBooted ||
      (window.dataLayer || []).some(x => ['config','event','js'].includes(x[0])) ||
      window.clarity || window.Brevo || window.beTracker || window.__nimbataDownloaded)`),
    false, "No inline tracking initialization before consent");
    assert.deepEqual(await evaluate("window.__consentPolicyViolations"), [], "No hidden CSP-blocked bypass");
    const cookies = await call("Network.getAllCookies");
    assert.deepEqual(cookies.cookies, [], "No tracking cookies on synthetic first/essential-only visit");
    assert.deepEqual(errors, [], "No page/runtime or forbidden API failures");
  };

  for (const width of [1280, 390]) {
    await call("Emulation.setDeviceMetricsOverride", {width,height:800,deviceScaleFactor:1,mobile:width<500});
    for (const [index, path] of publicPages.entries()) {
      await call("Storage.clearDataForOrigin", {origin, storageTypes:"all"});
      await visit(path);
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), null);
      assert.equal(await evaluate("!!document.getElementById('elh-cc')"), true);
      await assertNoTracking();
      await evaluate("document.getElementById('elh-cc-decl').click()");
      await sleep(250);
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential");
      await assertNoTracking();
      await visit(path); // A new document must honor persisted essential-only.
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential");
      assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
      await assertNoTracking();
      await visit(publicPages[(index + 1) % publicPages.length]);
      assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential");
      await assertNoTracking();
      console.log(`PASS ${width}px ${path}: first visit, essential-only reload and cross-page persistence`);
    }
  }
  for (const path of publicPages) {
    for (const consent of [null, "essential"]) {
      for (const probe of ["inline", "tag"]) {
        const seed = await call("Page.addScriptToEvaluateOnNewDocument", {source:consent ?
          "localStorage.setItem('elh_cc','essential')" : "localStorage.removeItem('elh_cc')"});
        try { await visit(`${path}?__consent_probe=${probe}`); }
        finally { await call("Page.removeScriptToEvaluateOnNewDocument", {identifier:seed.identifier}); }
        await assert.rejects(assertNoTracking, probe === "inline" ?
          /No inline tracking initialization/ : /No optional third-party request/,
        `Must detect ${probe} bypass on ${path} with ${consent || "fresh"} consent`);
      }
    }
  }
  assert.deepEqual(errors, []);
  console.log(`PASS negative controls: inline and external-tag bypasses caught on all ${publicPages.length} pages, fresh and essential-only`);
  console.log("SENTINEL: test-landing-consent-browser.mjs OK");
} finally {
  for (const p of pending.values()) { clearTimeout(p.timer); p.reject(new Error("Browser shutting down")); }
  pending.clear();
  ws?.close();
  if (browser && browser.exitCode === null) {
    browser.kill("SIGTERM");
    await new Promise(resolve => browser.once("exit", resolve));
  }
  if (server && server.exitCode === null) {
    server.stdin.end();
    await new Promise(resolve => server.once("exit", resolve));
  }
  await rm(profile, {recursive:true,force:true,maxRetries:5,retryDelay:150});
}
