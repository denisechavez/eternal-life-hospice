---
name: Shell callback newline handling
description: Avoid accidental carriage-return changes when copying shell output into configuration files
---

Prefer file-reading callbacks over shell stdout when transferring existing configuration text. If shell output is necessary, verify and normalize newline conventions before writing it.

**Why:** The programmatic shell callback returned CRLF line endings for a Git blob whose original file used LF. Copying that output into the publishing configuration produced a whole-file whitespace-only diff.

**How to apply:** Preserve the source file's newline convention, validate the resulting configuration through the supported replacement callback and check the diff before finishing.