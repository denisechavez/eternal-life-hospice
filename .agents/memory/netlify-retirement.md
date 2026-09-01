---
name: Netlify retirement
description: Freeze the legacy Netlify site before changing DNS or completing the Replit cutover.
---

The retirement target is to disable the Netlify project, not delete it, after the Replit cutover and DNS redirects are verified.

**Why:** Disabling takes the Netlify site offline so public traffic uses Replit, while preserving the project configuration and allowing the site to be re-enabled if needed. Stopped builds alone leave the old site publicly reachable.

**How to apply:** Use Build status → Stopped builds during the transition, then Project configuration → General → Danger zone → Disable project. Keep the project; do not choose Delete. Verify the canonical domain after disabling. Google may retain historical Netlify URLs temporarily, but canonical DNS, canonical tags, and the canonical sitemap direct indexing to Replit.