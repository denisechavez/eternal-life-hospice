---
name: Autoscale health monitoring
description: Production monitoring behavior and log interpretation for the Replit-hosted ELH website.
---

Use `/health` for external uptime checks. It is intentionally lightweight, uncached, and supports both GET and HEAD. Although the app also implements `/healthz`, Replit's production routing intercepts that path and returns 404 before the request reaches the app.

**Why:** Replit autoscale logs can show several failed `/` health checks while the port proxy and application instance start, followed quickly by successful responses. Strict external checks may count that startup window as downtime. Python's built-in HTTP server writes normal access lines to stderr, so Replit may label even HTTP 200 request logs as `ERROR`; judge those lines by the response status, not the label alone.

**How to apply:** When investigating uptime alerts, compare deployment startup timestamps with the first HTTP 200 response. Point external monitoring at `/health` with a reasonable timeout and retry policy. Replit's built-in Autoscale monitor still probes `/`; use a Reserved VM when cold-start-free uptime is required.