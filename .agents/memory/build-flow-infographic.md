---
name: Build-and-publish flow infographic
description: How the internal build/publish explainer PNG was made and its key facts.
---
# Build-flow infographic

`exports/diagrams/build-and-publish-flow.png` — internal (unpublished) plain-language
explainer of how the site ships: **AI Tools (Claude/ChatGPT/Perplexity) → Replit →
GitHub → Netlify → live site**.

**Accuracy rule (got this wrong once):** the ONLY manual step is the Replit→GitHub
"Git → Sync" click. Everything after (GitHub→Netlify→live) is automatic. Don't phrase
it as "steps 1–3 are manual."

**Tool marks:** monochrome brand logos pulled from Simple Icons
(`cdn.jsdelivr.net/npm/simple-icons@latest/icons/<slug>.svg`; slugs claude, openai,
perplexity, replit, github, netlify), tinted brand plum on cream discs for a calm,
cohesive look rather than clashing full-color logos. Live-site tile = hand-drawn
SVG browser window (no logo exists for it).
**Why:** tasteful + recognizable, matches ELH palette; avoids logo-licensing/color clash.

**Render pattern (no server needed):** build a self-contained temp HTML in /tmp with
`@font-face` pointing at `file:///.../elh-preview/assets/fonts/*.woff2` (Fraunces ELH +
Jost ELH) and the logo via `file://`, then
`chromium --headless=new --no-sandbox --force-device-scale-factor=2.5
--window-size=1600,1000 --default-background-color=00000000 --screenshot=out.png`.
1600×1000 CSS @2.5x → 4000×2500 PNG (~254 DPI at 11in wide, single-page print OK).
Delete temp files after.
