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
let server, browser, ws, origin, proxyPort, mainSession, sequence = 0, serverLog = "", browserLog = "";
const pending = new Map(), errors = [], requests = [], observed = [], documents = [];
const targets = new Map(), policyViolations = [];
let expectedMutation = false, expectedNewTab = false;
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
      try {
        const fixture = JSON.parse(output.split("\n")[0]);
        proxyPort = fixture.proxyPort;
        resolve(`http://127.0.0.1:${fixture.port}`);
      }
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
  const audit = async () => (await fetch(origin + "/__consent-audit")).json();
  // Exercise the independent proxy without DNS or any outbound connection.
  const proxyControl = await fetch(`http://127.0.0.1:${proxyPort}/deny-control`);
  assert.equal(proxyControl.status, 403);
  assert.ok((await audit()).proxy.some(r => r.url === "/deny-control"));
  const baselineAudit = (await audit()).requests.length;
  browser = spawn(process.env.CHROMIUM_BIN || "chromium", [
    "--headless", "--no-sandbox", "--disable-dev-shm-usage",
    "--disable-background-networking", "--disable-component-update",
    `--proxy-server=http://127.0.0.1:${proxyPort}`,
    `--proxy-bypass-list=<-loopback>;127.0.0.1:${new URL(origin).port}`,
    "--disable-quic",
    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
    "--no-first-run", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "http://consent-transport.invalid/__consent-proxy-control"
  ], {stdio:["ignore", "ignore", "pipe"]});
  browser.stderr.on("data", chunk => { browserLog = (browserLog + chunk).slice(-4000); });
  let port, browserPath;
  for (let i = 0; i < 300; i++) {
    if (browser.exitCode !== null) throw new Error("Chromium exited: " + browserLog);
    try {
      const lines = (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n");
      port = Number(lines[0]); browserPath = lines[1]; break;
    }
    catch { await sleep(50); }
  }
  assert.ok(port, browserLog);
  // Deliberately run this canary BEFORE installing any CDP interception.
  // The browser must use the deny proxy even for a wholly unobserved target.
  let proxyCanary;
  for (let i = 0; i < 200; i++) {
    proxyCanary = (await audit()).proxy.find(r =>
      r.url === "http://consent-transport.invalid/__consent-proxy-control");
    if (proxyCanary) break;
    await sleep(40);
  }
  assert.equal(proxyCanary?.status, 403, "Unintercepted browser transport denied independently");
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const pageId = tabs.find(tab => tab.type === "page").id;
  ws = new WebSocket(`ws://127.0.0.1:${port}${browserPath}`);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, {once:true});
    ws.addEventListener("error", reject, {once:true});
  });
  const call = (method, params = {}, sessionId = mainSession) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id); reject(new Error("CDP timeout: " + method));
    }, 10000);
    pending.set(id, {resolve, reject, timer});
    ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  const attach = async ({sessionId, targetInfo, waitingForDebugger}, parentSessionId) => {
    const target = {type:targetInfo.type, id:targetInfo.targetId, openerId:targetInfo.openerId,
      waitingForDebugger, parentSessionId, ready:false, documents:[]};
    targets.set(sessionId, target);
    if (targetInfo.targetId === pageId) mainSession = sessionId;
    // Pause before a new page/worker/OOPIF can execute. Recursively attach to its
    // descendants; browser-level auto-attach alone does not cover grandchildren.
    await call("Target.setAutoAttach", {autoAttach:true, waitForDebuggerOnStart:true, flatten:true}, sessionId);
    await call("Network.enable", {}, sessionId);
    await call("Network.setCacheDisabled", {cacheDisabled:true}, sessionId);
    await call("Network.setBypassServiceWorker", {bypass:true}, sessionId);
    await call("Runtime.enable", {}, sessionId);
    await call("Log.enable", {}, sessionId);
    if (["worker", "shared_worker", "service_worker"].includes(targetInfo.type)) {
      // Chromium's dedicated-worker target has no Fetch domain. Block its
      // entire network before resuming, while Network still reports attempts.
      await call("Network.setBlockedURLs", {urls:["*"]}, sessionId);
      target.transport = "blocked";
    } else {
      await call("Fetch.enable", {patterns:[{urlPattern:"*"}]}, sessionId);
      target.transport = "synthetic";
    }
    if (["page", "iframe"].includes(targetInfo.type)) {
      await call("Page.enable", {}, sessionId);
      await call("Page.addScriptToEvaluateOnNewDocument", {source:`
        window.__consentHarnessArmed = ${JSON.stringify(sessionId)};
        window.__consentPolicyViolations = [];
        document.addEventListener('securitypolicyviolation', e => {
          window.__consentPolicyViolations.push({directive:e.effectiveDirective, blocked:e.blockedURI});
          console.debug('__consent_csp__' + JSON.stringify({directive:e.effectiveDirective, blocked:e.blockedURI}));
        });
      `}, sessionId);
    }
    target.ready = true;
    await call("Runtime.runIfWaitingForDebugger", {}, sessionId);
  };
  ws.addEventListener("message", event => {
    const m = JSON.parse(event.data), p = pending.get(m.id);
    if (p) {
      clearTimeout(p.timer); pending.delete(m.id);
      m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result);
    }
    if (m.method === "Target.attachedToTarget") {
      attach(m.params, m.sessionId).catch(error => errors.push(String(error)));
      return;
    }
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails);
    if (m.method === "Runtime.consoleAPICalled") {
      for (const arg of m.params.args || []) {
        if (typeof arg.value === "string" && arg.value.startsWith("__consent_csp__"))
          policyViolations.push({sessionId:m.sessionId, ...JSON.parse(arg.value.slice(15))});
      }
    }
    if (m.method === "Log.entryAdded" && m.params.entry.source === "security")
      policyViolations.push({sessionId:m.sessionId, text:m.params.entry.text});
    if (m.method === "Network.requestWillBeSent")
      observed.push({url:m.params.request.url, method:m.params.request.method,
        requestId:m.params.requestId, sessionId:m.sessionId, type:targets.get(m.sessionId)?.type,
        armed:targets.get(m.sessionId)?.ready});
    if (m.method === "Network.loadingFailed") {
      const request = observed.findLast(r => r.requestId === m.params.requestId &&
        r.sessionId === m.sessionId);
      if (request) request.blockedReason = m.params.blockedReason;
    }
    if (m.method === "Network.responseReceived" && m.params.type === "Document" &&
        new URL(m.params.response.url).origin === origin) {
      targets.get(m.sessionId)?.documents.push(m.params.response);
      if (m.sessionId === mainSession) documents.push(m.params.response);
    }
    if (m.method !== "Fetch.requestPaused") return;
    const {requestId, request, resourceType} = m.params;
    const entry = {url:request.url, method:request.method, resourceType,
      sessionId:m.sessionId, type:targets.get(m.sessionId)?.type, action:null, completed:false};
    requests.push(entry);
    const url = new URL(request.url), local = url.origin === origin;
    const allowed = local && (request.method === "GET" && (
      publicPages.includes(url.pathname) || url.pathname === "/api/google-reviews" ||
      url.pathname.startsWith("/assets/")
    ) || (expectedMutation && request.method === "POST" &&
      url.pathname === "/assets/__consent-redirect-mutation"));
    // Every provider response is synthetic, including the sole permitted
    // essential widget. Unknown providers are recorded (and fail the check),
    // never forwarded. All other local APIs and all mutations fail closed.
    entry.action = allowed ? "fixture" : local ? "blocked" : "synthetic";
    const frameProbe = request.url === "https://cdn.userway.org/__consent-frame";
    const body = frameProbe ? `<script>
      fetch('https://www.google-analytics.com/g/collect?probe=frame',
        {method:'POST', mode:'no-cors', body:'synthetic'});
    </script>` : resourceType === "Script" ?
      "globalThis.__syntheticProviderExecutions=(globalThis.__syntheticProviderExecutions||0)+1;" : "";
    const send = (method, params) => call(method, params, m.sessionId);
    const response = allowed ? send("Fetch.continueRequest", {requestId}) :
      local ? send("Fetch.failRequest", {requestId, errorReason:"BlockedByClient"}) :
      send("Fetch.fulfillRequest", {
        requestId, responseCode:200,
        responseHeaders:[{name:"Content-Type", value:frameProbe ? "text/html" :
          resourceType === "Script" ? "text/javascript" : "text/plain"},
          {name:"Access-Control-Allow-Origin", value:"*"}],
        body:Buffer.from(body).toString("base64")
      });
    response.then(() => { entry.completed = true; }).catch(error => errors.push(String(error)));
    const newTabMutation = expectedNewTab && targets.get(m.sessionId)?.openerId === pageId &&
      targets.get(m.sessionId)?.type === "page";
    if (local && !allowed && url.pathname !== "/favicon.ico" &&
        !((expectedMutation || newTabMutation) &&
          url.pathname === "/api/form-submit" && request.method === "POST"))
      errors.push({unexpectedLocalRequest:request.url, method:request.method});
  });
  const evaluate = async (expression, sessionId = mainSession, userGesture = false) => {
    const r = await call("Runtime.evaluate",
      {expression, returnByValue:true, awaitPromise:true, userGesture}, sessionId);
    assert.ok(!r.exceptionDetails, JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  const until = async (expression, sessionId = mainSession) => {
    for (let i = 0; i < 200; i++) {
      if (await evaluate(expression, sessionId)) return;
      await sleep(40);
    }
    throw new Error("Timed out: " + expression);
  };
  await call("Target.setAutoAttach", {autoAttach:true, waitForDebuggerOnStart:true, flatten:true}, null);
  for (let i = 0; i < 200 && !targets.get(mainSession)?.ready; i++) await sleep(40);
  assert.ok(targets.get(mainSession)?.ready, "Main target armed before navigation");

  const visit = async path => {
    requests.length = 0;
    observed.length = 0;
    policyViolations.length = 0;
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
    assert.deepEqual(observed.filter(r => new URL(r.url).origin !== origin &&
      r.url !== essentialWidget), [], "No optional third-party request before consent");
    assert.equal(await evaluate(`!!(window.__elhAnalyticsBooted ||
      (window.dataLayer || []).some(x => ['config','event','js'].includes(x[0])) ||
      window.clarity || window.Brevo || window.beTracker || window.__nimbataDownloaded)`),
    false, "No inline tracking initialization before consent");
    assert.deepEqual(await evaluate("window.__consentPolicyViolations"), [], "No hidden CSP-blocked bypass");
    assert.deepEqual(policyViolations, [], "No CSP-blocked bypass in any target");
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
      for (const probe of ["inline", "tag", "frame", "worker", "new-tab", "beacon", "redirect", "redirect-mutation"]) {
        expectedMutation = probe === "redirect-mutation";
        expectedNewTab = probe === "new-tab";
        const seed = await call("Page.addScriptToEvaluateOnNewDocument", {source:consent ?
          "localStorage.setItem('elh_cc','essential')" : "localStorage.removeItem('elh_cc')"});
        try { await visit(`${path}?__consent_probe=${probe}`); }
        finally { await call("Page.removeScriptToEvaluateOnNewDocument", {identifier:seed.identifier}); }
        let newTabSession;
        if (expectedNewTab) {
          const existing = new Set(targets.keys());
          // A synthetic user gesture opens the fixture tab without weakening
          // popup policy or changing any production page/consent code.
          assert.equal(await evaluate("window.__openConsentProbe()", mainSession, true), true,
            "window.open must create a real new top-level page");
          for (let i = 0; i < 200; i++) {
            newTabSession = [...targets].find(([session, target]) =>
              !existing.has(session) && target.type === "page" && target.openerId === pageId &&
              target.ready)?.[0];
            if (newTabSession) break;
            await sleep(40);
          }
          assert.ok(newTabSession, "Browser-level attachment arms the opened page");
          const target = targets.get(newTabSession);
          assert.equal(target.parentSessionId, undefined, "New page attached at browser level");
          assert.equal(target.waitingForDebugger, true, "New page paused before execution");
          assert.equal(target.transport, "synthetic");
          await until("window.__newTabProbe?.done === true", newTabSession);
          assert.deepEqual(await evaluate("window.__newTabProbe", newTabSession),
            {armed:newTabSession, consent, topLevel:true, done:true},
            "First inline script runs only after the new top-level document is armed");
          assert.equal(await evaluate("window.dataLayer[0][0]", newTabSession), "config",
            "New-tab inline tracking control executed");
          assert.equal(await evaluate("localStorage.getItem('elh_cc')", newTabSession), consent);
          assert.deepEqual(await evaluate("window.__consentPolicyViolations", newTabSession), []);
          assert.equal(target.documents.length, 1, "New tab loaded its real fixture document");
          assert.equal(target.documents[0].url, origin + "/assets/__consent-new-tab.html");
          assert.equal(target.documents[0].status, 200);
          const headers = response => Object.fromEntries(
            Object.entries(response.headers).map(([key, value]) => [key.toLowerCase(), value]));
          for (const name of ["content-security-policy", "permissions-policy", "x-content-type-options"])
            assert.equal(headers(target.documents[0])[name], headers(documents.at(-1))[name],
              `New tab preserves production ${name}`);
          assert.ok(requests.some(r => r.sessionId === newTabSession &&
            r.url === origin + "/api/form-submit" && r.method === "POST" &&
            r.action === "blocked" && r.completed), "New-tab intake attempt blocked before fixture");
        }
        if (probe === "redirect-mutation") {
          assert.ok(requests.some(r => new URL(r.url).pathname === "/api/form-submit" &&
            r.method === "POST" && r.action === "blocked" && r.completed),
          "307 mutation destination blocked before the fixture receives it");
        } else {
          await assert.rejects(assertNoTracking, probe === "inline" ?
            /No inline tracking initialization/ : /No optional third-party request/,
          `Must detect ${probe} bypass on ${path} with ${consent || "fresh"} consent`);
        }
        if (["frame", "worker", "new-tab", "beacon", "redirect"].includes(probe)) {
          const destination = `https://www.google-analytics.com/g/collect?probe=${probe}`;
          const observation = observed.find(r => r.url === destination);
          assert.ok(observation, "Independent network observer reports attempt");
          assert.equal(observation.armed, true, "Target armed before tracking attempt");
          const attempt = requests.find(r => r.url === destination);
          if (probe === "worker") {
            assert.equal(observation.blockedReason, "inspector", "Worker attempt blocked before transport");
            assert.equal(targets.get(observation.sessionId)?.transport, "blocked");
            assert.equal(attempt, undefined, "Worker block needs no synthetic provider response");
          } else {
            assert.ok(attempt, `${probe} tracking attempt must actually reach interception`);
            assert.equal(attempt.action, "synthetic");
            assert.equal(attempt.completed, true, `${probe} synthetic response completed`);
          }
          if (["frame", "worker"].includes(probe)) {
            assert.notEqual(observation.sessionId, mainSession, `${probe} attempt outside main target`);
            assert.equal(observation.type, probe === "frame" ? "iframe" : "worker");
          }
          if (probe === "new-tab") {
            assert.equal(observation.sessionId, newTabSession, "Attempt reported from opened tab");
            assert.notEqual(observation.sessionId, mainSession);
            assert.equal(observation.type, "page");
            assert.equal(attempt.sessionId, newTabSession);
            assert.equal(attempt.method, "POST");
          }
          if (probe === "beacon") assert.equal(attempt.resourceType, "Ping");
        }
        assert.ok(requests.every(r => r.completed), "Every paused request resolved");
        assert.ok(requests.every(r => new URL(r.url).origin === origin ||
          r.action === "synthetic"), "No external request was continued");
        assert.equal(await evaluate("localStorage.getItem('elh_cc')"), consent,
          "Adversarial probe never grants or changes consent");
        assert.deepEqual(policyViolations, [], "Transport probes run under unchanged CSP");
        assert.deepEqual(errors, [], "No concealed runtime/interception failure");
        if (newTabSession) {
          const closed = await call("Target.closeTarget", {targetId:targets.get(newTabSession).id}, null);
          assert.equal(closed.success, true, "Close negative-control tab before the next case");
        }
        expectedMutation = false;
        expectedNewTab = false;
      }
    }
  }
  const finalAudit = await audit();
  const browserAudit = finalAudit.requests.slice(baselineAudit);
  assert.deepEqual(browserAudit.filter(r => r.path.startsWith("/api/") &&
    r.path !== "/api/google-reviews"), [], "No intake/API attempts reach even the deny-only fixture handler");
  assert.deepEqual(browserAudit.filter(r => r.method !== "GET" &&
    !(r.method === "POST" && r.path === "/assets/__consent-redirect-mutation")), [],
  "No non-fixture mutations");
  assert.ok(browserAudit.some(r => r.path === "/assets/__consent-redirect"), "Real fixture 307 exercised");
  assert.ok(browserAudit.some(r => r.path === "/assets/__consent-worker.js"), "Real fixture worker exercised");
  assert.equal(browserAudit.filter(r => r.path === "/assets/__consent-new-tab.html").length,
    publicPages.length * 2, "Real window.open document exercised on every page and consent state");
  // Chromium may speculatively CONNECT for a frame even when its document
  // response is intercepted. Such connections must be denied, never tunneled.
  assert.ok(finalAudit.proxy.every(r => r.status === 403), "Proxy never forwards any request or CONNECT");
  assert.deepEqual(finalAudit.proxy.filter(r => /google-analytics/.test(r.url)), [],
    "Tracking payloads never reach proxy: intercepted synthetically or blocked in worker");
  assert.deepEqual(errors, []);
  console.log(`PASS negative controls: inline, tag, cross-origin frame, worker, new tab, beacon and redirect bypasses caught on all ${publicPages.length} pages, fresh and essential-only`);
  console.log("PASS transport isolation: all-target synthetic responses, deny-only proxy, blocked mutation redirects and unchanged consent/permissions");
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
