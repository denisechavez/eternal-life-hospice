# Local and editorial content verification

Checked 2026-10-07 against the current workspace source.

## Care Brief publication clarity

Removed the unlinked “Issue Two — coming September 2026” teaser from the
Issue One archive. The current-issue label and existing Journal article link
remain. No new subscription flow or publication promise was introduced.

The page loads successfully in preview. The closed archive control renders
correctly; its menu contents were verified through source and regression tests,
not by interacting with the screenshot.

## City content

The current `city-data.json` already contains the wider editorial rollout:
all 145 published records have substantive source-backed editorial sections.
Every generated city page matches `build-cities.py` output after the builder's
normalization. The five pilot pages and county hub were not changed in this work.
No pages were removed, consolidated or newly noindexed.

Added the reported exact-paragraph method to `audit-city-redundancy.py`,
separately from its established eight-word phrase measurements:

- Corpus: 145 published data-backed city pages; county hub excluded.
- Paragraphs inside `<main>` only, excluding navigation, header, footer,
  scripts and styles.
- Decode HTML entities, collapse whitespace and lowercase text.
- Normalize all source city names and Ventura/Los Angeles County labels.
- Count words in exact paragraphs recurring on at least 20 distinct pages.

Current results, saved in `local-editorial-current-audit.json`:

| Measurement | Current result |
|---|---:|
| Pages with at least 50% repeated paragraph words | 0 / 145 |
| Median repeated paragraph words | 1.92% |
| Mean repeated paragraph words | 1.93% |
| Eight-word main-copy repeated-word coverage | 21.74% |

The supplied issue described 110 / 145 pages at the 50% threshold, with a
61% median and 60% mean. That finding does not describe the current workspace.
This is a current-state verification, not a new before/after rewrite experiment:
the original issue's raw corpus was not available for independent reconstruction.
The older eight-word before/after reports remain unchanged.

These measurements establish reduced exact repetition, not Google rankings,
clinical approval or verified address-level service availability. No new local
facility, affiliation, demographic or operational claims were authored.

## Checks

- `python3 website/test-local-editorial-content.py`: all six checks pass,
  including the 20-distinct-page threshold, geographic normalization, shared
  chrome exclusion, cluster repetition guard and publication archive guard.
- `python3 website/test-city-content-pilot.py`: all five checks pass.
- `python3 website/check-city-scripts.py`: passes across all 145 city pages.
- Source/render parity check: no city-page drift.
- `git diff --check`: passes.
- Preview server: running; Care Brief page and assets return HTTP 200.

### Pre-existing historical test failure

`python3 website/test-city-content-rollout.py` passes 11 of 12 checks.
`test_pilot_pages_and_county_hub_remain_byte_identical` fails because all six
protected files differ from the older `city-rewrite-preservation.json` snapshot
before this work. The current pilots pass source/render parity. Neither those
pages nor that historical snapshot was modified here; refreshing historical
preservation evidence without reviewing the intervening changes would hide the
reason for the mismatch.

## Reproduction

```sh
python3 website/test-local-editorial-content.py
python3 website/audit-city-redundancy.py --output /tmp/local-editorial-audit.json
```

Keep future editorial changes in `city-data.json` and regenerate with
`build-cities.py`. Retain human/compliance review for new local or clinical claims.
