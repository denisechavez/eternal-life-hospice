# Eternal Life Hospice

## Project overview
Static marketing website for **Eternal Life Hospice, Inc.** — an independent,
Medicare-certified hospice serving **Ventura & Los Angeles County, CA**.

- **Live site:** https://eternallifehospice.com
- **Publishing flow:** edit here → user clicks **Git → Sync** in Replit → Netlify
  auto-deploys to the live domain.
- **Website source:** `website/elh-preview/` (this folder, and only this folder,
  is what publishes to the live site).
- **Approved coverage:** Ventura + Los Angeles County only.
- **Brand:** logo = metallic-plum infinity "Eternal / Life Hospice" lockup;
  palette = deep plum, plum, gold, off-white cream; fonts = Fraunces (serif) +
  Jost (sans). Tagline "Care That Honors Life" / "Here in Moments That Matter Most".
- **The Eternal Standard — four pillars of care:** Clinical Confidence ·
  Guided Presence · Whole-Person Comfort · Compliance-Led Care. This is the
  core brand architecture across all collateral; keep messaging consistent with it.
- **HQ:** 4165 E Thousand Oaks Blvd, Suite 325B, Westlake Village, CA 91362.
  Phone 805.953.7273 · Fax 805.953.8530 · info@eternallifehospice.com · 24/7 nurse access.
- **Compliance posture:** Medicare-Certified · CDPH-Licensed · ACHC-Accredited.
  No medical-efficacy claims for integrative therapies; referral materials stay
  within Anti-Kickback / Stark boundaries (value & quality, never inducements).

## File organization (keep tidy as we grow)
- `website/elh-preview/` — the website (the only thing that deploys).
- `exports/` — finished, downloadable deliverables (NOT published to the site):
  - `exports/print/` — print-ready PDFs (rack cards, flyers, brochures).
    - `exports/print/press-kit/` — the professionally printed kit (die-cut
      presentation folder + the 4 "Eternal Standard" pillar rack cards).
  - `exports/decks/` — presentations (e.g. referral-partner deck).
  - `exports/diagrams/` — explainer graphics/infographics (e.g. build-and-publish flow).
- New collateral goes in the matching `exports/` subfolder with a clear,
  descriptive filename (e.g. `eternal-life-rack-card.pdf`).

## Multi-company structure
The user works with multiple companies. **One Replit App (project) per company** —
each with its own website + its own `exports/` collateral. A *new company* = a
*new App* (created from the Replit dashboard "Create" button), not a "New Task"
inside an existing project. This App is the Eternal Life Hospice company.

## Project Constitution
**Primary objective:** Generate qualified hospice referrals that convert into admissions.

Before any recommendation ask: *Will this increase referrals or admissions?* If not — it is not a priority.

**Conflict resolution:**
- Aesthetics vs. conversion → choose conversion
- Complexity vs. usability → choose usability
- Adding a feature vs. increasing referrals → prioritize referrals

The website is a **referral-generation platform**, not a brochure. Every page must answer: Why Eternal? Why now? What happens next? How do I refer? How quickly will someone respond? Why should I trust Eternal?

## Search index — keeping it in sync

`website/elh-preview/assets/search-index.json` is now generated automatically.
**Never edit it by hand** — your changes will be overwritten on the next run.

The script `website/elh-preview/assets/build-search-index.js` crawls every
HTML page under `website/elh-preview/`, extracts the title, meta description,
and canonical URL, and rebuilds the index. It:

- **Preserves hand-authored `kw` fields** for pages already in the index
- **Infers the `cat` category** from the URL for newly discovered pages
- **Skips** utility/noindex pages (404, privacy-policy, terms, card pages, etc.)
- Is **idempotent** — safe to run repeatedly

To regenerate locally after adding a new page:

```
node website/elh-preview/assets/build-search-index.js
```

Or use the **rebuild-search-index** workflow in the Replit workflow panel.

The script also runs automatically as part of the **Netlify build command**
(`netlify.toml`) before every production deploy, so new pages are indexed
without any manual step.

## How to verify city coverage data

Run the coverage lookup regression test after any edit to `website/city-data.json`:

```
node website/elh-preview/assets/test-coverage-lookup.js
```

Or use the **coverage-lookup-test** workflow in the Replit workflow panel — it runs the same command and surfaces pass/fail in the console output.

The test checks:
- All published cities resolve to `served: true` with the correct city name
- Exact-match priority (e.g. "Bell" ≠ "Bell Gardens", "El Monte" ≠ "South El Monte")
- Normalisation (diacritics, case, extra whitespace)
- Non-served cities and edge inputs return correct negative responses
- List mode (`?list=true`) returns the right count and structure

If any assertion fails the process exits with code 1 and prints the failing checks.

## User preferences
- **Keep everything well organized as the work grows** — clear, predictable
  folder structure and descriptive filenames; file each deliverable in its proper
  home automatically without being asked.
- Non-technical audience: explain in plain language, focus on outcomes, avoid jargon.
- Strong emphasis on SEO correctness and healthcare compliance.
- **Do not propose follow-up tasks.** Never call the follow-up-tasks skill or propose new tasks unprompted.
- **Design and test before implementing.** When given a new instruction or change request: design the approach, validate/test it, then implement — all in one turn. Do not ship first and test later.
