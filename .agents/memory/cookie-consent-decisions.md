---
name: Cross-tab consent policy
description: Why remote acceptance does not start optional providers in existing non-tracking documents.
---

Consent withdrawal across tabs takes priority over preserving the current document. Acceptance from another tab updates preferences but does not itself start optional providers in an already-open, non-tracking document; local acceptance or a new navigation may start them.

**Why:** Third-party runtimes cannot be reliably unloaded. Reloading an already-tracking document is needed to withdraw consent, but automatically starting trackers in other open documents would introduce unwanted starts and delayed-load races.

**How to apply:** Keep remote grants separate from document boot authorization. Do not broaden cross-tab synchronization into automatic provider startup. Preserve the essential accessibility widget and approved consent copy.
