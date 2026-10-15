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

The compiled Studio is a required application asset, not disposable export output.
Keep it out of Git history but do not exclude it from the published application.
Validate the complete build manifest, including private review chunks, during
the publishing build.

**Why:** The public Journal can remain online while the published Studio is
missing, leaving the approval workflow unusable. Release checks with no approved
posts must still check Studio availability rather than report the entire
editorial workflow as healthy.

**How to apply:** Preserve authentication on draft chunks when delivering the
build. Treat missing Studio delivery as a monitoring failure, never permission
to bypass approval or automatically publish past-dated drafts.
