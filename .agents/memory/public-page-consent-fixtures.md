---
name: Public-page consent fixtures
description: Public rendering and network boundaries for served-page privacy checks.
---

Run served-public-page consent checks using public rendering in an isolated fixture process, not workspace rendering.

**Why:** Workspace rendering injects draft service navigation and private preview asset paths. Production response headers alone do not make the page match its public rendering.

**How to apply:** Reject execution in a real deployment before selecting public rendering inside the child fixture. Keep an independent static-route allowlist, synthetic review data, server-side outbound socket denial and browser interception in place. Never start a production API handler or allow real provider responses just to obtain public HTML.
