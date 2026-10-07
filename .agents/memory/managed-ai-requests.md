---
name: Managed AI request paths
description: Avoid assuming a managed AI proxy has the public provider's versioned URL structure.
---

Treat the configured managed AI base URL as complete. Follow the existing
provider adapter instead of automatically appending an API-version prefix.

**Why:** A managed proxy accepted its configured chat-completions route but
returned INVALID_ENDPOINT when an extra `/v1` was appended. Public-provider
URL conventions do not necessarily apply to Replit-managed proxy routes.

**How to apply:** When adding offline authoring tools or other AI callers, use
the configured base verbatim and keep credentials inside runtime requests.
Diagnose endpoint errors from sanitized provider messages, never by printing
credentials or environment values.
