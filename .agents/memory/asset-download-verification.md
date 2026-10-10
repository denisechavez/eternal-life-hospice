---
name: Asset download verification
description: Verify real downloadable files when Library cards do not work for the reviewer.
---

When the reviewer cannot download an exported asset, do not merely resend the
same Library card. Supply a verified browser-accessible file download.

**Why:** Repeated image-PDF cards did not let the reviewer download the file.
The preview's generic filesystem route rejected it, while unknown download
paths could return the application's HTML with a misleading successful status.

**How to apply:** Check the actual proxied URL, response MIME type and attachment
header, then download the complete body and compare it with the source file.
Keep preview-only fallbacks narrowly allowlisted; do not expose arbitrary
workspace files, bypass an existing authentication boundary or publish internal
exports just to make a download work.
