#!/usr/bin/env python3
"""
ELH Backlink Health Checker
============================

Reads a list of referring domains (from a Google Search Console CSV export or
a plain-text file, one domain per line), scores each domain for health signals,
and produces a self-contained HTML report plus a Google-formatted disavow file.

Usage:
    python3 website/tools/check-backlinks.py --input referring-domains.csv
    python3 website/tools/check-backlinks.py --input domains.txt --dry-run
    python3 website/tools/check-backlinks.py --input domains.csv --output-dir /tmp/reports
    python3 website/tools/check-backlinks.py --input domains.csv --no-cache

Optional environment variables (tool runs in heuristic-only mode if absent):
    GOOGLE_API_KEY  — enables Google Safe Browsing threat check (key already in
                      Replit Secrets for this project)
    OPR_API_KEY     — enables Open PageRank domain authority check; takes
                      precedence over Tranco when set
                      (free key at https://www.domcop.com/openpagerank/signup)

Outputs (written to exports/seo/ by default, or --output-dir):
    backlink-report-YYYY-MM-DD.html   — colour-coded domain health report
    disavow-YYYY-MM-DD.txt            — Google disavow file (red-flagged domains)

Authority scoring (Tranco is used automatically; OPR takes precedence if key is set):
    The tool downloads the Tranco top-1M domain list on first run and caches it
    in /tmp/tranco-cache.csv for 7 days.  No API key or signup required.
      +3  OPR score ≥ 7 OR Tranco rank ≤ 100 000  (high authority)
       0  OPR score 3–6 OR Tranco rank 100 001–1 000 000  (medium)
      -3  OPR score < 3  (low — Tranco absence is not penalised)
      -3  Spammy TLD (.xyz, .tk, .click, etc.)
      -2  Suspicious domain name pattern (heavy hyphens, numbers, keyword stuffing)
     -10  Google Safe Browsing threat (malware / phishing / unwanted software)

    Verdict: GREEN (score ≥ 6, no GSB threat) | AMBER (score ≥ 3) | RED (otherwise)

Returns exit code 0 (informational; non-blocking by design).
"""

import argparse
import csv
import datetime
import html as html_lib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPAMMY_TLDS = {
    "xyz", "tk", "click", "link", "cf", "ga", "gq", "ml", "buzz",
    "top", "work", "party", "win", "loan", "download", "stream",
    "review", "trade", "racing", "men", "accountant", "faith", "date",
    "bid", "science", "cricket", "pw", "zip", "mov",
}

# Domains that are always authoritative — skip deeper analysis
AUTHORITATIVE_DOMAINS = {
    "medicare.gov", "cms.gov", "hcai.ca.gov", "cdph.ca.gov", "ca.gov",
    "achc.org", "nhpco.org", "chapca.org", "bbb.org", "yelp.com",
    "google.com", "facebook.com", "linkedin.com", "healthgrades.com",
    "wikipedia.org", "webmd.com", "nih.gov", "cdc.gov", "hospice.io",
    "hospicematch.com", "hospicecarenow.com",
}

OPR_ENDPOINT  = "https://openpagerank.com/api/v1.0/getPageRank"
GSB_ENDPOINT  = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
OPR_BATCH     = 100
GSB_BATCH     = 500
DELAY         = 0.25   # seconds between API batches

