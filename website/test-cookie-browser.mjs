// Real consent UI and persistence, synthetic third-party responses only.
// node --experimental-websocket website/test-cookie-browser.mjs
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const source = await readFile(new URL("./elh-preview/assets/analytics.js", import.meta.url), "utf8");
const server = createServer((req, res) => {
  res.setHeader("Content-Type", req.url === "/analytics.js" ? "text/javascript" : "text/html");
  res.end(req.url === "/analytics.js" ? source :
    '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><h1>Consent fixture</h1><button id="footer" onclick="elhCookieSettings()">Cookie Settings</button><script>window.__noClarity=true</script><script src="/analytics.js"></script>');
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const profile = await mkdtemp(join(tmpdir(), "elh-cookie-test-"));
const browser = spawn(process.env.CHROMIUM_BIN || "chromium", [
  "--headless", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
  "--no-first-run", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"
], {stdio: ["ignore", "ignore", "pipe"]});
let log = "", ws, id = 0;
browser.stderr.on("data", chunk => { log = (log + chunk).slice(-4000); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map(), external = [], errors = [];
try {
  let port;
  for (let i = 0; i < 600; i++) {
    if (browser.exitCode !== null) throw new Error("Chromium exited: " + log);
    try { port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]); break; }
    catch { await sleep(50); }
  }
  assert.ok(port, log);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise(resolve => ws.addEventListener("open", resolve, {once: true}));
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    pending.set(++id, [resolve, reject]); ws.send(JSON.stringify({id, method, params}));
  });
  ws.addEventListener("message", event => {
    const m = JSON.parse(event.data);
    if (pending.has(m.id)) {
      const [resolve, reject] = pending.get(m.id); pending.delete(m.id);
      m.error ? reject(m.error) : resolve(m.result);
    }
    if (m.method === "Fetch.requestPaused") {
      const local = m.params.request.url.startsWith(origin + "/");
      if (!local) external.push(m.params.request.url);
      const stub = m.params.request.url.includes("tracker.metricool.com")
        ? "window.beTracker={t:function(){}};" : "";
      (local ? call("Fetch.continueRequest", {requestId:m.params.requestId}) :
        call("Fetch.fulfillRequest", {requestId:m.params.requestId, responseCode:200,
          responseHeaders:[{name:"Content-Type", value:"text/javascript"}],
          body:Buffer.from(stub).toString("base64")})).catch(e => errors.push(e));
    }
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails);
  });
  const evaluate = async expression => {
    const r = await call("Runtime.evaluate", {expression, returnByValue:true});
    assert.ok(!r.exceptionDetails, JSON.stringify(r.exceptionDetails)); return r.result.value;
  };
  const until = async expression => {
    for (let i = 0; i < 150; i++) { if (await evaluate(expression)) return; await sleep(40); }
    throw new Error("Timed out: " + expression);
  };
  await call("Page.enable"); await call("Runtime.enable");
  await call("Fetch.enable", {patterns:[{urlPattern:"*"}]});
  for (const width of [1280, 390, 320]) {
    const seed = await call("Page.addScriptToEvaluateOnNewDocument", {
      source:"localStorage.removeItem('elh_cc');"
    });
    external.length = 0;
    await call("Emulation.setDeviceMetricsOverride", {width,height:720,deviceScaleFactor:1,mobile:width<500});
    await call("Page.navigate", {url:origin});
    await until("!!document.getElementById('elh-cc')");
    await call("Page.removeScriptToEvaluateOnNewDocument", {identifier:seed.identifier});
    assert.equal(await evaluate("document.documentElement.scrollWidth<=innerWidth"), true);
    assert.equal(await evaluate("document.querySelectorAll('h1').length"), 1);
    assert.equal(external.some(url => /googletagmanager|clarity\.ms|cdn\.brevo/.test(url)), false);
    await evaluate("document.getElementById('elh-cc-mgbtn').click()");
    assert.equal(await evaluate("document.getElementById('elh-tog-all').checked"), false);
    assert.equal(await evaluate("document.activeElement.id"), "elh-tog-all");
    await evaluate("document.getElementById('elh-tog-all').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
    assert.equal(await evaluate("document.activeElement.id"), "elh-cc-mgbtn");
    await evaluate("document.getElementById('elh-cc-decl').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "essential");
    await call("Page.reload"); await until("document.readyState==='complete' && !!window.elhCookieSettings");
    assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
    await evaluate("document.getElementById('footer').focus();document.getElementById('footer').click()");
    assert.equal(await evaluate("document.getElementById('elh-cc-preferences').hidden"), false);
    await evaluate("document.getElementById('elh-tog-all').checked=true;document.getElementById('elh-cc-save').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "all");
    assert.equal(await evaluate("document.activeElement.id"), "footer");
    await until("window.__elhAnalyticsBooted===true");
    assert.equal(await evaluate("Array.from(dataLayer).filter(a=>a[0]==='config'&&a[1]==='AW-18384023405').length"), 1);
    await call("Page.reload"); await until("document.readyState==='complete' && !!window.elhCookieSettings");
    assert.equal(await evaluate("!!document.getElementById('elh-cc')"), false);
    await evaluate("elhCookieSettings()");
    assert.equal(await evaluate("document.getElementById('elh-tog-all').checked"), true);
    await evaluate("document.getElementById('elh-tog-all').checked=false;document.getElementById('elh-cc-save').click()");
    await until("document.readyState==='complete' && localStorage.getItem('elh_cc')==='essential' && !window.__elhAnalyticsBooted && !document.getElementById('elh-cc')");
    await evaluate("elhCookieSettings();document.getElementById('elh-cc-okbtn').click()");
    assert.equal(await evaluate("localStorage.getItem('elh_cc')"), "all");
    console.log(`PASS ${width}px: consent defaults, no early tracking, keyboard, persistence, footer, save, accept all and revocation`);
  }
  assert.deepEqual(errors, []);
} finally {
  ws?.close(); browser.kill("SIGTERM");
  if (browser.exitCode === null) await new Promise(resolve => browser.once("exit", resolve));
  server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  await rm(profile, {recursive:true,force:true,maxRetries:5,retryDelay:150});
}
