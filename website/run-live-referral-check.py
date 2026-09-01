#!/usr/bin/env python3
"""Run the bounded, no-PHI production referral delivery check.

The default mode submits fixed synthetic values. Cleanup is a separate,
receipt-scoped mode that requires an explicit Gmail modification-scope
confirmation and an exact message-ID handoff record. It never searches by a
broad sender or date range, and it never permanently deletes mail.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://eternallifehospice.com"
DEFAULT_REQUESTER_EMAIL = "info@eternallifehospice.com"
INTERNAL_DESTINATION = "referral@eternallifehospice.com"
SYNTHETIC_PHONE = "805.555.0199"
SYNTHETIC_SITUATION = "Synthetic non-PHI routing test only. Do not call."
GMAIL_CONNECTOR = "google-mail"
GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
RECEIPT_ID_PATTERN = re.compile(r"^[A-Z0-9]{6,40}$")
MESSAGE_ROLES = (
    "internal_referral",
    "forwarded_referral",
    "requester_acknowledgement",
)


class LiveCheckError(RuntimeError):
    """A safe, operator-actionable live-check failure."""


class GmailApiError(LiveCheckError):
    """A Gmail API failure that is safe to show to an operator."""


class ReplitGmailApi:
    """Adapter around the Replit-managed Gmail connector helper."""

    def __init__(self, connection_id: str) -> None:
        if not connection_id.startswith("conn_google-mail_"):
            raise LiveCheckError(
                "--gmail-connection-id must identify an authorized Gmail "
                "connection"
            )
        self._connection_id = connection_id
        self._helper = Path(__file__).with_name("gmail-connector-request.mjs")
        if not self._helper.is_file():
            raise LiveCheckError("Gmail connector helper is missing")

    def _call_helper(self, request_payload: Mapping[str, Any]) -> Any:
        payload = {
            "connectionId": self._connection_id,
            "requiredScope": GMAIL_MODIFY_SCOPE,
            **request_payload,
        }
        try:
            completed = subprocess.run(
                ["node", str(self._helper)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise GmailApiError(
                f"Gmail connector helper failed before completion: "
                f"{type(exc).__name__}"
            ) from None

        try:
            result = json.loads(completed.stdout)
        except (ValueError, TypeError):
            raise GmailApiError(
                "Gmail connector helper returned an invalid response"
            ) from None
        if not isinstance(result, Mapping):
            raise GmailApiError(
                "Gmail connector helper returned an unexpected response"
            )

        status = result.get("status", 500)
        if not isinstance(status, int):
            raise GmailApiError(
                "Gmail connector helper returned an invalid status"
            )
        if not 200 <= status < 300:
            body = result.get("body")
            if (
                status == 409
                and isinstance(body, Mapping)
                and isinstance(body.get("verification"), Mapping)
                and body["verification"].get("status") == "OPEN"
            ):
                return body
            error = result.get("error")
            if isinstance(error, str) and error:
                raise GmailApiError(error)
            if status == 401:
                raise GmailApiError(
                    "Gmail authorization is invalid or expired; no mailbox "
                    "write was attempted"
                )
            if status == 403:
                raise GmailApiError(
                    "Gmail denied the request; verify the authorized connection "
                    f"includes {GMAIL_MODIFY_SCOPE}"
                )
            raise GmailApiError(f"Gmail returned HTTP {status}")
        return result.get("body") or {}

    def cleanup_transaction(
        self,
        receipt_id: str,
        message_ids: Mapping[str, str],
    ) -> dict[str, Any]:
        result = self._call_helper(
            {
                "action": "cleanup_receipt",
                "receiptId": receipt_id,
                "messageIds": dict(message_ids),
            }
        )
        if not isinstance(result, Mapping):
            raise GmailApiError(
                "Gmail cleanup helper returned an unexpected result"
            )
        return dict(result)


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


def _receipt_from_record(record: Mapping[str, Any]) -> str:
    try:
        receipt_id = record["processor"]["receipt_id"]
    except (KeyError, TypeError):
        raise LiveCheckError(
            "cleanup record is missing processor.receipt_id"
        ) from None
    if (
        not isinstance(receipt_id, str)
        or not RECEIPT_ID_PATTERN.fullmatch(receipt_id)
    ):
        raise LiveCheckError(
            "cleanup record has an invalid processor.receipt_id; use the "
            "uppercase receipt returned by the processor"
        )
    return receipt_id


def _message_ids_from_record(record: Mapping[str, Any]) -> dict[str, str]:
    try:
        raw_ids = record["cleanup"]["message_ids"]
    except (KeyError, TypeError):
        raise LiveCheckError(
            "cleanup record is missing cleanup.message_ids"
        ) from None
    if not isinstance(raw_ids, Mapping):
        raise LiveCheckError("cleanup.message_ids must be an object")
    unknown_roles = sorted(set(raw_ids) - set(MESSAGE_ROLES))
    if unknown_roles:
        raise LiveCheckError(
            "cleanup.message_ids contains unsupported roles: "
            f"{', '.join(unknown_roles)}"
        )

    message_ids: dict[str, str] = {}
    for role in MESSAGE_ROLES:
        message_id = raw_ids.get(role)
        if message_id in (None, "", "NONE") and role == "forwarded_referral":
            continue
        if not isinstance(message_id, str) or not message_id.strip():
            raise LiveCheckError(
                f"cleanup.message_ids.{role} must be a Gmail message ID"
            )
        message_ids[role] = message_id.strip()

    if "internal_referral" not in message_ids:
        raise LiveCheckError(
            "cleanup.message_ids.internal_referral is required"
        )
    if "requester_acknowledgement" not in message_ids:
        raise LiveCheckError(
            "cleanup.message_ids.requester_acknowledgement is required"
        )
    if len(set(message_ids.values())) != len(message_ids):
        raise LiveCheckError(
            "cleanup.message_ids must contain unique Gmail message IDs"
        )
    return message_ids


def load_cleanup_record(path: Path) -> tuple[str, dict[str, str]]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LiveCheckError(f"could not read cleanup record: {exc}") from None
    except (ValueError, UnicodeDecodeError):
        raise LiveCheckError("cleanup record is not valid UTF-8 JSON") from None
    if not isinstance(record, Mapping):
        raise LiveCheckError("cleanup record must be a JSON object")
    return _receipt_from_record(record), _message_ids_from_record(record)


def _gmail_messages(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, Mapping):
        raise GmailApiError("Gmail search returned an unexpected response")
    threads = result.get("threads")
    if not isinstance(threads, list):
        raise GmailApiError("Gmail search returned no thread list")

    messages: list[dict[str, Any]] = []
    for thread in threads:
        if not isinstance(thread, Mapping):
            continue
        thread_messages = thread.get("messages")
        if not isinstance(thread_messages, list):
            continue
        for message in thread_messages:
            if isinstance(message, Mapping) and isinstance(message.get("id"), str):
                messages.append(dict(message))
    return messages


def _search_receipt(api: Any, receipt_id: str) -> list[dict[str, Any]]:
    # The Replit Gmail connector documents this fused search endpoint. Unlike
    # Gmail's standard threads.list response, it hydrates each matching thread
    # with minimal message records so exact IDs and labels can be validated.
    messages: list[dict[str, Any]] = []
    page_token: str | None = None
    for _page in range(10):
        query_params = {
            "q": receipt_id,
            "pageSize": "50",
            "view": "THREAD_VIEW_MINIMAL",
            "includeTrash": "true",
        }
        if page_token:
            query_params["pageToken"] = page_token
        result = api.request(
            f"/gmail/v1/users/me/threads:search?{urlencode(query_params)}",
            method="GET",
        )
        messages.extend(_gmail_messages(result))
        next_page_token = result.get("nextPageToken")
        if not next_page_token:
            return messages
        if not isinstance(next_page_token, str) or next_page_token == page_token:
            raise GmailApiError(
                "Gmail search returned an invalid continuation token"
            )
        page_token = next_page_token
    raise GmailApiError(
        "receipt search exceeded 500 threads; no complete cleanup "
        "verification is possible"
    )


def _message_is_in_trash(message: Mapping[str, Any]) -> bool:
    labels = message.get("labelIds")
    return isinstance(labels, list) and "TRASH" in labels


def cleanup_mailbox(
    record_path: Path,
    api: Any,
) -> dict[str, Any]:
    """Trash only the recorded receipt messages and verify the final state.

    The scope check is deliberately the first operation. The target search
    then proves that every supplied ID belongs to this one receipt before any
    trash request is sent. Unexpected non-trash matches stop the operation
    rather than expanding the deletion set.
    """
    receipt_id, message_ids = load_cleanup_record(record_path)
    if hasattr(api, "cleanup_transaction"):
        return api.cleanup_transaction(receipt_id, message_ids)

    api.verify_modify_scope()
    initial_messages = _search_receipt(api, receipt_id)
    initial_by_id = {message["id"]: message for message in initial_messages}

    missing_ids = sorted(set(message_ids.values()) - set(initial_by_id))
    if missing_ids:
        raise LiveCheckError(
            "cleanup stopped before writing: these recorded IDs were not "
            f"found for receipt {receipt_id}: {', '.join(missing_ids)}"
        )

    target_ids = set(message_ids.values())
    unexpected_non_trash = sorted(
        message["id"]
        for message in initial_messages
        if message["id"] not in target_ids
        and not _message_is_in_trash(message)
    )
    if unexpected_non_trash:
        raise LiveCheckError(
            "cleanup stopped before writing: an unrecorded non-trash message "
            f"also matches receipt {receipt_id}: "
            f"{', '.join(unexpected_non_trash)}"
        )

    deletion_results: list[dict[str, Any]] = []
    message_items = list(message_ids.items())
    for index, (role, message_id) in enumerate(message_items):
        message = initial_by_id[message_id]
        if _message_is_in_trash(message):
            deletion_results.append(
                {
                    "role": role,
                    "message_id": message_id,
                    "status": "already_in_trash",
                }
            )
            continue
        try:
            api.request(
                f"/gmail/v1/users/me/messages/{message_id}/trash",
                method="POST",
            )
        except LiveCheckError as exc:
            deletion_results.append(
                {
                    "role": role,
                    "message_id": message_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            for remaining_role, remaining_id in message_items[index + 1 :]:
                deletion_results.append(
                    {
                        "role": remaining_role,
                        "message_id": remaining_id,
                        "status": "not_attempted_after_failure",
                    }
                )
            break
        deletion_results.append(
            {
                "role": role,
                "message_id": message_id,
                "status": "trashed",
            }
        )

    verification_error = ""
    try:
        final_messages = _search_receipt(api, receipt_id)
        remaining_non_trash = sorted(
            message["id"]
            for message in final_messages
            if not _message_is_in_trash(message)
        )
    except LiveCheckError as exc:
        remaining_non_trash = []
        verification_error = str(exc)
    failed = any(item["status"] == "failed" for item in deletion_results)
    return {
        "receipt_id": receipt_id,
        "scope_verified": True,
        "deleted": deletion_results,
        "verification": {
            "searched_by_receipt": True,
            "remaining_non_trash_ids": remaining_non_trash,
            "status": (
                "OPEN"
                if failed or remaining_non_trash or verification_error
                else "CLOSED"
            ),
            **(
                {"error": verification_error}
                if verification_error
                else {}
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
    parser.add_argument(
        "--cleanup-record",
        type=Path,
        help=(
            "Receipt record with exact cleanup.message_ids; selects the "
            "authorized Gmail cleanup mode instead of submitting a referral"
        ),
    )
    parser.add_argument(
        "--gmail-connection-id",
        help=(
            "Exact custom-OAuth Gmail connection authorized for cleanup. "
            "Required in cleanup mode."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cleanup_record:
        try:
            if not args.gmail_connection_id:
                raise LiveCheckError(
                    "--gmail-connection-id is required in cleanup mode"
                )
            result = cleanup_mailbox(
                args.cleanup_record,
                ReplitGmailApi(args.gmail_connection_id),
            )
        except LiveCheckError as exc:
            print(f"LIVE_REFERRAL_CLEANUP_FAILED: {exc}", file=sys.stderr)
            return 1
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"LIVE_REFERRAL_CLEANUP_RECORD_WRITTEN: {args.output}")
        else:
            print(rendered, end="")
        if result["verification"]["status"] != "CLOSED":
            print(
                "LIVE_REFERRAL_CLEANUP_INCOMPLETE: inspect the receipt-scoped "
                "result before any retry",
                file=sys.stderr,
            )
            return 1
        return 0

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