TRANCO_URL        = "https://tranco-list.eu/top-1m.csv.zip"
TRANCO_CACHE_PATH = "/tmp/tranco-cache.csv"
TRANCO_CACHE_DAYS = 7
TRANCO_HIGH_RANK  = 100_000    # rank ≤ this → high authority
TRANCO_MED_RANK   = 1_000_000  # rank ≤ this → medium authority

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class DomainResult:
    domain:        str
    linking_pages: int = 0
    target_pages:  int = 0
    anchors:       str = ""    # comma-joined anchor texts if present in CSV

    # API results
    opr_score:  Optional[float] = None
    opr_rank:   Optional[int]   = None
    opr_error:  str             = ""
    gsb_threats: List[str]      = field(default_factory=list)
    gsb_checked: bool           = False

    # Tranco authority (free fallback when OPR key is absent)
    tranco_rank: Optional[int] = None   # 1 = most popular; None = not in top-1M
    tranco_tier: str           = ""     # "high" | "medium" | ""

    # Heuristic flags
    spammy_tld:    bool = False
    suspicious:    bool = False
    authoritative: bool = False

    # Final
    score:   float = 5.0          # starts neutral
    verdict: str   = "AMBER"      # GREEN | AMBER | RED
    flags:   List[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise_domain(raw: str) -> str:
    """Strip scheme, www prefix, trailing slashes, and path components."""
    raw = raw.strip().lower()
    raw = re.sub(r'^https?://', '', raw)
    raw = re.sub(r'^www\.', '', raw)
    raw = raw.split('/')[0].split('?')[0].split('#')[0]
    return raw


def tld_of(domain: str) -> str:
    parts = domain.rstrip('.').split('.')
    return parts[-1] if len(parts) > 1 else ''


def is_suspicious_name(domain: str) -> bool:
    """Heuristic: heavy hyphens or numerics suggest auto-generated link-farm domains."""
    name = domain.split('.')[0] if '.' in domain else domain
    hyphen_ratio = name.count('-') / max(len(name), 1)
    digit_ratio  = sum(c.isdigit() for c in name) / max(len(name), 1)
    # More than 3 hyphens OR hyphen density > 30% OR digit density > 40%
    return (name.count('-') > 3) or (hyphen_ratio > 0.30) or (digit_ratio > 0.40)


def read_input(path: str) -> List[DomainResult]:
    """
    Parse a GSC 'Top linking sites' CSV export or a plain-text domain list.

    GSC CSV formats vary slightly; we look for a column containing 'domain'
    or 'site' (case-insensitive) for the domain, and 'linking' / 'target'
    columns for page counts.  Falls back to treating every non-empty non-
    comment line as a bare domain.
    """
    results = []
    seen: set = set()

    try:
        with open(path, newline='', encoding='utf-8-sig') as fh:
            sample = fh.read(1024)
            fh.seek(0)

            # Detect CSV vs plain text
            if ',' in sample or '\t' in sample:
                dialect = 'excel-tab' if '\t' in sample else 'excel'
                reader  = csv.DictReader(fh, dialect=dialect)
                rows    = list(reader)

                if not rows:
                    return results

                headers = [h.lower().strip() for h in rows[0].keys()]

                # Find the domain column
                domain_col = None
                for h in headers:
                    if any(kw in h for kw in ('domain', 'site', 'url', 'linking site')):
                        domain_col = h
                        break
                if domain_col is None:
                    # Use first column as fallback
                    domain_col = headers[0]

                # Find optional count / anchor columns
                link_col   = next((h for h in headers if 'linking' in h and 'page' in h), None)
                target_col = next((h for h in headers if 'target'  in h and 'page' in h), None)
                anchor_col = next((h for h in headers if 'anchor' in h or 'text' in h), None)

                for orig_row in rows:
                    # Re-key by lowercase header
                    row = {k.lower().strip(): v for k, v in orig_row.items()}
                    raw = row.get(domain_col, '').strip()
                    if not raw or raw.startswith('#'):
                        continue
                    domain = normalise_domain(raw)
                    if not domain or domain in seen:
                        continue
                    seen.add(domain)

                    dr = DomainResult(domain=domain)
                    if link_col:
                        try: dr.linking_pages = int(row.get(link_col, '0').replace(',', ''))
                        except ValueError: pass
                    if target_col:
                        try: dr.target_pages = int(row.get(target_col, '0').replace(',', ''))
                        except ValueError: pass
                    if anchor_col:
                        dr.anchors = row.get(anchor_col, '').strip()
                    results.append(dr)

            else:
                # Plain text — one domain per line
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    domain = normalise_domain(line)
                    if not domain or domain in seen:
                        continue
                    seen.add(domain)
                    results.append(DomainResult(domain=domain))

    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR reading {path}: {exc}", file=sys.stderr)
        sys.exit(1)

    return results

# ---------------------------------------------------------------------------
# Open PageRank API
# ---------------------------------------------------------------------------

def fetch_opr(domains: List[str], api_key: str) -> dict:
    """
    Query OPR in batches of OPR_BATCH.
    Returns dict: domain -> {'page_rank_decimal': float, 'rank': int}
    """
    results = {}
    for i in range(0, len(domains), OPR_BATCH):
        batch = domains[i:i + OPR_BATCH]
        params = urllib.parse.urlencode([('domains[]', d) for d in batch])
        url = f"{OPR_ENDPOINT}?{params}"
        req = urllib.request.Request(url, headers={'API-OPR': api_key})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            for entry in data.get('response', []):
                dom = normalise_domain(entry.get('domain', ''))
                if dom:
                    results[dom] = {
                        'page_rank_decimal': entry.get('page_rank_decimal'),
                        'rank': entry.get('rank'),
                    }
        except Exception as exc:
            print(f"  OPR batch {i//OPR_BATCH + 1} error: {exc}", file=sys.stderr)
        if i + OPR_BATCH < len(domains):
            time.sleep(DELAY)
    return results


def apply_opr(results: List[DomainResult], api_key: str) -> None:
    if not api_key:
        return
    print(f"  Checking Open PageRank for {len(results)} domain(s)…")
    non_auth = [r for r in results if not r.authoritative]
    domains  = [r.domain for r in non_auth]
    opr_data = fetch_opr(domains, api_key)
    for r in non_auth:
        entry = opr_data.get(r.domain)
        if entry:
            pr = entry.get('page_rank_decimal')
            if pr is not None:
                r.opr_score = float(pr)
                r.opr_rank  = entry.get('rank')
        else:
            r.opr_error = 'not in OPR index'

# ---------------------------------------------------------------------------
# Tranco top-1M list (free, no API key required)
# ---------------------------------------------------------------------------

def _cache_is_fresh(path: str) -> bool:
    """Return True if the cache file exists and is younger than TRANCO_CACHE_DAYS."""
    try:
        age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(path))
        return age.days < TRANCO_CACHE_DAYS
    except OSError:
        return False


