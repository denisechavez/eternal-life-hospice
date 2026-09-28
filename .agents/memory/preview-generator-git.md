---
name: Preview generator and Git
description: Why the design preview's generated file must remain deterministic to avoid Git publishing errors.
---

Keep discovery order stable whenever changing the design preview generator or its component inventory.

**Why:** A preview startup rewrote a tracked generated module in a different order without changing its components. Git marked the worktree dirty, which blocked synchronization during publishing. Reverting the module alone could be undone by the next startup.

**How to apply:** Check that a preview build and a workflow restart leave Git clean. A standalone preview build requires the preview's configured PORT and BASE_PATH and rewrites tracked build output, so avoid carrying those incidental artifacts into a commit.