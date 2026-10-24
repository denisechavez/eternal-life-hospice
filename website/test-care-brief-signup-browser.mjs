// Read-only preview checks: no submissions, approvals or third-party requests.
// Run: node --experimental-websocket website/test-care-brief-signup-browser.mjs
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";

assert.ok(process.env.REPLIT_DEV_DOMAIN, "REPLIT_DEV_DOMAIN is required");
const origin = "https://" + process.env.REPLIT_DEV_DOMAIN;
const profile = await mkdtemp(join(tmpdir(), "elh-signup-browser-"));
const browser = spawn("chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage",
  "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
], {stdio: ["ignore", "ignore", "pipe"]});
let diagnostics = "";
browser.stderr.on("data", chunk => { diagnostics = (diagnostics + chunk).slice(-12000); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
try {
  let port;
  for (let i = 0; i < 300; i++) {
    assert.equal(browser.exitCode, null, diagnostics);
    try {
      port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]);
      if (port) break;
    } catch { /* Wait for Chromium's endpoint. */ }
    await sleep(100);
  }
  assert.ok(port, "Browser did not start: " + diagnostics);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  let id = 0;
  const pending = new Map();
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => {
      pending.delete(requestId);
      reject(new Error("Browser command timed out: " + method));
    }, 20000);
    pending.set(requestId, {resolve, reject, timer});
    socket.send(JSON.stringify({id: requestId, method, params}));
  });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.method === "Fetch.requestPaused") {
      const {request, requestId} = message.params;
      const allowed = request.url.startsWith(origin + "/") && request.method === "GET";
      void call(allowed ? "Fetch.continueRequest" : "Fetch.failRequest",
        allowed ? {requestId} : {requestId, errorReason: "BlockedByClient"})
        .catch(error => console.error(error.message));
    }
    const waiter = pending.get(message.id);
    if (waiter) {
      clearTimeout(waiter.timer);
      pending.delete(message.id);
      message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result);
    }
  });
  const evaluate = async expression => {
    const result = await call("Runtime.evaluate", {expression, awaitPromise: true, returnByValue: true});
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async (expression, label) => {
    for (let i = 0; i < 150; i++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await sleep(100);
    }
    throw new Error("Timed out: " + label + " " + JSON.stringify(await evaluate(`({
      url:location.href,state:document.readyState,scroll:scrollY,
      width:innerWidth,scale:visualViewport.scale
    })`)));
  };
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  for (const [width, height] of [[1440, 1000], [390, 844], [320, 740]]) {
    await call("Emulation.setDeviceMetricsOverride", {
      width, height, deviceScaleFactor: 1, mobile: width < 500,
    });
    await call("Page.navigate", {url: origin + "/resources"});
    await until("location.pathname==='/resources' && document.readyState==='complete'", "resources");
    await evaluate("document.fonts.ready.then(()=>true)");
    const href = await evaluate(`(()=>{
      const a=document.querySelector('#site-footer .foot-signup');
      if(!a) return null;
      return a.getAttribute('href');
    })()`);
    assert.equal(href, "/care-brief#signup");
    // Activate the real anchor in the browser; destination checks use the
    // rendered viewport, independently of headless touch emulation.
    await evaluate("document.querySelector('#site-footer .foot-signup').click()");
    await until("location.pathname==='/care-brief' && location.hash==='#signup' && document.readyState==='complete'", "signup navigation");
    await evaluate("document.fonts.ready.then(()=>true)");
    await until(`(()=>{
      const section=document.querySelector('#signup');
      const email=section?.querySelector('form[name="elh-care-brief-signup"] input[type="email"]');
      if(!email) return false;
      const r=email.getBoundingClientRect(), header=document.querySelector('#hdr').getBoundingClientRect();
      return r.top>=Math.max(0,header.bottom) && r.bottom<=innerHeight && r.left>=0 && r.right<=innerWidth;
    })()`, "email field visible below header");
    assert.equal(await evaluate("document.querySelectorAll('#signup').length"), 1);
    await evaluate("document.querySelector('#signup input[type=\"email\"]').focus()");
    assert.equal(await evaluate("document.activeElement.name"), "email");
    console.log(`PASS ${width}px footer link reaches visible, focusable signup form`);
  }
} finally {
  socket?.close();
  browser.kill("SIGTERM");
  await sleep(200);
  await rm(profile, {recursive: true, force: true});
}
