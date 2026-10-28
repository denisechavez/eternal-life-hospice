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
// Synthetic lookup results only: exercise direct and refined suggestion outcomes.
const coverageResponses = {
  San: {served: false, city: "San", ambiguous: true, suggestions: ["San Fernando", "San Francisco", "San F"]},
  "San F": {served: false, city: "San F", ambiguous: true, suggestions: ["San Fernando", "San Francisco"]},
  "San Fernando": {served: true, city: "San Fernando", county: "Los Angeles County", phone: "805.409.9262"},
  "San Francisco": {served: false, city: "San Francisco"},
};
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
      const city = url.searchParams.get("city");
      if (api) apiRequests.push({path: url.pathname, method: request.method,
        ...(url.pathname === "/api/coverage" ? {city} : {})});
      const coverage = api && url.pathname === "/api/coverage" && request.method === "GET"
        && Object.hasOwn(coverageResponses, city) ? coverageResponses[city] : null;
      if (!local) blocked.push(request.url);
      // Fulfill every API and third-party request locally, including unexpected
      // submission attempts (which also fail the final assertions).
      const operation = local && !api && request.method === "GET"
        ? call("Fetch.continueRequest", {requestId})
        : call("Fetch.fulfillRequest", {requestId, responseCode: coverage ? 200 : api ? 503 : 200,
          responseHeaders: [{name: "Content-Type", value: api ? "application/json" : "text/plain"}],
          body: Buffer.from(coverage ? JSON.stringify(coverage)
            : api ? '{"error":"synthetic_unavailable"}' : "").toString("base64")});
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
  const warningMainLink = async (selector, expected) => {
    await until(`document.querySelector(${JSON.stringify(selector)})?.hidden === false`);
    const text = await evaluate(`document.querySelector(${JSON.stringify(selector)}).innerText`);
    assert.match(text, expected, caseName + ": wrong warning branch");
    assert.match(text, /Call 805\.409\.9262/, caseName + ": missing Main label in warning");
    assert.doesNotMatch(text, /805[. -](?:953[. -]7273|410[. -]1151)/,
      caseName + ": warning includes a non-Main number");
    await mainLinks(selector);
    assert.deepEqual(await evaluate(`[...document.querySelector(${JSON.stringify(selector)})
      .querySelectorAll('a[href^="tel:"]')].map(a=>({
        text:a.innerText, href:a.getAttribute('href'), resolved:a.href
      }))`), [{text: "Call 805.409.9262", href: "tel:18054099262", resolved: "tel:18054099262"}],
    caseName + ": warning label and actual dial URL must both match Main");
  };
  const checkReply = async (previousCount, expected, hasPhone = true) => {
    await until(`document.querySelectorAll('.elhc-bot').length > ${previousCount} &&
      [...document.querySelectorAll('.elhc-bot')].at(-1).innerText.includes(${JSON.stringify(expected)}) &&
      !document.querySelector('.elhc-send').disabled`);
    const reply = await evaluate(`[...document.querySelectorAll('.elhc-bot')].at(-1).innerText`);
    if (hasPhone) {
      assert.match(reply, /805\.409\.9262/, caseName);
      const dial = await evaluate(`document.querySelector('.elhc-head a[href^="tel:"]').getAttribute('href')`);
      assert.equal(digits(reply.match(/805\.409\.9262/)[0]), digits(dial), caseName);
    }
    assert.doesNotMatch(reply, /805[. -](?:953[. -]7273|410[. -]1151)/, caseName);
    await mainLinks(".elhc-head");
  };
  const ask = async (question, expected, hasPhone = true) => {
    const previousCount = await evaluate("document.querySelectorAll('.elhc-bot').length");
    await evaluate(`(()=>{
      const input=document.querySelector('.elhc-in'); input.value=${JSON.stringify(question)};
      input.dispatchEvent(new Event('input',{bubbles:true}));
      document.querySelector('.elhc-send').click();
    })()`);
    await checkReply(previousCount, expected, hasPhone);
  };
  const chooseCity = async (city, expected, hasPhone = true) => {
    const previousCount = await evaluate("document.querySelectorAll('.elhc-bot').length");
    await evaluate(`(()=>{
      const chips=[...document.querySelectorAll('.elhc-log > .elhc-chips')].at(-1);
      const chip=[...chips.querySelectorAll('button')].find(button=>button.innerText===${JSON.stringify(city)});
      if(!chip || !chip.getClientRects().length) throw new Error('Missing visible city suggestion');
      chip.click();
    })()`);
    await checkReply(previousCount, expected, hasPhone);
    assert.equal(await evaluate(`[...document.querySelectorAll('.elhc-user')].at(-1).innerText`),
      `Do you serve ${city}?`);
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
    const coverageStart = apiRequests.length;
    for (const [city, expected] of [
      ["San Fernando", "Yes—we do serve San Fernando in Los Angeles County."],
      ["San Francisco", "We don’t have a published service page for “San Francisco”"],
    ]) {
      caseName = `${width}px ambiguous coverage before ${city}`;
      // The disambiguation prompt has no phone in its copy; its persistent
      // Main dial link must still be visible and correct.
      await ask("Do you serve San?", "“San” matches several cities", false);
      assert.deepEqual(await evaluate(`(()=>{
        const chips=[...document.querySelectorAll('.elhc-log > .elhc-chips')].at(-1);
        return [...chips.querySelectorAll('button')].map(button=>button.innerText);
      })()`), ["San Fernando", "San Francisco", "San F"]);
      caseName = `${width}px selected ${city} coverage`;
      await chooseCity(city, expected);
    }
    assert.deepEqual(apiRequests.slice(coverageStart), [
      {path: "/api/coverage", method: "GET", city: "San"},
      {path: "/api/coverage", method: "GET", city: "San Fernando"},
      {path: "/api/coverage", method: "GET", city: "San"},
      {path: "/api/coverage", method: "GET", city: "San Francisco"},
    ], "Suggestion transitions must use coverage only, not AI or submissions");
    for (const [city, expected] of [
      ["San Fernando", "Yes—we do serve San Fernando in Los Angeles County."],
      ["San Francisco", "We don’t have a published service page for “San Francisco”"],
    ]) {
      const refinedStart = apiRequests.length;
      caseName = `${width}px initial coverage before narrowing to ${city}`;
      await ask("Do you serve San?", "“San” matches several cities", false);
      caseName = `${width}px selected suggestion still ambiguous before ${city}`;
      await chooseCity("San F", "“San F” matches several cities", false);
      assert.deepEqual(await evaluate(`(()=>{
        const chips=[...document.querySelectorAll('.elhc-log > .elhc-chips')].at(-1);
        return [...chips.querySelectorAll('button')].map(button=>button.innerText);
      })()`), ["San Fernando", "San Francisco"], caseName + ": wrong refined suggestions");
      caseName = `${width}px refined ${city} coverage`;
      await chooseCity(city, expected);
      assert.deepEqual(apiRequests.slice(refinedStart), [
        {path: "/api/coverage", method: "GET", city: "San"},
        {path: "/api/coverage", method: "GET", city: "San F"},
        {path: "/api/coverage", method: "GET", city},
      ], caseName + ": refined suggestions must use coverage only, not AI or submissions");
    }
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
    console.log(`PASS ${width}px: chat routing, direct/refined ambiguous/served/unserved coverage, fallback, three intake displays and reopened reminder`);

    for (const mode of ["access-blocked", "write-blocked"]) {
      caseName = `${width}px ${mode} callback storage warning`;
      // Install before chat.js runs, as in test-intake-browser.mjs. Keep the
      // native methods only for seeding/removing a timestamp, never contact data.
      const {identifier} = await call("Page.addScriptToEvaluateOnNewDocument", {source: `(()=>{
        const storage=sessionStorage, nativeSet=Storage.prototype.setItem;
        window.fixtureStorageWrites=[];
        window.fixtureSeedReminder=()=>nativeSet.call(storage,
          "elhcCallbackUncertainUntil",String(Date.now()+600000));
        window.fixtureClearReminder=()=>storage.removeItem("elhcCallbackUncertainUntil");
        Storage.prototype.setItem=function(key,value){
          if(this===storage){
            fixtureStorageWrites.push(String(key));
            throw new DOMException("Blocked storage (synthetic fixture)","QuotaExceededError");
          }
          return nativeSet.call(this,key,value);
        };
        if(${JSON.stringify(mode)}==="access-blocked")
          Object.defineProperty(window,"sessionStorage",{get(){
            throw new DOMException("Blocked access (synthetic fixture)","SecurityError");
          }});
      })()`});
      try {
        await navigate("/");
        await click(".elhc-launch");
        await until("document.querySelector('.elhc-chip-cb')");
        await click(".elhc-chip-cb");
        await warningMainLink(".elhc-cb-storage-warning",
          /Your browser cannot save the callback reminder/);
        assert.match(await evaluate("document.querySelector('.elhc-cb-storage-warning').innerText"),
          /after a reload or leaving this page/);
        await mainLinks(".elhc-head");

        if (mode === "write-blocked") {
          assert.ok((await evaluate("fixtureStorageWrites"))
            .includes("elhcCallbackUncertainUntilProbe"), "Quota fixture must reject a real storage probe");
          // Seed only the uncertain timestamp, not a submitted request. The real
          // chat renderer must detect failing writes and add its storage warning.
          await click(".elhc-cb-cancel");
          await evaluate("fixtureSeedReminder()");
          await click(".elhc-chip-cb");
          caseName = `${width}px quota-failure uncertain reminder`;
          await warningMainLink(".elhc-cb-reminder", /Your browser could not save this reminder/);
          assert.match(await evaluate("document.querySelector('.elhc-cb-reminder').innerText"),
            /only while this page stays open/);
          // Remove persisted state: the next reminder is backed only by chat's
          // in-memory timestamp while all sessionStorage writes still throw.
          await evaluate(`fixtureClearReminder();
            document.querySelector('.elhc-cb-reminder').remove()`);
          assert.equal(await evaluate("sessionStorage.getItem('elhcCallbackUncertainUntil')"), null);
          await click(".elhc-chip-cb");
          await warningMainLink(".elhc-cb-reminder", /Your browser could not save this reminder/);
          await click(".elhc-x");
          await click(".elhc-launch");
          await warningMainLink(".elhc-cb-reminder", /Reloading or leaving this page will lose this protection/);
        }
        console.log(`PASS ${width}px ${mode}: warning text and dial URL use Main` +
          (mode === "write-blocked" ? "; uncertain/in-memory/reopened reminders also use Main" : ""));
      } finally {
        await call("Page.removeScriptToEvaluateOnNewDocument", {identifier});
      }
    }
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
  assert.deepEqual(apiRequests.filter(request => !["/api/chat", "/api/google-reviews", "/api/coverage"].includes(request.path)), []);
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
