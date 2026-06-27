---
name: ELH hospice site CSS architecture
description: Which pages use shared elh.css vs inline-only CSS in the elh-preview static site, and the shared-header parity rule
---

# Eternal Life Hospice static site (website/elh-preview/)

## Stylesheet linkage is NOT uniform — check before any global style change
- Most inner pages (404, careers, volunteer, all `hospice-*.html`, all `resources/*.html`) link `assets/elh.css`.
- BUT `index.html` (homepage) AND `resources.html` are **inline-CSS only** — they do NOT link elh.css; their styles live in their own `<style>` block with their own `:root`.
- **Why it matters:** Editing elh.css does NOT affect index.html or resources.html. Any shared style change (header, vars, etc.) must be duplicated into those two pages' inline `<style>` blocks separately, or they silently render unstyled/stale. This caused rework — resources.html's new header was unstyled until its inline CSS was patched.
- **How to apply:** Before changing any "site-wide" CSS, grep each target page for `elh.css`; for inline-only pages, edit their `<style>` directly.

## Shared header (wordmark + hamburger nav)
- Markup uses `<header id="hdr">` + `.hdr-in` > `.hdr-logo` (two swap imgs `assets/img/logo-sym-cream.png` / `logo-sym-plum.png` + `.hdr-wordmark`), `nav`, `.hdr-cta` phone pill, `.menu-btn`.
- Behavior JS: `assets/header.js` (scroll→`.scrolled`, hamburger→`.nav-open`, close on outside-click + nav-link click). Faithfully mirrors homepage inline JS — keep at parity; homepage has no Esc/aria-controls, so don't add them to inner pages only.
- Inner pages use `position:sticky` (avoids hero overlap); homepage uses `position:fixed`. Accepted divergence.
- Path variants: top-level pages use `index.html#...` / `assets/...`; `resources/*` subpages use `../index.html#...` / `../assets/...`.
- Responsive parity rule that's easy to forget: `@media(max-width:980px){.hdr-cta{display:none}}` — must exist in elh.css AND resources.html inline AND index.html.
- `family-guide.html` and `ELH_Family_Guide_Interactive.html` are standalone docs with NO header by design — leave them alone.

## Editing index.html / resources.html
- These have long single-line body HTML — use python/grep, not line-based read/edit, to extract or replace blocks (e.g. `re.sub(r'<header\b.*?</header>', ..., flags=DOTALL)`).
