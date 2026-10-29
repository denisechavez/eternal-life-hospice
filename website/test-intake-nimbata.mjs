// Invoked by test-intake-browser.mjs (or its --nimbata-only mode).
// Uses the real rendered forms and security module, never a production backend.
import assert from "node:assert/strict";
import {nimbataFixtureURL} from "./intake-browser-fixture.mjs";

export async function runNimbataRegression({
  fixture, flows, call, evaluate, until, activate, fill, focus, sleep, setCase
}) {
  const {state} = fixture;
  assert.equal(state.realSecurity, false, "Nimbata UI matrix must use synthetic intake only");
  for (const mode of ["throws", "blocked", "timeout"])
  for (const consent of ["essential", "all"])
  for (const mobile of [false, true])
  for (const flow of flows.filter(f => ["family", "provider"].includes(f.name)))
  for (const outcome of ["accepted", "rejected", "unconfirmed"]) {
    const label = `Nimbata ${mode}, ${consent}, ${flow.name}, ${mobile ? "touch" : "keyboard"}, ${outcome}`;
    const tracker = {mode, requests: 0, exceptions: 0, held: [], external: [], unexpectedExceptions: [], documents: []};
    // Remove the previous visit's consent BEFORE loading analytics again.
    await call("Storage.clearDataForOrigin", {origin: fixture.origin, storageTypes: "local_storage"});
    if (await evaluate("location.origin") === fixture.origin)
      await evaluate("sessionStorage.clear()");
    // CDP navigation to the identical query/fragment can be same-document.
    // Leave the page first so accepted-form state never leaks into the next case.
    await call("Page.navigate", {url: "about:blank"});
    await until("location.href === 'about:blank' && document.readyState === 'complete'");
    setCase(label, tracker);
    state.security = [];state.posts = [];state.securityFailure = false;
    state.moduleFailure = false;state.historyCacheable = false;
    state.hold = true;state.held = null;state.submitResponse = null;
    await call("Emulation.setDeviceMetricsOverride", {width: mobile ? 390 : 1280,
      height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile});
    await call("Emulation.setTouchEmulationEnabled", {enabled: mobile});
    // Query/fragment can contain sensitive input; neither belongs in Ads data.
    await call("Page.navigate", {url: fixture.origin + flow.path + "?private=entered-secret#entered-fragment"});
    await until("document.readyState === 'complete' && document.querySelector('#elh-cc-decl')");
    await activate(consent === "all" ? "#elh-cc-okbtn" : "#elh-cc-decl", mobile);
    await until("!document.querySelector('#elh-cc')");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), consent, label);
    if (consent === "all") {
      await until("window.__elhAnalyticsBooted");
      for (let i = 0; i < 100 && !tracker.requests; i++) await sleep(40);
      assert.equal(tracker.requests, 1, label + ": actual injected SDK was intercepted");
      if (mode === "throws") {
        await until("intakeFixture.nimbataExecuted === true");
        for (let i = 0; i < 100 && !tracker.exceptions; i++) await sleep(40);
        assert.equal(tracker.exceptions, 1, label + ": SDK executed and threw; unexpected=" +
          JSON.stringify(tracker.unexpectedExceptions));
      }
    }
    const ads = () => evaluate(`(window.dataLayer || []).map(args=>Array.from(args))
      .filter(args=>args[0]==="event" && args[1]==="conversion")`);
    const noAds = async () => assert.deepEqual(await ads(), [], label + ": no premature/denied conversion");
    const noSuccess = async () => assert.equal(await evaluate(
      `!!document.querySelector(${JSON.stringify(flow.success)})`), false, label);
    const phoneLinks = () => evaluate(`Array.from(document.querySelectorAll('a[href^="tel:"]'))
      .map(a=>a.getAttribute('href')).sort()`);
    const phones = await phoneLinks();
    assert.ok(phones.length, label + ": existing phone links present");
    await evaluate(`intakeFixture.phoneAnchors=[...document.querySelectorAll('a[href^="tel:"]')]`);
    // Real activation, but cancel the OS action: no call can leave Chromium.
    const checkPhone = async (scope = "") => {
      const selector = await evaluate(`(()=>{
        const links=[...document.querySelectorAll(${JSON.stringify(scope + ' a[href^="tel:"]')})];
        const a=links.find(a=>a.getClientRects().length && getComputedStyle(a).visibility!=="hidden");
        if(!a)throw new Error("No visible phone link");
        a.setAttribute('data-nimbata-test-phone','');
        intakeFixture.phoneClicks=0;
        a.addEventListener('click',event=>{event.preventDefault();intakeFixture.phoneClicks++},{once:true});
        return '[data-nimbata-test-phone]';
      })()`);
      await focus(selector);
      assert.equal(await evaluate(`document.activeElement.matches(${JSON.stringify(selector)})`), true, label);
      // Confirmation/error handlers start a smooth scroll. Wait for its actual
      // geometry to settle before a physical tap, without changing page CSS.
      await evaluate(`new Promise((resolve,reject)=>{
        const a=document.querySelector(${JSON.stringify(selector)});
        a.scrollIntoView({block:"center",behavior:"instant"});
        let last="",stable=0,frames=0;
        function frame(){
          const r=a.getBoundingClientRect();
          const current=[r.x,r.y,visualViewport.offsetTop,visualViewport.offsetLeft].join(",");
          stable=current===last?stable+1:0;last=current;
          if(stable>=5)return resolve(true);
          if(++frames>120)return reject(new Error("Phone link never settled"));
          requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
      })`);
      await activate(selector, mobile);
      // Touch-generated click can arrive after the CDP touchEnd reply.
      await until("intakeFixture.phoneClicks === 1", "phone activation received without opening a dialer");
      assert.equal(await evaluate("intakeFixture.phoneClicks"), 1, label + ": usable phone link");
      await evaluate(`document.querySelector(${JSON.stringify(selector)}).removeAttribute('data-nimbata-test-phone')`);
    };
    await checkPhone();
    await activate(flow.submit, mobile); // Native invalid-form validation.
    await sleep(50);
    assert.equal(state.security.length, 0, label);
    assert.equal(state.posts.length, 0, label);
    await noAds();await noSuccess();
    for (const [selector, value] of Object.entries(flow.fields))
      await fill(flow.form + " " + selector, value);
    if (flow.name === "provider") await evaluate("document.querySelector('#rf-county').value='Ventura County'");
    await activate(flow.submit, mobile);
    await until("document.querySelector('#fixture-challenge')");
    await noAds();await noSuccess();
    await activate("#fixture-challenge", mobile);
    for (let i = 0; i < 100 && !state.held; i++) await sleep(40);
    assert.ok(state.held, label + ": synthetic POST reached fixture");
    assert.equal(state.security.length, 1, label);
    assert.equal(state.security[0].form, flow.formName, label);
    assert.equal(state.posts.length, 1, label);
    assert.equal(state.posts[0].fields["form-name"], flow.formName, label);
    assert.equal(state.posts[0].fields["cf-turnstile-response"], "synthetic-provider-token", label);
    await noAds();await noSuccess(); // Even a valid POST is not acceptance yet.
    if (mode === "timeout" && consent === "all")
      assert.equal(tracker.held.length, 1, label + ": SDK still stalled while form submits");
    state.submitResponse = outcome === "rejected"
      ? {status: 400, body: {ok: false, accepted: false, error: "synthetic_rejection"}}
      : outcome === "unconfirmed" ? {body: {ok: true}} : null;
    state.held();state.held = null;state.hold = false;
    if (outcome === "accepted") {
      await until(`document.querySelector(${JSON.stringify(flow.success)})`);
      assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.success)}).textContent`),
        /SYNTHETIC-RECEIPT/, label + ": confirmation remains visible");
      assert.deepEqual(await ads(), consent === "all" ? [["event", "conversion", {
        send_to: "AW-18384023405/JC8lCKGQ9qsdEO3el75E", value: 1, currency: "USD"
      }]] : [], label + ": exactly one privacy-safe consented conversion");
    } else {
      await until(`document.querySelector(${JSON.stringify(flow.error)})?.textContent.length > 0`);
      await noSuccess();await noAds();
      for (const [selector, value] of Object.entries(flow.fields)) {
        const actual = await evaluate(`document.querySelector(${JSON.stringify(flow.form + " " + selector)}).value`);
        assert.equal(selector.includes("phone") ? actual.replace(/\D/g, "") : actual, value, label);
      }
    }
    // Complete the stalled SDK only AFTER the intake result, proving its timeout
    // doesn't gate the form. No arbitrary delay or real network is involved.
    for (const requestId of tracker.held)
      await call("Fetch.failRequest", {requestId, errorReason: "TimedOut"});
    await sleep(60);
    assert.equal(tracker.requests, consent === "all" ? 1 : 0, label + ": consent gates Nimbata");
    assert.equal(await evaluate(`document.querySelectorAll('script[src=${JSON.stringify(nimbataFixtureURL)}]').length`),
      consent === "all" ? 1 : 0, label);
    assert.deepEqual(await evaluate(`intakeFixture.phoneAnchors.map(a=>{
      if(!a.isConnected)throw new Error("Existing phone link removed");
      return a.getAttribute('href');
    }).sort()`), phones, label + ": existing phone destinations unchanged");
    await checkPhone(outcome === "accepted" ? flow.success : flow.error);
    if (outcome === "accepted") {
      assert.match(await evaluate(`document.querySelector(${JSON.stringify(flow.success)}).textContent`),
        /SYNTHETIC-RECEIPT/, label + ": confirmation survives SDK failure");
    } else await noSuccess();
    // Inspect the entire queued Google payload and every intercepted external
    // request, not just the conversion: no entered contacts, free text or receipt.
    const captured = JSON.stringify({google: await evaluate(
      "(window.dataLayer || []).map(args=>Array.from(args))"), external: tracker.external});
    for (const secret of ["2025550190", "202.555.0190", "family@example.invalid",
      "provider@example.invalid", "Synthetic", "SYNTHETIC-RECEIPT", "entered-secret", "entered-fragment"]) {
      assert.ok(!captured.includes(secret) && !decodeURIComponent(captured).includes(secret),
        label + ": tracker payload excludes " + secret);
    }
    if (consent === "essential") {
      assert.equal(await evaluate("typeof window.gtag"), "undefined", label);
      assert.equal(tracker.external.some(r => /googletagmanager|google-analytics|googleadservices|nimbata/.test(r.url)),
        false, label + ": optional tracking never requested");
    }
    if (outcome !== "accepted") await noAds();
    else assert.equal((await ads()).length, consent === "all" ? 1 : 0, label + ": no duplicate conversion");
    assert.equal(state.posts.length, 1, label + ": no automatic resubmission");
    console.log("PASS " + label);
  }
  // Restore the surrounding suite's essential-only baseline before it switches
  // to real-security fixtures. Do not carry optional SDK boot into other tests.
  await evaluate("localStorage.setItem('elh_cc','essential');sessionStorage.clear()");
  await call("Page.navigate", {url: "about:blank"});
  await until("location.href === 'about:blank' && document.readyState === 'complete'");
}

// Change permission through the real footer/settings controls, never by editing
// consent storage in-flight. Every response and every SDK is synthetic.
export async function runConsentChangeRegression({
  fixture, flows, call, evaluate, until, activate, fill, focus, sleep, setCase
}) {
  const {state} = fixture;
  assert.equal(state.realSecurity, false, "Consent matrix must never send real intake");
  const careFlows = flows.filter(f => ["family", "provider", "chat"].includes(f.name));
  for (const scenario of ["withdraw-pending", "grant-pending", "withdraw-delayed-google", "grant-after-accepted"])
  for (const mobile of [false, true])
  for (const flow of careFlows)
  for (const outcome of (scenario.endsWith("pending") ? ["accepted", "rejected", "unconfirmed"] : ["accepted"])) {
    const label = `Consent ${scenario}, ${flow.name}, ${mobile ? "touch" : "keyboard"}, ${outcome}`;
    // Leave the previous document before replacing its evidence collector.
    await call("Page.navigate", {url: "about:blank"});
    await until("location.href === 'about:blank' && document.readyState === 'complete'");
    const tracker = {mode: "timeout", requests: 0, exceptions: 0, held: [], external: [],
      unexpectedExceptions: [], documents: [], delayLoad: scenario === "withdraw-delayed-google", loadHeld: []};
    setCase(label, tracker);
    await call("Storage.clearDataForOrigin", {origin: fixture.origin, storageTypes: "all"});
    // Establish an independent returning visitor BEFORE loading the test page.
    await call("Page.navigate", {url: fixture.origin + "/privacy-policy.html"});
    await until("document.readyState === 'complete' && typeof elhCookieSettings === 'function'");
    const withdraw = scenario.startsWith("withdraw");
    await evaluate(`localStorage.setItem('elh_cc',${JSON.stringify(withdraw ? "all" : "essential")});sessionStorage.clear()`);
    state.security = [];state.posts = [];state.securityFailure = false;
    state.moduleFailure = false;state.historyCacheable = false;
    state.hold = true;state.held = null;state.submitResponse = null;
    state.delayLoad = tracker.delayLoad;
    await call("Emulation.setDeviceMetricsOverride", {width: mobile ? 390 : 1280,
      height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile});
    await call("Emulation.setTouchEmulationEnabled", {enabled: mobile});
    await call("Page.navigate", {url: fixture.origin + flow.path + "?private=entered-secret#entered-fragment"});
    await until(`document.querySelector(${JSON.stringify(flow.name === "chat" ? ".elhc-launch" : flow.form)}) &&
      typeof elhCookieSettings === "function"`);
    if (tracker.delayLoad) {
      for (let i = 0; i < 100 && !tracker.loadHeld.length; i++) await sleep(40);
      assert.equal(tracker.loadHeld.length, 1, label + ": actual load barrier intercepted");
      assert.notEqual(await evaluate("document.readyState"), "complete", label);
      assert.equal(await evaluate("typeof gtag"), "undefined", label);
    } else {
      await until("document.readyState === 'complete'");
      if (withdraw) {
        await until("window.__elhAnalyticsBooted");
        for (let i = 0; i < 100 && !tracker.requests; i++) await sleep(40);
        assert.equal(tracker.held.length, 1, label + ": Nimbata actually stalled");
      }
    }
    if (flow.name === "chat") {
      await activate(".elhc-launch", mobile);
      await until("document.querySelector('.elhc-panel.open')");
      await activate(".elhc-chip-cb", mobile);
    }
    await until(`document.querySelector(${JSON.stringify(flow.form)})`);
    for (const [selector, value] of Object.entries(flow.fields))
      await fill(flow.form + " " + selector, value);
    if (flow.name === "provider") await evaluate("document.querySelector('#rf-county').value='Ventura County'");
    const accepted = flow.name === "chat"
      ? `[...document.querySelectorAll('.elhc-msg.elhc-bot')].some(el=>el.textContent.includes('SYNTHETIC-RECEIPT'))`
      : `document.querySelector(${JSON.stringify(flow.success)})?.textContent.includes('SYNTHETIC-RECEIPT')`;
    const ads = () => evaluate(`(window.dataLayer || []).map(args=>Array.from(args))
      .filter(args=>args[0]==='event' && args[1]==='conversion')`);
    await activate(flow.submit, mobile);
    await until("document.querySelector('#fixture-challenge')");
    await activate("#fixture-challenge", mobile);
    for (let i = 0; i < 100 && !state.held; i++) await sleep(40);
    assert.ok(state.held, label + ": secured synthetic POST is pending");
    assert.equal(state.security.length, 1, label);
    assert.equal(state.posts.length, 1, label);
    assert.equal(state.posts[0].fields["form-name"], flow.formName, label);
    assert.equal(state.posts[0].fields["cf-turnstile-response"], "synthetic-provider-token", label);
    assert.equal(await evaluate(`Boolean(${accepted})`), false, label + ": no premature success");
    assert.deepEqual(await ads(), [], label);
    const reply = state.held;
    const finish = () => {
      state.submitResponse = outcome === "rejected"
        ? {status: 400, body: {ok: false, accepted: false, error: "synthetic_rejection"}}
        : outcome === "unconfirmed" ? {body: {ok: true}} : null;
      reply();state.held = null;state.hold = false;
    };
    const acceptedBeforeChange = ["withdraw-delayed-google", "grant-after-accepted"].includes(scenario);
    if (acceptedBeforeChange) {
      finish();
      await until(accepted);
      assert.deepEqual(await ads(), [], label + ": acceptance before Google boot/permission queues no event yet");
    }
    const documentId = await evaluate("intakeFixture.documentId");
    // Open the actual footer link with keyboard/touch, not the public API.
    const settings = 'a[onclick*="elhCookieSettings"]';
    if (flow.name === "chat") {
      await activate(".elhc-x", mobile);
      await until("!document.querySelector('.elhc-panel.open')");
    }
    // The fixed chat launcher overlaps the footer at this phone viewport.
    // Open via its native keyboard action, then physically tap the preference
    // and Save controls on mobile; never hide overlays or call the settings API.
    await activate(settings, false);
    await until("document.querySelector('#elh-cc-preferences')?.hidden === false");
    assert.equal(await evaluate("document.querySelector('#elh-tog-all').checked"), withdraw, label);
    // Space is the native keyboard toggle; touch uses the visible label.
    if (mobile) await activate(".privacy-optional", true);
    else {
      await focus("#elh-tog-all");
      await call("Input.dispatchKeyEvent", {type: "keyDown", key: " ", code: "Space", windowsVirtualKeyCode: 32, text: " "});
      await call("Input.dispatchKeyEvent", {type: "keyUp", key: " ", code: "Space", windowsVirtualKeyCode: 32});
    }
    assert.equal(await evaluate("document.querySelector('#elh-tog-all').checked"), !withdraw, label);
    // Only the old document is stalled; the fresh essential-only page may load.
    state.delayLoad = false;
    const externalBeforeSave = tracker.external.length;
    await activate("#elh-cc-save", mobile);
    if (withdraw) {
      await until(`intakeFixture.documentId !== ${JSON.stringify(documentId)} &&
        document.readyState === 'complete' && typeof elhCookieSettings === 'function'`, "real settings reload");
      assert.equal(await evaluate("performance.getEntriesByType('navigation')[0].type"), "reload", label);
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential", label);
      assert.equal(await evaluate("typeof gtag"), "undefined", label);
      assert.equal(await evaluate("Boolean(window.__elhAnalyticsBooted)"), false, label);
      const destroyed = tracker.documents.find(d => d.documentId === documentId);
      assert.ok(destroyed, label + ": captured old-document evidence");
      assert.deepEqual(destroyed.google.filter(a => a[0] === "event" && a[1] === "conversion"), [], label);
      if (!acceptedBeforeChange) finish(); // Late response to the abandoned request.
      if (flow.name === "chat") {
        await activate(".elhc-launch", mobile);
        await until("document.querySelector('.elhc-panel.open')");
        await activate(".elhc-chip-cb", mobile);
        if (!acceptedBeforeChange) {
          await until("document.querySelector('.elhc-cb-reminder')");
          assert.match(await evaluate("document.querySelector('.elhc-cb-reminder').textContent"),
            /couldn't confirm whether your request was received/);
          assert.equal(await evaluate("!!document.querySelector('.elhc-cb')"), false, label);
        }
      }
      assert.equal(await evaluate(`Boolean(${accepted})`), false, label + ": reload never invents a receipt");
      if (flow.name !== "chat")
        assert.equal(await evaluate(`document.querySelector(${JSON.stringify(flow.error)})?.textContent || ''`),
          "", label + ": abandoned response is not a known result");
      if (flow.name !== "chat")
        for (const selector of Object.keys(flow.fields))
          assert.equal(await evaluate(`document.querySelector(${JSON.stringify(flow.form + " " + selector)}).value`),
            "", label + ": reload opens a blank form, not a restored submission");
    } else {
      await until("!document.querySelector('#elh-cc') && window.__elhAnalyticsBooted");
      assert.equal(await evaluate("intakeFixture.documentId"), documentId, label + ": granting does not reload");
      assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "all", label);
      if (!acceptedBeforeChange) finish();
      if (outcome === "accepted") await until(accepted);
      else {
        await until(`document.querySelector(${JSON.stringify(flow.form)}).__elhSubmissionState ===
          ${JSON.stringify(outcome === "unconfirmed" ? "unknown" : null)}`);
        assert.equal(await evaluate(`Boolean(${accepted})`), false, label);
        for (const [selector, value] of Object.entries(flow.fields)) {
          const actual = await evaluate(`document.querySelector(${JSON.stringify(flow.form + " " + selector)}).value`);
          assert.equal(selector.includes("phone") ? actual.replace(/\D/g, "") : actual, value, label);
        }
      }
    }
    // A canceled interception ID is expected after reload; all others must fail.
    for (const requestId of [...tracker.held, ...tracker.loadHeld]) {
      try {await call("Fetch.failRequest", {requestId, errorReason: "TimedOut"});}
      catch (error) {
        if (error.message !== '{"code":-32602,"message":"Invalid InterceptionId."}') throw error;
      }
    }
    await sleep(150);
    assert.equal(tracker.requests, tracker.delayLoad ? 0 : 1,
      label + ": Nimbata is not restarted after withdrawal or duplicated after granting");
    if (withdraw)
      assert.deepEqual(tracker.external.slice(externalBeforeSave).filter(r =>
        /googletagmanager|google-analytics|googleadservices|nimbata|clarity|brevo|metricool/.test(r.url)),
        [], label + ": the reloaded document makes no optional tracking requests");
    assert.deepEqual(await ads(), scenario === "grant-pending" && outcome === "accepted"
      ? [["event", "conversion", {send_to: "AW-18384023405/JC8lCKGQ9qsdEO3el75E", value: 1, currency: "USD"}]]
      : [], label + ": withdrawal/late permission never replays an Ads conversion");
    // Prove a visible phone link still works, while preventing any OS dialer.
    if (!withdraw && flow.name === "chat") {
      await activate(".elhc-launch", mobile);
      await until("document.querySelector('.elhc-panel.open')");
    }
    const phoneScope = flow.name === "chat" ? ".elhc-panel" : withdraw ? "" :
      outcome === "accepted" ? flow.success : flow.error;
    await evaluate(`(()=>{
      const a=[...document.querySelectorAll(${JSON.stringify(phoneScope + ' a[href^="tel:"]')})]
        .find(a=>a.getClientRects().length && getComputedStyle(a).visibility!=="hidden");
      if(!a)throw new Error('Missing visible care phone guidance');
      a.dataset.consentPhone='';intakeFixture.phoneClicks=0;
      a.addEventListener('click',event=>{event.preventDefault();intakeFixture.phoneClicks++},{once:true});
      a.scrollIntoView({block:'center',behavior:'instant'});
    })()`);
    await sleep(200);
    await activate("[data-consent-phone]", mobile);
    await until("intakeFixture.phoneClicks === 1");
    const captured = JSON.stringify({documents: tracker.documents, external: tracker.external,
      google: await evaluate("(window.dataLayer || []).map(args=>Array.from(args))")});
    for (const secret of ["2025550190", "202.555.0190", "family@example.invalid",
      "provider@example.invalid", "chat@example.invalid", "Synthetic", "SYNTHETIC-RECEIPT",
      "entered-secret", "entered-fragment"])
      assert.ok(!decodeURIComponent(captured).includes(secret), label + ": no tracking leak: " + secret);
    assert.equal(state.posts.length, 1, label + ": never automatically resubmits");
    assert.equal(state.security.length, 1, label + ": never automatically re-verifies");
    console.log("PASS " + label);
  }
  state.delayLoad = false;
  await evaluate("localStorage.setItem('elh_cc','essential');sessionStorage.clear()");
  await call("Page.navigate", {url: "about:blank"});
  await until("location.href === 'about:blank' && document.readyState === 'complete'");
}
