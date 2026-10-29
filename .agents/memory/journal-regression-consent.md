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

Date-rewind tests must isolate the verified-public workspace preview cache as
well as approval storage. Use explicit synthetic releases rather than frozen
history as their authorization fixture.

**Why:** The workspace overlay intentionally keeps already-public snapshots
visible even when the preview date is moved backward. Importing that cache into
a layout fixture hides date-gating regressions and changes the featured story.

**How to apply:** Give tests a disposable absent cache and explicit release
membership. Keep Pacific-day checks, the authoritative 06:30 release boundary,
held/unapproved drafts and archive rendering covered separately. Do not change
production overlay semantics to satisfy a date-rewind test.
