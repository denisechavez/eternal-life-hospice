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

Use an in-app confirmation for approval rather than a native browser popup.
Keep errors and recovery actions inside the article reader, and make the
workspace/live distinction visible before a reviewer begins.

**Why:** Studio is frequently used inside a canvas iframe, where browser
confirmation dialogs may be blocked. Workspace approval and live publication
must not be confused, and a lost save response is not proof that no approval
was committed.

**How to apply:** Keep live approval explicit and version-specific. On retry,
read the saved server status before enabling another approval; never recover by
silently approving a new version or trusting a browser-local status.

Reader portals need their own complete button/theme styles.

**Why:** The article reader renders outside the main dashboard wrapper. Missing
inherited theme variables made approval buttons transparent with near-white
labels, even while DOM-label and click-flow tests passed.

**How to apply:** Check actual computed foreground/background contrast in enabled,
disabled and confirmation states. Keep disabled labels readable and explain the
lock beside the action, not only above a long article.
