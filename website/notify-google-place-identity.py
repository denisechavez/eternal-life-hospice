#!/usr/bin/env python3
"""Email a credential-free Google Place identity failure alert."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ALERT_OWNER = "Aleksandra Dubina — Compliance/Operations"
ALERT_EMAIL = "aleksandra@eternallifehospice.com"
BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
MAX_OUTPUT_CHARS = 8000


def sanitize_output(output, secrets=()):
    """Redact configured secrets and common Google API-key shapes."""
    safe = output
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, "[REDACTED]")
    safe = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED_GOOGLE_API_KEY]", safe)
    return safe[:MAX_OUTPUT_CHARS]


def build_message(output, run_url, secrets=()):
    timestamp = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    safe_output = sanitize_output(output, secrets)
    return {
        "sender": {
            "name": "Eternal Life Hospice Operations",
            "email": "no-reply@eternallifehospice.com",
        },
        "to": [{"name": "Aleksandra Dubina", "email": ALERT_EMAIL}],
        "subject": "ACTION REQUIRED: Google profile identity check failed",
        "textContent": (
            f"Owner: {ALERT_OWNER}\n"
            f"Time: {timestamp}\n\n"
            "The Eternal/Westlake Google Place identity check failed. "
            "Review both Google Business Profiles before changing website links.\n\n"
            f"Safe checker output:\n{safe_output}\n\n"
            f"Failed GitHub run: {run_url}\n"
        ),
    }


def send_alert(api_key, message, endpoint=BREVO_ENDPOINT):
    request = Request(
        endpoint,
        data=json.dumps(message, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
            "user-agent": "ELH-Google-Place-Identity-Email/1.0",
        },
    )
    with urlopen(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise OSError("email provider rejected the notification")


def main():
    api_key = os.environ.get("BREVO_API", "").strip()
    endpoint = os.environ.get("IDENTITY_ALERT_BREVO_ENDPOINT", BREVO_ENDPOINT).strip()
    output_file = os.environ.get("IDENTITY_CHECK_OUTPUT_FILE", "").strip()
    run_url = os.environ.get("IDENTITY_CHECK_RUN_URL", "").strip()
    if not api_key:
        print("IDENTITY_ALERT_FAILED: BREVO_API is not configured", file=sys.stderr)
        return 1
    if not output_file or not run_url:
        print("IDENTITY_ALERT_FAILED: alert context is incomplete", file=sys.stderr)
        return 1

    try:
        output = Path(output_file).read_text(encoding="utf-8")
        message = build_message(
            output,
            run_url,
            secrets=(os.environ.get("GOOGLE_API_KEY", ""), api_key),
        )
        send_alert(api_key, message, endpoint)
    except Exception as exc:
        print(
            f"IDENTITY_ALERT_FAILED channel=email error={type(exc).__name__}",
            file=sys.stderr,
        )
        return 1

    print(f"IDENTITY_ALERT_SENT channel=email owner={ALERT_OWNER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())