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

## Offerings / therapies display has TWO tiers (decided)
- `#modalities` (homepage, inline CSS) = tier 1: 9 INTEGRATIVE therapy cards WITH per-therapy photos (`.mod-grid`/`.mod-card`): Music, Massage, Reiki, Aromatherapy, Pet, Audiology, Holistic Medicine, End-of-Life Doula, Sound Bath.
- Tier 2 = `.mod-extra` (id `clinical-mobile`) photo-LESS card grid (`.svc-grid`/`.svc-item`, gold ✦ chips) under subheading "Clinical & Mobile Services": Physical/Occupational/Speech Therapy, Dietitian, Mobile Podiatry/Optometry/Dialysis, Lab Testing, Licensed Gerontologist.
- **Why:** new clinical/mobile services have no photos; mixing photo + photo-less cards in one grid looks broken, so non-comfort services live in their own photo-less tier. Don't add photo-less cards into `.mod-grid`.
- City pages only summarize therapies in the `.prov` "What we provide" list ("…and more") — the detailed two-tier display is homepage-only; don't duplicate it onto city pages.

## `.prov` / `.creds` styling (shared elh.css, city pages)
- `.prov` "What we provide" = on-brand white cards (cream-dark border, gold ✦ chip in a rounded square, hover lift). `.creds` compliance line = cream-gradient bar; separators are `<span class="cd-sep" aria-hidden="true">&#10022;</span>` (gold ✦), NOT `&middot;`. The slate (`--slate`, off-brand blue) color was replaced by `--text-mid`; avoid `--slate` for text.

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
- The actual referral form is the homepage lead-capture `#leadcap`. To deep-link a specific tab cross-page, use **`/?lead=<cat>#leadcap`** (root path, cats: family/physician/casemanager/coordinator). The homepage JS ALREADY has a `URLSearchParams('lead')` handler that clicks `.lead-cat[data-cat=...]` on load — reuse it; do NOT add a duplicate. (Same-page links use `data-leadtab="<cat>"` instead.)
- **CRITICAL — never write `index.html?query` for deep-links.** Requesting `/index.html?...` triggers a 301 (local python http.server → `/index`; Netlify pretty-URLs → `/`) that **drops the query string**, so the `lead` param never reaches the page and the default Family tab stays active. Always link the homepage as `/?lead=...#leadcap` (absolute root path works from root pages AND `resources/*` subpages). **Why:** this silently broke every "Refer a Patient"/"Sign up to volunteer" deep-link. Verify any `?`-query link points at `/`, not `index.html`.
- **Why:** keeps "For Providers" (info hub) separate from "Refer a Patient"/"Refer a Patient →" (the intake form), and gives the providers page reachable, consistent navigation.

## Brand language: "founder-led" is banned sitewide (decided)
- Do NOT use "founder-led" / "Founder-led" anywhere on the site. It was deliberately removed from all prose, headings, meta descriptions, OG tags and JSON-LD.
- Approved positioning terms: "independent", "integrative", "compliance-led", and "physician-led clinical model" (physician-led = how care is directed, NOT the company owner).
- **Why:** the user decided "founder-led" should be dropped entirely. The founder's *origin story* sections (#founder / #amethyst / "About Eternal") are fine to keep — only the "founder-led" descriptor is banned.
- **How to apply:** after any content edit, `grep -rin 'founder-led' website/elh-preview` must return nothing.

## Netlify forms — file uploads
- Lead forms submit via AJAX urlencoded, but **any form with a file upload must use `enctype="multipart/form-data"` and submit `new FormData(form)` with no manual Content-Type** — the urlencoded path silently drops the file.
- **Why:** A job-application/upload funnel must never show false success. Gate the success UI on `response.ok`; on failure keep the form, re-enable the button, and show a phone fallback.

