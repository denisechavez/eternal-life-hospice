---
name: Studio shared React runtime
description: Parent-installed authentication packages must use the artifact's React runtime.
---

Keep shared authentication packages and the Studio artifact on one React runtime.

**Why:** Replit installs shared packages at the workspace root, while this
existing artifact also has its own package installation. Matching React APIs
does not prevent duplicate instances; hooks can fail with a null context and
leave the sign-in page entirely blank even when type checks and builds pass.

**How to apply:** Deduplicate React in the artifact bundler when introducing
parent-installed React packages. Verify a rendered public entry page, not just
the package versions or successful compilation.

Apply the same single-runtime constraint to isolated browser-test bundles,
including the parent-installed router. Otherwise a fixture can fail with null
React context even when the application's deduplicated Vite build is healthy.

The workspace's Node 20 requires `--experimental-websocket` for browser-test
scripts that rely on the global WebSocket client.

**Why:** Plain Node 20 invocation fails before browser assertions; temporary
Chromium-profile cleanup can sometimes hide that original failure.

**How to apply:** Use the flag for existing browser checks until their runtime
compatibility is made explicit. Do not mistake a cleanup error for an app failure.
