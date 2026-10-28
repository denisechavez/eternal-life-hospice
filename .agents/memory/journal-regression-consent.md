---
name: Journal regression tests and editorial consent
description: Keep full-corpus test fixtures independent of historical owner approvals.
---

Historical owner approval pins are not an invariant of the current review corpus.
Changed review drafts may legitimately differ. Verify that reconciliation rejects
those differences; never update approval pins just to make a test pass.

**Why:** A full-corpus test assumed every staged draft still matched an old
approval, blocking unrelated intake work even though the approval guard correctly
refused changed content. Permission to investigate a failing check was not
permission to grant new publication approvals.

**How to apply:** Keep explicit real-pin matching/rejection checks separate from
performance and rollback fixtures. Synthetic bulk permissions belong only in
disposable test storage and must be labelled synthetic. Preserve the production
approval constants, articles, photos and saved decisions.
