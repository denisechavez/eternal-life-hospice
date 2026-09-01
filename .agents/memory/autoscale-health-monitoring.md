---
name: Autoscale health monitoring
description: Production monitoring behavior and log interpretation for the Replit-hosted ELH website.
---

Use `/healthz` for external uptime checks. It is intentionally lightweight, uncached, and supports both GET and HEAD.

**Why:** Replit autoscale logs can show several failed `/` health checks while the port proxy and application instance start, followed quickly by successful responses. Strict external checks may count that startup window as downtime. Python's built-in HTTP server writes normal access lines to stderr, so Replit may label even HTTP 200 request logs as `ERROR`; judge those lines by the response status, not the label alone.

**How to apply:** When investigating uptime alerts, compare deployment startup timestamps with the first HTTP 200 response. Point external monitoring at `/healthz` with a reasonable timeout and retry policy. If cold-start outages continue after that, evaluate an always-running VM deployment before changing the deployment target.