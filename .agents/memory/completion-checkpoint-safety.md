---
name: Completion checkpoint safety
description: Automatic completion checkpoints can include pre-existing unrelated workspace edits.
---

Completion may automatically checkpoint all dirty workspace files, even when the assigned task only verifies an already-equivalent correction and makes no source edits.

**Why:** A no-change verification captured unrelated Journal edits and untracked editorial assets in an automatic checkpoint, then encountered conflicts with newer main-branch editorial work. Not manually staging files did not prevent this.

**How to apply:** Before completing a no-change task in a dirty shared workspace, disclose the checkpoint risk rather than promise that edits will remain uncommitted. Preserve a content and index baseline. If automatic reconciliation encounters unrelated conflicts, inspect both versions and keep newer complete editorial work with its matching photo manifest; never treat the automatic checkpoint diff as the verification task's implementation.