## Unified footer (decided) — the mega-footer is `#site-footer`, lives in 3 CSS places
- ALL pages that have a footer use the homepage mega-footer markup `<footer id="site-footer">` (5-col grid: logo/tagline + Our Care / For Families / For Providers / Contact, then disclaimer + bottom bar). 31 pages carry it.
- `family-guide.html` and `ELH_Family_Guide_Interactive.html` have NO footer by design — never add one.
- CSS is scoped under `#site-footer` and must exist in THREE places (same rule as the header): `assets/elh.css` (covers all linked inner + `resources/*` pages), `index.html` inline, and `resources.html` inline. The legacy generic `footer{}` / `.ftag` / `.fcontact` rules in elh.css are dead but harmless; the `#site-footer`-scoped block (appended later) wins on specificity+order.
- Path prefixes by depth: root pages use `index.html#x` / `assets/...`; `resources/*` subpages use `../index.html#x` / `../assets/...`. Footer logo is `assets/img/inline-edee248dcb.png` (cream wordmark).
- **"Refer a Patient" routing in the footer:** homepage uses the `#leadcap` modal (`data-leadtab="physician"`); every NON-home page instead links to `providers.html` (a modal anchor can't open cross-page). This intentional difference keeps the link functional — don't "fix" it to a shared `#leadcap`.

## QR codes (point to eternallifehospice.com)
- A QR placed on a DARK surface must carry its own light backing or it won't scan. The footer sits on `--deep` (dark plum), so the footer QR uses the **cream** variant (`assets/img/qr-cream.png` = plum modules on cream) — NOT the transparent/plum variant, which would be dark-on-dark and unscannable. **Why:** scanners need module/background contrast; "transparent for dark backgrounds" is wrong for QR. Same reasoning anywhere a QR lands on a colored surface.
- QR source PNGs are generated with high error-correction (level H) so the centered ELH infinity logo doesn't break decoding. If you regenerate or resize, keep EC level H and re-decode to confirm before shipping (see family-guide memory for the puppeteer+jsQR verify pattern).
- Placements: footer brand column on all 31 footer pages (`.foot-qr`, CSS in the same 3 places as header/footer — elh.css + index inline + resources.html inline), a `.res-qr-card` callout on resources.html, and a self-contained `.guide-qr` block on the family-guide colophon leaf. `family-guide.html` carries `.guide-qr`, not `.foot-qr` (it has no site footer). Path depth rule applies: root = `assets/img/...`, `resources/*` subpages = `../assets/img/...`.

## index.html is fully externalized — no base64 left
- All 27 inline base64 data URIs (jpeg/png/woff2) were pulled out of `index.html` to `assets/img/inline-*.{jpg,png}` and `assets/fonts/inline-*.woff2`, shrinking it from ~4.58MB to ~174KB (huge SEO/crawl win). Keep new homepage assets as external files; never reintroduce base64 into index.html.

## resources.html is also externalized now
- `resources.html` (inline-CSS page) previously embedded 6 base64 `@font-face` woff2 + 1 base64 hero JPEG (~654KB). Fonts now point to existing `assets/fonts/*.woff2` (4 Jost weights matched by content hash; the 2 Fraunces variable normal+italic reuse the shared `Fraunces-var.woff2`/`Fraunces-Italic-var.woff2` — near-identical builds, renders fine), hero JPEG extracted to `assets/img/resources-hero.jpg`. File ~33KB. Don't reintroduce base64.

## Internal link audits — two false-positive traps
- A naive href/src audit over this site WILL falsely flag two link styles that are actually valid: (1) **absolute paths** like `/assets/chat.js`, `/assets/img/*` resolve to the Netlify **publish root** (= `website/elh-preview/`), not the OS filesystem root — strip the leading `/` and resolve from the site root. (2) **query-string links** like `index.html?lead=physician#leadcap` are valid (homepage `URLSearchParams('lead')` handler) — split off `?...` before the existence check. After accounting for both, the site has zero broken internal links.

## Global font-size lifts MUST exempt SVG map-label selectors
- A site-wide readability "floor-lift" (regex bumping every `font-size:Npx`, e.g. 8.5→10.5 … 15.5→16.5, leaving ≥16 alone) is the accepted way to enlarge small UI/label/caption text across `*.html` + `elh.css`. Homepage body is already 19px.
- **But it crowds the service-area maps:** the SVG label selectors `.served-lab .soon-lab .cty-lab .city-lab .city-name .hq-lab .inset-lab .inset-cap` (elh.css) and `.map-label` (index.html) are spatially constrained — bumping them overlaps labels on the region map. After any blanket bump, REVERT these to originals (13/12/15/11/11/13/11/9.5; .map-label 9.5). Verify on `hospice-ventura-and-los-angeles-county-ca.html`.

## Header warm 24/7 invite (decided)
- The header phone pill is wrapped: `<div class="hdr-cta-wrap"><span class="hdr-cta-note">Here for you, 24/7 —</span><a class="hdr-cta" href="tel:18059537273">805.953.7273</a></div>` on all 31 header pages. Both `.hdr-cta` and `.hdr-cta-note` are hidden together on mobile. CSS lives in the same 3 places as the footer/header (elh.css + index inline + resources.html inline).

## Chatbot (guided + AI)
- Widget: `assets/chat.js` — fully self-contained (injects its own <style>+markup) because index.html & resources.html don't link elh.css. Loaded via `<script src="/assets/chat.js" defer>` on all 33 pages (before </body>). Guided FAQ chips + free-text. Emergency + clinical regex short-circuit in code → route to 24/7 line / 911, never sent to AI.
- Collapsed launcher is a DISCREET single circular icon button (no phone pill, no text label) — user explicitly chose this to mimic westlakevillagehospice.com's chat bubble. **Why it matters:** the phone number is intentionally NOT shown until the panel opens (the gold "Call" button is the top item in the panel header). Do NOT "restore" an always-visible call pill to the collapsed dock — that was the prior design the user deliberately replaced.
- AI: `netlify/functions/chat.js` (CommonJS exports.handler, global fetch, OpenAI gpt-4o-mini). Mirrors the same emergency/clinical guards server-side.
- **Why Netlify Function (not Replit integration):** site deploys to Netlify, so the OpenAI key MUST live in Netlify env (`OPENAI_API_KEY`) — Replit-managed/integration creds don't reach the Netlify runtime. Never commit the key. Guided answers + phone work with no key; AI activates once key is set.
