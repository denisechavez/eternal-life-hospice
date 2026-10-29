---
name: Public-page consent fixtures
description: Public rendering and network boundaries for served-page privacy checks.
---

Run served-public-page consent checks using public rendering in an isolated fixture process, not workspace rendering.

**Why:** Workspace rendering injects draft service navigation and private preview asset paths. Production response headers alone do not make the page match its public rendering.

**How to apply:** Reject execution in a real deployment before selecting public rendering inside the child fixture. Keep an independent static-route allowlist, synthetic review data, server-side outbound socket denial and browser interception in place. Never start a production API handler or allow real provider responses just to obtain public HTML.

Browser isolation must cover child targets and speculative connections, not just page requests.

**Why:** Chromium dedicated-worker targets lack the Fetch domain. Cross-origin frame navigations can also trigger speculative CONNECTs despite synthetic document interception.

**How to apply:** Attach recursively before child execution. Block worker networking before resuming and observe its attempts through Network events. Keep a deny-only proxy behind interception, with a browser canary run before interception is installed. A denied speculative CONNECT is not a live provider response.

Keep the fixture's proxy bypass HTTP-only when testing same-origin WebSockets.

**Why:** A host-only bypass also lets sockets reach the fixture directly. Chromium can tunnel even plain WebSockets through CONNECT; a denied tunnel stops the upgrade before a handshake event exists. Same-origin sockets exercise real transport under the unchanged public CSP.

**How to apply:** Correlate native socket creation, failure and closure with a denied proxy tunnel or upgrade, and verify the fixture received no socket request. Do not require an upgrade event when the tunnel was already denied.

Identify EventSource independently in observation and interception.

**Why:** Chromium can label the same native stream `EventSource` in Network events but `XHR` in Fetch interception. Depending only on the Fetch label silently misses stream-specific handling.

**How to apply:** Use the native stream Accept header for synthetic terminal responses and the Network resource type for observation assertions. Stop retries explicitly and assert no open or message event.
