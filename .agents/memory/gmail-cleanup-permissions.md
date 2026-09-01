---
name: Gmail cleanup permissions
description: Permission boundary to expect when cleaning up synthetic mailbox tests through the connected Gmail integration.
---

The default Replit Gmail integration can have read, send, compose, and label scopes without `gmail.modify`. In that state, searching and verifying a test message works, but Gmail trash/archive/label writes return HTTP 403. A custom-OAuth Gmail connection is required for `gmail.modify`.

**Why:** A delivery test must not claim cleanup succeeded when the integration cannot modify the mailbox. The Python connector package advertised by the integration was unavailable in this project registry, while the supported JavaScript connector SDK worked. The privileged helper must own the complete receipt-search-to-Trash transaction; exposing a generic Trash-by-ID helper is too broad.

**How to apply:** Verify the selected connection's actual configured scopes before mailbox access and fail closed if scope metadata is unavailable. Default/platform credentials remain manual-cleanup only. For automated cleanup, use the JavaScript connector SDK, one healthy custom-OAuth connection, and a helper that validates one receipt plus the exact role-bound IDs before any reversible Trash call.