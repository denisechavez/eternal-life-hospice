#!/usr/bin/env node
/**
 * Regression guard for the public worksheet and injected callback form.
 *
 * These controls are generated or injected at runtime, so this guard checks
 * the source contracts that keep their labels and table relationships intact.
 * It specifically protects against duplicate callback IDs on repeat use and
 * against the worksheet row header losing its mobile stacked layout.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const BASE = path.join(__dirname, '..');
const FAMILY_GUIDE = fs.readFileSync(path.join(BASE, 'family-guide.html'), 'utf8');
const CHAT = fs.readFileSync(path.join(__dirname, 'chat.js'), 'utf8');
let allPassed = true;

function check(condition, message) {
  if (condition) {
    console.log('  ✓', message);
  } else {
    console.error('  ✗ FAIL:', message);
    allPassed = false;
  }
}

console.log('\nAccessibility form regression check\n');

check(
  /table\.ws tbody,table\.ws tbody tr,table\.ws tbody th,table\.ws tbody td\{display:block;width:100%\}/.test(FAMILY_GUIDE),
  'mobile worksheet layout block-displays generated row headers and cells'
);
check(
  /function wsCell\(agency,row\)/.test(FAMILY_GUIDE) &&
    FAMILY_GUIDE.includes(`aria-labelledby="'+cellHeaders+'"` ) &&
    FAMILY_GUIDE.includes(`headers="'+cellHeaders+'"`),
  'generated worksheet fields reference both row and agency headers'
);
check(
  FAMILY_GUIDE.includes(`<th class="q" scope="row" id="'+questionId+'">`),
  'generated worksheet questions remain scoped row headers'
);
check(
  /var callbackInstance = 0;/.test(CHAT) &&
    /var callbackPrefix = "elhc-callback-" \+ \(\+\+callbackInstance\) \+ "-";/.test(CHAT),
  'callback form IDs include an incrementing instance prefix'
);

const callbackFields = ['name', 'phone', 'email', 'time', 'notes'];
callbackFields.forEach((field) => {
  check(
    CHAT.includes(`setAttribute("for", callbackPrefix + "${field}")`) &&
      CHAT.includes(`id = callbackPrefix + "${field}"`),
    `callback ${field} label and control use the same generated ID`
  );
});

if (!allPassed) process.exit(1);
console.log('\nSENTINEL: test-a11y-forms.js self-test OK');