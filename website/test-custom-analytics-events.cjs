#!/usr/bin/env node
'use strict';

// Exercise the actual shared event handlers without starting third-party trackers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(path.join(__dirname, 'elh-preview/assets/analytics.js'), 'utf8');
const handlers = source.split('/* ── Analytics init')[0] + '\nbindCustomEvents();\n})();';

function setup(initialConsent = 'all') {
  let consent = initialConsent;
  const events = [];
  const gaEvents = [];
  const listeners = {};
  const window = {
    location: { pathname: '/', href: 'https://example.test/', origin: 'https://example.test' },
    umami: { track(name, data) { events.push({ name, data: JSON.parse(JSON.stringify(data)) }); } }
  };
  window.gtag = (command, name, data) => {
    assert.equal(data.send_to, 'G-WTMEYKXW8H',
      'Care and reading events must not broadcast to the Ads destination');
    const payload = JSON.parse(JSON.stringify(data));
    delete payload.send_to;
    gaEvents.push({ command, name, data: payload });
  };
  const context = vm.createContext({
    window,
    localStorage: { getItem() { return consent; } },
    document: { addEventListener(name, callback) { listeners[name] = callback; } },
    URL
  });
  vm.runInContext(handlers, context);
  return {
    window, events, gaEvents,
    reload() { vm.runInContext(handlers, context); },
    consent(value) { consent = value; },
    fire(name, target) {
      // Any attempt to cancel/delay navigation makes this check fail.
      listeners[name]({ target, preventDefault() { throw new Error('navigation blocked'); } });
    }
  };
}

function link(href, placement = 'content', download = false) {
  return {
    getAttribute(name) { return name === 'href' ? href : null; },
    hasAttribute(name) { return name === 'download' && download; },
    classList: { contains() { return false; } },
    closest(selector) {
      if (selector === 'a[href]') return this;
      return selector === placement ? this : null;
    }
  };
}

function form() {
  const attrs = { name: 'elh-family' };
  return {
    tagName: 'FORM',
    querySelector() { return null; },
    getAttribute(name) { return attrs[name] || null; },
    setAttribute(name, value) { attrs[name] = value; },
    closest(selector) { return selector === 'form' ? this : null; }
  };
}

test('care requests are distinct from team-contact clicks', () => {
  const app = setup();
  app.fire('click', link('/?lead=family#leadcap', 'header'));
  app.fire('click', link('/?lead=family'));
  app.fire('click', link('/?lead=voice#leadcap'));
  app.fire('click', link('/#leadcap'));
  assert.deepEqual(app.events.map(e => e.name), [
    'request_care_click', 'request_care_click', 'contact_team_click', 'contact_cta_click'
  ]);
  assert.deepEqual(app.events[0].data, { page: '/', placement: 'header' });
  assert.deepEqual(app.gaEvents.map(e => e.name), ['request_care_click', 'request_care_click']);
  assert.deepEqual(app.gaEvents[0].data, { source_page: '/', destination_page: '/', placement: 'header' });
});

function readingLink(href = '/services', overrides = {}) {
  const anchor = link(href);
  const attrs = {
    'data-reading-source': '/hospice-care',
    'data-reading-destination': '/services',
    'data-reading-topic': 'services',
    ...overrides
  };
  const get = anchor.getAttribute;
  const closest = anchor.closest.bind(anchor);
  anchor.getAttribute = name => name in attrs ? attrs[name] : get(name);
  anchor.closest = selector => selector === '.elh-related' ? {} : closest(selector);
  return anchor;
}

test('curated reading sends fixed metadata to GA4 only, including nested clicks', () => {
  const app = setup();
  app.window.location.pathname = '/hospice-care';
  app.window.location.href = 'https://example.test/hospice-care?email=private@example.test#patient';
  const anchor = readingLink('/services?email=private@example.test#patient');
  anchor.textContent = 'Patient private@example.test';
  app.fire('click', { closest: selector => anchor.closest(selector) });
  assert.deepEqual(app.gaEvents, [{
    command: 'event', name: 'related_reading_click',
    data: { source_page: '/hospice-care', destination_page: '/services', topic: 'services' }
  }]);
  assert.equal(app.events.length, 0);
});

test('reading is suppressed without consent and immediately after revocation', () => {
  for (const consent of ['essential', null]) {
    const app = setup(consent);
    app.fire('click', readingLink());
    assert.equal(app.gaEvents.length, 0);
  }
  const app = setup();
  app.fire('click', readingLink());
  app.consent('essential');
  app.fire('click', readingLink());
  assert.equal(app.gaEvents.length, 1);
});

test('ordinary links and malformed or free-form reading metadata are excluded', () => {
  const app = setup();
  app.fire('click', link('/services'));
  for (const overrides of [
    { 'data-reading-source': null },
    { 'data-reading-source': '/?email=private@example.test' },
    { 'data-reading-destination': '/services#patient' },
    { 'data-reading-destination': 'https://other.test/services' },
    { 'data-reading-topic': 'Patient details' }
  ]) app.fire('click', readingLink('/services', overrides));
  assert.equal(app.gaEvents.length, 0);
});

