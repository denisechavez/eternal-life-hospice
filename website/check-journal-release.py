#!/usr/bin/env python3
"""Independent approved-release monitor; never schedules newsletters or drafts."""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from journal_release import release_at
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location("identity_email", Path(__file__).with_name("notify-google-place-identity.py"))
email = module_from_spec(spec)
spec.loader.exec_module(email)
JOURNAL_ALERT_EMAIL = "denise@eternallifehospice.com"


def fetch(url):
    request = Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "ELH-Journal-Release-Monitor/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode(), response.headers


def scheduled_today(cron, instant):
    if not cron:
        return True
    local = instant.astimezone(ZoneInfo("America/Los_Angeles"))
    check = (release_at(local.date().isoformat()) + timedelta(minutes=15)).astimezone(timezone.utc)
    return cron == f"45 {check.hour} * * *"


def check(site, getter=fetch):
    try:
        body, _ = getter(site + "/api/journal-release-status")
    except HTTPError as exc:
        if exc.code == 404:
            # New monitor may merge before the user approves deployment.
            return "not-installed", []
        raise
    payload = json.loads(body)
    if payload.get("timezone") != "America/Los_Angeles" or payload.get("releaseTime") != "06:30":
        raise ValueError("Release monitoring contract is invalid")
    # Review availability is independent of approved-release counts. A missing
    # Studio must not look healthy just because nothing has been approved yet.
    studio, _ = getter(site + "/studio/")
    if not re.search(r'<script\b[^>]*\bsrc=["\']/studio/assets/[^"\']+', studio):
        raise ValueError("Live Studio login build is unavailable")
    expected = payload["expected"]
    gaps = [
        f"{day}: no Journal article published for this scheduled date; review approval or hold in Studio"
        for day in payload.get("scheduleGaps", [])
    ]
    if not expected:
        return ("missed", gaps) if gaps else ("healthy", [])
    archive, _ = getter(site + "/blog")
    sitemap, _ = getter(site + "/sitemap.xml")
    search, _ = getter(site + "/assets/search-index.json")
    search_urls = {row["url"] for row in json.loads(search)}

    def verify(row):
        slug, revision = row["slug"], row["revision"]
        failures = []
        if not row["available"]:
            failures.append("approved version is unavailable")
        try:
            article, headers = getter(site + "/blog/" + slug)
            if headers.get("X-Journal-Revision") != revision or "<h1" not in article:
                failures.append("article version does not match approval")
        except Exception:
            failures.append("article URL did not load")
        if not any(href in archive for href in (f'href="blog/{slug}"', f'href="/blog/{slug}"')):
            failures.append("missing from Journal archive")
        if f"/blog/{slug}</loc>" not in sitemap:
            failures.append("missing from sitemap")
        if f"/blog/{slug}" not in search_urls:
            failures.append("missing from site search")
        return f"{slug} ({row['date']}): " + "; ".join(failures) if failures else None

    with ThreadPoolExecutor(max_workers=4) as pool:
        failures = gaps + [value for value in pool.map(verify, expected) if value]
    return ("missed" if failures else "healthy"), failures


def notify(failures, monitoring_unavailable=False, missing_run=False):
    api_key = os.environ.get("BREVO_API")
    if not api_key:
        raise RuntimeError("BREVO_API is not configured")
    message = {
        "sender": {"name": "Eternal Life Hospice Operations", "email": "no-reply@eternallifehospice.com"},
        "to": [{"name": "Denise", "email": JOURNAL_ALERT_EMAIL}],
        "subject": ("ACTION REQUIRED: Journal daily monitor run missing or unverified" if missing_run else
                    "ACTION REQUIRED: Journal release monitoring unavailable" if monitoring_unavailable
                    else "ACTION REQUIRED: Journal daily publication gap"),
        "textContent": (
            "Journal release time: 6:30 a.m. America/Los_Angeles.\n\n"
            + ("The release check could not run. This is a monitoring failure, not evidence that a held draft should publish.\n"
               if monitoring_unavailable else
               "Scheduled days without a published article or failed approved releases are listed below. "
               "Missing approvals require review. Held or unapproved drafts remain private; "
               "this alert never authorizes publication.\n")
            + "\n".join(failures)
            + "\n\nReview the Journal release workflow and Eternal Studio. No content was approved or sent by this check.\n"
        ),
    }
    return email.send_alert(api_key, message, require_message_id=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--scheduled-cron", default="")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--result-file", type=Path)
    args = parser.parse_args()
    instant = datetime.now(timezone.utc)
    result = {
        "schema": 1, "checkedAt": instant.isoformat(),
        "scheduledCron": args.scheduled_cron, "status": "skipped",
        "alert": "not-needed", "messageId": None,
    }

    def finish(code):
        if args.result_file:
            args.result_file.write_text(json.dumps(result) + "\n", encoding="utf-8")
        return code

    if not scheduled_today(args.scheduled_cron, instant):
        print("Journal check skipped: other Pacific UTC offset")
        return finish(0)
    try:
        status, failures = check(args.site.rstrip("/"))
    except Exception as exc:
        status, failures = "unavailable", [f"Monitoring failed: {type(exc).__name__}"]
    if status == "not-installed":
        status, failures = "unavailable", ["Journal release status endpoint is not installed"]
    result["status"] = status
    if status == "healthy":
        print(f"Journal release check: {status}")
        return finish(0)
    print(f"Journal release check: {status}\n" + "\n".join(failures), file=sys.stderr)
    result["alert"] = "suppressed" if args.no_email else "failed"
    if not args.no_email:
        try:
            result["messageId"] = notify(failures, monitoring_unavailable=status == "unavailable")
            result["alert"] = "accepted"
            print("Journal release email accepted by provider")
        except Exception as exc:
            print(f"JOURNAL_ALERT_FAILED channel=email error={type(exc).__name__}", file=sys.stderr)
            return finish(2)
    return finish(1)


if __name__ == "__main__":
    raise SystemExit(main())
