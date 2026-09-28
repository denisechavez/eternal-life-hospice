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

Internal workspace drafts that remain under the static source tree must be blocked
by the Replit server, not merely omitted from the sitemap or tagged `noindex`.

**Why:** `noindex` still returns the content to anyone who knows its URL; the
retired static-host configuration is not a protective layer.

**How to apply:** When adding work or QA artifacts, keep them outside the public
tree when possible; if tooling requires them there, enforce a 404 for both GET
and HEAD in development and production and exercise that in publish checks.