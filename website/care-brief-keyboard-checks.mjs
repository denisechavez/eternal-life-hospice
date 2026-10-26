// Focused companion to test-care-brief-layout.mjs; uses its isolated browser,
// static fixture and network/submission fences. No application APIs are started.
import assert from "node:assert/strict";

// This runs inside Chromium and measures only the control being reached.
// A short keyboard viewport need not contain the entire form at once.
function inspectControl(selector) {
  const element = document.querySelector(selector);
  if (!element) return {errors: ["missing control"]};
  const r = element.getBoundingClientRect();
  const vv = visualViewport;
  const header = document.querySelector("#hdr")?.getBoundingClientRect();
  const bounds = {left: vv.offsetLeft, right: vv.offsetLeft + vv.width,
    top: Math.max(vv.offsetTop, header?.bottom || 0),
    bottom: vv.offsetTop + vv.height};
  const errors = [];
  if (!element.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) ||
      r.width <= 0 || r.height <= 0 || element.disabled) errors.push("hidden or disabled");
  if (r.top < bounds.top - 1) errors.push("behind sticky header or viewport top");
  if (r.bottom > bounds.bottom + 1) errors.push("below reduced visual viewport");
  if (r.left < bounds.left - 1 || r.right > bounds.right + 1) errors.push("horizontal clipping");
  // Sample edge midpoints, not transparent rounded corners.
  for (const [x, y] of [
    [r.left + 2, r.top + r.height / 2], [r.right - 2, r.top + r.height / 2],
    [r.left + r.width / 2, r.top + 2], [r.left + r.width / 2, r.bottom - 2],
    [r.left + r.width / 2, r.top + r.height / 2],
  ]) {
    const hit = document.elementFromPoint(x, y);
    if (!hit || !(hit === element || element.contains(hit))) errors.push("obscured or clipped");
  }
  return {errors, bounds, rect: {top: r.top, bottom: r.bottom, left: r.left, right: r.right},
    active: document.activeElement === element, scrollY,
    viewportHeight: vv.height, layoutHeight: innerHeight, scale: vv.scale};
}

