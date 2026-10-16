// Real HTML + chat + shared ES module, synthetic transports only.
// Run with Node 20: node --experimental-websocket website/test-intake-browser.mjs
// Requires Chromium on PATH (or CHROMIUM_BIN). No npm/browser downloads needed.
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {startIntakeFixture, fixtureBootstrap, turnstileFixture} from "./intake-browser-fixture.mjs";

assert.notEqual(process.env.REPLIT_DEPLOYMENT, "1", "Never run browser fixtures in production");
assert.equal(typeof WebSocket, "function", "Node 20 needs --experimental-websocket");
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const directory = await mkdtemp(join(tmpdir(), "elh-intake-browser-"));
let fixture, browser, ws;
const pending = new Map();
const browserErrors = [], transportErrors = [];
let id = 0, currentCase = "startup";
try {
  fixture = await startIntakeFixture();
  browser = spawn(process.env.CHROMIUM_BIN || "chromium", ["--headless", "--no-sandbox",
    "--disable-dev-shm-usage", "--disable-background-networking", "--no-first-run",
    "--remote-debugging-port=0", `--user-data-dir=${directory}`, "about:blank"], {stdio: ["ignore", "ignore", "pipe"]});
  let browserLog = "";
  browser.stderr.on("data", chunk => {browserLog = (browserLog + chunk).slice(-4000);});
  let spawnError;
  browser.on("error", error => {spawnError = error;});
  let port;
  for (let i = 0; i < 300; i++) {
    if (spawnError) throw spawnError;
    try {port = Number((await readFile(join(directory, "DevToolsActivePort"), "utf8")).split("\n")[0]);break;}
    catch {await sleep(50);}
  }
  assert.ok(port, "Chromium did not expose its debugging port\n" + browserLog);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, {once: true});
    ws.addEventListener("error", reject, {once: true});
  });
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    const timer = setTimeout(() => {pending.delete(key);reject(new Error("CDP timeout: " + method));}, 10000);
    pending.set(key, {resolve, reject, timer});
    ws.send(JSON.stringify({id: key, method, params}));
  });
  ws.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    const handler = pending.get(message.id);
    if (handler) {
      clearTimeout(handler.timer);pending.delete(message.id);
      if (message.error) handler.reject(new Error(JSON.stringify(message.error)));
      else handler.resolve(message.result);
    }
    if (message.method === "Runtime.exceptionThrown") browserErrors.push(message.params.exceptionDetails);
    if (message.method === "Fetch.requestPaused") {
      const {requestId, request} = message.params;
      const url = new URL(request.url);
      // Fail closed: no external request ever reaches Cloudflare, analytics, AI or email.
      const local = url.origin === fixture.origin;
      const challenge = url.origin === "https://challenges.cloudflare.com" &&
        url.pathname === "/turnstile/v0/api.js";
      (async () => {
        if (local) return call("Fetch.continueRequest", {requestId});
        if (challenge) {
          const fail = await evaluate("intakeFixture.scriptFailure");
          if (fail) return call("Fetch.failRequest", {requestId, errorReason: "Failed"});
        }
        await call("Fetch.fulfillRequest", {requestId, responseCode: 200,
          responseHeaders: [{name: "Content-Type", value: challenge ? "text/javascript" : "text/plain"}],
          body: Buffer.from(challenge ? turnstileFixture : "").toString("base64")});
      })().catch(error => transportErrors.push(String(error)));
    }
  });
  const evaluate = async expression => {
    const result = await call("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async (expression, label = expression) => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await sleep(40);
    }
    throw new Error(`${currentCase}: timed out: ${label}\n${await evaluate(`JSON.stringify({
      fixture:intakeFixture,active:document.activeElement?.outerHTML.slice(0,500),
      forms:[...document.querySelectorAll('form')].map(f=>({name:f.name,state:f.__elhSubmissionState,
        invalid:[...f.querySelectorAll(':invalid')].map(e=>({name:e.name,value:e.value,message:e.validationMessage}))})),
      protection:document.querySelector('[aria-label="Spam protection"]')?.outerHTML
    })`)}\nsecurity=${fixture.state.security.length} posts=${fixture.state.posts.length}
    browser=${JSON.stringify(browserErrors)} transports=${JSON.stringify(transportErrors)}`);
  };
  const key = async (key, code, virtual, modifiers = 0) => {
    await call("Input.dispatchKeyEvent", {type: "keyDown", key, code, windowsVirtualKeyCode: virtual,
      modifiers, ...(key === "Enter" ? {text: "\r", unmodifiedText: "\r"} : {})});
    await call("Input.dispatchKeyEvent", {type: "keyUp", key, code, windowsVirtualKeyCode: virtual, modifiers});
  };
  const focus = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).focus()`);
  const fill = async (selector, value) => {
    await focus(selector);
    await call("Input.insertText", {text: value});
  };
  async function activate(selector, mobile) {
    if (!mobile) {await focus(selector);await key("Enter", "Enter", 13);return;}
    const point = await evaluate(`(()=>{
      const el=document.querySelector(${JSON.stringify(selector)});
      el.scrollIntoView({block:"center",behavior:"instant"});const r=el.getBoundingClientRect();
      const target=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      if(!el.contains(target))throw new Error("Tap obstructed by "+target?.outerHTML.slice(0,400));
      return {x:r.x+r.width/2,y:r.y+r.height/2};
    })()`);
    await call("Input.dispatchTouchEvent", {type: "touchStart", touchPoints: [point]});
    await call("Input.dispatchTouchEvent", {type: "touchEnd", touchPoints: []});
  }
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  await call("Page.addScriptToEvaluateOnNewDocument", {source: fixtureBootstrap});

  const flows = [
    {name: "family", path: "/", form: 'form[name="elh-family"]', submit: '[data-submit="family"]',
      error: ".lead-submit-error", success: "#leadSuccess.show", formName: "elh-family",
      fields: {'[name="first_name"]': "Synthetic", '[name="last_name"]': "Family",
        '[name="phone"]': "2025550190", '[name="email"]': "family@example.invalid",
        '[name="message"]': "Synthetic callback only"}},
    {name: "provider", path: "/refer", form: "#referForm", submit: "#referForm .af-submit",
      error: ".apply-error", success: ".apply-success", formName: "elh-physician",
      fields: {'[name="referrer_name"]': "Synthetic Provider", '[name="phone"]': "2025550190",
        '[name="email"]': "provider@example.invalid", '[name="situation"]': "Synthetic referral only"}},
    {name: "chat", path: "/", form: ".elhc-cb", submit: ".elhc-cb-submit",
      error: '.elhc-sr[role="alert"]', success: '.elhc-sr[role="status"]', formName: "elh-chat-callback",
      fields: {'input[id$="-name"]': "Synthetic Chat", 'input[id$="-phone"]': "2025550190",
        'input[id$="-email"]': "chat@example.invalid", 'textarea': "Synthetic chat only"}}
  ];
  for (const mobile of [false, true]) for (const flow of flows) {
    currentCase = `${flow.name} ${mobile ? "mobile/touch" : "desktop/keyboard"}`;
    const {state} = fixture;
    state.security = [];state.posts = [];state.securityFailure = false;state.submitResponse = null;
    await call("Emulation.setDeviceMetricsOverride", {width: mobile ? 390 : 1280,
      height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile});
    await call("Emulation.setTouchEmulationEnabled", {enabled: mobile});
    await call("Page.navigate", {url: fixture.origin + flow.path});
    await until("document.readyState === 'complete'");
    if (flow.name === "chat") {
      await until("document.querySelector('.elhc-launch')");
      await activate(".elhc-launch", mobile);
      await until("document.querySelector('.elhc-panel.open')");
      await until("document.querySelector('.elhc-chip-cb')");
      await activate(".elhc-chip-cb", mobile);
    }
    await until(`document.querySelector(${JSON.stringify(flow.form)})`);
    // Native validation for real forms; chat's custom validation must focus the missing name.
    await activate(flow.submit, mobile);
    await sleep(100);
    assert.equal(state.security.length, 0, currentCase + ": invalid form requested security");
    if (flow.name === "chat") {
      assert.ok(await evaluate(`document.activeElement.id.endsWith("-name")`));
      await until(`document.querySelector(${JSON.stringify(flow.error)})?.textContent.includes("name")`);
    }
    for (const [field, value] of Object.entries(flow.fields)) await fill(flow.form + " " + field, value);
    if (flow.name === "provider") await evaluate(`document.querySelector('#rf-county').value="Ventura County"`);
    if (flow.name === "chat") {
      assert.ok(await evaluate(`[...document.querySelectorAll('.elhc-cb input,.elhc-cb textarea')].every(
        input=>document.querySelector('label[for="'+input.id+'"]'))`));
    }
    const expectedFields = flow.name === "chat"
      ? {name: "Synthetic Chat", phone: "2025550190", email: "chat@example.invalid",
        message: "Synthetic chat only", source: "chat", preferred_time: "", "bot-field": "",
        "form-name": flow.formName}
      : await evaluate(`Object.fromEntries(new FormData(document.querySelector(${JSON.stringify(flow.form)})))`);
    const success = flow.name === "chat"
      ? `[...document.querySelectorAll(${JSON.stringify(flow.success)})].some(el=>el.textContent.includes("accepted")) &&
         [...document.querySelectorAll('.elhc-msg.elhc-bot')].some(el=>el.textContent.includes("SYNTHETIC-RECEIPT"))`
      : `document.querySelector(${JSON.stringify(flow.success)})`;
    const noSuccess = async () => assert.equal(await evaluate(`Boolean(${success})`), false, currentCase);
    const start = async () => {
      await activate(flow.submit, mobile);
      await until("document.querySelector('#fixture-challenge')");
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.submit)}).disabled`));
      await noSuccess();
    };
    const failed = async () => {
      await until(`document.querySelector(${JSON.stringify(flow.error)})?.textContent.length > 0`);
      await until(`!document.querySelector(${JSON.stringify(flow.submit)}).disabled`);
      assert.equal(await evaluate("document.querySelectorAll('[aria-label=\"Spam protection\"]').length"), 0);
      assert.equal(await evaluate("intakeFixture.renders"), await evaluate("intakeFixture.removed"));
      await noSuccess();
      for (const [field, value] of Object.entries(flow.fields)) {
        const actual = await evaluate(`document.querySelector(${JSON.stringify(flow.form + " " + field)}).value`);
        assert.equal(field.includes("phone") ? actual.replace(/\D/g, "") : actual, value);
      }
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).getAttribute("aria-live")==="assertive"`));
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent.includes("805.953.7273")`));
      if (flow.name !== "chat") assert.ok(await evaluate(
        `document.querySelector(${JSON.stringify(flow.error)}).querySelector('a[href="tel:18059537273"]')`));
    };
    // A script load failure must not POST and must allow loading the script again on retry.
    await evaluate("intakeFixture.scriptFailure=true");
    await activate(flow.submit, mobile);await failed();
    assert.equal(state.posts.length, 0);
    await evaluate("intakeFixture.scriptFailure=false");
    for (const mode of ["error", "expired", "timeout"]) {
      await evaluate(`intakeFixture.challenge=${JSON.stringify(mode)}`);
      await start();
      const before = state.posts.length;
      if (mode !== "timeout") await activate("#fixture-challenge", mobile);
      await failed();
      assert.equal(state.posts.length, before, currentCase + ": failed challenge POSTed");
    }
    state.securityFailure = true;
    await activate(flow.submit, mobile);await failed();
    assert.equal(state.posts.length, 0, "Security service failure must not POST");
    state.securityFailure = false;
    // Transport failures and even HTTP 200 without explicit acceptance cannot show success.
    for (const response of [
      {status: 403, body: {ok: false, accepted: false}},
      {status: 429, body: {ok: false, accepted: false}},
      {status: 503, body: {ok: false, accepted: false}},
      {body: {ok: true, accepted: false}}, {raw: true}
    ]) {
      state.submitResponse = response;
      await evaluate('intakeFixture.challenge="success"');
      await start();await activate("#fixture-challenge", mobile);await failed();
    }
    state.submitResponse = null;state.hold = true;
    await start();
    const before = state.posts.length;
    // The disabled submit cannot create a second challenge or request.
    await evaluate(`document.querySelector(${JSON.stringify(flow.submit)}).click()`);
    assert.equal(await evaluate("intakeFixture.renders-intakeFixture.removed"), 1);
    assert.equal(state.posts.length, before, "POST before interactive verification");
    await focus("#fixture-challenge");
    await key("Tab", "Tab", 9);
    assert.notEqual(await evaluate("document.activeElement.id"), "fixture-challenge", "Keyboard focus trapped");
    await key("Tab", "Tab", 9, 8); // Shift+Tab must return to the interactive challenge.
    assert.equal(await evaluate("document.activeElement.id"), "fixture-challenge");
    const bounds = await evaluate(`(()=>{
      const el=document.querySelector('#fixture-challenge');el.scrollIntoView({block:"center",behavior:"instant"});
      const r=el.getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth};
    })()`);
    assert.ok(bounds.left >= 0 && bounds.right <= bounds.width, JSON.stringify(bounds));
    await activate("#fixture-challenge", mobile);
    for (let i = 0; !state.held && i < 100; i++) await sleep(20);
    assert.ok(state.held, "Submission did not reach isolated fixture");
    await noSuccess();
    assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.submit)}).disabled`));
    state.held();state.held = null;state.hold = false;
    await until(success);
    assert.equal(state.posts.length, before + 1);
    const post = state.posts.at(-1), security = state.security.at(-1);
    for (const [field, value] of Object.entries(expectedFields)) assert.equal(post.fields[field], value, field);
    assert.equal(post.fields["form-name"], flow.formName);
    assert.equal(security.form, flow.formName);
    assert.equal(post.fields._elh_security, security.token);
    assert.equal(post.fields["cf-turnstile-response"], "synthetic-provider-token");
    assert.equal(new Set(state.posts.map(post => post.fields._elh_security)).size, state.posts.length,
      "Each retry must request a fresh security token");
    assert.equal(post.fields.phone.replace(/\D/g, ""), "2025550190", "Out-of-area numbers must be preserved");
    assert.ok(post.at - security.at >= 140, "Shared minimum-age wait was skipped");
    assert.match(post.headers["content-type"], /application\/x-www-form-urlencoded/);
    assert.equal(await evaluate("document.querySelectorAll('[aria-label=\"Spam protection\"]').length"), 0);
    assert.ok(state.assets.includes("/assets/intake-security.js"), "Real shared module was not loaded");
    if (flow.name !== "family") assert.ok(await evaluate(`document.body.innerText.includes("SYNTHETIC-RECEIPT")`));
    console.log(`PASS ${currentCase}: validation, interactive challenge, load/error/expiry/timeout,
  security and delivery failures, preserved fields, retry, guarded confirmation`);
  }
  assert.deepEqual(fixture.state.violations, [], "Unexpected local transport");
  assert.deepEqual(transportErrors, [], "Request interception failed");
  assert.deepEqual(browserErrors, [], "Uncaught browser exceptions");
  console.log("PASS all six rendered intake flows; no external request or real lead transport");
} catch (error) {
  console.error(`FAIL ${currentCase}`, error);
  process.exitCode = 1;
} finally {
  for (const handler of pending.values()) clearTimeout(handler.timer);
  ws?.close();
  if (browser && browser.exitCode === null && browser.pid) {
    browser.kill();
    await new Promise(resolve => browser.once("exit", resolve));
  }
  await fixture?.close();
  await rm(directory, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
}
