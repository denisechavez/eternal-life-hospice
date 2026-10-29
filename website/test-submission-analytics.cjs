#!/usr/bin/env node
'use strict';

// Run the actual intake-page submission handlers with synthetic responses.
// No real requests, visitor data or third-party scripts are used. This VM suite
// tests submission outcomes, not the rendered Nimbata integration.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const { webcrypto } = require('node:crypto');
const read = name => fs.readFileSync(path.join(__dirname, 'elh-preview', name), 'utf8');
const analytics = read('assets/analytics.js').split('/* ── Analytics init')[0] + '\nbindCustomEvents();\n})();';
const security = read('assets/intake-security.js').replace(/^export /gm, '') +
  '\nglobalThis.intakeSecurity = { submit, showFailure };';
const leadFailure = 'function leadFail(' + read('index.html').split('  function leadFail(')[1]
  .split("  document.querySelectorAll('form.lead-form')")[0];
const home = read('index.html').split("  document.querySelectorAll('form.lead-form').forEach(function(f){")[1]
  .split('  // header phone pill')[0];
const scripts = [...read('refer.html').matchAll(/<script>([\s\S]*?)<\/script>/g)];
const referral = scripts.find(match => match[1].includes("var f=document.getElementById('referForm')"))[1];

const flush = () => new Promise(resolve => setImmediate(resolve));
const adsDestination = 'AW-18384023405/JC8lCKGQ9qsdEO3el75E';

function setup(isReferral, consent = 'all', formName = 'elh-family') {
  if (isReferral) formName = 'elh-physician';
  const events = [], ga = [], handlers = {}, securityRequests = [], posts = [];
  let shown = 0, failed = 0, pending;
  let securityResponse = { ok: true, data: { token: 'SYNTHETIC-SECURITY', waitMs: 0, siteKey: '' } };
  let storageThrows = false;
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
  function element() {
    return {
      style: {}, setAttribute() {}, scrollIntoView() {}, appendChild() {},
      querySelector() { return element(); }
    };
  }
  function response(status, data, malformed = false) {
    return {
      status, ok: status >= 200 && status < 300,
      json: () => malformed ? Promise.reject(new Error('invalid json')) : Promise.resolve(data),
      clone: () => response(status, data, malformed)
    };
  }
  const window = {
    location: { pathname: isReferral ? '/refer' : '/' },
    // Only the security wait runs here: no browser/third-party scripts are loaded.
    setTimeout(callback) { queueMicrotask(callback); return 1; },
    clearTimeout() {},
    umami: { track(name, data) { events.push({ name, data: JSON.parse(JSON.stringify(data)) }); } },
    gtag(command, name, data) { ga.push({ command, name, data: JSON.parse(JSON.stringify(data)) }); }
  };
  const context = vm.createContext({
    window, location: window.location,
    localStorage: { getItem(key) {
      assert.equal(key, 'elh_cc');
      if (storageThrows) throw new Error('storage unavailable');
      return consent;
    } },
    document: {
      addEventListener() {},
      querySelectorAll() { return [form]; },
      getElementById() { return form; },
      createElement: element
    },
    URL, URLSearchParams, crypto: webcrypto,
    FormData: class {
      forEach(callback) {
        callback(formName, 'form-name');
        callback('private@example.test', 'email');
        callback('PRIVATE-NAME', 'name');
        callback('PRIVATE-CLINICAL-NOTE', 'message');
      }
    },
    fetch(url, options) {
      assert.equal(options.credentials, 'same-origin');
      if (url.startsWith('/api/form-security?')) {
        assert.equal(url, '/api/form-security?form=' + formName);
        assert.equal(options.cache, 'no-store');
        assert.match(options.headers['X-ELH-Intake-Proof'], /^[a-f0-9]{64}$/);
        securityRequests.push(options);
        return Promise.resolve(response(securityResponse.ok ? 200 : 503, securityResponse.data));
      }
      assert.equal(url, '/api/form-submit', 'unexpected network request');
      assert.equal(options.method, 'POST');
      const body = new URLSearchParams(options.body);
      assert.equal(body.get('form-name'), formName);
      assert.equal(body.get('_elh_security'), 'SYNTHETIC-SECURITY');
      assert.equal(body.get('_elh_browser_proof'),
        securityRequests.at(-1).headers['X-ELH-Intake-Proof']);
      posts.push(options);
      assert.equal(pending, undefined, 'only one POST may be pending');
      return new Promise((resolve, reject) => { pending = { resolve, reject }; });
    },
    leadShow() { shown++; }
  });
  vm.runInContext(analytics, context);
  // vm.Script cannot import browser ES modules on the normal Node command.
  // Bridge only the import; evaluate the real shared module in the same realm.
  vm.runInContext(security, context);
  vm.runInContext(leadFailure, context);
  const handler = isReferral ? referral :
    "document.querySelectorAll('form.lead-form').forEach(function(f){" + home;
  assert.equal(handler.split("import('/assets/intake-security.js')").length, 2);
  vm.runInContext(handler.replace("import('/assets/intake-security.js')",
    'Promise.resolve(globalThis.intakeSecurity)'), context);
  return {
    window, events, ga,
    async submit() {
      handlers.submit({ preventDefault() {} });
      await flush(); // Import, security GET and wait must finish before responding.
    },
    async respond(status = 200, data = { ok: true, accepted: true, receipt_id: 'PRIVATE' }, malformed = false) {
      assert.ok(pending, 'expected a pending synthetic submission');
      const { resolve } = pending;
      pending = undefined;
      resolve(response(status, data, malformed));
      await flush();
    },
    async disconnect() {
      assert.ok(pending, 'expected a pending synthetic submission');
      const { reject } = pending;
      pending = undefined;
      reject(new Error('synthetic network failure'));
      await flush();
    },
    consent(value) { consent = value; },
    denyStorage() { storageThrows = true; },
    securityResponse(value) { securityResponse = value; },
    state() { return form.__elhSubmissionState; },
    counts() { return { shown, failed, requests: posts.length }; },
    securityCount() { return securityRequests.length; },
    outcomes() { return ga.filter(event => event.name === 'form_success'); },
    ads() { return ga.filter(event => event.name === 'conversion'); }
  };
}

