// Real consent UI and persistence, synthetic third-party responses only.
// node --experimental-websocket website/test-cookie-browser.mjs
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

assert.notEqual(process.env.REPLIT_DEPLOYMENT, "1", "Never run browser fixtures in production");
assert.equal(typeof WebSocket, "function", "Node 20 needs --experimental-websocket");
const server = spawn("python3", [new URL("./tracker-browser-fixture.py", import.meta.url).pathname],
  {stdio:["pipe", "pipe", "pipe"]});
let serverLog = "";
server.stderr.on("data", chunk => { serverLog = (serverLog + chunk).slice(-4000); });
const origin = await new Promise((resolve, reject) => {
  const timer = setTimeout(() => { server.kill(); reject(new Error("Fixture startup timed out: " + serverLog)); }, 15000);
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
const tagURL = "https://cdn.dni.nimbata.com/72680137074.min.js";
const sessionURL = "https://dakvo8z10w4va.cloudfront.net/session?fixture=elh-runtime";
function isExpectedEvalError(details) {
  // Chromium may put the message in the RemoteObject description and leave
  // text as "Uncaught", or omit the RemoteObject and include it all in text.
  const description = details.exception?.description || details.text || "";
  return details.url === tagURL &&
    (details.exception?.className === "EvalError" || /^(?:Uncaught )?EvalError:/.test(description)) &&
    description.includes("unsafe-eval");
}
for (const details of [
  {url:tagURL, text:"Uncaught", exception:{className:"EvalError", description:"EvalError: CSP disallows unsafe-eval"}},
  {url:tagURL, text:"Uncaught EvalError: CSP disallows unsafe-eval"}
]) assert.equal(isExpectedEvalError(details), true, "Recognize both Chromium exception formats");
for (const details of [
  {url:"https://example.invalid/tag.js", text:"Uncaught EvalError: CSP disallows unsafe-eval"},
  {url:tagURL, text:"Uncaught", exception:{className:"TypeError", description:"TypeError: unsafe-eval"}},
  {url:tagURL, text:"Uncaught", exception:{className:"EvalError", description:"EvalError: unrelated failure"}}
]) assert.equal(isExpectedEvalError(details), false, "Never hide an unrelated runtime exception");
// Deliberately fails between download and session initialization without eval.
const syntheticTag = `
  window.__nimbataDownloaded = true;
  const rule = new Function("return 'synthetic-attribution-rule'");
  window.__nimbataRule = rule();
  fetch(${JSON.stringify(sessionURL)})
    .then(r => { if (!r.ok) throw new Error("Synthetic session rejected"); return r.json(); })
    .then(r => { window.__nimbataSession = r.session; });
`;
const profile = await mkdtemp(join(tmpdir(), "elh-cookie-test-"));
const browser = spawn(process.env.CHROMIUM_BIN || "chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
  "--no-first-run", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"
], {stdio: ["ignore", "ignore", "pipe"]});
let log = "";
const sockets = [];
browser.stderr.on("data", chunk => { log = (log + chunk).slice(-4000); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const errors = [], expectedEvalErrors = [];
let negativeControl = false;
try {
  let port;
  for (let i = 0; i < 600; i++) {
    if (browser.exitCode !== null) throw new Error("Chromium exited: " + log);
    try { port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]); break; }
    catch { await sleep(50); }
  }
  assert.ok(port, log);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  async function connectTarget(target) {
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    sockets.push(ws);
    let id = 0, navigations = 0;
    const pending = new Map(), external = [], sessions = [], tags = [], policies = [];
    await new Promise(resolve => ws.addEventListener("open", resolve, {once: true}));
    const call = (method, params = {}) => new Promise((resolve, reject) => {
      const key = ++id;
      const timer = setTimeout(() => {
        pending.delete(key); reject(new Error("Browser command timed out: " + method));
      }, 10000);
      pending.set(key, [resolve, reject, timer]); ws.send(JSON.stringify({id:key, method, params}));
    });
    ws.addEventListener("message", event => {
      const m = JSON.parse(event.data);
      if (pending.has(m.id)) {
        const [resolve, reject, timer] = pending.get(m.id); pending.delete(m.id); clearTimeout(timer);
        m.error ? reject(m.error) : resolve(m.result);
      }
      if (m.method === "Fetch.requestPaused") {
        const {url, method} = m.params.request;
        const local = new URL(url).origin === origin;
        if (!local) external.push(url);
        const allowedLocal = local && method === "GET" &&
          ["/", "/no-eval", "/analytics.js", "/favicon.ico"].includes(new URL(url).pathname);
        let stub = "", type = "text/javascript";
        if (url === tagURL) { tags.push(url); stub = syntheticTag; }
        else if (url === sessionURL && method === "GET") {
          sessions.push(url); stub = '{"session":"synthetic-session-ok"}'; type = "application/json";
        } else if (url.includes("tracker.metricool.com")) stub = "window.beTracker={t:function(){}};";
        // All external resources are synthetic; no intercepted request ever goes
        // to a provider. Local API/mutation requests are denied too.
        (allowedLocal ? call("Fetch.continueRequest", {requestId:m.params.requestId}) :
          local ? call("Fetch.failRequest", {requestId:m.params.requestId, errorReason:"BlockedByClient"}) :
          call("Fetch.fulfillRequest", {requestId:m.params.requestId, responseCode:200,
            responseHeaders:[{name:"Content-Type", value:type},
              {name:"Access-Control-Allow-Origin", value:origin}],
            body:Buffer.from(stub).toString("base64")})).catch(e => errors.push(e));
        if (local && !allowedLocal) errors.push({unexpectedLocalRequest: url, method});
      }
      if (m.method === "Page.frameNavigated" && !m.params.frame.parentId) navigations++;
      if (m.method === "Network.responseReceived" && m.params.type === "Document") {
        const headers = m.params.response.headers;
        policies.push(Object.entries(headers).find(([key]) => key.toLowerCase() === "content-security-policy")?.[1]);
      }
      if (m.method === "Runtime.exceptionThrown") {
        const details = m.params.exceptionDetails;
        if (negativeControl && isExpectedEvalError(details)) expectedEvalErrors.push(details);
        else errors.push(details);
      }
    });
    const evaluate = async expression => {
      const r = await call("Runtime.evaluate", {expression, returnByValue:true});
      assert.ok(!r.exceptionDetails, JSON.stringify(r.exceptionDetails)); return r.result.value;
    };
    const until = async expression => {
      for (let i = 0; i < 150; i++) { if (await evaluate(expression)) return; await sleep(40); }
      throw new Error("Timed out: " + expression);
    };
    await call("Page.enable"); await call("Runtime.enable"); await call("Network.enable");
    await call("Network.setBypassServiceWorker", {bypass:true});
    await call("Page.addScriptToEvaluateOnNewDocument", {source:`
      window.__policyViolations = [];
      document.addEventListener('securitypolicyviolation', e => {
        window.__policyViolations.push({directive:e.effectiveDirective, blocked:e.blockedURI});
      });
    `});
    await call("Fetch.enable", {patterns:[{urlPattern:"*"}]});
    return {call, evaluate, until, external, sessions, tags, policies,
      navigationCount: () => navigations};
  }
  const primary = await connectTarget(tabs.find(tab => tab.type === "page"));
  const {call, evaluate, until, external, sessions, tags, policies} = primary;
  const noTracker = () => {
    assert.deepEqual(tags, [], "Nimbata must not download without optional consent");
    assert.deepEqual(sessions, [], "No session before optional consent");
    assert.deepEqual(external.filter(url => url !== "https://cdn.userway.org/widget.js"), [],
      "Only the essential accessibility widget may load without optional consent");
  };
  const sessionCount = async count => {
    await until("window.__nimbataSession==='synthetic-session-ok'");
    assert.equal(await evaluate("window.__nimbataDownloaded"), true);
    assert.equal(await evaluate("window.__nimbataRule"), "synthetic-attribution-rule");
    // Let the fulfilled request and any duplicate script callbacks drain.
    await sleep(150);
    assert.deepEqual(sessions, Array(count).fill(sessionURL), "Exactly one expected session per accepted document");
    assert.deepEqual(tags, Array(count).fill(tagURL), "Exactly one Nimbata tag per accepted document");
    assert.equal(external.some(url => /whatconverts|ksrndkehqnwntyxlhgto/i.test(url)), false);
    assert.deepEqual(external.filter(url => /cloudfront\.net/.test(url)), sessions, "No other session endpoint or method");
    assert.deepEqual(external.filter(url => /nimbata\.com/.test(url)), tags, "No unexpected Nimbata requests");
    assert.deepEqual(await evaluate("window.__policyViolations"), []);
  };
  for (const width of [1280, 390, 320]) {
    const seed = await call("Page.addScriptToEvaluateOnNewDocument", {
      source:"localStorage.removeItem('elh_cc');"
    });
    external.length = tags.length = sessions.length = 0;
    await call("Emulation.setDeviceMetricsOverride", {width,height:720,deviceScaleFactor:1,mobile:width<500});
    await call("Page.navigate", {url:origin});
    await until("!!document.getElementById('elh-cc')");
    await until("document.readyState==='complete'");
    await call("Page.removeScriptToEvaluateOnNewDocument", {identifier:seed.identifier});
    assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"), true);
    assert.equal(await evaluate("document.querySelectorAll('h1').length"), 1);
    noTracker();
    assert.ok(policies.at(-1)?.includes("'unsafe-eval'"), "Actual document response must permit the approved generated rules");
    await evaluate("document.getElementById('elh-cc-mgbtn').click()");
    assert.equal(await evaluate("document.getElementById('elh-tog-all').checked"), false);
    assert.equal(await evaluate("document.activeElement.id"), "elh-tog-all");
    await evaluate("document.getElementById('elh-tog-all').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
    assert.equal(await evaluate("document.activeElement.id"), "elh-cc-mgbtn");
    await evaluate("document.getElementById('elh-cc-decl').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential");
    await call("Page.reload"); await until("document.readyState==='complete' && !!window.elhCookieSettings");
    assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
    noTracker();
    await evaluate("document.getElementById('footer').focus();document.getElementById('footer').click()");
    assert.equal(await evaluate("document.getElementById('elh-cc-preferences').hidden"), false);
    await evaluate("document.getElementById('elh-tog-all').checked=true;document.getElementById('elh-cc-save').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "all");
    assert.equal(await evaluate("document.activeElement.id"), "footer");
    await until("window.__elhAnalyticsBooted===true");
    await sessionCount(1);
    await evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
    await sessionCount(1); // Repeated acceptance must not boot another session.
    assert.equal(await evaluate("Array.from(dataLayer).filter(a=>a[0]==='config'&&a[1]==='AW-18384023405').length"), 1);
    await call("Page.reload"); await until("document.readyState==='complete' && !!window.elhCookieSettings");
    assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
    await sessionCount(2);
    await evaluate("elhCookieSettings()");
    assert.equal(await evaluate("document.getElementById('elh-tog-all').checked"), true);
    await evaluate("document.getElementById('elh-tog-all').checked=false;document.getElementById('elh-cc-save').click()");
    await until("document.readyState==='complete' && localStorage.getItem('elh_cc')==='essential' && !window.__elhAnalyticsBooted && !document.getElementById('elh-cc')");
    assert.deepEqual(tags, [tagURL, tagURL], "Revocation must not load another tracker");
    assert.deepEqual(sessions, [sessionURL, sessionURL], "Revocation must not open another session");
    assert.equal(await evaluate("window.__nimbataDownloaded"), undefined, "Revoked document has no Nimbata runtime");
    external.length = tags.length = sessions.length = 0;
    await evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "all");
    await sessionCount(1);
    assert.equal(external.some(url => /whatconverts|ksrndkehqnwntyxlhgto/i.test(url)), false);
    console.log(`PASS ${width}px: consent, persistence, revocation and synthetic Nimbata runtime/session under actual CSP`);
  }
   // Separate CDP targets: globals, runtimes and request accounting are isolated,
   // while the default browser context shares localStorage like ordinary tabs.
   const secondTarget = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`,
     {method:"PUT"})).json();
   const second = await connectTarget(secondTarget);
   await second.call("Page.navigate", {url:origin});
   await second.until("window.__nimbataSession==='synthetic-session-ok'");
   await until("window.__nimbataSession==='synthetic-session-ok'");
   assert.equal(await second.evaluate("document.readyState"), "complete");
   await Promise.all([primary, second].map(tab => tab.until(
     "!!document.querySelector('script[src=\"https://cdn.userway.org/widget.js\"]')")));
   const bootedCounts = [primary, second].map(tab => ({
     navigations:tab.navigationCount(), tags:tab.tags.length, sessions:tab.sessions.length,
     accessibility:tab.external.filter(url => url === "https://cdn.userway.org/widget.js").length
   }));
   // Reject from one tab; both already-running documents must be replaced once.
   await evaluate("elhCookieSettings();document.getElementById('elh-cc-decl').click()");
   for (const [i, tab] of [primary, second].entries()) {
     await tab.until("document.readyState==='complete' && !!window.elhCookieSettings && !window.__elhAnalyticsBooted && localStorage.getItem('elh_cc')==='essential'");
     await tab.until("!!document.querySelector('script[src=\"https://cdn.userway.org/widget.js\"]')");
     await sleep(250);
     assert.equal(tab.navigationCount(), bootedCounts[i].navigations + 1, "Exactly one reload per running tab");
     assert.equal(tab.tags.length, bootedCounts[i].tags, "No tracker download during cross-tab withdrawal");
     assert.equal(tab.sessions.length, bootedCounts[i].sessions, "No session during cross-tab withdrawal");
     assert.equal(tab.external.filter(url => url === "https://cdn.userway.org/widget.js").length,
       bootedCounts[i].accessibility + 1, "Essential accessibility loads in the replacement document");
     assert.equal(await tab.evaluate("window.__nimbataDownloaded"), undefined);
     assert.equal(await tab.evaluate("!!document.getElementById('elh-cc')"), false);
   }
   const essentialCounts = [primary, second].map(tab => ({
     navigations:tab.navigationCount(), external:tab.external.length
   }));
   await second.evaluate("elhCookieSettings()");
   // Repeated values, unrelated keys and sessionStorage must not reload or boot.
   await evaluate(`localStorage.setItem('elh_cc','essential');
     localStorage.setItem('unrelated','all');sessionStorage.setItem('elh_cc','all')`);
   await sleep(200);
   assert.equal(await second.evaluate("document.getElementById('elh-tog-all').checked"), false);
   await evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
   await until("window.__nimbataSession==='synthetic-session-ok'");
   await second.until("!document.getElementById('elh-cc')");
   await sleep(200);
   assert.equal(second.navigationCount(), essentialCounts[1].navigations);
   assert.equal(second.external.length, essentialCounts[1].external, "Remote acceptance must not start optional providers");
   assert.equal(await second.evaluate("window.__elhAnalyticsBooted"), undefined);
   assert.equal(await second.evaluate("elhTrackEvent('phone_click', {page:'/'})"), false);
   // A local acceptance still starts exactly one session in that tab.
   const secondSessions = second.sessions.length;
   await second.evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
   await second.until("window.__nimbataSession==='synthetic-session-ok'");
   assert.equal(second.sessions.length, secondSessions + 1);
   // Deleting consent also withdraws permission. Ignore stale event payloads:
   // clear() reports key=null and the current stored value is authoritative.
   for (const operation of ["localStorage.removeItem('elh_cc')", "localStorage.clear()"]) {
     const counts = [primary, second].map(tab => tab.navigationCount());
     await evaluate(operation);
     // The writing document gets no storage event; the receiving tab must stop.
     await second.until("document.readyState==='complete' && !!document.getElementById('elh-cc') && !window.__elhAnalyticsBooted");
     await sleep(200);
     assert.equal(second.navigationCount(), counts[1] + 1, "Removed consent reloads a running receiving tab once");
     assert.equal(primary.navigationCount(), counts[0], "Storage events do not fire in the writer");
     await second.until("!!document.querySelector('script[src=\"https://cdn.userway.org/widget.js\"]')");
     const inactiveCount = second.navigationCount();
     await evaluate("localStorage.setItem('elh_cc','essential')");
     await second.until("!document.getElementById('elh-cc')");
     assert.equal(second.navigationCount(), inactiveCount, "Inactive tab does not reload on withdrawal");
     await second.evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
     await second.until("window.__nimbataSession==='synthetic-session-ok'");
   }
   // Hold an initially consented document's scheduled load callback, then revoke
   // and re-accept elsewhere before it can run. No delayed accidental boot.
   const delayed = await second.call("Page.addScriptToEvaluateOnNewDocument", {source:`
     const listen = window.addEventListener;
     window.addEventListener = function(type, callback, options) {
       if (type === 'load' && callback.name === 'bootAnalytics') {
         window.__releaseAnalyticsLoad = callback;
       } else { return listen.call(this, type, callback, options); }
     };
   `});
   await second.call("Page.reload");
   await second.until("document.readyState==='complete' && !!window.__releaseAnalyticsLoad");
   await second.call("Page.removeScriptToEvaluateOnNewDocument", {identifier:delayed.identifier});
   const delayedNavigations = second.navigationCount(), delayedTags = second.tags.length;
   await evaluate("localStorage.setItem('elh_cc','essential')");
   await second.until("localStorage.getItem('elh_cc')==='essential'");
   // A storage-event barrier ensures the withdrawal was delivered before grant.
   await second.evaluate(`window.__storageSeen=false;
     window.addEventListener('storage',()=>window.__storageSeen=true,{once:true})`);
   await evaluate("localStorage.setItem('barrier','ready')");
   await second.until("window.__storageSeen");
   await evaluate("localStorage.setItem('elh_cc','all')");
   await second.until("localStorage.getItem('elh_cc')==='all'");
   await sleep(150);
   await second.evaluate("window.__releaseAnalyticsLoad()");
   await sleep(150);
   assert.equal(second.tags.length, delayedTags, "A pending load cannot boot after remote withdrawal and re-acceptance");
   assert.equal(second.navigationCount(), delayedNavigations, "Unbooted tab does not reload");
   assert.equal(await second.evaluate("window.__elhAnalyticsBooted"), undefined);
   // Stale payloads and another storage area cannot revoke the actual all choice.
   const stableNavigation = primary.navigationCount();
   await evaluate(`window.dispatchEvent(new StorageEvent('storage',
     {key:'elh_cc',newValue:'essential',storageArea:localStorage}));
     window.dispatchEvent(new StorageEvent('storage',
     {key:'elh_cc',newValue:'essential',storageArea:sessionStorage}));`);
   await sleep(150);
   assert.equal(primary.navigationCount(), stableNavigation, "Ignore stale payload and sessionStorage");
   await call("Target.closeTarget", {targetId:secondTarget.id});
   console.log("PASS shared-storage targets: cross-tab withdrawal, one reload, no remote boot, removal/clear and essential accessibility");
   negativeControl = true;
  external.length = tags.length = sessions.length = 0;
  const seed = await call("Page.addScriptToEvaluateOnNewDocument", {source:"localStorage.removeItem('elh_cc');"});
  await call("Page.navigate", {url:origin + "/no-eval"});
  await until("document.readyState==='complete' && !!document.getElementById('elh-cc')");
  await call("Page.removeScriptToEvaluateOnNewDocument", {identifier:seed.identifier});
  noTracker();
  assert.equal(policies.at(-1), policies[0].replace(" 'unsafe-eval'", ""), "Negative control changes only eval permission");
  await evaluate("document.getElementById('elh-cc-okbtn').click()");
  await until("window.__nimbataDownloaded===true && window.__policyViolations.some(v=>v.blocked==='eval' && v.directive==='script-src')");
  await sleep(150);
  assert.deepEqual(tags, [tagURL], "Negative-control tag must download successfully");
  assert.equal(await evaluate("window.__nimbataRule"), undefined);
  assert.equal(await evaluate("window.__nimbataSession"), undefined);
  assert.deepEqual(sessions, [], "Without eval the downloaded tag cannot initialize a session");
  assert.equal(expectedEvalErrors.length, 1, "Exactly the expected generated-rule EvalError");
  assert.equal(external.some(url => /whatconverts|ksrndkehqnwntyxlhgto/i.test(url)), false);
  console.log("PASS negative control: downloaded Nimbata tag blocked at generated rule, before session initialization");
  assert.deepEqual(errors, []);
  console.log("SENTINEL: test-cookie-browser.mjs OK");
} finally {
   sockets.forEach(socket => socket.close()); browser.kill("SIGTERM");
  if (browser.exitCode === null) await new Promise(resolve => browser.once("exit", resolve));
  server.stdin.end();
  if (server.exitCode === null) await new Promise(resolve => server.once("exit", resolve));
  await rm(profile, {recursive:true,force:true,maxRetries:5,retryDelay:150});
}
