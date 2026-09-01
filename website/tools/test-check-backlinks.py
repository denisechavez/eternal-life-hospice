#!/usr/bin/env python3
"""
Regression tests for check-backlinks.py

Tests:
  1. _host_from_url() exact hostname extraction (no substring collisions)
  2. GSB threat attribution — notexample.com threat must NOT poison example.com
  3. GSC CSV parsing — domain, linking-pages, and anchor columns extracted
  4. Plain-text input parsing
  5. Heuristic scoring — spammy TLD, suspicious name, authoritative domain
  6. Scoring / verdict thresholds
  7. Disavow file rendered only for RED domains

Run:
    python3 website/tools/test-check-backlinks.py
"""

import sys
import os
import types
import importlib
import importlib.util

# ---------------------------------------------------------------------------
# Locate the module relative to this test file's location
# ---------------------------------------------------------------------------
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)

# Load check-backlinks.py as a module (file has a hyphen — use importlib)
spec   = importlib.util.spec_from_file_location(
    "check_backlinks",
    os.path.join(TOOLS_DIR, "check-backlinks.py"),
)
mod    = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DomainResult    = mod.DomainResult
_host_from_url  = mod._host_from_url
apply_heuristics = mod.apply_heuristics
compute_scores   = mod.compute_scores
render_disavow   = mod.render_disavow
read_input       = mod.read_input
normalise_domain = mod.normalise_domain

# ---------------------------------------------------------------------------
# Tiny test harness
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def section(title):
    print(f"\n=== {title} ===")

# ---------------------------------------------------------------------------
# 1. _host_from_url — exact hostname extraction
# ---------------------------------------------------------------------------
section("_host_from_url() hostname extraction")

cases = [
    ("http://www.spam.com/bad-page",     "spam.com"),
    ("https://notexample.com/path",      "notexample.com"),
    ("http://example.com/",              "example.com"),
    ("http://sub.example.com/",          "sub.example.com"),
    ("https://foo.bar:8080/path?q=1",    "foo.bar"),
    ("malware.xyz",                      "malware.xyz"),
    ("http://www.example.com",           "example.com"),
]
for url, expected in cases:
    got = _host_from_url(url)
    check(f"_host_from_url({url!r}) == {expected!r}", got == expected,
          f"got {got!r}")

# ---------------------------------------------------------------------------
# 2. GSB threat attribution — substring collision safety
# ---------------------------------------------------------------------------
section("GSB threat attribution (no substring pollution)")

# Simulate what fetch_gsb does internally after receiving a match:
# a threat on "notexample.com" must NOT be attributed to "example.com"
requested_domains = ["example.com", "notexample.com", "bbb.org"]
domain_set = set(requested_domains)

threat_url  = "http://notexample.com/malware"
threat_host = _host_from_url(threat_url)

check("threat host parsed as 'notexample.com'",
      threat_host == "notexample.com")
check("'notexample.com' IS in domain_set",
      threat_host in domain_set)
check("'example.com' would NOT be wrongly matched via substring",
      # Old buggy check: 'example.com' in 'http://notexample.com/malware' → True (BAD)
      "example.com" in threat_url)   # demonstrates the OLD bug was real
check("New exact match: 'example.com' NOT attributed",
      threat_host != "example.com")
check("'bbb.org' NOT attributed for a notexample.com threat",
      threat_host != "bbb.org")

# Threat on www.example.com must reach example.com
threat_url2  = "http://www.example.com/phishing"
threat_host2 = _host_from_url(threat_url2)
check("www.example.com threat maps to 'example.com' after normalisation",
      threat_host2 == "example.com")
check("'example.com' IS in domain_set (correctly attributed)",
      threat_host2 in domain_set)

# ---------------------------------------------------------------------------
# 3. CSV parsing — GSC 'Top linking sites' format
# ---------------------------------------------------------------------------
section("CSV parsing — GSC format")

import csv, io, tempfile

GSC_CSV = """\
Top linking sites,Linking pages,Target pages
hcai.ca.gov,12,5
bbb.org,3,1
spam-site.xyz,1,1
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False,
                                 encoding='utf-8') as f:
    f.write(GSC_CSV)
    csv_path = f.name

results = read_input(csv_path)
os.unlink(csv_path)

check("CSV: 3 domains parsed", len(results) == 3, f"got {len(results)}")
domains = [r.domain for r in results]
check("CSV: hcai.ca.gov present", "hcai.ca.gov" in domains)
check("CSV: spam-site.xyz present", "spam-site.xyz" in domains)
check("CSV: linking_pages parsed for hcai.ca.gov",
      next(r for r in results if r.domain == "hcai.ca.gov").linking_pages == 12)
check("CSV: no duplicate domains", len(domains) == len(set(domains)))

# ---------------------------------------------------------------------------
# 4. Plain-text parsing
# ---------------------------------------------------------------------------
section("Plain-text input parsing")

TXT = """\
# comment line — should be skipped
hcai.ca.gov
https://www.bbb.org/some/path
spam.xyz
spam.xyz
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                 encoding='utf-8') as f:
    f.write(TXT)
    txt_path = f.name