test('missing, throwing and rejecting GA4 never interrupt reading navigation', async () => {
  const app = setup();
  delete app.window.gtag;
  assert.doesNotThrow(() => app.fire('click', readingLink()));
  app.window.gtag = () => { throw new Error('GA4 unavailable'); };
  assert.doesNotThrow(() => app.fire('click', readingLink()));
  app.window.gtag = () => Promise.reject(new Error('network unavailable'));
  assert.doesNotThrow(() => app.fire('click', readingLink()));
  await new Promise(resolve => setImmediate(resolve));
});

test('reading instrumentation preserves care and referral conversions on the same links', () => {
  const app = setup();
  app.fire('click', readingLink('/refer#referral-form', {
    'data-reading-destination': '/refer', 'data-reading-topic': 'referral'
  }));
  app.fire('click', readingLink('/?lead=family#leadcap', {
    'data-reading-destination': '/', 'data-reading-topic': 'care'
  }));
  assert.deepEqual(app.events.map(e => e.name), ['referral_cta_click', 'request_care_click']);
  assert.deepEqual(app.gaEvents.map(e => e.name), [
    'related_reading_click', 'referral_cta_click', 'related_reading_click', 'request_care_click'
  ]);
});

test('nested category targets emit only predefined categories, never input text', () => {
  const app = setup();
  for (const value of ['family', 'physician', 'casemanager', 'coordinator', 'voice', 'patient@example.test']) {
    const category = { getAttribute() { return value; } };
    app.fire('click', { closest(selector) {
      return selector === '.lead-cat[data-cat]' ? category : null;
    } });
  }
  assert.deepEqual(app.events.map(e => e.data.lead_type),
    ['family', 'physician', 'casemanager', 'coordinator', 'voice']);
  assert.ok(app.events.every(e => e.name === 'lead_type_selected'));
  assert.ok(!JSON.stringify(app.events).includes('patient@example.test'));
});

test('essential-only and missing consent suppress every event', () => {
  for (const consent of ['essential', null]) {
    const app = setup(consent);
    app.fire('click', link('/?lead=family#leadcap'));
    app.fire('click', link('tel:18059537273'));
    app.fire('submit', form());
    app.fire('click', link('/refer#referral-form'));
    app.window.elhTrackEvent('form_success', { page: '/', form: 'elh-family' });
    assert.equal(app.events.length, 0);
    assert.equal(app.gaEvents.length, 0);
  }
});

test('revoking consent suppresses subsequent events', () => {
  const app = setup();
  app.fire('click', link('tel:18059537273'));
  app.consent('essential');
  app.fire('click', link('tel:18059537273'));
  assert.equal(app.events.length, 1);
});

test('form starts remain eligible until consent and tracker are available', () => {
  const app = setup('essential');
  const target = form();
  app.fire('focusin', target);
  assert.equal(target.getAttribute('data-analytics-started'), null);
  app.consent('all');
  const tracker = app.window.umami;
  delete app.window.umami;
  app.fire('focusin', target);
  assert.equal(target.getAttribute('data-analytics-started'), null);
  app.window.umami = tracker;
  app.fire('focusin', target);
  app.fire('focusin', target);
  app.fire('submit', target);
  assert.deepEqual(app.events.map(e => e.name), ['form_start', 'form_submit']);
  assert.deepEqual(app.events[0].data, { page: '/', form: 'elh-family' });
});

test('tracker exceptions cannot interrupt interactions', () => {
  const app = setup();
  app.window.umami.track = () => { throw new Error('tracker unavailable'); };
  assert.doesNotThrow(() => app.fire('click', link('/?lead=family#leadcap')));
  assert.equal(app.window.elhTrackEvent('form_success', { form: 'elh-family' }), false);
});

test('rejected tracker promises are handled', async () => {
  const app = setup();
  app.window.umami.track = () => Promise.reject(new Error('network unavailable'));
  assert.doesNotThrow(() => app.fire('click', link('/?lead=family#leadcap')));
  await new Promise(resolve => setImmediate(resolve));
});

test('existing call, referral and download events still work without sensitive query data', () => {
  const app = setup();
  app.fire('click', link('tel:18059537273', 'footer'));
  app.fire('click', link('/refer#send-referral'));
  app.fire('click', link('/family-guide.pdf?email=private@example.test'));
  app.fire('click', link('https://other.test/?lead=family#leadcap'));
  assert.deepEqual(app.events.map(e => e.name), ['phone_click', 'referral_cta_click', 'resource_download']);
  assert.deepEqual(app.events[2].data, { page: '/', placement: 'content', resource: 'family-guide.pdf' });
  assert.ok(!JSON.stringify(app.events).includes('private@example.test'));
});

