// Final DOM phone-role checks; no form submissions, backend, mail or live AI.
// Run: node --experimental-websocket website/test-website-phone-browser.mjs
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {startIntakeFixture} from "./intake-browser-fixture.mjs";

assert.notEqual(process.env.REPLIT_DEPLOYMENT, "1", "Never run fixtures in production");
assert.equal(typeof WebSocket, "function", "Node 20 needs --experimental-websocket");
const profile = await mkdtemp(join(tmpdir(), "elh-phone-browser-"));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let fixture, browser, socket, caseName = "startup", id = 0;
const pending = new Map(), errors = [], apiRequests = [], blocked = [];
try {
  fixture = await startIntakeFixture(); // Synthetic mode only; never start its real backend.
  browser = spawn(process.env.CHROMIUM_BIN || "chromium", ["--headless", "--no-sandbox",
    "--disable-dev-shm-usage", "--disable-background-networking", "--no-first-run",
    "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank"],
  {stdio: ["ignore", "ignore", "pipe"]});
  let browserLog = "", spawnError, port;
  browser.stderr.on("data", chunk => {browserLog = (browserLog + chunk).slice(-4000);});
  browser.on("error", error => {spawnError = error;});
  for (let i = 0; i < 200; i++) {
    if (spawnError) throw spawnError;
    if (browser.exitCode !== null) throw new Error("Chromium exited: " + browserLog);
    try {port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]);}
    catch { /* Wait for Chromium's endpoint. */ }
    if (port) break;
    await sleep(50);
  }
  assert.ok(port, "Chromium startup timed out: " + browserLog);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    const timer = setTimeout(() => {
      pending.delete(key);
      reject(new Error("Browser command timed out: " + method));
    }, 10000);
    pending.set(key, {resolve, reject, timer});
    socket.send(JSON.stringify({id: key, method, params}));
  });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data), waiter = pending.get(message.id);
    if (waiter) {
      clearTimeout(waiter.timer);
      pending.delete(message.id);
      message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result);
    }
    if (message.method === "Runtime.exceptionThrown") errors.push(message.params.exceptionDetails);
    if (message.method === "Fetch.requestPaused") {
      const {requestId, request} = message.params, url = new URL(request.url);
      const local = url.origin === fixture.origin;
      const api = local && url.pathname.startsWith("/api/");
      if (api) apiRequests.push({path: url.pathname, method: request.method});
      if (!local) blocked.push(request.url);
      // Fulfill every API and third-party request locally, including unexpected
      // submission attempts (which also fail the final assertions).
      const operation = local && !api && request.method === "GET"
        ? call("Fetch.continueRequest", {requestId})
        : call("Fetch.fulfillRequest", {requestId, responseCode: api ? 503 : 200,
          responseHeaders: [{name: "Content-Type", value: api ? "application/json" : "text/plain"}],
          body: Buffer.from(api ? '{"error":"synthetic_unavailable"}' : "").toString("base64")});
      operation.catch(error => errors.push(String(error)));
    }
  });
  const evaluate = async expression => {
    const result = await call("Runtime.evaluate", {expression, awaitPromise: true, returnByValue: true});
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async expression => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await sleep(40);
    }
    throw new Error("Timed out: " + expression);
  };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const navigate = async (path, ready = ".elhc-launch") => {
    await call("Page.navigate", {url: fixture.origin + path});
    await until(`document.readyState === 'complete' && !!document.querySelector(${JSON.stringify(ready)})`);
  };
  const digits = text => {
    const value = text.replace(/\D/g, "");
    return value.length === 10 ? "1" + value : value;
  };
  const mainLinks = async selector => {
    const links = await evaluate(`(()=>{
      const container=document.querySelector(${JSON.stringify(selector)});
      return container ? [...container.querySelectorAll('a[href^="tel:"]')].map(a=>({
        text:a.innerText, href:a.getAttribute('href'), resolved:a.href,
        visible:a.getClientRects().length>0 && getComputedStyle(a).visibility!=='hidden'
      })) : [];
    })()`);
    assert.ok(links.length, caseName + ": no telephone links in " + selector);
    for (const link of links) {
      assert.equal(link.visible, true, JSON.stringify(link));
      assert.match(link.text, /805\.409\.9262/, JSON.stringify(link));
      // The header includes a 24/7 suffix; compare its phone substring.
      const label = link.text.match(/\d{3}[. -]\d{3}[. -]\d{4}/)?.[0];
      assert.equal(digits(label), "18054099262");
      assert.equal(digits(link.href), digits(label), JSON.stringify(link));
      assert.equal(link.resolved, link.href, "Actual browser dial URL differs");
    }
  };
  const ask = async (question, expected) => {
    await evaluate(`(()=>{
      const input=document.querySelector('.elhc-in'); input.value=${JSON.stringify(question)};
      input.dispatchEvent(new Event('input',{bubbles:true}));
      document.querySelector('.elhc-send').click();
    })()`);
    await until(`document.querySelector('.elhc-bot') &&
      [...document.querySelectorAll('.elhc-bot')].at(-1).innerText.includes(${JSON.stringify(expected)})`);
    const reply = await evaluate(`[...document.querySelectorAll('.elhc-bot')].at(-1).innerText`);
    assert.match(reply, /805\.409\.9262/);
    assert.doesNotMatch(reply, /805[. -](?:953[. -]7273|410[. -]1151)/);
    await mainLinks(".elhc-head");
  };
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  await call("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});

  for (const width of [1280, 390]) {
    await call("Emulation.setDeviceMetricsOverride", {
      width, height: 900, deviceScaleFactor: 1, mobile: width < 500,
    });
    caseName = `${width}px chat opening`;
    await navigate("/");
    await click(".elhc-launch");
    await until("document.querySelector('.elhc-panel.open') && document.querySelector('.elhc-chip-cb')");
    await mainLinks(".elhc-head");
    caseName = `${width}px emergency routing`;
    await ask("This is an emergency, call 911", "If this is a medical emergency");
    caseName = `${width}px nurse routing`;
    await ask("I have a medication question", "best for one of our nurses");
    caseName = `${width}px unavailable AI fallback`;
    await ask("What is hospice care?", "having trouble responding");

    caseName = `${width}px callback and simulated intake displays`;
    await click(".elhc-chip-cb");
    await until("document.querySelector('.elhc-cb-err')");
    // Exercise the real exported renderer in the real callback container.
    // Deliberately do not call submit(), dispatch submit, or enter contact data.
    for (const [outcome, message] of [
      ["verification", "request has not been sent"],
      ["rejected", "request was not accepted"],
      ["unknown", "couldn't confirm whether your request was received"],
    ]) {
      caseName = `${width}px ${outcome} display`;
      await evaluate(`(async()=>{
        const security=await import('/assets/intake-security.js');
        const container=document.querySelector('.elhc-cb-err');
        container.hidden=false; container.style.display='block';
        security.showFailure({intakeOutcome:${JSON.stringify(outcome)}},container);
        container.scrollIntoView({block:'center'});
      })()`);
      assert.ok((await evaluate("document.querySelector('.elhc-cb-err').innerText")).includes(message));
      await mainLinks(".elhc-cb-err");
      await mainLinks(".elhc-head");
    }
    caseName = `${width}px chat-owned uncertain callback reminder`;
    await evaluate("sessionStorage.setItem('elhcCallbackUncertainUntil', String(Date.now()+600000))");
    await click(".elhc-chip-cb");
    await until("document.querySelector('.elhc-cb-reminder')");
    await mainLinks(".elhc-cb-reminder");
    await click(".elhc-x");
    await click(".elhc-launch");
    await mainLinks(".elhc-head");
    await mainLinks(".elhc-cb-reminder");
    await evaluate("sessionStorage.removeItem('elhcCallbackUncertainUntil')");
    console.log(`PASS ${width}px: chat routing, fallback, three intake displays and reopened reminder`);
  }

  caseName = "explicit office role";
  await navigate("/card-aleksandra-dubina.html", 'a[href^="tel:"]');
  const office = await evaluate(`[...document.querySelectorAll('a[href^="tel:"]')]
    .filter(a=>/office/i.test(a.innerText)).map(a=>({text:a.innerText,href:a.getAttribute('href')}))`);
  assert.ok(office.length, "Expected an explicitly labeled office link on the actual contact card");
  for (const link of office) {
    assert.match(link.text, /805\.953\.7273/);
    assert.equal(digits(link.href), "18059537273");
  }
  assert.ok(apiRequests.some(request => request.path === "/api/chat"), "AI fallback was not exercised");
  assert.deepEqual(apiRequests.filter(request => !["/api/chat", "/api/google-reviews"].includes(request.path)), []);
  assert.deepEqual(fixture.state.posts, [], "No submissions permitted");
  assert.deepEqual(fixture.state.security, [], "No verification requests permitted");
  assert.deepEqual(fixture.state.violations, []);
  assert.deepEqual(errors, [], "Browser/transport errors");
  console.log(`PASS office role retained; all APIs/third parties stubbed (${blocked.length} external requests); zero submissions`);
} catch (error) {
  console.error("FAIL " + caseName);
  throw error;
} finally {
  for (const waiter of pending.values()) clearTimeout(waiter.timer);
  socket?.close();
  if (browser && browser.exitCode === null) {
    const exited = new Promise(resolve => browser.once("exit", resolve));
    browser.kill("SIGKILL");
    await exited;
  }
  await fixture?.close();
  await rm(profile, {recursive: true, force: true});
}
