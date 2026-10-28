---
name: Intake verification behind live proxies
description: Live verification bindings vary across requests even when the preview remains stable.
---

Do not assume the proxy-derived client identity is stable enough to authenticate a browser's form-verification token.

**Why:** During investigation of a legitimate family-form rejection, five consecutive same-origin security GETs from one client produced five distinct anonymous client bindings on the live site, while preview requests produced one stable binding. Production logged `verification_invalid` before intake delivery. This establishes inconsistent live bindings, but not the precise validation branch behind that individual rejection; signatures and proxy routing must both be considered.

**How to apply:** Separate stable browser verification from network-based abuse limits. Preserve origin checks, signed token expiry, minimum age, replay prevention and shared limits when changing the binding. Test rotating proxy identities, missing cookies and cross-browser attempts with synthetic delivery only. Do not weaken checks or claim a Brevo outage based on generic delivery-error copy. Changes require verification and publishing approval.

Keep the browser proof fresh for each attempt and only in memory, rather than introducing a persistent visitor identifier or a cookie dependency.

**Why:** Verification must survive proxy changes without adding tracking, cross-tab cookie races or failures caused by blocked cookie storage. A per-attempt proof can accompany both the challenge request and submission without identifying a person.

**How to apply:** Do not put raw proofs in URLs, analytics, email, logs or saved browser storage. Missing secure randomness must stop before sending. Keep network-based abuse limits independent of verification identity, and revise cached entry points together with the shared verification protocol.