txt_results = read_input(txt_path)
os.unlink(txt_path)

txt_domains = [r.domain for r in txt_results]
check("TXT: 3 unique domains (comment + duplicate stripped)",
      len(txt_results) == 3, f"got {len(txt_results)}: {txt_domains}")
check("TXT: scheme+www stripped from bbb.org", "bbb.org" in txt_domains)
check("TXT: spam.xyz deduplicated (appears once)", txt_domains.count("spam.xyz") == 1)

# ---------------------------------------------------------------------------
# 5. Heuristic signals
# ---------------------------------------------------------------------------
section("Heuristic scoring signals")

r_auth  = DomainResult(domain="medicare.gov")
r_spam  = DomainResult(domain="buy-cheap-links.xyz")
r_susp  = DomainResult(domain="click-here-now-4-free-stuff1234.com")
r_clean = DomainResult(domain="venturacountyhospice.com")

apply_heuristics([r_auth, r_spam, r_susp, r_clean])

check("medicare.gov flagged authoritative",    r_auth.authoritative)
check("buy-cheap-links.xyz flagged spammy TLD", r_spam.spammy_tld)
check("buy-cheap-links.xyz NOT authoritative",  not r_spam.authoritative)
check("suspicious domain: many hyphens+digits flagged", r_susp.suspicious)
check("venturacountyhospice.com: no spammy TLD", not r_clean.spammy_tld)
check("venturacountyhospice.com: not suspicious", not r_clean.suspicious)

# ---------------------------------------------------------------------------
# 6. Scoring and verdicts
# ---------------------------------------------------------------------------
section("Scoring and verdict thresholds")

# Authoritative domain → always GREEN after apply_heuristics
check("authoritative domain → GREEN verdict", r_auth.verdict == "GREEN")

# Spammy TLD without OPR → score should drop below 6 → at least AMBER
compute_scores([r_spam, r_susp, r_clean])
check("spammy TLD verdict is RED (score < 3 from 5 - 3)",
      r_spam.verdict == "RED",
      f"got verdict={r_spam.verdict} score={r_spam.score}")
check("clean domain with no signals defaults to AMBER (neutral score 5)",
      r_clean.verdict == "AMBER",
      f"got verdict={r_clean.verdict} score={r_clean.score}")

# High OPR score should push to GREEN
r_high_opr = DomainResult(domain="trusted-partner.com")
apply_heuristics([r_high_opr])
r_high_opr.opr_score = 8.5
compute_scores([r_high_opr])
check("OPR 8.5 → GREEN (score 5 + 3 = 8 ≥ 6)",
      r_high_opr.verdict == "GREEN",
      f"got verdict={r_high_opr.verdict} score={r_high_opr.score}")

# Low OPR + spammy TLD → RED
r_toxic = DomainResult(domain="linkfarm.tk")
apply_heuristics([r_toxic])
r_toxic.opr_score = 1.2
compute_scores([r_toxic])
check("OPR 1.2 + spammy TLD → RED",
      r_toxic.verdict == "RED",
      f"got verdict={r_toxic.verdict} score={r_toxic.score}")

# GSB threat → RED regardless of OPR
r_gsb = DomainResult(domain="malware-site.com")
apply_heuristics([r_gsb])
r_gsb.opr_score  = 8.0   # high OPR, but...
r_gsb.gsb_checked = True
r_gsb.gsb_threats = ["MALWARE"]
compute_scores([r_gsb])
check("GSB malware threat → RED even with high OPR",
      r_gsb.verdict == "RED",
      f"got verdict={r_gsb.verdict} score={r_gsb.score}")

# ---------------------------------------------------------------------------
# 7. Disavow file — only RED domains included
# ---------------------------------------------------------------------------
section("Disavow file output")

all_results = [r_auth, r_spam, r_susp, r_clean, r_high_opr, r_toxic, r_gsb]
disavow = render_disavow(all_results, "2026-08-13")
red_in_disavow = [r for r in all_results if r.verdict == "RED"]

for r in red_in_disavow:
    check(f"RED domain '{r.domain}' appears in disavow file",
          f"domain:{r.domain}" in disavow)

green_domains = [r for r in all_results if r.verdict == "GREEN"]
for r in green_domains:
    check(f"GREEN domain '{r.domain}' NOT in disavow file",
          f"domain:{r.domain}" not in disavow)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*55}")
print(f"  Results: {PASS} passed, {FAIL} failed")
print(f"{'='*55}")
sys.exit(0 if FAIL == 0 else 1)
