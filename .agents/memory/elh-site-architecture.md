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

## Modality card photos — duotone was baked into the image bytes, not CSS
- The 9 `#modalities` card photos (`.mod-photo`) carry their look in the FILE itself. No CSS tint/blend exists; `.mod-photo{filter:none;opacity:1}` and `.mod-img{background:var(--cream-mid)}` are intentionally neutral.
- **Why it matters:** a mauve/sepia duotone that several cards once showed was pre-applied to the inline base64 images, so no CSS edit could remove it — only swapping the asset bytes did. If a card's tint/treatment looks wrong, fix the source file (re-export/replace), don't hunt for a CSS rule.
- All 9 now reference external files in `assets/img/` (photos as `.jpg`, resized to max 900px); none are base64. Keep new card photos as optimized external files, not inline base64.

## Coverage-area architecture (decided)
- The county page `hospice-ventura-and-los-angeles-county-ca.html` is the single coverage/SEO hub. It owns the only "real" map: a designed image `assets/img/service-hero-map.png` (with a Google Maps HQ pin), plus per-county sections.
- Homepage `#coverage` uses that SAME static map image + a "View our full coverage area →" CTA to the hub. The old code-drawn SVG map (JS-built `#mapPanel`/`mapSvg`/`.cpill` county pills + the footer-fill IIFE using a `/hospice-care-SLUG` href scheme) was REMOVED — it looked like a crude doodle. Don't reintroduce it.
- **Why:** the 16 `hospice-<city>-ca.html` pages were thin (~666 words, no unique images, near-duplicate) = doorway-page risk. They are PARKED: `<meta name="robots" content="noindex,follow">`, removed from `sitemap.xml`, and every internal `<a>` to them sitewide converted to plain `<span>` text (city names kept for content, links gone). Files NOT deleted.
- **How to apply:** keep city pages out of the sitemap and unlinked until each has genuinely unique copy + a unique location image; only then flip to indexable and re-link. To find stray links: `grep -roP 'href="hospice-(?!ventura-and-los-angeles)[a-z-]+-ca\.html'`.

## Trust bar (credential marquee) — now sitewide
- Animated `.cred-strip > .cred-track` marquee (CMS/CDPH/ACHC cards + 2 SVG info cards, content duplicated for the `cscroll` translateX(-50%) loop). Lives under the header on the homepage AND all inner pages.
- Homepage embeds the 3 accreditation logos as inline base64; inner pages reference extracted file copies `assets/img/cred-{cms,cdph,achc}.png` (reuse those, don't re-extract). Shared CSS + `@keyframes cscroll` + `--cream-mid` var live in `assets/elh.css`.
- **Why margin-top differs:** homepage inline `.cred-strip{margin-top:74px}` (fixed header needs the offset); elh.css version uses `margin-top:0` (inner headers are sticky and already occupy space). Any element placed right after `</header>` must follow this same fixed-vs-sticky rule.
- Inner pages still keep their mid-page static `.creds` text line (separate element, left in place).

## Fonts — naming/loading is split (latent inconsistency)
- Two typefaces sitewide: Fraunces (display) + Jost (body). BUT family names differ by page: `index.html` declares `'Fraunces'`/`'Jost'` (its own base64 fonts, `:root --ff-d/--ff-b` point to those); `assets/elh.css` (all inner pages) + `resources.html` declare `'Fraunces ELH'`/`'Jost ELH'` (elh.css loads `assets/fonts/*.woff2`, resources.html base64). Same designs, different names AND different font files/subsets.
- `assets/fonts/JostELH-*.woff2` only ships weights 300/400/500/600 → any `font-weight:700` renders faux-bold (elh.css uses 700 in ~9 places; homepage in ~20).
- **How to apply:** for true consistency, unify the family naming and ensure the same weights exist everywhere; don't assume editing elh.css affects homepage/resources.html fonts.

## Providers hub + referral-intake routing (decided)
- `providers.html` is the compliance-led "For Referring Providers" hub (standard elh.css inner page; chrome cloned from careers.html). ALL provider entry points sitewide route here: homepage hero "For Referring Providers" CTA, the "For Providers" nav link on every page (homepage, inner pages, and `resources/*` subpages via `../providers.html`).
- The actual referral form is the homepage lead-capture `#leadcap`. To deep-link a specific tab cross-page, use `index.html?lead=<cat>#leadcap` (cats: family/physician/casemanager/coordinator). The homepage JS ALREADY has a `URLSearchParams('lead')` handler that clicks `.lead-cat[data-cat=...]` on load — reuse it; do NOT add a duplicate. (Same-page links use `data-leadtab="<cat>"` instead.)
- **Why:** keeps "For Providers" (info hub) separate from "Refer a Patient"/"Refer a Patient →" (the intake form), and gives the providers page reachable, consistent navigation.

## Brand language: "founder-led" is banned sitewide (decided)
- Do NOT use "founder-led" / "Founder-led" anywhere on the site. It was deliberately removed from all prose, headings, meta descriptions, OG tags and JSON-LD.
- Approved positioning terms: "independent", "integrative", "compliance-led", and "physician-led clinical model" (physician-led = how care is directed, NOT the company owner).
- **Why:** the user decided "founder-led" should be dropped entirely. The founder's *origin story* sections (#founder / #amethyst / "About Eternal") are fine to keep — only the "founder-led" descriptor is banned.
- **How to apply:** after any content edit, `grep -rin 'founder-led' website/elh-preview` must return nothing.
