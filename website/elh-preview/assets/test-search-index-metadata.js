'use strict';
const assert = require('node:assert/strict');
const { extractMeta, extractTitle } = require('./build-search-index.js');

assert.equal(extractMeta(
  '<meta name="description" content="Discuss the patient\'s care and family\'s questions.">',
  'description'), "Discuss the patient's care and family's questions.");
assert.equal(extractMeta(
  '<meta content=\'Ask about "comfort care" and support.\' name=\'description\'>',
  'description'), 'Ask about "comfort care" and support.');
assert.equal(extractMeta(
  '<meta property="og:description" content="Care &amp; support &quot;at home&quot;.">',
  'og:description'), 'Care & support "at home".');
assert.equal(extractMeta(
  '<meta content="A patient\'s next steps" NAME="DESCRIPTION">',
  'description'), "A patient's next steps");
assert.equal(extractMeta(
  '<meta name="description" content="Ask whether support > supervision.">',
  'description'), 'Ask whether support > supervision.');
assert.equal(extractMeta('<meta name="robots" content="index,follow">', 'description'), null);
assert.equal(extractTitle(
  '<title>Acton Hospice Care | Eternal Life Hospice</title>'), 'Acton Hospice Care');
console.log('Search metadata: 7 quote, entity, ordering and title checks passed.');