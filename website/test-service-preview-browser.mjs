// Real browser checks for preview services. Blocks third-party traffic and does
// not authenticate, publish, submit forms or create analytics events.
// Run: node --experimental-websocket website/test-service-preview-browser.mjs
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";

assert.equal(typeof WebSocket, "function", "Use Node's --experimental-websocket flag");
const origin = "https://" + process.env.REPLIT_DEV_DOMAIN;
assert.ok(process.env.REPLIT_DEV_DOMAIN, "REPLIT_DEV_DOMAIN is required");
const catalog = JSON.parse(await readFile("website/previews/catalog.json", "utf8"));
const profile = await mkdtemp(join(tmpdir(), "elh-service-browser-"));
const browser = spawn("chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage",
  "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank",
], {stdio: ["ignore", "ignore", "pipe"]});
let diagnostics = "";
browser.stderr.on("data", chunk => {
  diagnostics = (diagnostics + chunk.toString()).slice(-12000);
});
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;

try {
  let port;
  for (let attempt = 0; attempt < 300; attempt++) {
    if (browser.exitCode !== null || browser.signalCode !== null) {
      throw new Error("Browser exited before startup:\n" + diagnostics);
    }
    try {
      port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]);
      if (port) break;
    } catch { /* Chromium has not written its endpoint yet. */ }
    await sleep(100);
  }
  assert.ok(port, "Browser failed to open DevTools:\n" + diagnostics);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener("open", resolve, {once: true}));
  let id = 0;
  const pending = new Map();
  const failures = [];
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
    const result = JSON.parse(event.data);
    if (result.method === "Fetch.requestPaused") {
      const {request, requestId} = result.params;
      const allowed = request.url.startsWith(origin + "/") || request.url.startsWith("data:");
      void call(allowed ? "Fetch.continueRequest" : "Fetch.failRequest",
        allowed ? {requestId} : {requestId, errorReason: "BlockedByClient"})
        .catch(error => failures.push(error.message));
    }
    if (result.method === "Runtime.exceptionThrown") {
      failures.push(result.params.exceptionDetails.text);
    }
    const waiter = pending.get(result.id);
    if (waiter) {
      clearTimeout(waiter.timer);
      pending.delete(result.id);
      result.error ? waiter.reject(new Error(JSON.stringify(result.error))) : waiter.resolve(result.result);
    }
  });
  const evaluate = async expression => {
    const result = await call("Runtime.evaluate", {expression, awaitPromise: true, returnByValue: true});
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async (expression, label) => {
    for (let attempt = 0; attempt < 150; attempt++) {
      if (await evaluate(`Boolean(${expression})`)) return;
      await sleep(100);
    }
    throw new Error("Timed out: " + label);
  };
  const viewport = async width => {
    await call("Emulation.setDeviceMetricsOverride", {
      width, height: 1000, deviceScaleFactor: 1, mobile: width < 500,
    });
    await sleep(80);
  };
  const navigate = async path => {
    await call("Page.navigate", {url: origin + path});
    await until(`location.pathname===${JSON.stringify(path)} && document.readyState!=='loading' &&
      document.querySelector('#service-page') && document.querySelector('#sp-services-menu .sp-group-toggle') &&
      document.querySelector('#hdr .nav-toggle')`, "service page and navigation");
    await evaluate("document.fonts.ready.then(()=>true)");
  };
  await call("Page.enable");
  await call("Runtime.enable");
  await call("Fetch.enable", {patterns: [{urlPattern: "*"}]});

  for (const page of process.argv.includes("--menus-only") ? [] : catalog) {
    await navigate("/services/" + page.slug);
    await until("document.querySelector('#service-page .cc-hero-photo img').naturalWidth>0", "hero photograph");
    for (const width of [320, 390, 768, 1024, 1440]) {
      await viewport(width);
      const layout = await evaluate(`({
        width:innerWidth, scroll:document.documentElement.scrollWidth,
        h1:document.querySelector('#service-page h1').textContent,
        details:document.querySelectorAll('#service-page details').length,
        removed:document.querySelector('#service-page').textContent.includes(
          'Phone access does not mean a nurse stays continuously at the bedside.')
      })`);
      assert.ok(layout.scroll <= width, page.slug + " overflows: " + JSON.stringify(layout));
      assert.equal(layout.h1, page.title);
      assert.ok(layout.details >= 2, page.slug);
      assert.equal(layout.removed, false);
    }
    assert.equal(await evaluate(`(()=>{
      const summary=document.querySelector('#service-page details summary');
      summary.click();const expanded=summary.parentElement.open;
      summary.click();return expanded&&!summary.parentElement.open;
    })()`), true, page.slug + " FAQ interaction");
    assert.equal(await evaluate(`document.querySelector('#service-page .cc-actions a').getAttribute('href')`),
      "tel:8059537273");
    assert.equal(await evaluate(`document.querySelector('#service-page .cc-actions a:nth-child(2)').getAttribute('href')`),
      "/refer#referral-form");
    console.log("PASS", page.slug, "five viewport widths, photograph, FAQ and CTAs");
  }

  await navigate("/services");
  for (const width of [320, 390, 768, 1024, 1440]) {
    await viewport(width);
    const directory = await evaluate(`({
      width:innerWidth,scroll:document.documentElement.scrollWidth,
      groups:document.querySelectorAll('#service-page .directory-group').length,
      links:document.querySelectorAll('#service-page .directory-item a').length,
      notes:document.querySelectorAll('#service-page figcaption').length
    })`);
    assert.ok(directory.scroll <= width, "Services directory overflows: " + JSON.stringify(directory));
    assert.equal(directory.groups, 4);
    assert.equal(directory.links, 13);
    assert.equal(directory.notes, 0);
  }
  console.log("PASS Services overview at five widths, four groups, 13 links and no photo notes");
  await viewport(1440);
  assert.equal(await evaluate(`document.querySelectorAll('#service-page .directory-item').length`), 13);
  assert.equal(await evaluate(`document.querySelectorAll('#service-page .directory-group').length`), 4);
  await evaluate(`document.querySelector('[data-section=services]>.nav-toggle').click()`);
  await until("getComputedStyle(document.querySelector('#sp-services-menu')).visibility==='visible'",
    "desktop mega menu opens");
  const desktop = await evaluate(`(()=>{
    const menu=document.querySelector('#sp-services-menu'),r=menu.getBoundingClientRect();
    return {left:r.left,right:r.right,width:innerWidth,visible:getComputedStyle(menu).visibility,
      columns:getComputedStyle(menu.querySelector('.sp-menu-grid')).gridTemplateColumns.split(' ').length,
      links:[...menu.querySelectorAll('.sp-group-links a')].filter(a=>a.getClientRects().length).length};
  })()`);
  assert.equal(desktop.visible, "visible");
  assert.ok(desktop.left >= 0 && desktop.right <= desktop.width, JSON.stringify(desktop));
  assert.equal(desktop.columns, 4);
  assert.equal(desktop.links, 13);
  await evaluate(`document.querySelector('[data-section=services]>.nav-toggle').focus();
    document.querySelector('[data-section=services]>.nav-toggle').dispatchEvent(
      new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
  assert.equal(await evaluate(`document.querySelector('[data-section=services]').classList.contains('expanded')`), false);
  console.log("PASS desktop four-column menu, all direct links and Escape");

  await viewport(390);
  await evaluate(`document.querySelector('#hdr .menu-btn').click();
    document.querySelector('[data-section=services]>.nav-toggle').click()`);
  const headings = await evaluate(`(()=>{
    const service=document.querySelector('[data-section=services]');
    return [...service.querySelectorAll('.sp-group-toggle')].map(b=>({
      expanded:b.getAttribute('aria-expanded'),visible:b.getClientRects().length>0
    }));
  })()`);
  assert.equal(headings.length, 4);
  assert.ok(headings.every(item => item.expanded === "false" && item.visible));
  for (let i = 0; i < 4; i++) {
    const open = await evaluate(`(()=>{
      const buttons=[...document.querySelectorAll('.sp-group-toggle')],button=buttons[${i}];
      button.click();const links=document.getElementById(button.getAttribute('aria-controls'));
      return {expanded:button.getAttribute('aria-expanded'),
        visible:getComputedStyle(links).display!=='none',
        count:links.querySelectorAll('a').length,
        otherOpen:buttons.filter(b=>b!==button&&b.getAttribute('aria-expanded')==='true').length};
    })()`);
    assert.equal(open.expanded, "true");
    assert.equal(open.visible, true);
    assert.ok(open.count > 0);
    assert.equal(open.otherOpen, 0);
  }
  await evaluate(`document.querySelector('.sp-group-links.is-open a').click()`);
  await until("location.pathname==='/services/hospice-evaluation' && document.readyState!=='loading'",
    "mobile service link navigation");
  assert.equal(await evaluate(`document.querySelector('#hdr').classList.contains('nav-open')`), false);
  console.log("PASS mobile accordion groups, state, direct navigation and menu dismissal");
  await until("document.querySelector('#service-page') && document.querySelector('#searchBtn')", "destination header");
  await evaluate(`document.querySelector('#searchBtn').click()`);
  await until("document.querySelector('#searchOverlay').getAttribute('aria-hidden')==='false'", "shared site search");
  await evaluate(`document.querySelector('#searchClose').click()`);
  assert.equal(await evaluate(`document.querySelector('#searchOverlay').getAttribute('aria-hidden')`), "true");
  console.log("PASS shared search dialog opens and closes");
  assert.deepEqual(failures, []);
} finally {
  socket?.close();
  browser.kill("SIGTERM");
  await sleep(200);
  await rm(profile, {recursive: true, force: true});
}
