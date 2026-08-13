# ELH Website Tools

Command-line scripts for site quality, SEO, and content checks.
All scripts live in `website/tools/` and are run from the repo root.

---

## check-backlinks.py — Backlink Health Checker

Scores referring domains for health signals and produces a colour-coded HTML
report plus a Google-formatted disavow file. Run this whenever you have a fresh
export from Google Search Console.

### Quick start

```bash
python3 website/tools/check-backlinks.py --input referring-domains.csv
```

Outputs two files in `exports/seo/`:
- `backlink-report-YYYY-MM-DD.html` — open in a browser; sortable/filterable table
- `disavow-YYYY-MM-DD.txt` — pre-filled disavow file (review before submitting)

### How to export the domain list from Google Search Console

1. Go to [Google Search Console](https://search.google.com/search-console/) →
   select the **eternallifehospice.com** property.
2. In the left menu, click **Links**.
3. Under **External links → Top linking sites**, click **Export** (top right).
4. Choose **Download CSV**.
5. Pass that file to the script with `--input`.

The script also accepts a plain-text file (one domain per line) if you want to
check a custom list.

### Authority scoring — Tranco (free, no signup needed)

The tool automatically downloads the **Tranco top-1M domain list**
([tranco-list.eu](https://tranco-list.eu)) on first run and caches it in
`/tmp/tranco-cache.csv` for 7 days.  No API key or account required.

| Tranco rank | Signal | Score effect |
|---|---|---|
| ≤ 100,000 | High authority | +3 |
| 100,001 – 1,000,000 | Medium authority | 0 |
| Not in top-1M | No signal | 0 (not penalised) |

Use `--no-cache` to force a fresh list download before the 7-day window expires.

When `OPR_API_KEY` is also set, Open PageRank scores take precedence and Tranco
is used only for domains OPR doesn't cover.

### API keys (optional — tool runs full authority checks via Tranco without them)

| Variable | What it unlocks | How to get it |
|---|---|---|
| `OPR_API_KEY` | Open PageRank score (0–10) — takes precedence over Tranco | Free signup at [domcop.com/openpagerank](https://www.domcop.com/openpagerank/signup) |
| `GOOGLE_API_KEY` | Google Safe Browsing malware/phishing check | Already in Replit Secrets for this project |

Without these the tool still runs Tranco authority checks plus heuristics
(spammy TLDs, suspicious domain-name patterns, known-authoritative domain list).

### Flags and options

```
--input FILE        GSC CSV export or plain-text domain list (required)
--output-dir DIR    Where to write report files (default: exports/seo)
--dry-run           Check first 5 domains and print results; write no files
--no-cache          Force a fresh Tranco list download, ignoring the local cache
```

### How verdicts are assigned

| Verdict | Meaning | Action |
|---|---|---|
| ✅ **Healthy** | Score ≥ 6, no threats | No action needed |
| ⚠️ **Review** | Score 3–5 | Check manually; low-authority but not clearly spam |
| 🚫 **Toxic** | Score < 3 or Safe Browsing threat | Add to disavow file and submit |

**Scoring signals:**
- OPR ≥ 7 **or** Tranco rank ≤ 100k → +3 (high authority)
- OPR 3–6 **or** Tranco rank 100k–1M → 0 (neutral)
- OPR < 3 → −3 (low authority); Tranco absence = no penalty
- Google Safe Browsing threat → −10 (instant red)
- Spammy TLD (`.xyz`, `.tk`, `.click`, etc.) → −3
- Suspicious domain-name pattern → −2
- Known authoritative domain (`.gov`, accreditation bodies, major platforms) → automatically green

The **Authority Score** column in the HTML report shows the source of the score:
`OPR` when an Open PageRank key was used, or `Tranco` with the domain's rank
when the free Tranco list was used.

### Submitting the disavow file

Only submit the disavow file to Google if:
- You see a **manual spam action** in Search Console, OR
- You have a **clear pattern of paid or spammy links** you cannot get removed

Submitting unnecessarily can strip good links and hurt rankings. Google's own
guidance is to use it as a last resort. When in doubt, don't submit.

Upload at:
<https://search.google.com/search-console/disavow-links>
(select the `eternallifehospice.com` property)

---

## deepl-translate.py — Content Translation

Translates page content using the DeepL API. Requires `DEEPL_API_KEY`.

```bash
python3 website/tools/deepl-translate.py --help
```