export async function checkKeyboardViewports({call, evaluate, until, sleep}) {
  const first = '#signup input[name="first_name"]';
  const email = '#signup input[name="email"]';
  const submit = '#signup button[type="submit"]';
  const inspect = selector => evaluate(`(${inspectControl.toString()})(${JSON.stringify(selector)})`);
  const settle = () => evaluate(`new Promise(resolve=>{
    let previous=scrollY, stable=0;
    const timer=setInterval(()=>{
      stable=Math.abs(scrollY-previous)<0.5?stable+1:0;
      previous=scrollY;
      if(stable>=4){clearInterval(timer);resolve();}
    },50);
  })`);
  const reach = async selector => {
    // Native scrolling, not CSS fixes or forced positioning of the controls.
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({
      block:'center',inline:'nearest',behavior:'instant'
    })`);
    await settle();
    return inspect(selector);
  };
  const tab = async (backward = false) => {
    await call("Input.dispatchKeyEvent", {type: "keyDown", key: "Tab", code: "Tab",
      windowsVirtualKeyCode: 9, modifiers: backward ? 8 : 0});
    await call("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab",
      windowsVirtualKeyCode: 9, modifiers: backward ? 8 : 0});
  };
  const metrics = (width, height) => call("Emulation.setDeviceMetricsOverride", {
    width, height, deviceScaleFactor: 1, mobile: true,
  });
  // Portrait phone sizes plus a short landscape keyboard case. Chromium's
  // resize model reduces BOTH layout and visual viewport heights at scale 1.
  // It does not emulate iOS visual-only panning, keyboard UI, autofill or zoom.
  for (const [width, fullHeight, reducedHeight] of [
    [320, 740, 340], [360, 800, 380], [390, 844, 400], [740, 390, 240],
  ]) {
    await metrics(width, fullHeight);
    await call("Page.navigate", {url: await evaluate("location.origin") + "/care-brief#signup"});
    await until("location.hash==='#signup' && document.readyState==='complete'", "keyboard signup loaded");
    await evaluate("document.fonts.ready.then(()=>true)");
    await sleep(400); // Page's delayed anchor correction.
    await settle();
    const full = await inspect(first);
    assert.ok(Math.abs(full.viewportHeight - fullHeight) <= 1, JSON.stringify(full));
    // First-name focus opens the emulated keyboard.
    await evaluate(`document.querySelector(${JSON.stringify(first)}).focus({preventScroll:true})`);
    await metrics(width, reducedHeight);
    for (const [index, selector] of [first, email, first, email].entries()) {
      if (index) await tab(index === 2); // Forward, back, forward: real focus order.
      let result = await inspect(selector);
      assert.equal(result.active, true, `${width}px: field transition lost focus: ${JSON.stringify(result)}`);
      assert.ok(Math.abs(result.viewportHeight - reducedHeight) <= 1 &&
        result.viewportHeight < full.viewportHeight - 100 &&
        Math.abs(result.scale - 1) < 0.01,
      `${width}px: reduced visual viewport not applied: ${JSON.stringify(result)}`);
      result = await reach(selector);
      assert.deepEqual(result.errors, [], `${width}px active ${selector}: ${JSON.stringify(result)}`);
      assert.equal(result.active, true, "Scrolling must not blur the input");
      // Reach the button with the keyboard still open, without submitting or
      // requiring simultaneous visibility of all fields in the short viewport.
      result = await reach(submit);
      assert.deepEqual(result.errors, [], `${width}px submit after ${selector}: ${JSON.stringify(result)}`);
      assert.equal((await inspect(selector)).active, true, "Reaching submit must preserve input focus");
    }
    await tab();
    assert.equal((await inspect(submit)).active, true, "Submit must follow email in focus order");
    assert.deepEqual((await reach(submit)).errors, [], "Focused submit must remain reachable");
    assert.equal(await evaluate("window.__blockedSubmits"), 0, "Keyboard checks must not submit");

    // Keyboard dismissed: focus and scroll still work at the original height.
    await metrics(width, fullHeight);
    await tab(true);
    const restored = await reach(email);
    assert.equal(restored.active, true);
    assert.ok(Math.abs(restored.viewportHeight - fullHeight) <= 1);
    assert.deepEqual(restored.errors, [], `Keyboard dismissal: ${JSON.stringify(restored)}`);
    console.log(`PASS emulated keyboard ${width}px: ${fullHeight}→${reducedHeight}→${fullHeight}px; fields and submit reachable`);
  }

  // Disposable negative controls prove this is not a full-height-only test.
  await metrics(320, 340);
  await evaluate(`document.querySelector(${JSON.stringify(email)}).focus({preventScroll:true})`);
  await reach(email);
  const mutations = [
    ["field behind header", `${email}{position:fixed!important;top:0!important;left:20px!important;z-index:1!important}`,
      email, "behind sticky header"],
    ["field below keyboard viewport", `${email}{position:fixed!important;top:400px!important;left:20px!important}`,
      email, "below reduced visual viewport"],
    ["unreachable submit", `${submit}{display:none!important}`, submit, "hidden or disabled"],
  ];
  for (const [label, css, selector, expected] of mutations) {
    await evaluate(`(()=>{
      const s=document.createElement('style');s.id='keyboard-negative';s.textContent=${JSON.stringify(css)};
      document.head.append(s);
    })()`);
    const result = await reach(selector);
    assert.ok(result.errors.some(error => error.includes(expected)),
      `Keyboard guard missed ${label}: ${JSON.stringify(result)}`);
    await evaluate("document.querySelector('#keyboard-negative').remove()");
    console.log("PASS keyboard negative control: " + label);
  }
  assert.deepEqual((await reach(email)).errors, [], "Restored field must pass");
  assert.deepEqual((await reach(submit)).errors, [], "Restored submit must pass");
  assert.equal(await evaluate("window.__blockedSubmits"), 0);
  console.log("Keyboard coverage is Chromium resized-viewport emulation, NOT real-device software-keyboard verification.");
}
