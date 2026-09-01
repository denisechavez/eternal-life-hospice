#!/usr/bin/env python3
"""Verify that retired event routes are gone from production."""

import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://eternallifehospice.com"
RETIRED_EVENT_URLS = (
    "/events",
    "/events/",
    "/events/caregiver-support-workshop",
    "/events/caregiver-support-workshop/",
    "/events/community-grief-circle",
    "/events/community-grief-circle/",
)
EVENT_JSON_LD = re.compile(
    r'"@type"\s*:\s*"Event"', re.IGNORECASE
)


def fetch(path):
    request = Request(
        BASE_URL + path,
        headers={"User-Agent": "ELH-retired-event-check/1.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.geturl(), response.read()
    except HTTPError as error:
        return error.code, error.geturl(), error.read()


def main():
    failed = False
    for path in RETIRED_EVENT_URLS:
        status, final_url, body = fetch(path)
        text = body.decode("utf-8", errors="replace")
        has_event_json_ld = bool(EVENT_JSON_LD.search(text))
        passed = status in (404, 410) and not has_event_json_ld
        marker = "PASS" if passed else "FAIL"
        print(
            f"{marker} {path} status={status} "
            f"final={final_url} event_json_ld={has_event_json_ld}"
        )
        failed |= not passed

    if failed:
        print("Retired event route check failed.", file=sys.stderr)
        return 1

    print("All retired event routes return 404/410 without Event JSON-LD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())