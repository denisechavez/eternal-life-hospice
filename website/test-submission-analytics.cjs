#!/usr/bin/env node
'use strict';

// Run the actual intake-page submission handlers with synthetic responses.
// No real requests, visitor data or third-party scripts are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const read = name => fs.readFileSync(path.join(__dirname, 'elh-preview', name), 'utf8');
const analytics = read('assets/analytics.js').split('/* ── Analytics init')[0] + '\nbindCustomEvents();\n})();';
const home = read('index.html').split("  document.querySelectorAll('form.lead-form').forEach(function(f){")[1]
  .split('  // header phone pill')[0];
const scripts = [...read('refer.html').matchAll(/<script>([\s\S]*?)<\/script>/g)];
const referral = scripts.find(match => match[1].includes("var f=document.getElementById('referForm')"))[1];

function setup(isReferral, consent = 'all', formName = 'elh-family') {
  const events = [], ga = [], handlers = {};
  let shown = 0, failed = 0, requests = 0, resolve;
  const button = { textContent: 'Send', innerHTML: 'Send' };
  const form = {
    style: {}, nextSibling: null,
    getAttribute(name) { return name === 'name' ? formName : null; },
    setAttribute() {},
    querySelector(selector) { return selector.includes('button') || selector === '.af-submit' ? button : null; },
    addEventListener(name, handler) { handlers[name] = handler; },
    appendChild() { failed++; },
    parentNode: {
      querySelector() { return null; },
      insertBefore(element) { if (element.className === 'apply-success') shown++; else failed++; }
    }
  };
  const window = {
    location: { pathname: isReferral ? '/refer' : '/' },
    umami: { track(name, data) { events.push({ name, data: JSON.parse(JSON.stringify(data)) }); } },
    gtag(command, name, data) { ga.push({ command, name, data: JSON.parse(JSON.stringify(data)) }); }
  };
  const context = vm.createContext({
    window, location: window.location,
    localStorage: { getItem() { return consent; } },
    document: {
      addEventListener() {},
      querySelectorAll() { return [form]; },
      getElementById() { return form; },
      createElement() { return { setAttribute() {}, scrollIntoView() {} }; }
    },
    URL, URLSearchParams,
    FormData: class { forEach(callback) { callback('private@example.test', 'email'); } },
    fetch() { requests++; return new Promise(r => { resolve = r; }); },
    leadShow() { shown++; },
    leadFail() { failed++; }
  });
  vm.runInContext(analytics, context);
  vm.runInContext(isReferral ? referral :
    "document.querySelectorAll('form.lead-form').forEach(function(f){" + home, context);
  return {
    window, events, ga,
    submit() { handlers.submit({ preventDefault() {} }); },
    async respond(status = 200, data = { ok: true, accepted: true, receipt_id: 'PRIVATE' }, malformed = false) {
      resolve({ ok: status >= 200 && status < 300,
        json: () => malformed ? Promise.reject(new Error('invalid json')) : Promise.resolve(data) });
      await new Promise(r => setImmediate(r));
    },
    counts() { return { shown, failed, requests }; }
  };
}

for (const isReferral of [false, true]) {
  const page = isReferral ? 'referral' : 'home';
  test(`${page}: only accepted responses count, once per form in both destinations`, async () => {
    const app = setup(isReferral);
    app.submit();
    app.submit(); // Rapid duplicate while pending.
    assert.equal(app.events.length, 0);
    assert.equal(app.ga.length, 0);
    assert.equal(app.counts().requests, 1);
    await app.respond();
    app.submit(); // Duplicate after accepted.
    assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
    assert.deepEqual(app.events.map(e => e.name), ['form_success']);
    assert.deepEqual(app.ga.map(e => e.name), ['form_success']);
    assert.equal(app.ga[0].data.submission_type, isReferral ? 'referral' : 'care');
    assert.ok(!/PRIVATE|private@example/.test(JSON.stringify([...app.events, ...app.ga])));
  });

  test(`${page}: rejected, malformed and unaccepted responses produce no outcomes and allow retry`, async () => {
    const app = setup(isReferral);
    for (const [status, data, malformed] of [
      [500, { ok: true, accepted: true }, false],
      [200, { ok: false, accepted: true }, false],
      [200, { ok: true, accepted: false }, false],
      [200, { ok: true }, false],
      [200, null, false],
      [200, null, true]
    ]) {
      app.submit();
      await app.respond(status, data, malformed);
      assert.equal(app.events.length, 0);
      assert.equal(app.ga.length, 0);
    }
    app.submit();
    await app.respond();
    assert.deepEqual(app.counts(), { shown: 1, failed: 6, requests: 7 });
    assert.equal(app.ga.length, 1);
  });

  test(`${page}: essential-only consent still accepts submission with no analytics`, async () => {
    const app = setup(isReferral, 'essential');
    app.submit();
    await app.respond();
    assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
    assert.equal(app.events.length, 0);
    assert.equal(app.ga.length, 0);
  });

  test(`${page}: tracker failures cannot turn accepted submission into an error`, async () => {
    for (const mode of ['throw-umami', 'throw-ga', 'throw-hook', 'reject-both', 'absent-both']) {
      const app = setup(isReferral);
      if (mode === 'throw-umami') app.window.umami.track = () => { throw new Error('Umami failed'); };
      if (mode === 'throw-ga') app.window.gtag = () => { throw new Error('GA failed'); };
      if (mode === 'throw-hook') app.window.elhTrackEvent = () => { throw new Error('hook failed'); };
      if (mode === 'reject-both') {
        app.window.umami.track = app.window.gtag = () => Promise.reject(new Error('network failed'));
      }
      if (mode === 'absent-both') { delete app.window.umami; delete app.window.gtag; }
      app.submit();
      await app.respond();
      assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
      if (mode === 'throw-umami') assert.equal(app.ga.length, 1);
      if (mode === 'throw-ga') assert.equal(app.events.length, 1);
    }
  });
}

test('homepage professional-contact forms are not counted as care or referral requests', async () => {
  for (const [form, kind] of [
    ['elh-physician', 'referral'], ['elh-casemanager', 'referral'],
    ['elh-coordinator', 'professional_contact'], ['elh-voice', 'team_contact']
  ]) {
    const app = setup(false, 'all', form);
    app.submit();
    await app.respond();
    assert.equal(app.ga[0].data.submission_type, kind);
  }
});
