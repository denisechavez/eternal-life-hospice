// Read-only browser layout guard; independent of signup button wording.
// Run from any directory:
// node --experimental-websocket website/test-care-brief-layout.mjs
// Requires Chromium and Node's built-in WebSocket; no preview server or secrets.
// Includes focused reduced-viewport checks from care-brief-keyboard-checks.mjs.
// These emulate a keyboard resize, not a real-device software keyboard.
import assert from "node:assert/strict";
import {checkKeyboardViewports} from "./care-brief-keyboard-checks.mjs";
import {spawn} from "node:child_process";
import {createServer} from "node:http";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, extname, join, resolve, sep} from "node:path";
import {fileURLToPath} from "node:url";

assert.equal(typeof WebSocket, "function", "Run with node --experimental-websocket");
const root = join(dirname(fileURLToPath(import.meta.url)), "elh-preview");
const types = {".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".woff2": "font/woff2", ".woff": "font/woff", ".png": "image/png",
  ".webp": "image/webp", ".jpg": "image/jpeg", ".svg": "image/svg+xml"};
const served = [];
// Static files only: never start the application, its APIs or publication jobs.
const server = createServer(async (req, res) => {
  const path = new URL(req.url, "http://fixture").pathname;
  const relative = path === "/care-brief" ? "care-brief.html" : path.slice(1);
  const file = resolve(root, relative);
  if (req.method !== "GET" || !file.startsWith(root + sep) ||
      !(path === "/care-brief" || path.startsWith("/assets/"))) {
    res.writeHead(403).end();
    return;
  }
  try {
    const body = await readFile(file);
    served.push(path);
    res.writeHead(200, {"Content-Type": types[extname(file)] || "application/octet-stream"});
    res.end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const profile = await mkdtemp(join(tmpdir(), "elh-care-brief-layout-"));
const browser = spawn("chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage",
  "--disable-background-networking", "--disable-component-update",
  "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
], {stdio: ["ignore", "ignore", "pipe"]});
let diagnostics = "";
let startupError;
browser.on("error", error => { startupError = error; });
browser.stderr.on("data", chunk => { diagnostics = (diagnostics + chunk).slice(-12000); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
const pending = new Map();

// Runs inside Chromium: include ancestor clipping even when the page hides
// horizontal overflow (scrollWidth alone would miss that regression).
function inspectSignup() {
  const errors = [];
  const vv = visualViewport;
  const bounds = {left: vv.offsetLeft, top: vv.offsetTop,
    right: vv.offsetLeft + vv.width, bottom: vv.offsetTop + vv.height};
  const form = document.querySelector('#signup form[name="elh-care-brief-signup"]');
  const targets = {
    "first-name field": form?.querySelector('input[name="first_name"]'),
    "email field": form?.querySelector('input[name="email"][type="email"]'),
    "submit button": form?.querySelector('button[type="submit"]'),
  };
  const rects = {};
  const header = document.querySelector("#hdr")?.getBoundingClientRect();
  for (const [label, element] of Object.entries(targets)) {
    if (!element) { errors.push(`${label}: missing`); continue; }
    const r = element.getBoundingClientRect();
    rects[label] = {left: r.left, right: r.right, top: r.top, bottom: r.bottom};
    if (r.width <= 0 || r.height <= 0 || !element.checkVisibility({
      checkOpacity: true, checkVisibilityCSS: true,
    })) errors.push(`${label}: hidden or zero-sized`);
    if (r.left < bounds.left - 1 || r.right > bounds.right + 1 ||
        r.top < bounds.top - 1 || r.bottom > bounds.bottom + 1) {
      errors.push(`${label}: outside visual viewport`);
    }
    if (header && r.top < header.bottom - 1) errors.push(`${label}: behind header`);
    if (element.disabled) errors.push(`${label}: disabled`);
    // A button can fit while its label is clipped inside its own content box.
    if (element.tagName === "BUTTON" && element.scrollWidth > element.clientWidth + 1) {
      errors.push(`${label}: horizontal content clipping`);
    }
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      const style = getComputedStyle(parent);
      const p = parent.getBoundingClientRect();
      if (["hidden", "clip", "auto", "scroll"].includes(style.overflowX) &&
          (r.left < p.left + parent.clientLeft - 1 ||
           r.right > p.left + parent.clientLeft + parent.clientWidth + 1)) {
        errors.push(`${label}: horizontal ancestor clipping (${parent.tagName}.${parent.className})`);
      }
      if (["hidden", "clip", "auto", "scroll"].includes(style.overflowY) &&
          parent !== document.body && parent !== document.documentElement &&
          (r.top < p.top + parent.clientTop - 1 ||
           r.bottom > p.top + parent.clientTop + parent.clientHeight + 1)) {
        errors.push(`${label}: vertical ancestor clipping`);
      }
    }
    for (const x of [r.left + 2, r.left + r.width / 2, r.right - 2]) {
      const hit = document.elementFromPoint(x, r.top + r.height / 2);
      if (!hit || !(hit === element || element.contains(hit))) {
        errors.push(`${label}: obscured or clipped at x=${x}`);
      }
    }
  }
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) {
    errors.push("page: horizontal overflow");
  }
  return {errors, rects, bounds, layoutWidth: innerWidth,
    clientWidth: document.documentElement.clientWidth, scale: vv.scale};
}

try {
  let port;
  for (let i = 0; i < 150; i++) {
    if (startupError) throw startupError;
    assert.equal(browser.exitCode, null, "Chromium exited: " + diagnostics);
    try {
      port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]);
      if (port) break;
    } catch { /* Wait for Chromium. */ }
    await sleep(100);
  }
  assert.ok(port, "Chromium did not start: " + diagnostics);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  let id = 0;
  const interceptionErrors = [];
  const blocked = [];
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => {
      pending.delete(requestId);
      reject(new Error("Browser command timed out: " + method));
    }, 15000);
    pending.set(requestId, {resolve, reject, timer});
    socket.send(JSON.stringify({id: requestId, method, params}));
  });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.method === "Fetch.requestPaused") {
      const {request, requestId} = message.params;
      const url = new URL(request.url);
      const allowed = url.origin === origin && request.method === "GET" &&
        (url.pathname === "/care-brief" ||
         (url.pathname.startsWith("/assets/") && url.pathname !== "/assets/analytics.js"));
      if (!allowed) blocked.push({url: request.url, method: request.method});
      void call(allowed ? "Fetch.continueRequest" : "Fetch.failRequest",
        allowed ? {requestId} : {requestId, errorReason: "BlockedByClient"})
        .catch(error => interceptionErrors.push(error.message));
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
      if (await evaluate(expression)) return;
      await sleep(100);
    }
    throw new Error("Timed out: " + label);
  };
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  await call("Page.addScriptToEvaluateOnNewDocument", {source: `
    window.__blockedSubmits = 0;
    addEventListener('submit', e => {
      window.__blockedSubmits++;
      e.preventDefault(); e.stopImmediatePropagation();
    }, true);
    HTMLFormElement.prototype.submit = function(){window.__blockedSubmits++;};
    HTMLFormElement.prototype.requestSubmit = function(){window.__blockedSubmits++;};
  `});
  const inspect = () => evaluate(`(${inspectSignup.toString()})()`);
  for (const [width, height] of [[320, 740], [360, 800], [390, 844], [768, 1024], [1440, 1000]]) {
    await call("Emulation.setDeviceMetricsOverride", {
      width, height, deviceScaleFactor: 1, mobile: width < 500,
    });
    await call("Page.navigate", {url: origin + "/care-brief#signup"});
    await until("location.hash==='#signup' && document.readyState==='complete'", "signup loaded");
    await evaluate("document.fonts.ready.then(()=>true)");
    // The actual page performs an anchor correction 250ms after load.
    await sleep(400);
    await until("document.querySelector('#signup').getBoundingClientRect().top < innerHeight",
      "signup anchor scroll starts");
    await evaluate(`new Promise(resolve=>{
      let previous=scrollY, stable=0;
      const timer=setInterval(()=>{
        stable=Math.abs(scrollY-previous)<0.5?stable+1:0;
        previous=scrollY;
        if(stable>=4){clearInterval(timer);resolve();}
      },100);
    })`);
    const result = await inspect();
    // Desktop Chromium reserves space for a vertical scrollbar; the visual
    // viewport must match clientWidth, not necessarily the outer layout width.
    assert.ok(Math.abs(result.bounds.right - result.bounds.left - result.clientWidth) <= 1 &&
      Math.abs(result.layoutWidth - width) <= 1 && Math.abs(result.scale - 1) < 0.01,
    `${width}px: emulated viewport does not match requested width: ${JSON.stringify(result)}`);
    assert.deepEqual(result.errors, [], `${width}x${height}: ${JSON.stringify(result)}`);
    assert.equal(await evaluate("window.__blockedSubmits"), 0, "Layout check must never submit");
    console.log(`PASS ${width}x${height}: first name, email and submit visible without clipping`);
  }
  // Known-bad browser mutations prove the geometry guard detects regressions.
  // These affect only the disposable DOM, never care-brief.html.
  for (const [label, css, expected] of [
    ["hidden first name", 'input[name="first_name"]{display:none!important}', "first-name field"],
    ["offscreen email", 'input[name="email"]{transform:translateX(2000px)!important}', "email field"],
    ["hidden button", '#signup button{visibility:hidden!important}', "submit button"],
    ["clipped ancestor", '.cbl-signup-fields{clip-path:inset(0 90% 0 0)!important}', "obscured or clipped"],
    ["overflowing fields", '.cbl-signup-fields{flex-wrap:nowrap!important;width:2000px!important}', "horizontal"],
    ["clipped button label", '#signup button{width:10px!important;max-width:10px!important;padding:0!important;overflow:hidden!important;white-space:nowrap!important}', "horizontal content clipping"],
  ]) {
    await evaluate(`(()=>{
      const s=document.createElement('style'); s.id='layout-negative'; s.textContent=${JSON.stringify(css)};
      document.head.append(s);
    })()`);
    const result = await inspect();
    assert.ok(result.errors.some(error => error.includes(expected)),
      `Guard missed ${label}: ${JSON.stringify(result)}`);
    await evaluate("document.querySelector('#layout-negative').remove()");
    console.log("PASS negative control: " + label);
  }
  assert.deepEqual((await inspect()).errors, [], "Restored layout should pass");
  await checkKeyboardViewports({call, evaluate, until, sleep});
  // Prove the submit-event fence without activating or filling the form.
  assert.equal(await evaluate(`(()=>{
    const event=new Event('submit',{bubbles:true,cancelable:true});
    document.querySelector('#signup form').dispatchEvent(event);
    return event.defaultPrevented && window.__blockedSubmits===1;
  })()`), true, "Submit must be stopped before application handlers");
  const probes = [
    {url: origin + "/api/form-submit", method: "POST"},
    {url: "https://api.brevo.com/v3/contacts", method: "POST"},
  ];
  for (const probe of probes) {
    assert.equal(await evaluate(`fetch(${JSON.stringify(probe.url)},{
      method:${JSON.stringify(probe.method)},mode:'no-cors'
    }).then(()=>false,()=>true)`), true, "Network fence must block " + probe.url);
    assert.ok(blocked.some(request => request.url === probe.url && request.method === probe.method));
  }
  assert.ok(served.includes("/care-brief"), "Must load the actual Care Brief HTML");
  assert.ok(served.includes("/assets/elh.css"), "Must load shared site styles");
  assert.ok(!served.some(path => path.startsWith("/api/")), "No API requests may reach the fixture");
  assert.deepEqual(interceptionErrors, []);
  console.log("SENTINEL: test-care-brief-layout.mjs browser checks OK");
} finally {
  for (const waiter of pending.values()) clearTimeout(waiter.timer);
  socket?.close();
  browser.kill("SIGTERM");
  await new Promise(resolve => server.close(resolve));
  if (browser.exitCode === null && browser.signalCode === null && !startupError) {
    await new Promise(resolve => browser.once("exit", resolve));
  }
  await rm(profile, {recursive: true, force: true});
}
