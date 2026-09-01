---
name: Production hosting identity
description: How to distinguish the ELH production platform when its edge headers identify Google infrastructure.
---

Do not infer that ELH is hosted on a Google Cloud application solely from `server: Google Frontend` or an `x-cloud-trace-context` response header. Confirm the actual serving platform from page-level deployment evidence and the active deployment configuration.

**Why:** Replit deployments can be delivered through Google Frontend, so those generic edge headers are not sufficient ownership evidence.

**How to apply:** When validating live routes or deciding where an obsolete asset must be removed, inspect the response body and active deployment configuration as well as headers. Treat Google Frontend as transport infrastructure until application-level evidence identifies the deployed service.

For server-side integrations, treat the running workflow as the authoritative environment check. An isolated secret-validation context may not match the environment attached to the deployed server.

**Why:** The Google Places key appeared invalid in an isolated validation context while the restarted Replit server successfully used its attached key for the canonical review feed.

**How to apply:** Validate credentials through the actual server endpoint after a workflow restart, while checking that responses and logs never expose the credential.