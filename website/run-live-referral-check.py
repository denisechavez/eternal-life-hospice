#!/usr/bin/env python3
"""Run the bounded, no-PHI production referral delivery check.

This command intentionally submits fixed synthetic values. It does not read
or print a response body beyond the processor's safe JSON status fields, and
it never attempts mailbox cleanup. An authorized mailbox user must verify and
delete the exact message IDs listed in FORM-INTAKE-OPERATIONS.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://eternallifehospice.com"
DEFAULT_REQUESTER_EMAIL = "info@eternallifehospice.com"
INTERNAL_DESTINATION = "referral@eternallifehospice.com"
SYNTHETIC_PHONE = "805.555.0199"
SYNTHETIC_SITUATION = "Synthetic non-PHI routing test only. Do not call."


class LiveCheckError(RuntimeError):
    """A safe, operator-actionable live-check failure."""


def _origin(base_url: str) -> tuple[str, str]:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LiveCheckError("--base-url must be an absolute http(s) URL")
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    return origin, parsed.netloc


def _endpoint(base_url: str) -> tuple[str, str]:
    origin, _host = _origin(base_url)
    return f"{origin}/api/form-submit", origin


def _payload(check_label: str, requester_email: str) -> dict[str, str]:
    """Return the exact fields used by the public /refer form."""
    return {
        "form-name": "elh-physician",
        "audience": "referral",
        "source": "Refer a Patient page — live no-PHI check",
        "subject": "New patient referral — Eternal Life Hospice",
        "bot-field": "",
        "referrer_name": check_label,
        "phone": SYNTHETIC_PHONE,
        "referrer_role": "Operations delivery check",
        "facility": "Eternal Life Hospice QA",
        "county": "Ventura County",
        "timeframe": "Routine",
        "email": requester_email,
        "preferred_time": "No callback — synthetic check",
        "situation": SYNTHETIC_SITUATION,
    }


def submit(base_url: str, requester_email: str, timeout: float) -> dict[str, Any]:
    """Submit the synthetic referral and return a non-PHI audit record."""
    endpoint, origin = _endpoint(base_url)
    submitted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    check_label = f"ELH LIVE CHECK — DO NOT CALL — {submitted_at}"
    request = Request(
        endpoint,
        data=urlencode(_payload(check_label, requester_email)).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": origin,
            "Referer": f"{origin}/refer",
            "User-Agent": "ELH-Replit-Live-Referral-Check/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read(16_384)
    except HTTPError as exc:
        raise LiveCheckError(
            f"processor returned HTTP {exc.code}; no delivery was confirmed"
        ) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise LiveCheckError(
            f"could not reach the processor ({type(exc).__name__}); "
            "no delivery was confirmed"
        ) from None

    try:
        result = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise LiveCheckError(
            f"processor returned HTTP {status} without JSON; "
            "no delivery was confirmed"
        ) from None

    if (
        status != 200
        or result.get("ok") is not True
        or result.get("accepted") is not True
        or not result.get("receipt_id")
    ):
        raise LiveCheckError(
            f"processor did not accept the referral (HTTP {status}); "
            "no delivery was confirmed"
        )

    acknowledgement_sent = result.get("acknowledgement_sent") is True
    acknowledgement_error = result.get("acknowledgement_error") is True
    if not acknowledgement_sent or acknowledgement_error:
        raise LiveCheckError(
            "processor accepted the internal referral but did not confirm the "
            "requester acknowledgement; check the response before retrying"
        )

    return {
        "check_label": check_label,
        "submitted_at_utc": submitted_at,
        "route": f"{origin}/refer",
        "requester_mailbox": requester_email,
        "synthetic_phone": SYNTHETIC_PHONE,
        "processor": {
            "http_status": status,
            "accepted": True,
            "receipt_id": result["receipt_id"],
            "provider_message_id": result.get("provider_message_id", ""),
        },
        "internal_delivery": {
            "destination": INTERNAL_DESTINATION,
            "provider_accepted": True,
            "mailbox_receipt": "PENDING_MANUAL_CONFIRMATION",
        },
        "requester_acknowledgement": {
            "sent": True,
            "mailbox": requester_email,
            "mailbox_receipt": "PENDING_MANUAL_CONFIRMATION",
        },
        "cleanup": {
            "automated": False,
            "handoff": (
                "An authorized mailbox user must record and delete the exact "
                "bounded Gmail message IDs for this receipt."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Submit one clearly labeled synthetic referral through /refer. "
            "No patient or clinical information is sent."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Production site base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--requester-email",
        default=DEFAULT_REQUESTER_EMAIL,
        help=(
            "Monitored mailbox for the static acknowledgement "
            f"(default: {DEFAULT_REQUESTER_EMAIL})"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the non-PHI JSON audit record",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        record = submit(args.base_url.rstrip("/"), args.requester_email, args.timeout)
    except LiveCheckError as exc:
        print(f"LIVE_REFERRAL_CHECK_FAILED: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"LIVE_REFERRAL_CHECK_RECORD_WRITTEN: {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())