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
  const listeners = {};
  const window = {
    location: { pathname: '/', href: 'https://example.test/', origin: 'https://example.test' },
    umami: { track(name, data) { events.push({ name, data: JSON.parse(JSON.stringify(data)) }); } }
  };
  vm.runInNewContext(handlers, {
    window,
    localStorage: { getItem() { return consent; } },
    document: { addEventListener(name, callback) { listeners[name] = callback; } },
    URL
  });
  return {
    window, events,
    consent(value) { consent = value; },
    fire(name, target) { listeners[name]({ target }); }
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
    assert.equal(app.events.length, 0);
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