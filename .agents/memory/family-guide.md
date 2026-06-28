---
name: family-guide booklet
description: Gotchas for editing website/elh-preview/family-guide.html (the interactive booklet)
---

- [Page-turn timing is duplicated](#) — the booklet flip duration lives in BOTH CSS (`body.booklet .page{transition:transform ...}`) and JS (`setTimeout(restingZ, <ms>)` in `go()`). **Why:** the JS timer resets z-index after the flip; if it doesn't match the CSS duration the leaf snaps or flickers. **How to apply:** change both together (CSS ms + JS ms, JS slightly larger as buffer).

- [Appended overrides re-break reduced-motion](#) — the file has an early `@media(prefers-reduced-motion:reduce){body.booklet .page{transition:opacity .3s ease}}`. Any later same-specificity `body.booklet .page{transition:...}` override re-enables full motion for reduced-motion users. **How to apply:** after adding a motion override, re-assert the reduced-motion block AFTER it (last in source wins).

- [QA cannot use screenshots](#) — the page shows a `#bootveil` intro that hides content ~3s (`setTimeout(revealGuide,3000)`) and content lives in a no-scroll booklet/stack. `app_preview` screenshots only ever capture the cover. **How to apply:** verify via reading CSS + `curl` (HTTP 200 + asset 200s), not screenshots.

- [Mobile worksheet restack](#) — the comparison `table.ws` is transposed to per-question cards under `@media(max-width:640px)`. Agency-name inputs live in `<thead>`; do NOT `display:none` the whole thead (loses editable names) — keep thead as a flex row of pills. Card cell labels are positional via `td.cell:nth-of-type(2/3/4)` (CSS can't read input values).

- [Fonts are externalized](#) — @font-face uses shared `assets/fonts/*.woff2` (Fraunces-var, Fraunces-Italic-var, JostELH-Light/Regular/Medium/SemiBold), not inline base64. Keeps file ~430KB. The old `ELH_Family_Guide_Interactive.html` twin was deleted (0 inbound links; `family-guide.html` is canonical).

- [Cover is NOT a numbered page](#) — there are 6 `.page` leaves: leaf 0 = cover (its own footer, no folio), leaves 1–5 = content. **Decision:** numbering counts content only — bottom `#pageLbl` reads "Cover" on the cover then "1 / 5"…"5 / 5"; per-page folio `pf-r` = `idx + ' / ' + (N-1)`; dots are generated for `d=1..N-1` (5 dots, none for the cover) and toggled by `data-i===cur`. **Why:** counting the cover made the first content page read "2 / 6" (off-by-one) which the user flagged. Don't reintroduce the cover into the count or dots.

- [Contact colophon — no orphaned numbers](#) — in `.contact .info`, each phone/email unit is wrapped in `<span class="ph">` with `white-space:nowrap` so a number never wraps away from its label; separators are `<span class="sep">·</span>` (opacity .5, inherits theme color). No "A Conduit International build" credit on the booklet (user removed it — only the standard 31 pages carry the Conduit credit).
