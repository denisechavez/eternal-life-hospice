// Real HTML + chat + shared ES module, plus real Python/PostgreSQL security.
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
let postOriginOverride; // CDP-only negative cases; normal requests remain untouched.
let attackerOrigin;
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
        if (local) {
          if (url.pathname === "/assets/intake-security.js" && fixture.state.moduleFailure)
            return call("Fetch.failRequest", {requestId, errorReason: "Failed"});
          if (request.method === "POST" && url.pathname === "/api/form-submit" &&
              postOriginOverride !== undefined) {
            const headers = Object.entries(request.headers)
              .filter(([name]) => name.toLowerCase() !== "origin")
              .map(([name, value]) => ({name, value}));
            if (postOriginOverride !== null) headers.push({name: "Origin", value: postOriginOverride});
            return call("Fetch.continueRequest", {requestId, headers});
          }
          return call("Fetch.continueRequest", {requestId});
        }
        if (url.origin === attackerOrigin) {
          return call("Fetch.fulfillRequest", {requestId, responseCode: 200,
            responseHeaders: [{name: "Content-Type", value: "text/html"}],
            body: Buffer.from("<!doctype html><title>Synthetic cross-site caller</title>").toString("base64")});
        }
        if (challenge) {
          const fail = await evaluate("intakeFixture.scriptFailure");
          if (fail) return call("Fetch.failRequest", {requestId, errorReason: "Failed"});
        }
        await call("Fetch.fulfillRequest", {requestId, responseCode: 200,
          responseHeaders: [{name: "Content-Type", value: challenge ? "text/javascript" : "text/plain"}],
          body: Buffer.from(challenge ? turnstileFixture : "").toString("base64")});
      })().catch(error => {
        // Navigating between cases can cancel a paused request before CDP's
        // reply arrives. Its interception ID is then gone; it cannot escape
        // interception. Keep every other transport failure fatal.
        if (error.message === '{"code":-32602,"message":"Invalid InterceptionId."}') return;
        transportErrors.push(String(error));
      });
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
  const replace = async (selector, value) => {
    // Initial contact entry uses keyboard input. Negative fixtures exercise the
    // same input listener and native validation with exact synthetic values.
    await evaluate(`(()=>{
      const input=document.querySelector(${JSON.stringify(selector)});
      input.value=${JSON.stringify(value)};
      input.dispatchEvent(new Event('input',{bubbles:true}));
    })()`);
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
  async function assertCallbackReminderAccessibility(selector) {
    const {nodes} = await call("Accessibility.getFullAXTree");
    const {root: {nodeId}} = await call("DOM.getDocument");
    const exposed = async (selector, allowIgnoredContainer = false) => {
      const {nodeId: selected} = await call("DOM.querySelector", {nodeId, selector});
      assert.ok(selected, currentCase + ": missing " + selector);
      const {node: {backendNodeId}} = await call("DOM.describeNode", {nodeId: selected});
      // Generic visual wrappers may be ignored while their text and controls
      // remain exposed. A partial tree retains that wrapper as a traversal root.
      if (allowIgnoredContainer) {
        const partial = await call("Accessibility.getPartialAXTree", {backendNodeId});
        nodes.push(...partial.nodes);
      }
      const node = nodes.find(node => node.backendDOMNodeId === backendNodeId &&
        (allowIgnoredContainer || !node.ignored));
      assert.ok(node, currentCase + ": not exposed in accessibility tree: " + selector);
      return node;
    };
    const properties = node => Object.fromEntries((node.properties || []).map(p => [p.name, p.value.value]));
    // Flat AX responses are not in reading order. Traverse child IDs, stopping
    // at StaticText to avoid counting its inline-text children twice.
    const byId = new Map();
    const readText = node => node.role?.value === "StaticText"
      ? node.name?.value || ""
      : (node.childIds || []).map(id => readText(byId.get(id))).join("");
    const normalize = text => text.replace(/\s+/g, " ").trim();
    const expected = normalize(await evaluate(`document.querySelector(${JSON.stringify(selector)}).textContent`));
    const reminder = await exposed(selector, true);
    for (const node of nodes) byId.set(node.nodeId, node);
    const text = normalize(readText(reminder));
    assert.equal(text, expected, currentCase + ": complete reminder is accessible");
    assert.match(text, /couldn't confirm whether your request was received/);
    assert.match(text, /call our care team to confirm receipt before sending another request/);
    assert.match(text, /expiry does not mean your request failed/);
    assert.match(text, /If the team confirms receipt, no new request is needed/);
    assert.doesNotMatch(text, /request was accepted|confirmation [A-Z0-9-]+|successfully sent|try again/i);
    const announcement = await exposed('.elhc-sr[role="alert"]');
    assert.equal(announcement.role.value, "alert");
    assert.equal(properties(announcement).live, "assertive");
    assert.equal(properties(announcement).atomic, true);
    assert.equal(normalize(readText(announcement)), expected,
      currentCase + ": live announcement includes the full current reminder, not success");
    const phone = await exposed(selector + ' a[href="tel:18059537273"]');
    const recovery = await exposed(selector + " .elhc-cb-confirm-not-received");
    assert.equal(phone.role.value, "link");
    assert.equal(phone.name.value, "Call 805.953.7273");
    assert.equal(recovery.role.value, "button");
    assert.equal(recovery.name.value, "The team confirmed it was not received");
    for (const control of [phone, recovery]) {
      assert.equal(properties(control).focusable, true, control.name.value + ": focusable");
      assert.notEqual(properties(control).disabled, true, control.name.value + ": enabled");
    }
    // Use real Tab events, not .focus() on the recovery button, to prove it
    // remains in keyboard order after the old callback form has been removed.
    await focus(selector + ' a[href="tel:18059537273"]');
    await key("Tab", "Tab", 9);
    await until(`document.activeElement === document.querySelector(${JSON.stringify(selector + " .elhc-cb-confirm-not-received")})`,
      "Tab reaches the confirmed-non-receipt button");
    await key("Tab", "Tab", 9, 8);
    await until(`document.activeElement === document.querySelector(${JSON.stringify(selector + ' a[href="tel:18059537273"]')})`,
      "Shift+Tab returns to the care-team phone link");
    await noCallbackSuccess();
  }
  async function noCallbackSuccess() {
    assert.equal(await evaluate(`[...document.querySelectorAll('.elhc-sr[role="status"],.elhc-msg.elhc-bot')]
      .some(el=>/request was accepted|SYNTHETIC-RECEIPT/.test(el.textContent))`), false,
      currentCase + ": uncertain reminder must not claim success");
  }
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}]});
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});
  await call("Page.addScriptToEvaluateOnNewDocument", {source: fixtureBootstrap});

  const flows = [
    {name: "newsletter", path: "/care-brief.html", form: 'form[name="elh-care-brief-signup"]',
      submit: 'form[name="elh-care-brief-signup"] button[type="submit"]',
      error: ".cbl-signup-error", success: ".cbl-signup-thanks:not([hidden])",
      formName: "elh-care-brief-signup",
      fields: {'[name="first_name"]': "Synthetic Newsletter", '[name="email"]': "newsletter@example.invalid"}},
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
  for (const outcome of ["accepted", "interrupted", "unreadable", "unconfirmed", "server-error", "module-unavailable"])
  for (const mobile of [false, true]) for (const flow of flows) {
    currentCase = `${flow.name} ${mobile ? "mobile/touch" : "desktop/keyboard"} ${outcome}`;
    const {state} = fixture;
    state.security = [];state.posts = [];state.securityFailure = false;state.submitResponse = null;
    state.moduleFailure = outcome === "module-unavailable";
    await call("Emulation.setDeviceMetricsOverride", {width: mobile ? 390 : 1280,
      height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile});
    await call("Emulation.setTouchEmulationEnabled", {enabled: mobile});
    await call("Page.navigate", {url: fixture.origin + flow.path});
    await until("document.readyState === 'complete'");
    // Cases model independent visits, except explicit reopen/reload tests below.
    await evaluate('sessionStorage.removeItem("elhcCallbackUncertainUntil")');
    // A real first-time visitor chooses consent before using content beneath
    // the notification. Exercise that control rather than hiding the overlay.
    if (await evaluate("!!document.getElementById('elh-cc-decl')")) {
      await activate("#elh-cc-decl", mobile);
      await until("!document.getElementById('elh-cc')");
    }
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
    if (outcome === "accepted" && flow.name !== "newsletter") {
      const phone = flow.form + ' input[type="tel"]', email = flow.form + ' input[type="email"]';
      await until(`document.querySelector(${JSON.stringify(phone)}).getAttribute("inputmode")==="tel"`);
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(phone)}).value`), "202.555.0190");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(email)}).getAttribute("inputmode")`), "email");
      // Run exact negative fixtures on desktop. Mobile still exercises actual
      // typed formatting and all subsequent touch submission outcomes.
      if (!mobile) {
      for (const [selector, invalid] of [[phone, "2025550"], [phone, "call2025550190"],
        [phone, "2025550190123456"],
        [email, "synthetic@invalid"]]) {
        const before = state.security.length;
        await replace(selector, invalid);
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(selector)}).checkValidity()`), false,
          currentCase + ": invalid contact accepted: " + invalid + " value=" +
          await evaluate(`document.querySelector(${JSON.stringify(selector)}).value`));
        await activate(flow.submit, mobile);
        await sleep(50);
        assert.equal(state.security.length, before, currentCase + ": invalid contact reached security: " + invalid);
        assert.equal(state.posts.length, 0, currentCase + ": invalid contact POSTed");
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(selector)}).checkValidity()`), false);
        const valid = selector === phone ? "2025550190" : flow.fields[Object.keys(flow.fields).find(k=>k.includes("email"))];
        await replace(selector, valid);
      }
      await replace(phone, "+12025550190");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(phone)}).value`), "+1 202.555.0190");
      await replace(phone, "+442079460123");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(phone)}).value`), "+442079460123");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(phone)}).checkValidity()`), true);
      await replace(phone, "2025550190");
      }
    }
    if (flow.name === "chat") {
      assert.ok(await evaluate(`[...document.querySelectorAll('.elhc-cb input,.elhc-cb textarea')].every(
        input=>document.querySelector('label[for="'+input.id+'"]'))`));
    }
    const expectedFields = flow.name === "chat"
      ? {name: "Synthetic Chat", phone: "202.555.0190", email: "chat@example.invalid",
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
    const failed = async (unknown = false) => {
      if (unknown) await until(`document.querySelector(${JSON.stringify(flow.form)}).__elhSubmissionState === "unknown"`);
      await until(`document.querySelector(${JSON.stringify(flow.error)})?.textContent.length > 0`);
      await until(`document.querySelector(${JSON.stringify(flow.submit)}).disabled === ${unknown}`);
      assert.equal(await evaluate("document.querySelectorAll('[aria-label=\"Spam protection\"]').length"), 0);
      assert.equal(await evaluate("intakeFixture.renders"), await evaluate("intakeFixture.removed"));
      await noSuccess();
      for (const [field, value] of Object.entries(flow.fields)) {
        const actual = await evaluate(`document.querySelector(${JSON.stringify(flow.form + " " + field)}).value`);
        assert.equal(field.includes("phone") ? actual.replace(/\D/g, "") : actual, value);
      }
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).getAttribute("aria-live")==="assertive"`));
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent.includes("805.953.7273")`));
      const visibleError = flow.name === "chat" ? ".elhc-cb-err" : flow.error;
      assert.ok(await evaluate(
        `document.querySelector(${JSON.stringify(visibleError)}).querySelector('a[href="tel:18059537273"]')`));
      if (flow.name === "newsletter") {
        const text = await evaluate(`document.querySelector(${JSON.stringify(visibleError)}).textContent`);
        assert.match(text, /newsletter subscription help/);
        assert.doesNotMatch(text, /care team|help now|speak with someone now|24 hours|7 days|urgent/i);
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(flow.form)}).hidden`), false);
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(visibleError)}).hidden`), false);
      } else {
        assert.ok(await evaluate(
          `document.querySelector(${JSON.stringify(visibleError)}).textContent.includes("We're here for you 24 hours a day, 7 days a week.")`));
      }
    };
    if (outcome === "module-unavailable") {
      await activate(flow.submit, mobile);await failed();
      assert.equal(state.posts.length, 0);
      assert.equal(state.security.length, 0);
      assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent`),
        flow.name === "newsletter" ? /security check.*signup has not been sent/ : /couldn't load the security check.*not been sent/);
      console.log(`PASS ${currentCase}: no POST, preserved fields and clickable phone`);
      continue;
    }
    if (outcome !== "accepted") {
      state.submitResponse = {
        interrupted: {disconnect: true},
        unreadable: {raw: true},
        unconfirmed: {body: {ok: true, accepted: false}},
        "server-error": {status: 500, body: {ok: false, error: "processing_error",
          message: "Please retry (untrusted server copy)"}}
      }[outcome];
      await start();await activate("#fixture-challenge", mobile);await failed(true);
      const text = await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent`);
      assert.match(text, flow.name === "newsletter" ? /couldn't confirm whether your newsletter signup was received/ : /couldn't confirm whether your request was received/);
      assert.match(text, flow.name === "newsletter" ? /avoid a duplicate signup/ : /avoid a duplicate request/);
      assert.doesNotMatch(text, /not been sent|not accepted|try again|Please retry|couldn't send/);
      assert.equal(state.posts.length, 1, currentCase + ": missing synthetic POST");
      const securityCount = state.security.length;
      // Guard both ordinary activation and a programmatic submit event.
      await evaluate(`(()=>{
        const f=document.querySelector(${JSON.stringify(flow.form)});
        const b=document.querySelector(${JSON.stringify(flow.submit)});
        b.click();
        if(f.tagName==='FORM')f.dispatchEvent(new Event('submit',{cancelable:true}));
        else b.dispatchEvent(new Event('click'));
      })()`);
      await sleep(250);
      assert.equal(state.posts.length, 1, currentCase + ": uncertain request was retried");
      assert.equal(state.security.length, securityCount, currentCase + ": uncertain request restarted verification");
      await noSuccess();
      if (flow.name === "chat" && outcome === "interrupted") {
        await assertCallbackReminderAccessibility(".elhc-cb-err");
        const reminderKey = "elhcCallbackUncertainUntil";
        const stored = await evaluate(`sessionStorage.getItem(${JSON.stringify(reminderKey)})`);
        assert.match(stored, /^\d+$/, "Only an expiry timestamp may be stored");
        assert.ok(Number(stored) > Date.now() && Number(stored) <= Date.now() + 1800000);
        // Closing chat, cancelling the form and starting again must not bypass the guard.
        await activate('button[aria-label="Close the support guide"]', mobile);
        await activate(".elhc-launch", mobile);
        await assertCallbackReminderAccessibility(".elhc-cb-err");
        await activate(".elhc-cb-cancel", mobile);
        await activate(".elhc-chip-cb", mobile);
        await until("document.querySelector('.elhc-cb-reminder')");
        await assertCallbackReminderAccessibility(".elhc-cb-reminder");
        assert.equal(await evaluate("document.querySelectorAll('.elhc-cb').length"), 0);
        assert.ok(await evaluate(`document.querySelector('.elhc-cb-reminder a[href="tel:18059537273"]')`));
        assert.match(await evaluate("document.querySelector('.elhc-cb-reminder').textContent"),
          /If the team confirms receipt, no new request is needed/);
        assert.equal(await evaluate(`sessionStorage.getItem(${JSON.stringify(reminderKey)})`), stored,
          "Reopening must not extend reminder lifetime");
        // Same-tab navigation also retains the privacy-safe marker, not the inputs.
        await call("Page.navigate", {url: fixture.origin + "/refer"});
        await until("document.readyState === 'complete' && document.querySelector('.elhc-launch')");
        await activate(".elhc-launch", mobile);
        await until("document.querySelector('.elhc-chip-cb')");
        await activate(".elhc-chip-cb", mobile);
        await until("document.querySelector('.elhc-cb-reminder')");
        await assertCallbackReminderAccessibility(".elhc-cb-reminder");
        assert.equal(await evaluate("document.querySelectorAll('.elhc-cb').length"), 0);
        assert.equal(state.posts.length, 1);
        assert.equal(state.security.length, securityCount);
        assert.doesNotMatch(await evaluate(`JSON.stringify(Object.entries(sessionStorage))`),
          /Synthetic|example.invalid|2025550190|clinical/i);
        // Confirmation unlocks a blank form, not a replay of the old submission.
        await activate(".elhc-cb-confirm-not-received", mobile);
        await until("document.querySelector('.elhc-cb')");
        await until(`document.activeElement === document.querySelector('.elhc-cb input[id$="-name"]')`,
          "Recovery returns keyboard focus to the blank name input");
        await noCallbackSuccess();
        assert.equal(await evaluate(`sessionStorage.getItem(${JSON.stringify(reminderKey)})`), null);
        assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('.elhc-cb input,.elhc-cb textarea')).map(e=>e.value)`),
          ["", "", "", "", ""]);
        assert.equal(state.posts.length, 1);
        assert.equal(state.security.length, securityCount);
        // Expired, malformed and excessive future markers must not lock out care.
        for (const marker of [String(Date.now() - 1), "invalid", String(Date.now() + 3600000)]) {
          await activate(".elhc-cb-cancel", mobile);
          await evaluate(`sessionStorage.setItem(${JSON.stringify(reminderKey)},${JSON.stringify(marker)})`);
          await activate(".elhc-chip-cb", mobile);
          await until("document.querySelector('.elhc-cb')");
          assert.equal(await evaluate(`sessionStorage.getItem(${JSON.stringify(reminderKey)})`), null);
        }
        // Blocked storage falls back to memory, even after the failed form is removed.
        await evaluate(`window.fixtureSetItem=Storage.prototype.setItem;
          Storage.prototype.setItem=function(){throw new Error("Storage blocked (fixture)")}`);
        for (const [selector, value] of Object.entries(flow.fields)) await fill(flow.form + " " + selector, value);
        await start();await activate("#fixture-challenge", mobile);await failed(true);
        await activate(".elhc-cb-cancel", mobile);
        await activate(".elhc-chip-cb", mobile);
        await until("document.querySelectorAll('.elhc-cb-reminder').length === 1");
        await assertCallbackReminderAccessibility(".elhc-cb-reminder");
        assert.equal(await evaluate("document.querySelectorAll('.elhc-cb').length"), 0);
        assert.equal(state.posts.length, 2);
        await evaluate("Storage.prototype.setItem=window.fixtureSetItem");
        await activate(".elhc-cb-confirm-not-received", mobile);
        console.log(`PASS ${currentCase}: accessible reminder/alert/names, keyboard recovery, reopen/navigation,
  timestamp-only storage, confirmation, expiry and blocked storage`);
      }
      console.log(`PASS ${currentCase}: unknown delivery, preserved fields, clickable phone and no retry`);
      continue;
    }
    // A script load failure must not POST and must allow loading the script again on retry.
    await evaluate("intakeFixture.scriptFailure=true");
    await activate(flow.submit, mobile);await failed();
    assert.equal(state.posts.length, 0);
    assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent`),
      /security check.*not been sent/);
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
    // Explicit rejections preserve fields and allow a fresh verified attempt.
    for (const response of [
      {status: 403, body: {ok: false, accepted: false}},
      {status: 429, body: {ok: false, accepted: false}},
      {status: 503, body: {ok: false, accepted: false}},
      {status: 503, body: {ok: false, error: "security_unavailable"}}
    ]) {
      state.submitResponse = response;
      await evaluate('intakeFixture.challenge="success"');
      await start();await activate("#fixture-challenge", mobile);await failed();
      assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).textContent`),
        flow.name === "newsletter" ? /newsletter signup was not accepted/ : /request was not accepted/);
    }
    state.submitResponse = null;state.hold = true;
    await start();
    const before = state.posts.length;
    // The disabled submit cannot create a second challenge or request.
    await evaluate(`(()=>{
      document.querySelector(${JSON.stringify(flow.submit)}).click();
      const form=document.querySelector(${JSON.stringify(flow.form)});
      if(form.tagName==='FORM')form.dispatchEvent(new Event('submit',{cancelable:true}));
    })()`);
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
    if (flow.name === "chat") {
      // A slow response cannot be bypassed by opening another callback form.
      await activate('button[aria-label="Close the support guide"]', mobile);
      await activate(".elhc-launch", mobile);
      await activate(".elhc-chip-cb", mobile);
      assert.equal(await evaluate("document.querySelectorAll('.elhc-cb').length"), 1);
      assert.ok(await evaluate(`document.querySelector('.elhc-log').textContent.includes("still being checked")`));
      assert.equal(state.posts.length, before + 1);
      // Missing receipt email is still accepted intake, never uncertain delivery.
      state.submitResponse = {body: {ok: true, accepted: true, receipt_id: "SYNTHETIC-RECEIPT",
        acknowledgement_sent: false,
        care_cta_html: `<p>Need to speak with someone now?</p><p>We're here for you 24 hours a day, 7 days a week.</p><p><a href="tel:18059537273">Call 805.953.7273</a></p>`}};
    }
    state.held();state.held = null;state.hold = false;
    await until(success);
    if (flow.name === "chat") {
      assert.equal(await evaluate('sessionStorage.getItem("elhcCallbackUncertainUntil")'), null);
      assert.equal(await evaluate("document.querySelectorAll('.elhc-cb-reminder').length"), 0);
    }
    assert.equal(state.posts.length, before + 1);
    const post = state.posts.at(-1), security = state.security.at(-1);
    for (const [field, value] of Object.entries(expectedFields)) assert.equal(post.fields[field], value, field);
    assert.equal(post.fields["form-name"], flow.formName);
    assert.equal(security.form, flow.formName);
    assert.equal(post.fields._elh_security, security.token);
    assert.equal(post.fields["cf-turnstile-response"], "synthetic-provider-token");
    assert.equal(new Set(state.posts.map(post => post.fields._elh_security)).size, state.posts.length,
      "Each retry must request a fresh security token");
    if (flow.name !== "newsletter")
      assert.equal(post.fields.phone.replace(/\D/g, ""), "2025550190", "Out-of-area numbers must be preserved");
    assert.ok(post.at - security.at >= 140, "Shared minimum-age wait was skipped");
    assert.match(post.headers["content-type"], /application\/x-www-form-urlencoded/);
    assert.equal(await evaluate("document.querySelectorAll('[aria-label=\"Spam protection\"]').length"), 0);
    assert.ok(state.assets.includes("/assets/intake-security.js"), "Real shared module was not loaded");
    if (flow.name === "newsletter") {
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.form)}).hidden`));
      assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.success)}).textContent`),
        /Thank you.*you’re on the list.*next issue of The Eternal Care Brief/s);
      assert.ok(await evaluate(`document.querySelector(${JSON.stringify(flow.error)}).hidden`));
      const count = state.posts.length, securityCount = state.security.length;
      await evaluate(`document.querySelector(${JSON.stringify(flow.form)}).dispatchEvent(new Event('submit',{cancelable:true}))`);
      await sleep(250);
      assert.equal(state.posts.length, count, "Accepted newsletter signup retried");
      assert.equal(state.security.length, securityCount, "Accepted newsletter signup restarted verification");
    } else {
    assert.ok(await evaluate(`document.body.innerText.includes("SYNTHETIC-RECEIPT")`));
    assert.ok(await evaluate(`document.body.innerText.includes("Need to speak with someone now?")`));
    assert.ok(await evaluate(`document.body.innerText.includes("We're here for you 24 hours a day, 7 days a week.")`));
    assert.ok(await evaluate(`Array.from(document.querySelectorAll('a[href="tel:18059537273"]')).some(a=>a.textContent==="Call 805.953.7273")`));
    }
    console.log(`PASS ${currentCase}: validation, interactive challenge, load/error/expiry/timeout,
  security and delivery failures, preserved fields, retry, guarded confirmation`);
  }
  currentCase = "request category choices";
  await call("Page.navigate", {url: fixture.origin + "/"});
  await until("document.readyState === 'complete' && document.querySelector('#founderConnect option[value=\"aleksandra-meeting\"]')");
  const requestIds = ["share-voice", "be-featured", "education-session", "speaking-engagement",
    "general-meeting", "all-interests", "aleksandra-meeting"];
  for (const selector of ["#founderConnect", '.lead-form[data-form="voice"] select[name="interest"]']) {
    assert.deepEqual(await evaluate(`Array.from(document.querySelector(${JSON.stringify(selector)}).options).slice(1).map(o=>o.value)`), requestIds);
  }
  for (const category of requestIds) {
    await evaluate(`document.querySelector('#founderConnect').value=${JSON.stringify(category)};document.querySelector('#founderConnectGo').click()`);
    assert.equal(await evaluate(`document.querySelector('.lead-form[data-form="voice"] select[name="interest"]').value`), category);
  }
  console.log("PASS all seven request choices: unchanged order, stable IDs and founder-to-form selection");

  // Unlike UI failure injection above, every request below traverses the real
  // devserver handler, signed-token verifier and disposable PostgreSQL schema.
  attackerOrigin = fixture.origin.replace("127.0.0.1", "localhost");
  const realState = () => fixture.backendState();
  const browserFetch = (path, options = {}) => evaluate(`(async()=>{
    const response=await fetch(${JSON.stringify(path)},${JSON.stringify(options)});
    return {status:response.status, body:await response.json()};
  })()`);
  const postOptions = fields => ({method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: new URLSearchParams(fields).toString()});
  for (const mobile of [false, true]) {
    currentCase = `real security ${mobile ? "mobile" : "desktop"}`;
    await fixture.useRealSecurity();
    await call("Emulation.setDeviceMetricsOverride", {width: mobile ? 390 : 1280,
      height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile});
    await call("Emulation.setTouchEmulationEnabled", {enabled: mobile});
    await call("Page.navigate", {url: fixture.origin + "/"});
    await until("document.readyState === 'complete'");
    // This section tests the shared module + real server, not page placement
    // (covered by all six UI flows above). Keep its synthetic widget visible
    // without editing or hiding the site's mobile phone/consent overlays.
    await evaluate(`{
      const host=document.createElement("section");host.id="real-security-fixture";
      host.setAttribute("aria-label","Real security test harness");
      host.style.cssText="position:fixed;top:100px;left:20px;width:280px;z-index:2147483647;background:white";
      document.body.appendChild(host);
    }`);
    const baseline = await realState();
    const fields = {"form-name": "elh-family", first_name: "Synthetic", last_name: "Security",
      phone: mobile ? "2025550182" : "2025550181", email: "security@example.invalid"};
    const challenge = await browserFetch("/api/form-security?form=elh-family");
    assert.equal(challenge.status, 200, currentCase + ": default browser GET");
    assert.equal(challenge.body.siteKey, "synthetic-site-key");
    assert.equal(challenge.body.waitMs, 1800, "Do not shorten the real minimum age");
    assert.match(challenge.body.token, /^[\w-]+\.[a-f0-9]{64}$/);
    const get = fixture.state.realRequests.at(-1);
    assert.equal(get.headers.origin, undefined, "Default GET must omit Origin");
    assert.equal(get.headers["sec-fetch-site"], "same-origin");
    assert.ok(get.headers.referer.startsWith(fixture.origin));
    const privateGet = await browserFetch("/api/form-security?form=elh-family",
      {referrerPolicy: "no-referrer"});
    assert.equal(privateGet.status, 200, "Same-origin GET without Referer");
    assert.equal(fixture.state.realRequests.at(-1).headers.referer, undefined);

    for (const origin of [null, "null", "https://other.invalid"]) {
      postOriginOverride = origin;
      try {
        const denied = await browserFetch("/api/form-submit",
          postOptions({...fields, _elh_security: challenge.body.token,
            "cf-turnstile-response": "synthetic-provider-token"}));
        assert.equal(denied.status, 403);
        assert.equal(denied.body.error, "invalid_origin");
        const post = fixture.state.realRequests.at(-1);
        assert.equal(post.headers["sec-fetch-site"], "same-origin");
        assert.equal(post.headers.origin, origin === null ? undefined : origin);
      } finally {postOriginOverride = undefined;}
    }
    const missingToken = await browserFetch("/api/form-submit", postOptions(fields));
    assert.equal(missingToken.status, 403);
    assert.equal(missingToken.body.error, "verification_required");
    const missingProvider = await browserFetch("/api/form-submit",
      postOptions({...fields, _elh_security: challenge.body.token}));
    assert.equal(missingProvider.status, 403);
    assert.ok(["verification_invalid", "bot_verification_required"].includes(missingProvider.body.error));
    assert.deepEqual(await realState(), baseline, "Rejected POST must not reserve or deliver");

    // Finish token denials on this backend before creating independent form
    // clients. More form types must never exhaust the production POST budget.
    await sleep(challenge.body.waitMs + 100);
    const noProvider = await browserFetch("/api/form-submit",
      postOptions({...fields, _elh_security: challenge.body.token}));
    assert.equal(noProvider.status, 403);
    assert.equal(noProvider.body.error, "bot_verification_required", "Aged token still requires CAPTCHA");
    const crossForm = await browserFetch("/api/form-submit", postOptions({...fields,
      "form-name": "elh-physician", referrer_name: "Synthetic Provider",
      _elh_security: challenge.body.token, "cf-turnstile-response": "synthetic-provider-token"}));
    assert.equal(crossForm.status, 403);
    assert.equal(crossForm.body.error, "verification_invalid");
    assert.deepEqual(await realState(), baseline, "Invalid tokens must not reserve or deliver");

    // Each real shared-module submission/replay pair gets fresh backend state,
    // retaining unmodified GET headers, provider checks and minimum token age.
    for (const [index, flow] of flows.entries()) {
      await fixture.useRealSecurity();
      const uniqueFields = {...fields, "form-name": flow.formName,
        name: "Synthetic Chat", referrer_name: "Synthetic Provider",
        phone: `20255501${(mobile ? 40 : 30) + index}`,
        email: `security-${mobile}-${index}@example.invalid`};
      const before = await realState();
      const requestOffset = fixture.state.realRequests.length;
      await evaluate(`intakeFixture.realBackend=true;
        window.realSubmission=null;window.realSubmissionError=null;
        void import("/assets/intake-security.js").then(module=>module.submit(
          ${JSON.stringify(postOptions(uniqueFields))}, document.querySelector("#real-security-fixture")))
        .then(async response=>{window.realSubmission={status:response.status,body:await response.json()}})
        .catch(error=>{window.realSubmissionError=String(error)});`);
      await until("document.querySelector('#fixture-challenge') || realSubmissionError");
      assert.equal(await evaluate("realSubmissionError"), null);
      await activate("#fixture-challenge", mobile);
      await until("realSubmission || realSubmissionError");
      assert.equal(await evaluate("realSubmissionError"), null);
      const accepted = await evaluate("realSubmission");
      assert.equal(accepted.status, 200, JSON.stringify(accepted));
      assert.equal(accepted.body.accepted, true);
      assert.ok(accepted.body.receipt_id);
      const requests = fixture.state.realRequests.slice(requestOffset);
      assert.equal(requests.length, 2);
      assert.equal(requests[0].headers.origin, undefined);
      assert.equal(requests[0].headers["sec-fetch-site"], "same-origin");
      assert.equal(requests[1].headers.origin, fixture.origin);
      assert.equal(requests[1].headers["sec-fetch-site"], "same-origin");
      assert.ok(requests[1].at - requests[0].at >= 1800, "Real token minimum age skipped");
      const after = await realState();
      assert.equal(after.mail, before.mail + 2, "Synthetic internal email and acknowledgment");
      assert.equal(after.provider, before.provider + 1, "Server must verify provider token");
      assert.ok(after.guard_rows > before.guard_rows, "Real reservation must be persisted");
      assert.equal(after.blocked_network, 0);
      const replay = await browserFetch("/api/form-submit", postOptions(requests[1].fields));
      assert.equal(replay.status, 403);
      assert.equal(replay.body.error, "verification_reused");
      assert.equal((await realState()).mail, after.mail, "Replay must not send mail");
    }
    // A genuine second browser origin generates cross-site Fetch Metadata.
    // Its document alone is fulfilled locally; security requests are not mocked.
    const beforeCrossSite = await realState();
    await call("Page.navigate", {url: attackerOrigin + "/synthetic-attacker"});
    await until(`location.origin === ${JSON.stringify(attackerOrigin)} && document.readyState === "complete"`);
    for (const method of ["GET", "POST"]) {
      const offset = fixture.state.realRequests.length;
      await evaluate(`fetch(${JSON.stringify(fixture.origin + (method === "GET"
        ? "/api/form-security?form=elh-family" : "/api/form-submit"))},
        ${JSON.stringify({mode: "no-cors", ...(method === "POST" ? postOptions(fields) : {})})})
        .then(()=>true)`);
      const denied = fixture.state.realRequests[offset];
      assert.ok(denied, "Cross-site request must reach the real handler");
      assert.equal(denied.headers["sec-fetch-site"], "cross-site");
      assert.equal(denied.headers.origin, method === "GET" ? undefined : attackerOrigin);
      assert.equal(denied.status, 403);
      assert.equal(denied.result.error, "invalid_origin");
      assert.equal(denied.result.token, undefined, "Cross-site GET must not disclose tokens");
    }
    assert.deepEqual(await realState(), beforeCrossSite, "Cross-site requests must not touch guard or mail");
    console.log(`PASS ${currentCase}: default/no-referrer GET, strict POST, ${flows.length} protected forms,
  real signed tokens and database reservations, replay rejection, cross-site GET/POST denial`);
  }
  assert.deepEqual(fixture.state.violations, [], "Unexpected local transport");
  assert.deepEqual(transportErrors, [], "Request interception failed");
  assert.deepEqual(browserErrors, [], "Uncaught browser exceptions");
  console.log("PASS all rendered intake outcomes on desktop and mobile; no external request or real lead transport");
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
