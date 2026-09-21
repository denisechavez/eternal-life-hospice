#!/usr/bin/env python3
"""Send a credential-free Google Place identity failure alert."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ALERT_OWNER = "Aleksandra Dubina — Compliance/Operations"
MAX_OUTPUT_CHARS = 8000


def sanitize_output(output, secrets=()):
    """Redact configured secrets and common Google API-key shapes."""
    safe = output
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, "[REDACTED]")
    safe = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED_GOOGLE_API_KEY]", safe)
    return safe[:MAX_OUTPUT_CHARS]


def build_payload(output, run_url, secrets=()):
    return {
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "environment": "github-actions",
        "alert_type": "google_place_identity_failure",
        "owner": ALERT_OWNER,
        "message": (
            "The Eternal/Westlake Google Place identity check failed. "
            "Review both Google Business Profiles before changing website links."
        ),
        "checker_output": sanitize_output(output, secrets),
        "failed_run_url": run_url,
    }


def send_alert(webhook_url, payload):
    request = Request(
        webhook_url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "ELH-Google-Place-Identity-Alert/1.0",
        },
    )
    with urlopen(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise OSError("alert endpoint rejected the notification")


def main():
    webhook_url = os.environ.get("FORM_ALERT_WEBHOOK_URL", "").strip()
    output_file = os.environ.get("IDENTITY_CHECK_OUTPUT_FILE", "").strip()
    run_url = os.environ.get("IDENTITY_CHECK_RUN_URL", "").strip()
    if not webhook_url:
        print("IDENTITY_ALERT_FAILED: FORM_ALERT_WEBHOOK_URL is not configured", file=sys.stderr)
        return 1
    if not output_file or not run_url:
        print("IDENTITY_ALERT_FAILED: alert context is incomplete", file=sys.stderr)
        return 1

    try:
        output = Path(output_file).read_text(encoding="utf-8")
        payload = build_payload(
            output,
            run_url,
            secrets=(os.environ.get("GOOGLE_API_KEY", ""), webhook_url),
        )
        send_alert(webhook_url, payload)
    except Exception as exc:
        print(
            f"IDENTITY_ALERT_FAILED channel=webhook error={type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    print(f"IDENTITY_ALERT_SENT owner={ALERT_OWNER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())