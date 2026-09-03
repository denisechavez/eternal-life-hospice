---
name: Netlify retired
description: Records the decision to remove the legacy fallback and use Replit Autoscale exclusively.
---

The legacy Netlify fallback is retired. Replit Autoscale is the only supported
production host, and the repository must not retain old Netlify configuration,
functions, plugins, redirects, or build scripts.

**Why:** The owner explicitly chose a clean future setup over preserving a dormant
fallback after the Replit cutover was verified.

**How to apply:** Keep hosting, APIs, redirects, security headers, and validation
Replit-native. If Netlify is ever requested again, configure it from scratch rather
than restoring the retired implementation.