function assertNoOutcomes(app) {
  assert.deepEqual(app.events, []);
  assert.deepEqual(app.ga, []);
}

function assertAccepted(app, isReferral) {
  const form = isReferral ? 'elh-physician' : 'elh-family';
  const page = isReferral ? '/refer' : '/';
  assert.deepEqual(app.events, [{ name: 'form_success', data: { page, form } }]);
  assert.deepEqual(app.outcomes(), [{
    command: 'event', name: 'form_success',
    data: { source_page: page, form, submission_type: isReferral ? 'referral' : 'care',
      send_to: 'G-WTMEYKXW8H' }
  }]);
  assert.deepEqual(app.ads(), [{
    command: 'event', name: 'conversion',
    data: { send_to: adsDestination, value: 1, currency: 'USD' }
  }]);
  assert.equal(app.ga.length, 2, 'no additional Google events');
  assert.ok(!/PRIVATE|private@example|SYNTHETIC-SECURITY|browser_proof|turnstile/i
    .test(JSON.stringify([...app.events, ...app.ga])));
}

for (const isReferral of [false, true]) {
  const page = isReferral ? 'referral' : 'home';
  test(`${page}: only accepted responses count, once per form in both destinations`, async () => {
    const app = setup(isReferral);
    const first = app.submit();
    const duplicate = app.submit(); // Rapid duplicate while pending.
    await Promise.all([first, duplicate]);
    assertNoOutcomes(app);
    assert.equal(app.counts().requests, 1);
    assert.equal(app.securityCount(), 1);
    await app.respond();
    await app.submit(); // Duplicate after accepted.
    assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
    assert.equal(app.securityCount(), 1);
    assertAccepted(app, isReferral);
  });

  test(`${page}: explicit rejection produces no outcomes and allows a successful retry`, async () => {
    const app = setup(isReferral);
    await app.submit();
    await app.respond(400, { ok: false, accepted: false });
    assertNoOutcomes(app);
    assert.equal(app.state(), null);
    await app.submit();
    await app.respond();
    assert.deepEqual(app.counts(), { shown: 1, failed: 1, requests: 2 });
    assertAccepted(app, isReferral);
  });

  test(`${page}: uncertain, malformed and unaccepted responses do not count or allow duplicate delivery`, async () => {
    for (const [status, data, malformed] of [
      [500, { ok: true, accepted: true }, false],
      [200, { ok: false, accepted: true }, false],
      [200, { ok: true, accepted: false }, false],
      [200, { ok: true }, false],
      [200, null, false],
      [200, null, true],
      [503, { ok: false }, false],
      [200, { ok: 1, accepted: true }, false],
      [200, { ok: true, accepted: 'true' }, false]
    ]) {
      const app = setup(isReferral);
      await app.submit();
      await app.respond(status, data, malformed);
      assertNoOutcomes(app);
      assert.equal(app.state(), 'unknown');
      await app.submit();
      assert.deepEqual(app.counts(), { shown: 0, failed: 1, requests: 1 });
      assert.equal(app.securityCount(), 1);
    }
  });

  test(`${page}: failed verification emits nothing, never posts and permits retry`, async () => {
    for (const securityResponse of [
      { ok: false },
      { ok: true, data: { token: '', waitMs: 0 } },
      { ok: true, data: { token: 'SYNTHETIC-SECURITY', waitMs: -1 } }
    ]) {
      const app = setup(isReferral);
      app.securityResponse(securityResponse);
      await app.submit();
      assertNoOutcomes(app);
      assert.deepEqual(app.counts(), { shown: 0, failed: 1, requests: 0 });
      assert.equal(app.state(), null);
      app.securityResponse({ ok: true, data: { token: 'SYNTHETIC-SECURITY', waitMs: 0 } });
      await app.submit();
      await app.respond();
      assertAccepted(app, isReferral);
    }
  });

  test(`${page}: lost POST response is not an outcome and cannot be resubmitted`, async () => {
    const app = setup(isReferral);
    await app.submit();
    await app.disconnect();
    await app.submit();
    assertNoOutcomes(app);
    assert.equal(app.state(), 'unknown');
    assert.deepEqual(app.counts(), { shown: 0, failed: 1, requests: 1 });
  });

  test(`${page}: denied, absent, revoked or unreadable consent still accepts without analytics`, async () => {
    for (const mode of ['essential', 'absent', 'revoked', 'unreadable']) {
      const app = setup(isReferral, mode === 'essential' ? 'essential' : mode === 'absent' ? null : 'all');
      await app.submit();
      if (mode === 'revoked') app.consent('essential');
      if (mode === 'unreadable') app.denyStorage();
      await app.respond();
      assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
      assertNoOutcomes(app);
    }
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
      await app.submit();
      await app.respond();
      assert.deepEqual(app.counts(), { shown: 1, failed: 0, requests: 1 });
      if (mode === 'throw-umami') {
        assert.equal(app.outcomes().length, 1);
        assert.equal(app.ads().length, 1);
      }
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
    await app.submit();
    await app.respond();
    assert.equal(app.outcomes()[0].data.submission_type, kind);
  }
});
