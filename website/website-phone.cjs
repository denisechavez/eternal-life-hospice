'use strict';

// Build-time counterpart of website_phone.py. Website settings only, not mail
// templates, employee identities, or Google/WhatConverts profile settings.
const config = require('./website-contact.json');
const main = config.main;
const aliases = new Set([...config.previousWebsiteNumbers, main]);
for (const number of aliases) {
  if (typeof number !== 'string' || !/^[2-9]\d{9}$/.test(number)) {
    throw new Error('Website phone settings must contain ten-digit US numbers');
  }
}
const display = `${main.slice(0, 3)}.${main.slice(3, 6)}.${main.slice(6)}`;
function publicPhoneText(text) {
  return text.replaceAll('__ELH_MAIN_DISPLAY__', display)
    .replaceAll('__ELH_MAIN_TEL__', '1' + main)
    .replace(/(?<!\d)(\+?1[ .-]?)?(\(?\d{3}\)?)([ .-]?)(\d{3})([ .-]?)(\d{4})(?!\d)/g,
      (match, country, area, first, middle, second, last) => {
        if (!aliases.has(area.replace(/\D/g, '') + middle + last)) return match;
        return (country || '') + area.replace(/\d{3}/, main.slice(0, 3))
          + first + main.slice(3, 6) + second + main.slice(6);
      });
}
module.exports = {publicPhoneText};
