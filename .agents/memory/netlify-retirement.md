---
name: Netlify retirement
description: Freeze the legacy Netlify site before changing DNS or completing the Replit cutover.
---

Stop Netlify builds while the Replit cutover and DNS redirects are being verified; the current Netlify deployment remains available as a fallback.

**Why:** A stopped-build site preserves the known-good fallback without allowing new Git pushes or build hooks to change it during DNS propagation.

**How to apply:** Use Netlify's Build status → Stopped builds first. Do not delete the site or remove its deployed services until the canonical Replit site and every required domain redirect have been verified.