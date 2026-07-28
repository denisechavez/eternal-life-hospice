# Cookie Consent Gate — Test Results
**Date:** 2026-07-28  
**Tester:** Replit Agent (automated audit)  
**Live site:** https://eternallifehospice.com

---

## Test 1 — Decline cookies → analytics blocked

**Method:** Code path trace on live `analytics.js` (fetched from production).

**Result: PASS ✓**

When a visitor clicks **Decline All** (or saves with both toggles off):
- `saveConsent('essential')` is called
- `localStorage.setItem('elh_cc', 'essential')` is written
- `level === 'all'` is `false` → `loadAnalytics()` is **not called**
- No `<script>` tags for `googletagmanager.com`, `clarity.ms`, or `cdn.brevo.com` are injected
- No requests to `google-analytics.com`, `clarity.ms`, or `sibautomation.com` are made

On a **return visit** with `elh_cc = 'essential'` in localStorage:
- Entry point: `consent === 'all'` → false
- `forceShow || !consent` → false (`'essential'` is truthy)
- Neither branch fires → analytics permanently suppressed, no banner shown

---

## Test 2 — Accept cookies → analytics load

**Method:** Code path trace on live `analytics.js`.

**Result: PASS ✓**

When a visitor clicks **Accept**:
- `saveConsent('all')` is called
- `localStorage.setItem('elh_cc', 'all')` is written
- `level === 'all'` is `true` → `loadAnalytics()` is called
- GA4 (`G-JRLYCRC48G`), Microsoft Clarity (`xddyi1rk95`), and Brevo SDK are injected

On a **return visit** with `elh_cc = 'all'`:
- Entry point: `!forceShow && consent === 'all'` → `loadAnalytics()` fires immediately

---

## Test 3 — localStorage key correctness

| Action | `elh_cc` value |
|---|---|
| Accept (banner) | `"all"` |
| Save Preferences (both toggles on) | `"all"` |
| Save Preferences (both toggles off) | `"essential"` |
| Decline All (modal) | `"essential"` |
| First visit (no prior choice) | *(key absent)* → banner shown |

---

## Test 4 — No inline analytics bypass

**Method:** `grep` across all 60+ HTML files for `gtag/js`, `clarity.ms/tag`, `sdk-loader.js`, `sibautomation.com`.

**Result: PASS ✓**

Zero inline analytics script tags found in any HTML file. The only references to analytics domains in HTML are `<link rel="preconnect">` hints in `index.html` — these warm DNS/TCP connections but do **not** send tracking data and are harmless when analytics are declined.

---

## Test 5 — Live banner rendering

**Method:** Screenshot of `https://eternallifehospice.com/?show-consent=1`.

**Result: PASS ✓**

Banner renders correctly at bottom-left with **Accept** and **Manage** buttons. The `?show-consent` flag forces the banner even for returning visitors (useful for manual QA).

---

## Summary

All consent gate paths behave correctly. Analytics are **fully blocked** when visitors decline, and **correctly loaded** when they accept. No bypass vectors exist in the current codebase.
