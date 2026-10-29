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
    const tracker = {mode, requests: 0, exceptions: 0, held: [], external: [], unexpectedExceptions: []};
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