def fetch_tranco(no_cache: bool = False) -> Dict[str, int]:
    """
    Download (or load from cache) the Tranco top-1M domain list.
    Returns dict: domain -> rank  (1 = most popular).
    The cache lives at TRANCO_CACHE_PATH and is refreshed every TRANCO_CACHE_DAYS days.
    Pass no_cache=True to force a fresh download regardless of cache age.
    """
    if not no_cache and _cache_is_fresh(TRANCO_CACHE_PATH):
        print(f"  Loading Tranco list from cache ({TRANCO_CACHE_PATH})…")
        return _load_tranco_csv(TRANCO_CACHE_PATH)

    print(f"  Downloading Tranco top-1M list from {TRANCO_URL} …")
    try:
        req = urllib.request.Request(
            TRANCO_URL,
            headers={'User-Agent': 'ELH-backlink-checker/1.0'},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()

        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            # The zip contains a single CSV named top-1m.csv
            csv_name = next(n for n in zf.namelist() if n.endswith('.csv'))
            csv_bytes = zf.read(csv_name)

        with open(TRANCO_CACHE_PATH, 'wb') as fh:
            fh.write(csv_bytes)
        print(f"  Tranco list cached → {TRANCO_CACHE_PATH}")
        return _load_tranco_csv(TRANCO_CACHE_PATH)

    except Exception as exc:
        print(f"  WARNING: Could not fetch Tranco list: {exc}", file=sys.stderr)
        # Try stale cache as a last resort
        if os.path.exists(TRANCO_CACHE_PATH):
            print(f"  Falling back to stale Tranco cache.", file=sys.stderr)
            return _load_tranco_csv(TRANCO_CACHE_PATH)
        return {}


def _load_tranco_csv(path: str) -> Dict[str, int]:
    """Parse the cached Tranco CSV (rank,domain) and return {domain: rank}."""
    data: Dict[str, int] = {}
    try:
        with open(path, newline='', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',', 1)
                if len(parts) != 2:
                    continue
                try:
                    rank = int(parts[0])
                    domain = parts[1].strip().lower()
                    if domain:
                        data[domain] = rank
                except ValueError:
                    continue
    except OSError as exc:
        print(f"  WARNING: Cannot read Tranco cache: {exc}", file=sys.stderr)
    return data


def apply_tranco(results: List[DomainResult], tranco_data: Dict[str, int],
                 opr_active: bool) -> None:
    """
    Check each non-authoritative domain against the Tranco list and set
    tranco_rank / tranco_tier.  When OPR is active, Tranco still populates
    tranco_rank but compute_scores() will prefer the OPR signal.
    """
    if not tranco_data:
        return
    matched = 0
    non_auth = [r for r in results if not r.authoritative]
    for r in non_auth:
        rank = tranco_data.get(r.domain)
        if rank is not None:
            r.tranco_rank = rank
            if rank <= TRANCO_HIGH_RANK:
                r.tranco_tier = 'high'
            else:
                r.tranco_tier = 'medium'
            matched += 1
    source_note = " (OPR takes precedence)" if opr_active else ""
    print(f"  Tranco: {matched}/{len(non_auth)} domain(s) found in top-1M list{source_note}.")

# ---------------------------------------------------------------------------
# Google Safe Browsing API
# ---------------------------------------------------------------------------

def _host_from_url(url: str) -> str:
    """
    Parse the hostname from a URL and normalise it the same way normalise_domain()
    does: strip scheme, strip leading www., strip port, lower-case.

    Examples:
        http://www.spam.com/path  -> spam.com
        https://notexample.com/   -> notexample.com
        example.com               -> example.com
    """
    try:
        netloc = urllib.parse.urlparse(url).netloc
    except Exception:
        netloc = ''
    host = (netloc or url).lower()
    host = re.sub(r'^www\.', '', host)
    host = host.split(':')[0]  # strip port
    host = host.split('/')[0]  # guard against bare url with no scheme
    return host.strip()


def fetch_gsb(domains: List[str], api_key: str) -> dict:
    """
    Query Google Safe Browsing v4 Lookup API.
    Returns dict: domain -> list of threat types found.

    Threat URLs returned by the API are matched back to the requested domain
    by exact hostname comparison (after stripping scheme/www/port) — NOT by
    substring search — so 'notexample.com' can never pollute 'example.com'.
    """
    threats: dict = {}
    urls_to_check = [f"http://{d}/" for d in domains]
    # Build a lookup set for O(1) exact matching
    domain_set = set(domains)

    for i in range(0, len(urls_to_check), GSB_BATCH):
        batch_urls = urls_to_check[i:i + GSB_BATCH]
        payload = {
            "client": {"clientId": "elh-backlink-checker", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes":      ["MALWARE", "SOCIAL_ENGINEERING",
                                     "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes":    ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries":    [{"url": u} for u in batch_urls],
            },
        }
        endpoint = f"{GSB_ENDPOINT}?key={api_key}"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            for match in data.get('matches', []):
                matched_url  = match.get('threat', {}).get('url', '')
                threat_type  = match.get('threatType', 'UNKNOWN')
                matched_host = _host_from_url(matched_url)
                # Exact domain match only — substring collisions are impossible
                if matched_host in domain_set:
                    threats.setdefault(matched_host, []).append(threat_type)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            print(f"  GSB batch {i//GSB_BATCH + 1} HTTP {exc.code}: {body[:120]}", file=sys.stderr)
        except Exception as exc:
            print(f"  GSB batch {i//GSB_BATCH + 1} error: {exc}", file=sys.stderr)
        if i + GSB_BATCH < len(urls_to_check):
            time.sleep(DELAY)
    return threats


def apply_gsb(results: List[DomainResult], api_key: str) -> None:
    if not api_key:
        return
    print(f"  Checking Google Safe Browsing for {len(results)} domain(s)…")
    non_auth = [r for r in results if not r.authoritative]
    domains  = [r.domain for r in non_auth]
    gsb_data = fetch_gsb(domains, api_key)
    for r in non_auth:
        r.gsb_checked = True
        r.gsb_threats = gsb_data.get(r.domain, [])

# ---------------------------------------------------------------------------
# Heuristics & scoring
# ---------------------------------------------------------------------------

def apply_heuristics(results: List[DomainResult]) -> None:
    for r in results:
        # Authoritative domain override
        base = r.domain
        # Check if base OR any parent matches an authoritative domain
        parts = base.split('.')
        for i in range(len(parts) - 1):
            candidate = '.'.join(parts[i:])
            if candidate in AUTHORITATIVE_DOMAINS:
                r.authoritative = True
                break

        if r.authoritative:
            r.score   = 10.0
            r.verdict = 'GREEN'
            r.flags.append('authoritative domain')
            continue

        r.spammy_tld  = tld_of(r.domain) in SPAMMY_TLDS
        r.suspicious  = is_suspicious_name(r.domain)


def compute_scores(results: List[DomainResult]) -> None:
    for r in results:
        if r.authoritative:
            continue   # already scored above

        score = 5.0

        # Authority contribution — OPR score takes precedence when available.
        # When OPR has no score for a domain, Tranco is tried next.
        # The OPR-missing penalty only applies when neither source has a signal.
        if r.opr_score is not None:
            if r.opr_score >= 7:
                score += 3
                r.flags.append(f'OPR {r.opr_score:.1f}/10 — high authority')
            elif r.opr_score >= 3:
                r.flags.append(f'OPR {r.opr_score:.1f}/10 — medium authority')
            else:
                score -= 3
                r.flags.append(f'OPR {r.opr_score:.1f}/10 — low authority')
        elif r.tranco_tier == 'high':
            score += 3
            r.flags.append(f'Tranco rank #{r.tranco_rank:,} — high authority (top 100k)')
        elif r.tranco_tier == 'medium':
            r.flags.append(f'Tranco rank #{r.tranco_rank:,} — medium authority (top 1M)')
        elif r.opr_error:
            # OPR was queried but has no data for this domain, and Tranco has no signal either
            score -= 1
            r.flags.append(f'OPR: {r.opr_error}')
        # Absent from Tranco with no OPR data: no penalty — many legitimate niche sites
        # aren't in the top 1M

        # Safe Browsing
        if r.gsb_checked and r.gsb_threats:
            score -= 10
            for t in r.gsb_threats:
                r.flags.append(f'⚠ GSB: {t.replace("_", " ").title()}')
        elif r.gsb_checked:
            r.flags.append('Safe Browsing: clean')

        # Heuristics
        if r.spammy_tld:
            score -= 3
            r.flags.append(f'spammy TLD (.{tld_of(r.domain)})')
        if r.suspicious:
            score -= 2
            r.flags.append('suspicious domain pattern')

        r.score = score

        # Verdict
        has_threat = bool(r.gsb_threats)
        if score >= 6 and not has_threat:
            r.verdict = 'GREEN'
        elif score >= 3 and not has_threat:
            r.verdict = 'AMBER'
        else:
            r.verdict = 'RED'

# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------

VERDICT_COLOR = {
    'GREEN': ('#1a7a4a', '#e6f5ed', '✅ Healthy'),
    'AMBER': ('#7a5c00', '#fff8e0', '⚠️ Review'),
    'RED':   ('#8b1a1a', '#fde8e8', '🚫 Toxic'),
}


def render_html(results: List[DomainResult], input_file: str, today: str,
                opr_active: bool, gsb_active: bool, tranco_active: bool = False) -> str:
    green = sum(1 for r in results if r.verdict == 'GREEN')
    amber = sum(1 for r in results if r.verdict == 'AMBER')
    red   = sum(1 for r in results if r.verdict == 'RED')
    total = len(results)

    def esc(s):
        return html_lib.escape(str(s))

    rows_html = []
    for r in results:
        color, bg, label = VERDICT_COLOR[r.verdict]
        if r.opr_score is not None:
            authority_cell = f'<b>{r.opr_score:.1f}</b>/10 <span style="color:#999;font-size:11px">OPR</span>'
        elif r.tranco_rank is not None:
            tier_label = 'high' if r.tranco_tier == 'high' else 'mid'
            authority_cell = (
                f'#{r.tranco_rank:,} '
                f'<span style="color:#999;font-size:11px">Tranco·{tier_label}</span>'
            )
        else:
            authority_cell = '<span style="color:#999">—</span>'
        gsb_cell = (
            '🚫 ' + ', '.join(t.replace('_', ' ').title() for t in r.gsb_threats) if r.gsb_threats
            else ('✅ clean' if r.gsb_checked else '<span style="color:#999">—</span>')
        )
        flags_cell = '; '.join(esc(f) for f in r.flags) or '—'
        lp = r.linking_pages or '—'
        rows_html.append(f"""
        <tr style="background:{bg}">
          <td><a href="https://{esc(r.domain)}" target="_blank" rel="noopener noreferrer"
                 style="color:{color};font-weight:600;word-break:break-all">{esc(r.domain)}</a></td>
          <td style="text-align:center">{authority_cell}</td>
          <td style="text-align:center">{gsb_cell}</td>
          <td style="font-size:12px;color:#444">{flags_cell}</td>
          <td style="text-align:center">{lp}</td>
          <td style="text-align:center;font-weight:700;color:{color}">{label}</td>
        </tr>""")

    apis_note = []
    if opr_active:     apis_note.append('Open PageRank')
    if tranco_active:  apis_note.append('Tranco top-1M')
    if gsb_active:     apis_note.append('Google Safe Browsing')
    if not apis_note:  apis_note.append('heuristics only — set GOOGLE_API_KEY for Safe Browsing; Tranco used automatically')
    apis_str = esc(', '.join(apis_note))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Backlink Health Report — {esc(today)}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#222;padding:24px}}
  h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
  .meta{{font-size:13px;color:#666;margin-bottom:24px}}
  .cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .card{{background:#fff;border-radius:10px;padding:18px 24px;min-width:130px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .card .n{{font-size:36px;font-weight:700;line-height:1.1}}
  .card .l{{font-size:12px;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:.06em}}
  .card.green .n{{color:#1a7a4a}} .card.amber .n{{color:#7a5c00}} .card.red .n{{color:#8b1a1a}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;
         overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);font-size:13.5px}}
  th{{background:#2c2c3e;color:#fff;padding:10px 12px;text-align:left;font-size:12px;
      text-transform:uppercase;letter-spacing:.07em;cursor:pointer;user-select:none;white-space:nowrap}}
  th:hover{{background:#3a3a52}}
  td{{padding:9px 12px;vertical-align:top;border-bottom:1px solid rgba(0,0,0,.04)}}
  tr:last-child td{{border-bottom:none}}
  .legend{{margin-top:20px;font-size:12px;color:#666}}
  input#search{{width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:8px;
               font-size:14px;margin-bottom:16px;outline:none}}
  input#search:focus{{border-color:#5a5aff;box-shadow:0 0 0 3px rgba(90,90,255,.15)}}
  @media(max-width:640px){{.cards{{flex-direction:column}}.card{{min-width:0}}}}
</style>
</head>
<body>
<h1>Backlink Health Report — Eternal Life Hospice</h1>
<p class="meta">Generated: {esc(today)} &nbsp;·&nbsp; Source: {esc(os.path.basename(input_file))}
  &nbsp;·&nbsp; APIs used: {apis_str}</p>

<div class="cards">
  <div class="card"><div class="n">{total}</div><div class="l">Total domains</div></div>
  <div class="card green"><div class="n">{green}</div><div class="l">✅ Healthy</div></div>
  <div class="card amber"><div class="n">{amber}</div><div class="l">⚠️ Review needed</div></div>
  <div class="card red"><div class="n">{red}</div><div class="l">🚫 Toxic / flag</div></div>
</div>

<input type="text" id="search" placeholder="Filter domains…" oninput="filterTable(this.value)">

<table id="tbl">
<thead>
  <tr>
    <th onclick="sortTable(0)">Domain ↕</th>
    <th onclick="sortTable(1)" style="width:120px">Authority Score ↕</th>
    <th onclick="sortTable(2)" style="width:130px">Safe Browsing ↕</th>
    <th>Signals</th>
    <th onclick="sortTable(4)" style="width:90px">Linking pages ↕</th>
    <th onclick="sortTable(5)" style="width:110px">Verdict ↕</th>
  </tr>
</thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>

<p class="legend">Authority scoring: OPR ≥ 7 or Tranco rank ≤ 100k = high (+3); OPR 3–6 or Tranco rank 100k–1M = medium (0);
OPR &lt; 3 = low (−3); absent from Tranco = no penalty.
Google Safe Browsing threat = instant red (−10); spammy TLD (−3); suspicious name pattern (−2).
Green = score ≥ 6, no threat. Amber = score ≥ 3. Red = score &lt; 3 or threat detected.
Authority source shown as <i>OPR</i> (Open PageRank, if key set) or <i>Tranco</i> (free, no signup needed).</p>

<script>
let sortDir = {{}};
function sortTable(col) {{
  const tbody = document.querySelector('#tbl tbody');
  const rows  = [...tbody.rows];
  const asc   = !sortDir[col];
  sortDir = {{}};
  sortDir[col] = asc;
  rows.sort((a, b) => {{
    const av = a.cells[col].innerText.trim();
    const bv = b.cells[col].innerText.trim();
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
function filterTable(q) {{
  const rows = document.querySelectorAll('#tbl tbody tr');
  const lq = q.toLowerCase();
  rows.forEach(r => {{
    r.style.display = r.innerText.toLowerCase().includes(lq) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Disavow file generation
# ---------------------------------------------------------------------------

def render_disavow(results: List[DomainResult], today: str) -> str:
    red_results = [r for r in results if r.verdict == 'RED']
    lines = [
        f"# Google Disavow File — Eternal Life Hospice (eternallifehospice.com)",
        f"# Generated: {today} by check-backlinks.py",
        f"#",
        f"# REVIEW BEFORE SUBMITTING: Google advises disavowing only when you",
        f"# have a confirmed manual action or a clear spam-link pattern you",
        f"# cannot resolve by contacting the site owner.",
        f"# Upload at: https://search.google.com/search-console/disavow-links",
        f"#",
    ]
    if not red_results:
        lines.append("# No red-flagged domains found — this file has zero active entries.")
        lines.append("# Do not submit an empty disavow file.")
    else:
        lines.append(f"# {len(red_results)} domain(s) flagged as toxic/harmful:")
        lines.append("#")
        for r in red_results:
            reason = '; '.join(r.flags) if r.flags else 'low composite score'
            lines.append(f"# {r.domain}: {reason}")
        lines.append("#")
        lines.append("# --- Active entries ---")
        for r in red_results:
            lines.append(f"domain:{r.domain}")
    return '\n'.join(lines) + '\n'

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ELH Backlink Health Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--input',      required=True, metavar='FILE',
                        help='GSC CSV export or plain-text domain list')
    parser.add_argument('--output-dir', default='exports/seo', metavar='DIR',
                        help='Directory for report outputs (default: exports/seo)')
    parser.add_argument('--dry-run',    action='store_true',
                        help='Check first 5 domains, print to terminal, write no files')
    parser.add_argument('--no-cache',   action='store_true',
                        help='Force a fresh Tranco list download, ignoring the local cache')
    args = parser.parse_args()

    opr_key = os.environ.get('OPR_API_KEY', '').strip()
    gsb_key = os.environ.get('GOOGLE_API_KEY', '').strip()
    today   = datetime.date.today().isoformat()

    # Read input
    print(f"\nReading: {args.input}")
    results = read_input(args.input)
    if not results:
        print("No domains found in input file.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(results)} unique domain(s).")

    if args.dry_run:
        results = results[:5]
        print(f"[dry-run] Processing first {len(results)} domain(s) only — no files will be written.\n")

    # Pipeline
    print("\nRunning analysis…")
    apply_heuristics(results)

    if opr_key:
        apply_opr(results, opr_key)
    else:
        print("  OPR_API_KEY not set — Tranco will provide authority scores (no signup required).")

    # Tranco: always attempted as a free authority signal; OPR takes precedence when set
    tranco_data = fetch_tranco(no_cache=args.no_cache)
    tranco_active = bool(tranco_data)
    apply_tranco(results, tranco_data, opr_active=bool(opr_key))

    if gsb_key:
        apply_gsb(results, gsb_key)
    else:
        print("  GOOGLE_API_KEY not set — skipping Google Safe Browsing check.")

    compute_scores(results)

    # Summary
    green = [r for r in results if r.verdict == 'GREEN']
    amber = [r for r in results if r.verdict == 'AMBER']
    red   = [r for r in results if r.verdict == 'RED']

    print(f"\n{'═'*55}")
    print(f"  Backlink Health Summary")
    print(f"{'═'*55}")
    print(f"  Total domains : {len(results)}")
    print(f"  ✅ Healthy     : {len(green)}")
    print(f"  ⚠️  Review      : {len(amber)}")
    print(f"  🚫 Toxic/flag  : {len(red)}")
    print(f"{'═'*55}\n")

    if red:
        print("  RED-flagged domains:")
        for r in red:
            print(f"    • {r.domain}  [{'; '.join(r.flags[:2])}]")
        print()

    if args.dry_run:
        print("[dry-run] No files written. Remove --dry-run to generate the full report.\n")
        sys.exit(0)

    # Write outputs
    os.makedirs(args.output_dir, exist_ok=True)

    report_path  = os.path.join(args.output_dir, f"backlink-report-{today}.html")
    disavow_path = os.path.join(args.output_dir, f"disavow-{today}.txt")

    html_content = render_html(results, args.input, today,
                               opr_active=bool(opr_key), gsb_active=bool(gsb_key),
                               tranco_active=tranco_active)
    with open(report_path, 'w', encoding='utf-8') as fh:
        fh.write(html_content)

    disavow_content = render_disavow(results, today)
    with open(disavow_path, 'w', encoding='utf-8') as fh:
        fh.write(disavow_content)

    print(f"  Report   → {report_path}")
    print(f"  Disavow  → {disavow_path}")
    if red:
        print(f"\n  ⚠️  {len(red)} domain(s) flagged as toxic — review the disavow file before submitting to Google.")
    else:
        print("\n  ✅ No toxic domains found — disavow file is empty (do not submit it).")
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
