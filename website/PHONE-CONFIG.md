# Website main phone

Edit `main` in `website-contact.json` for an **approved website-only** number
change, using ten US digits (no country code or punctuation). Keep the outgoing
number in `previousWebsiteNumbers`: existing static pages and approved Journal
snapshots can still contain it. Do not remove historical aliases while public
sources still use them.

Restart the website after changing the setting. The Python server projects it
into public HTML, employee-card company-phone downloads, the public intake,
security, coverage and chat API responses, discovery
text, search responses, `.well-known` metadata and the two intake JavaScript
assets. Browser URLs are versioned from projected bytes, including the setting.
No browser configuration fetch is needed for failure/recovery call links.

Python fragments/footer generation and the Node search-index builder share this
setting. The Node projection lives in `website-phone.cjs`; its parity with Python
is covered by `test-website-phone-config.py`. Old literals in source documents
are migration inputs, not additional settings to edit. Metadata and browser
source files may use `__ELH_MAIN_DISPLAY__` and `__ELH_MAIN_TEL__`; these are
resolved by the website server, not directly served as static files.

Do not run broad source replacements. In particular, do not rewrite approved
Journal source/snapshot bytes, acknowledgment templates, role email addresses,
employee identities, fax/other numbers, no-swap attributes, or external
Google/WhatConverts identity configuration. Existing company call links
(including referral labels and employee-card company downloads) retain their
current website projection behavior. Explicit office-labeled links, paragraphs
and office API fields remain separate; this setting does not redefine their roles.

Verify without sending email or publishing:

```
python3 website/test-website-phone-config.py
python3 website/test-website-phone.py
python3 website/test-footer-contact.py
node website/elh-preview/assets/build-search-index.js --check
```

The synthetic regression changes a copied setting in a temporary directory,
never the workspace or live site's number.
