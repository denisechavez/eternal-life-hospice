---
name: Browser exception shapes
description: Chromium runtime errors can expose their message in different CDP fields.
---

Browser regression error classification must handle both a populated exception object's description and a text-only exception detail, while retaining source and error-type checks.

**Why:** Chromium can report a CSP EvalError with text only saying "Uncaught" and the useful message in the exception description; another observed response omitted the exception object and put the complete error in text. Matching only one shape makes an expected negative control fail on another browser setup.

**How to apply:** When recognizing intentional browser errors, exercise both detail shapes and reject unrelated sources, error classes and messages. Do not broadly suppress runtime failures.