test('GA4 mirrors only allowlisted successful forms with fixed outcome categories', () => {
  const app = setup();
  for (const name of ['elh-family', 'elh-physician', 'elh-casemanager', 'elh-coordinator', 'elh-voice', 'unknown']) {
    app.window.elhTrackEvent('form_success', {
      page: '/', form: name, email: 'private@example.test', receipt_id: 'PRIVATE',
      message: 'Patient details', destination_page: '/?patient=PRIVATE'
    });
  }
  assert.equal(app.events.length, 6); // Original Umami hook unchanged.
  assert.deepEqual(app.gaEvents.map(e => e.data.submission_type),
    ['care', 'referral', 'referral', 'professional_contact', 'team_contact']);
  assert.deepEqual(app.gaEvents[0], {
    command: 'event', name: 'form_success',
    data: { source_page: '/', form: 'elh-family', submission_type: 'care' }
  });
  assert.ok(!/PRIVATE|private@example|Patient details/.test(JSON.stringify(app.gaEvents)));
  app.window.elhTrackEvent('form_success', { page: '/?email=private@example.test', form: 'elh-family' });
  app.window.elhTrackEvent('form_success', { page: '/refer#private', form: 'elh-physician' });
  assert.equal(app.gaEvents.length, 5);
  app.window.elhTrackEvent('form_success', { page: '/refer.html', form: 'elh-physician' });
  assert.equal(app.gaEvents[5].data.source_page, '/refer');
});

test('missing or failing Umami does not stop GA4 outcomes; failing GA4 does not stop Umami', async () => {
  const app = setup();
  const original = app.window.umami;
  delete app.window.umami;
  app.fire('click', link('/?lead=family'));
  app.window.umami = { track() { throw new Error('Umami failed'); } };
  app.window.elhTrackEvent('form_success', { page: '/', form: 'elh-family' });
  app.window.umami.track = () => Promise.reject(new Error('Umami rejected'));
  app.fire('click', link('/refer'));
  assert.equal(app.gaEvents.length, 3);
  app.window.umami = original;
  for (const ga of [undefined, () => { throw new Error('GA failed'); },
    () => Promise.reject(new Error('GA rejected'))]) {
    app.window.gtag = ga;
    app.window.elhTrackEvent('form_success', { page: '/refer', form: 'elh-physician' });
  }
  assert.equal(app.events.length, 3);
  await new Promise(resolve => setImmediate(resolve));
});

test('duplicate loader execution does not duplicate click listeners or outcomes', () => {
  const app = setup();
  app.reload();
  app.fire('click', link('/refer'));
  app.window.elhTrackEvent('form_success', { page: '/refer', form: 'elh-physician' });
  assert.deepEqual(app.events.map(e => e.name), ['referral_cta_click', 'form_success']);
  assert.deepEqual(app.gaEvents.map(e => e.name), ['referral_cta_click', 'form_success']);
});

test('consent revoked before accepted submission suppresses both destinations', () => {
  const app = setup();
  app.consent('essential');
  app.window.elhTrackEvent('form_success', { page: '/', form: 'elh-family' });
  assert.equal(app.events.length, 0);
  assert.equal(app.gaEvents.length, 0);
});

test('full loader boots GA4 once and checks consent again at window load', () => {
  for (const revoke of [false, true]) {
    let consent = 'all';
    const load = [], appended = [];
    const context = {
      __noClarity: true,
      location: { pathname: '/', search: '', hash: '' },
      localStorage: { getItem() { return consent; } },
      document: {
        readyState: 'loading', URL: 'https://example.test/', referrer: '',
        addEventListener() {},
        createElement() { return { setAttribute() {} }; },
        head: { appendChild(el) { appended.push(el); } },
        body: { appendChild(el) { appended.push(el); } }
      },
      addEventListener(name, callback) { if (name === 'load') load.push(callback); },
      URL
    };
    context.window = context;
    vm.createContext(context);
    vm.runInContext(source, context);
    vm.runInContext(source, context); // No duplicate loaders or listeners.
    if (revoke) consent = 'essential';
    load.forEach(callback => { callback(); callback(); });
    assert.equal(appended.filter(el => (el.src || '').includes('googletagmanager.com')).length, revoke ? 0 : 1);
    const config = (context.dataLayer || []).filter(args => args[0] === 'config');
    assert.equal(config.length, revoke ? 0 : 2);
    assert.deepEqual(Array.from(config, args => args[1]),
      revoke ? [] : ['G-WTMEYKXW8H', 'AW-18384023405']);
    // Exercise the public hook in the complete loader too: textual merges can
    // leave helpers outside its closure or accidentally remove the assignment.
    assert.equal(typeof context.elhTrackEvent, 'function');
    assert.doesNotThrow(() => context.elhTrackEvent('form_success', {
      page: '/', form: 'elh-family'
    }));
    const outcomes = (context.dataLayer || []).filter(args =>
      args[0] === 'event' && args[1] === 'form_success');
    assert.equal(outcomes.length, revoke ? 0 : 1);
    if (!revoke) assert.equal(outcomes[0][2].send_to, 'G-WTMEYKXW8H');
  }
});