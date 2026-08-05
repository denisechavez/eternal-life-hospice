#!/usr/bin/env python3
"""
PageSpeed Insights API smoke-test.

Usage:
    python3 website/check-pagespeed.py
    python3 website/check-pagespeed.py --url https://eternallifehospice.com/about --strategy desktop

Returns exit code 0 on success, 1 on any error.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse

DEFAULT_URL = "https://eternallifehospice.com"
DEFAULT_STRATEGY = "mobile"
PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

AUDITS_OF_INTEREST = [
    ("uses-long-cache-ttl",    "Serve static assets with an efficient cache policy"),
    ("largest-contentful-paint", "Largest Contentful Paint (LCP)"),
    ("first-contentful-paint", "First Contentful Paint (FCP)"),
    ("speed-index",            "Speed Index"),
    ("total-blocking-time",    "Total Blocking Time"),
    ("cumulative-layout-shift", "Cumulative Layout Shift"),
    ("performance",            "Overall performance score"),
]


def run(url: str, strategy: str, key: str) -> dict:
    params = urllib.parse.urlencode({
        "url": url,
        "strategy": strategy,
        "key": key,
        "category": "performance",
    })
    req = urllib.request.urlopen(f"{PSI_ENDPOINT}?{params}", timeout=60)
    return json.loads(req.read())


def extract_scores(data: dict) -> dict:
    cats  = data.get("lighthouseResult", {}).get("categories", {})
    audits = data.get("lighthouseResult", {}).get("audits", {})

    results = {}

    perf_score = cats.get("performance", {}).get("score")
    if perf_score is not None:
        results["performance"] = round(perf_score * 100)

    for audit_id, label in AUDITS_OF_INTEREST:
        if audit_id == "performance":
            continue
        audit = audits.get(audit_id, {})
        score = audit.get("score")
        display = audit.get("displayValue", "")
        results[audit_id] = {
            "label": label,
            "score": round(score * 100) if score is not None else None,
            "displayValue": display,
        }

    return results


THRESHOLD_DEFAULT = 80


def main():
    parser = argparse.ArgumentParser(description="PageSpeed Insights API smoke-test")
    parser.add_argument("--url",       default=DEFAULT_URL,      help="Page URL to test")
    parser.add_argument("--strategy",  default=DEFAULT_STRATEGY, choices=["mobile", "desktop"])
    parser.add_argument(
        "--threshold",
        type=int,
        default=THRESHOLD_DEFAULT,
        help=f"Minimum acceptable performance score (0–100). Exit 1 if below. Default: {THRESHOLD_DEFAULT}",
    )
    args = parser.parse_args()

    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        print("ERROR: GOOGLE_API_KEY env var is not set", file=sys.stderr)
        sys.exit(1)

    print(f"Running PageSpeed Insights for {args.url} ({args.strategy})…")
    try:
        data = run(args.url, args.strategy, key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
            reason = (err.get("error", {}).get("details") or [{}])[0].get("reason", "")
        except Exception:
            msg, reason = body, ""
        print(f"ERROR {exc.code}: {msg}", file=sys.stderr)
        if reason == "API_KEY_SERVICE_BLOCKED":
            print(
                "\n  Fix: open https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com"
                "\n  for project 181277979525 and click Enable."
                "\n  Also check the key's API restrictions at:"
                "\n  https://console.cloud.google.com/apis/credentials",
                file=sys.stderr,
            )
        sys.exit(1)

    scores = extract_scores(data)

    print(f"\n{'='*55}")
    print(f"  PageSpeed Insights — {args.strategy.upper()}")
    print(f"{'='*55}")

    perf = scores.pop("performance", None)
    if perf is not None:
        bar = "█" * (perf // 5)
        print(f"  Overall performance : {perf:>3}/100  {bar}")

    print()
    for audit_id, info in scores.items():
        label = info["label"]
        score = info["score"]
        dv    = info["displayValue"]
        score_str = f"{score:>3}/100" if score is not None else "  n/a  "
        print(f"  {label:<50}  {score_str}  {dv}")

    print(f"{'='*55}\n")

    # Check cache-ttl audit specifically
    cache_audit = scores.get("uses-long-cache-ttl", {})
    cache_score = cache_audit.get("score")
    if cache_score is not None and cache_score < 50:
        print(f"WARNING: Cache-TTL score is low ({cache_score}/100) — review _headers.", file=sys.stderr)

    # Enforce performance threshold
    if perf is not None and perf < args.threshold:
        print(
            f"FAIL: Performance score {perf}/100 is below threshold {args.threshold}/100.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"✓ API call succeeded. Performance score {perf}/100 meets threshold {args.threshold}/100.")
    sys.exit(0)


if __name__ == "__main__":
    main()
