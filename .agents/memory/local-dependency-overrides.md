---
name: Local dependency override verification
description: npm can retain an old registry package despite a local override and successful install.
---

Verify both the installed source and the lockfile resolution when switching a
registry dependency to a local security backport. A successful update or clean
install is not sufficient evidence.

**Why:** npm accepted a new local dependency specification and override while
retaining the old registry tarball in its existing lock metadata. Even `npm ci`
completed successfully with the vulnerable source still installed.

**How to apply:** Assert the package identity, resolved source and actual patched
behavior. Refresh stale resolution metadata before accepting the update, then
verify a clean install. Keep explicit regression checks for the patched behavior
until an official upstream fix replaces the local backport.
