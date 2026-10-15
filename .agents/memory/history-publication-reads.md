---
name: History publication reads
description: Private history must not perform publication work to report the live version.
---

History browsing must remain read-only and independent of the global publication
lock. Report due approved versions using the same effective-time rules as public
release materialization, with frozen originals as the fallback.

**Why:** Calling the public release path from history made each pagination request
wait behind approvals and scheduled release work. Simply reading persisted releases
instead would misreport a due approval until a public request materialized it.

**How to apply:** Keep metadata and review events in one committed snapshot so
concurrent approvals or holds cannot produce a mixed response. Do not move release
writes into history or weaken reviewer authorization to avoid contention.
