---
name: Gmail cleanup permissions
description: Permission boundary to expect when cleaning up synthetic mailbox tests through the connected Gmail integration.
---

The connected Gmail integration can have read, send, compose, and label scopes without `gmail.modify`. In that state, searching and verifying a test message works, but Gmail trash/archive/label writes return HTTP 403.

**Why:** A delivery test must not claim cleanup succeeded when the integration cannot modify the mailbox. The exact test records can be verified in search, but an authorized mailbox user must perform deletion.

**How to apply:** Before planning automated mailbox cleanup, inspect the actual granted scopes. If `gmail.modify` is absent, record the failed write accurately, ask an authorized mailbox user to clean up the bounded synthetic records, and re-run a targeted search to verify the visible copies are in Trash.