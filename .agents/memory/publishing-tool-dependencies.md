---
name: Publishing tool dependency boundary
description: Keep internal content-generation libraries separate from the live site's runtime requirements
---

Internal publication and image-generation libraries should be optional tooling dependencies unless a live route actually needs them. Do not make publishing the public site depend on installing an unrelated content-production library.

**Why:** A publishing attempt failed while installing Pillow into a read-only Nix Python directory, even though the library already worked in the workspace and the live server used only standard-library Python imports. Development import success does not prove the publishing installer can install or update the same library.

**How to apply:** Audit the live server's transitive imports before changing dependency scope. Preserve tool dependencies explicitly, validate the default publishing dependency commands and verify the tool still runs. If a future live route genuinely requires a third-party library, declare it as a runtime dependency and repair the managed installation path rather than omitting it to bypass an error.