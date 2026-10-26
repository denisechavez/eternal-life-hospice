// Isolated failure/retry coverage for the actual Care Brief HTML and intake JS.
// Run from any directory:
// node --experimental-websocket website/test-care-brief-signup-retry.mjs
// No application server, secrets, live providers or publication jobs. Resized
// Chromium viewports are NOT real-device software-keyboard verification.
import assert from "node:assert/strict";
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
const submissions = [];
const served = new Set();
const unexpected = [];
let replies = [];
let securityRequests = 0;
const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://fixture");
  const json = (status, body) => {
    res.writeHead(status, {"Content-Type": "application/json"});
    res.end(JSON.stringify(body));
  };
  if (req.method === "GET" && url.pathname === "/api/form-security" &&
      url.searchParams.get("form") === "elh-care-brief-signup") {
    securityRequests++;
    // Exercise the real security module, but never load a challenge provider.
    json(200, {siteKey: "", token: "local-fixture-only", waitMs: 0});
    return;
  }
  if (req.method === "POST" && url.pathname === "/api/form-submit") {
    let body = "";
    for await (const chunk of req) body += chunk;
    submissions.push(Object.fromEntries(new URLSearchParams(body)));
    const reply = replies.shift();
    if (!reply) {
      unexpected.push("Unplanned form submission");
      json(500, {ok: false});
    } else if (reply === "malformed") {
      res.writeHead(200, {"Content-Type": "application/json"});
      res.end("{not-json");
    } else if (reply === "rejected") {
      json(200, {ok: true, accepted: false});
    } else if (reply === "server") {
      json(503, {ok: false, accepted: false});
    } else {
      json(200, {ok: true, accepted: true});
    }
    return;
  }
  const file = resolve(root, url.pathname === "/care-brief"
    ? "care-brief.html" : url.pathname.slice(1));
  if (req.method !== "GET" || !file.startsWith(root + sep) ||
      !(url.pathname === "/care-brief" || url.pathname.startsWith("/assets/"))) {
    unexpected.push(`${req.method} ${url.pathname}`);
    res.writeHead(403).end();
    return;
  }
  try {
    const body = await readFile(file);
    served.add(url.pathname);
    res.writeHead(200, {"Content-Type": types[extname(file)] || "application/octet-stream"});
    res.end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const profile = await mkdtemp(join(tmpdir(), "elh-care-brief-retry-"));
const browser = spawn("chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage",
  "--disable-background-networking", "--disable-component-update",
  "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
  "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
], {stdio: ["ignore", "ignore", "pipe"]});
let diagnostics = "";
let startupError;
browser.on("error", error => { startupError = error; });
browser.stderr.on("data", chunk => { diagnostics = (diagnostics + chunk).slice(-12000); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map();
let socket;

// Check one target at a time: a reduced viewport need not fit the whole form.
function inspect(selector) {
  const el = document.querySelector(selector);
  if (!el) return {errors: ["missing target"]};
  const r = el.getBoundingClientRect(), vv = visualViewport;
  const header = document.querySelector("#hdr").getBoundingClientRect();
  const bounds = {left: vv.offsetLeft, right: vv.offsetLeft + vv.width,
    top: Math.max(vv.offsetTop, header.bottom), bottom: vv.offsetTop + vv.height};
  const errors = [];
  if (!el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) ||
      r.width <= 0 || r.height <= 0 || el.disabled) errors.push("hidden or disabled");
  if (r.left < bounds.left - 1 || r.right > bounds.right + 1) errors.push("horizontal clipping");
  if (r.top < bounds.top - 1 || r.bottom > bounds.bottom + 1) errors.push("outside visible height");
  if (el.scrollWidth > el.clientWidth + 1) errors.push("content clipping");
  for (const [x, y] of [
    [r.left + 2, r.top + r.height / 2], [r.right - 2, r.top + r.height / 2],
    [r.left + r.width / 2, r.top + 2], [r.left + r.width / 2, r.bottom - 2],
  ]) {
    const hit = document.elementFromPoint(x, y);
    if (!hit || !(hit === el || el.contains(hit))) errors.push("obscured or clipped");
  }
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) {
    errors.push("page horizontal overflow");
  }
  return {errors, bounds, rect: {left: r.left, right: r.right, top: r.top, bottom: r.bottom},
    active: document.activeElement === el, width: innerWidth, height: innerHeight,
    visualHeight: vv.height, scale: vv.scale};
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
  const interceptionErrors = [], blocked = [];
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
      const allowed = url.origin === origin && (
        (request.method === "GET" && (url.pathname === "/care-brief" ||
          url.pathname === "/api/form-security" ||
          (url.pathname.startsWith("/assets/") && url.pathname !== "/assets/analytics.js"))) ||
        (request.method === "POST" && url.pathname === "/api/form-submit"));
      // Fail the browser request deterministically. Destroying an HTTP socket
      // can make Chromium transparently resend a POST on a fresh connection.
      if (allowed && request.method === "POST" && replies[0] === "connection") {
        replies.shift();
        submissions.push(Object.fromEntries(new URLSearchParams(request.postData)));
        void call("Fetch.failRequest", {requestId, errorReason: "ConnectionFailed"})
          .catch(error => interceptionErrors.push(error.message));
        return;
      }
      if (!allowed) blocked.push(request.url);
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
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return;
      await sleep(50);
    }
    throw new Error(`Timed out: ${label}; submissions=${submissions.length}; security=${securityRequests}; blocked=${JSON.stringify(blocked)}; unexpected=${JSON.stringify(unexpected)}`);
  };
  const first = '#signup input[name="first_name"]';
  const email = '#signup input[name="email"]';
  const button = '#signup button[type="submit"]';
  const error = ".cbl-signup-error";
  // Check browser-exposed semantics, not just HTML attributes. The live-region
  // containers must exist before submission, even while their messages are hidden.
  const assertAnnouncements = async (visible = null) => {
    const {nodes} = await call("Accessibility.getFullAXTree");
    for (const [selector, role, live] of [
      [error, "alert", "assertive"],
      [".cbl-signup-thanks", "status", "polite"],
    ]) {
      const {root: {nodeId}} = await call("DOM.getDocument");
      const {nodeId: regionId} = await call("DOM.querySelector", {
        nodeId, selector: `#signup [role="${role}"]:has(> ${selector})`,
      });
      const {node: {backendNodeId}} = await call("DOM.describeNode", {nodeId: regionId});
      const region = nodes.find(node => node.backendDOMNodeId === backendNodeId && !node.ignored);
      assert.ok(region, selector + " has an exposed, persistent announcement container");
      assert.equal(region.role.value, role);
      const properties = Object.fromEntries(region.properties.map(p => [p.name, p.value.value]));
      assert.equal(properties.live, live, selector + " announcement priority");
      assert.equal(properties.atomic, true, selector + " announces the complete message");
      // The flat AX response is not in reading order (links may come last).
      // Follow child IDs so the phone link stays within the error sentence.
      const byId = new Map(nodes.map(node => [node.nodeId, node]));
      const readText = node => node.role?.value === "StaticText"
        ? node.name?.value || ""
        : (node.childIds || []).map(id => readText(byId.get(id))).join("");
      const text = readText(region).replace(/\s+/g, " ").trim();
      const content = await evaluate(`document.querySelector(${JSON.stringify(selector)}).textContent`);
      assert.equal(text, visible === selector ? content.trim().replace(/\s+/g, " ") : "",
        selector + " is exposed only when shown");
    }
  };
  const metrics = (width, height) => call("Emulation.setDeviceMetricsOverride", {
    width, height, deviceScaleFactor: 1, mobile: true,
  });
  const check = selector => evaluate(`(${inspect.toString()})(${JSON.stringify(selector)})`);
  const reach = async selector => {
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({
      block:'center',inline:'nearest',behavior:'instant'
    })`);
    return check(selector);
  };
  const assertReachable = async (selector, label) => {
    const result = await reach(selector);
    assert.deepEqual(result.errors, [], `${label}: ${JSON.stringify(result)}`);
    return result;
  };
  const key = async (name, code, modifiers = 0) => {
    for (const type of ["keyDown", "keyUp"]) {
      await call("Input.dispatchKeyEvent", {type, key: name, code: name,
        windowsVirtualKeyCode: code, modifiers,
        ...(name === "Enter" && type === "keyDown" ? {text: "\r"} : {})});
    }
  };
  const values = () => evaluate(`({
    first_name:document.querySelector(${JSON.stringify(first)}).value,
    email:document.querySelector(${JSON.stringify(email)}).value
  })`);
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  let cases = 0;
  for (const [width, fullHeight, reducedHeight] of [
    [320, 740, 340], [360, 800, 380], [390, 844, 400], [740, 390, 240],
  ]) {
    for (const failure of ["server", "rejected", "malformed", "connection"]) {
      const label = `${width}x${reducedHeight} ${failure}`;
      const entered = {first_name: "Local Retry", email: "care-brief-retry@example.test"};
      const start = submissions.length, securityStart = securityRequests;
      replies = [failure, "success"];
      await metrics(width, fullHeight);
      // A distinct URL forces a fresh document rather than same-hash navigation
      // retaining the previous case's successful (hidden) form.
      await call("Page.navigate", {url: origin + `/care-brief?case=${cases}#signup`});
      await until(`location.search==='?case=${cases}' && document.readyState==='complete' &&
        !!document.querySelector('#signup form') && !document.querySelector('#signup form').hidden`, "signup loaded");
      await evaluate("document.fonts.ready.then(()=>true)");
      await sleep(400); // Let the actual page's delayed anchor correction finish.
      assert.equal(await evaluate("document.querySelector('.cbl-signup-error').hidden"), true);
      await assertAnnouncements();
      await evaluate(`document.querySelector(${JSON.stringify(first)}).value=${JSON.stringify(entered.first_name)};
        document.querySelector(${JSON.stringify(email)}).value=${JSON.stringify(entered.email)};
        document.querySelector(${JSON.stringify(email)}).focus()`);
      await metrics(width, reducedHeight);
      const reduced = await assertReachable(email, label + " email");
      assert.equal(reduced.active, true);
      assert.equal(reduced.width, width);
      assert.equal(reduced.height, reducedHeight);
      assert.equal(reduced.visualHeight, reducedHeight);
      assert.ok(Math.abs(reduced.scale - 1) < 0.01);
      await key("Tab", 9);
      assert.equal((await assertReachable(button, label + " initial submit")).active, true);
      await evaluate(`window.signupFocusChanges=[];
        document.addEventListener('focusin',e=>window.signupFocusChanges.push(e.target.tagName))`);
      await key("Enter", 13); // Native form submission; no handler replacements.
      await until("!document.querySelector('.cbl-signup-error').hidden", label + " failure");
      assert.equal(submissions.length, start + 1, "Exactly one failed attempt");
      assert.equal(await evaluate("document.querySelector('#signup form').hidden"), false);
      assert.equal(await evaluate("document.querySelector('.cbl-signup-thanks').hidden"), true);
      assert.match(await evaluate("document.querySelector('.cbl-signup-error').textContent"),
        /couldn.t confirm your signup.*try again/s);
      assert.deepEqual(await values(), entered, label + " preserves entered values");
      await assertAnnouncements(error);
      assert.deepEqual(await evaluate("window.signupFocusChanges"), [],
        "Failure announcement must not move focus");
      await assertReachable(error, label + " error message");
      await assertReachable(error + " a", label + " help link");
      await assertReachable(button, label + " retry");
      // The retry button must still be keyboard-reachable, and Shift+Tab must
      // return to the original email field without clearing either value.
      assert.equal((await check(button)).active, true);
      await key("Tab", 9, 8);
      assert.equal((await assertReachable(email, label + " return to email")).active, true);
      assert.deepEqual(await values(), entered);
      // Keyboard dismissal must not hide the failure or remove retry.
      await metrics(width, fullHeight);
      await assertReachable(error, label + " restored error");
      await assertReachable(button, label + " restored retry");
      await metrics(width, reducedHeight);
      await key("Tab", 9);
      assert.equal((await assertReachable(button, label + " resubmit")).active, true);

      if (cases === 0) {
        // Known-bad disposable DOM changes prove the assertions can fail.
        for (const [name, selector, css, expected] of [
          ["hidden error", error, "display:none!important", "hidden or disabled"],
          ["clipped error", error, "clip-path:inset(0 90% 0 0)!important", "obscured or clipped"],
          ["disabled retry", button, "", "hidden or disabled"],
        ]) {
          const originalStyle = await evaluate(`document.querySelector(${JSON.stringify(selector)}).getAttribute('style')`);
          await evaluate(`(()=>{
            const el=document.querySelector(${JSON.stringify(selector)});
            el.setAttribute('style',${JSON.stringify(css)});
            if(${JSON.stringify(name)}==='disabled retry')el.disabled=true;
          })()`);
          const result = await reach(selector);
          assert.ok(result.errors.some(e => e.includes(expected)), `Guard missed ${name}`);
          await evaluate(`(()=>{
            const el=document.querySelector(${JSON.stringify(selector)});
            const original=${JSON.stringify(originalStyle)};
            if(original===null)el.removeAttribute('style');else el.setAttribute('style',original);
          })();
            document.querySelector(${JSON.stringify(button)}).disabled=false`);
          console.log("PASS negative control: " + name);
        }
        await assertReachable(error, "restored error guard");
        await assertReachable(button, "restored retry guard");
        // Disabling the focused button in the negative control blurs it.
        await evaluate(`document.querySelector(${JSON.stringify(email)}).focus()`);
        await key("Tab", 9);
        assert.equal((await assertReachable(button, "restored retry focus")).active, true);
      }
      await evaluate("window.signupFocusChanges=[]");
      await key("Enter", 13);
      await until("!document.querySelector('.cbl-signup-thanks').hidden", label + " retry success");
      assert.equal(await evaluate("document.querySelector('#signup form').hidden"), true);
      assert.equal(await evaluate("document.querySelector('.cbl-signup-error').hidden"), true);
      await assertAnnouncements(".cbl-signup-thanks");
      assert.deepEqual(await evaluate("window.signupFocusChanges"), [],
        "Success announcement must not move focus to another element");
      assert.deepEqual(await values(), entered, "Success must not clear entered values");
      await assertReachable(".cbl-signup-thanks", label + " success message");
      assert.equal(submissions.length, start + 2, "Retry must issue exactly one more request");
      assert.equal(securityRequests, securityStart + 2, "Each attempt uses local security fixture");
      for (const payload of submissions.slice(start)) {
        assert.deepEqual(payload, {...entered, "form-name": "elh-care-brief-signup",
          "bot-field": "", "_elh_security": "local-fixture-only"});
      }
      assert.deepEqual(replies, [], "Both planned responses must be consumed");
      cases++;
      console.log(`PASS ${label}: visible failure, retained fields, email focus and successful retry`);
    }
  }
  // Exercise the network fence: these attempts must never reach any host.
  for (const url of ["https://api.brevo.com/v3/contacts", origin + "/api/unplanned"]) {
    assert.equal(await evaluate(`fetch(${JSON.stringify(url)},{method:'POST',mode:'no-cors'})
      .then(()=>false,()=>true)`), true);
    assert.ok(blocked.includes(url), "Request must be intercepted before network");
  }
  for (const path of ["/care-brief", "/assets/elh.css", "/assets/intake-security.js"]) {
    assert.ok(served.has(path), "Must exercise actual source: " + path);
  }
  assert.deepEqual(unexpected, []);
  assert.deepEqual(interceptionErrors, []);
  console.log(`PASS ${cases} local-only failure/retry cases; no live providers or publication changes`);
  console.log("SENTINEL: test-care-brief-signup-retry.mjs browser checks OK");
} finally {
  for (const waiter of pending.values()) clearTimeout(waiter.timer);
  socket?.close();
  browser.kill("SIGTERM");
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  if (browser.exitCode === null && browser.signalCode === null && !startupError) {
    await new Promise(resolve => browser.once("exit", resolve));
  }
  await rm(profile, {recursive: true, force: true});
}
