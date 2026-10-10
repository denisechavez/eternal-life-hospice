---
name: Studio environment boundary
description: Live Journal approvals must be made in production Studio, not inferred from workspace approvals.
---

Use the published Studio for approvals intended to control the live Journal.
Workspace reviews may validate drafts but must not be treated as live authority.

**Why:** Replit-managed Clerk accounts and PostgreSQL data are separated between
development and production. A persistent workspace approval still cannot govern
the published app merely because both applications run the same code.

**How to apply:** Keep production sign-in and approval APIs on the published
origin. Never bridge the environments by accepting development session tokens,
copying browser statuses or automatically approving every past-dated article.
Preserve explicit revision review and require user permission before deployment.

Protect draft-bearing JavaScript chunks as well as review APIs.

**Why:** The Studio preview imports complete unpublished articles. An API-only
authorization gate would still disclose their text through a public static bundle.

**How to apply:** Keep login assets public and verify reviewer authority before
delivering draft-bearing application assets. Check static and encoded paths, not
only the visible review route.
