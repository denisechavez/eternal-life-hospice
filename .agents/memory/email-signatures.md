---
name: Email signatures
description: How ELH HTML email signatures are built and the remote-logo gotcha.
---

# Email signatures (exports/email/)

HTML email signatures mirror the business card (mark + name/title + 24/7 phone +
email + website + address + Medicare/CDPH/ACHC + Ventura & LA County coverage).

**Email-safe build rules:** table layout (no flex/grid), all styles inline (Gmail
strips `<style>`, Outlook ignores web fonts), web-safe font fallbacks — Georgia for
the name (echoes Fraunces), Arial for the rest (echoes Jost). Brand fonts cannot
load in email; colors + logo carry the brand.

**Remote-logo gotcha:** signatures reference the logo by absolute URL
`https://eternallifehospice.com/assets/logo-eternal-trans.png`. Email clients can
only fetch a published image — local/repo paths won't work.
**Why:** at build time `logo-eternal-trans.png` 404'd live (only logo-eternal/plum/
cream/og-logo were deployed); the trans mark is in `website/elh-preview/assets/` and
goes live on the next Git→Sync.
**How to apply:** any email/remote-embedded collateral must point at an
already-deployed asset, or the how-to must tell the user to sync once first.
