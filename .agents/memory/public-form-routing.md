---
name: Public form routing
description: Operational constraint for ELH public forms across Google-hosted and Netlify deployments.
---

The public domain may serve the static site from Google infrastructure while the form markup and submission function are designed for Netlify. Netlify-specific form declarations do not forward same-origin posts from Google hosting to Netlify; the production host must run the form processor itself or be Netlify.

**Why:** The Google-hosted public endpoint returned a preview response to form POSTs while the client code treated its HTTP 200 as a successful referral. A visually successful confirmation is therefore not evidence that a team received a referral.

**How to apply:** Before changing DNS, host, forms, or success messaging, verify the actual public host, selected form processor, internal notification recipient, and an end-to-end non-PHI test. Treat an unverified inbox destination as unknown, even when source comments name one.