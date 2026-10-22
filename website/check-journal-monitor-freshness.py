#!/usr/bin/env python3
"""Read-only Actions watchdog. Never calls approval or publication endpoints."""
import argparse
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

spec = spec_from_file_location("journal_monitor", Path(__file__).with_name("check-journal-release.py"))
monitor = module_from_spec(spec)
spec.loader.exec_module(monitor)
PACIFIC = ZoneInfo("America/Los_Angeles")


class SafeRedirect(HTTPRedirectHandler):
    """Artifact downloads redirect to signed storage; do not forward the token."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        if redirected and urlsplit(newurl).netloc != urlsplit(request.full_url).netloc:
            redirected.remove_header("Authorization")
        return redirected


def scheduled_today(cron, instant):
    local = instant.astimezone(PACIFIC)
    due = local.replace(hour=8, minute=17, second=0, microsecond=0)
    return not cron or cron == f"17 {due.astimezone(timezone.utc).hour} * * *"


def expected_run(instant):
    local = instant.astimezone(PACIFIC)
    due = local.replace(hour=6, minute=45, second=0, microsecond=0)
    # Before today's grace period ends, verify yesterday instead.
    if local < due + timedelta(minutes=90):
        due -= timedelta(days=1)
    return due.astimezone(timezone.utc)


class Actions:
    def __init__(self, repository, token):
        if not token:
            raise ValueError("Actions read token is missing")
        if len(repository.split("/")) != 2 or any(
                not part or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in part)
                for part in repository.split("/")):
            raise ValueError("Invalid repository")
        self.base = f"https://api.github.com/repos/{repository}"
        self.token = token

    def get(self, path, binary=False):
        request = Request(self.base + path, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ELH-Journal-Freshness/1.0",
        })
        with build_opener(SafeRedirect()).open(request, timeout=20) as response:
            body = response.read()
        return body if binary else json.loads(body)


def check(actions, instant):
    due = expected_run(instant)
    workflow = actions.get("/actions/workflows/journal-release.yml")
    if workflow["state"] != "active":
        return ["Journal release workflow is disabled; daily monitoring is not running."]
    query = urlencode({
        "event": "schedule", "per_page": 100,
        "created": f"{due.isoformat()}..{instant.isoformat()}",
    })
    runs = actions.get("/actions/workflows/journal-release.yml/runs?" + query)["workflow_runs"]
    cron = f"45 {due.hour} * * *"
    problems = []
    for run in runs:
        if run["event"] != "schedule" or run["status"] != "completed":
            continue
        artifacts = actions.get(f"/actions/runs/{run['id']}/artifacts?per_page=100")["artifacts"]
        for artifact in artifacts:
            if artifact["name"] != "journal-monitor-result" or artifact["expired"]:
                continue
            raw = actions.get(f"/actions/artifacts/{artifact['id']}/zip", binary=True)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                result = json.loads(archive.read("journal-monitor-result.json"))
            checked = datetime.fromisoformat(result["checkedAt"])
            if (result.get("schema") != 1 or result.get("scheduledCron") != cron
                    or checked.astimezone(PACIFIC).date() != due.astimezone(PACIFIC).date()
                    or not due <= checked <= instant or result.get("status") == "skipped"):
                continue
            status, alert = result.get("status"), result.get("alert")
            if run["conclusion"] not in {"success", "failure"}:
                problems.append(f"Scheduled run {run['id']} did not finish normally.")
            elif status == "healthy" and alert == "not-needed" and run["conclusion"] == "success":
                return []
            elif (status in {"missed", "unavailable"} and alert == "accepted"
                  and isinstance(result.get("messageId"), str) and result["messageId"].strip()):
                # The monitor ran and its own publication/availability warning
                # was accepted. Do not relabel it as a missed monitoring run.
                return []
            else:
                problems.append(f"Scheduled run {run['id']} has no verified monitor outcome or provider acceptance.")
    return problems or [
        f"No completed Journal monitoring receipt for {due.astimezone(PACIFIC).date()} "
        "at 6:45 a.m. Pacific (90-minute grace period)."
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--scheduled-cron", default="")
    parser.add_argument("--no-email", action="store_true")
    args = parser.parse_args()
    instant = datetime.now(timezone.utc)
    if not scheduled_today(args.scheduled_cron, instant):
        print("Journal freshness check skipped: other Pacific UTC offset")
        return 0
    try:
        problems = check(Actions(args.repository, os.environ.get("GITHUB_TOKEN", "")), instant)
    except Exception as exc:
        problems = [f"Cannot verify daily monitor execution: {type(exc).__name__}"]
    if not problems:
        print("Journal monitor execution and any required email-provider acceptance verified")
        return 0
    print("JOURNAL_MONITOR_UNVERIFIED\n" + "\n".join(problems), file=sys.stderr)
    if not args.no_email:
        try:
            monitor.notify(problems, monitoring_unavailable=True, missing_run=True)
            print("Journal freshness email accepted by provider")
        except Exception as exc:
            print(f"JOURNAL_FRESHNESS_ALERT_FAILED channel=email error={type(exc).__name__}", file=sys.stderr)
            return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
