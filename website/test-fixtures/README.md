# Acknowledgment approval baseline

`acknowledgments-approved.json` is the maintained, transport-free approval fixture
for `../test-acknowledgments.py`. It must be committed with the tests so publishing
checkouts do not depend on uploaded attachments.

The 14 subjects and body paragraphs were checked against the October 26, 2026
“Eternal Life Hospice — Online Form Acknowledgments and Request Routing” approval
document. The final approved three-line care CTA supersedes that document's
availability paragraphs; `{cta}` records its exact position. The care-related
general-meeting introduction is retained with the final CTA.

The fixture deliberately excludes recipient data, confirmation numbers, private
submissions and credentials. Form IDs, stable interest IDs, historical dropdown
labels and care-template membership are also locked here to prevent tests from
using changed production constants as their own expected results.

Change this baseline only after explicit approval of copy or routing changes.
Review the fixture diff against that approval; never regenerate expected copy
automatically from the implementation just to make a failing test pass.

Run from any directory:

```sh
python3 /path/to/project/website/test-acknowledgments.py
```

The suite injects a synthetic mailer and blocks network connections. It prints
its publishing sentinel only when all tests pass with no skips.
