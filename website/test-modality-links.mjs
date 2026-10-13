// Run: node --experimental-websocket website/test-modality-links.mjs
// Uses installed Chromium; no browser packages or production mutations.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const base = process.env.REPLIT_DEV_DOMAIN
  ? `https://${process.env.REPLIT_DEV_DOMAIN}` : 'http://127.0.0.1:5000';
const profile = await mkdtemp(join(tmpdir(), 'elh-modality-test-'));
const browser = spawn('chromium', ['--headless', '--no-sandbox', '--disable-dev-shm-usage',
  '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'],
  { stdio: 'ignore' });
let ws;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  let port;
  for (let i = 0; i < 100; i++) {
    try { port = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break; }
    catch { await sleep(100); }
  }
  assert.ok(port, 'Chromium debugging port available');
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (pending.has(message.id)) {
      const callback = pending.get(message.id); pending.delete(message.id);
      if (message.error) callback.reject(new Error(JSON.stringify(message.error)));
      else callback.resolve(message.result);
    }
  });
  function call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const requestId = ++id; pending.set(requestId, { resolve, reject });
      ws.send(JSON.stringify({ id: requestId, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', { expression, returnByValue: true });
    assert.ok(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function waitFor(expression) {
    for (let i = 0; i < 200; i++) {
      try { if (await evaluate(expression)) return; } catch { /* Context changes during navigation. */ }
      await sleep(100);
    }
    throw new Error(`Timed out: ${expression}`);
  }
  await call('Page.enable');
  await call('Page.navigate', { url: base + '/resources/comfort-therapies' });
  await waitFor(`document.querySelectorAll('li a[href^="/#therapy-"]').length===9`);
  const links = await evaluate(`Array.from(document.querySelectorAll('li a[href^="/#therapy-"]')).map(a=>({text:a.textContent,href:a.getAttribute('href')}))`);
  assert.equal(new Set(links.map(link => link.href)).size, 9);
  for (const link of links) {
    // Follow the actual resource link, not a constructed substitute.
    await call('Page.navigate', { url: base + link.href });
    const cardId = link.href.split('#')[1];
    await waitFor(`document.getElementById(${JSON.stringify(cardId)})?.getAttribute('aria-expanded')==='true'`);
    await waitFor(`document.readyState==='complete' && document.fonts.status==='loaded'`);
    await sleep(400);
    const state = await evaluate(`(()=>{
      const card=document.getElementById(${JSON.stringify(cardId)});
      return {open:card.classList.contains('open'),focused:document.activeElement===card,
        detailHeight:card.querySelector('.mod-detail').getBoundingClientRect().height,
        top:card.getBoundingClientRect().top,headerBottom:document.getElementById('hdr').getBoundingClientRect().bottom,
        headingTop:card.querySelector('.mod-name').getBoundingClientRect().top,
        scrollY:window.scrollY,bodyScroll:document.body.scrollTop,htmlScroll:document.documentElement.scrollTop,
        margin:getComputedStyle(card).scrollMarginTop,hash:location.hash,
        root:document.scrollingElement.tagName,
        htmlOverflow:getComputedStyle(document.documentElement).overflowY,bodyOverflow:getComputedStyle(document.body).overflowY};
    })()`);
    assert.ok(state.open && state.focused && state.detailHeight > 0, JSON.stringify(state));
    // The requested target is the descriptive heading/text, not the photo's top.
    assert.ok(state.headingTop >= state.headerBottom - 2, `${link.text}: ${JSON.stringify(state)}`);
    console.log('PASS', link.text, link.href);
  }
  await evaluate(`location.hash='#therapy-music'`);
  await waitFor(`document.getElementById('therapy-music').getAttribute('aria-expanded')==='true' && document.activeElement.id==='therapy-music'`);
  await call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter' });
  await call('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter' });
  assert.equal(await evaluate(`document.getElementById('therapy-music').getAttribute('aria-expanded')`), 'false');
  console.log('PASS same-page hash navigation and keyboard toggle');
  await call('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await call('Page.navigate', { url: base + '/#therapy-doula' });
  await waitFor(`document.getElementById('therapy-doula')?.getAttribute('aria-expanded')==='true'`);
  await sleep(400);
  assert.ok(await evaluate(`document.getElementById('therapy-doula').querySelector('.mod-name').getBoundingClientRect().top>=document.getElementById('hdr').getBoundingClientRect().bottom-2`));
  console.log('PASS mobile doula deep link');
} finally {
  ws?.close();
  browser.kill('SIGTERM');
  await new Promise(resolve => browser.once('exit', resolve));
  await rm(profile, { recursive: true, force: true });
}
