#!/usr/bin/env python3
"""Regression tests for the receipt-scoped live referral cleanup mode."""

from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODULE_PATH = Path(__file__).resolve().parent / "run-live-referral-check.py"
MODULE_SPEC = importlib.util.spec_from_file_location("live_referral_check", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
live_check = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(live_check)


def make_record(message_ids: dict[str, str]) -> dict:
    return {
        "processor": {"receipt_id": "ABC123DEF456"},
        "cleanup": {"message_ids": message_ids},
    }


class FakeGmailApi:
    def __init__(
        self,
        messages: list[dict],
        *,
        fail_trash_id: str | None = None,
    ):
        self.messages = messages
        self.fail_trash_id = fail_trash_id
        self.scope_verified = True
        self.calls: list[tuple[str, str]] = []

    def verify_modify_scope(self):
        self.calls.append(("VERIFY_SCOPE", ""))
        if not self.scope_verified:
            raise live_check.GmailApiError("gmail.modify is missing")

    def request(self, path: str, *, method: str = "GET", body=None):
        self.calls.append((method, path))
        if ":search?" in path:
            return {
                "threads": [
                    {
                        "id": message["threadId"],
                        "messages": [message],
                    }
                    for message in self.messages
                ]
            }
        if path.endswith("/trash") and method == "POST":
            message_id = path.rsplit("/", 2)[-2]
            if message_id == self.fail_trash_id:
                raise live_check.GmailApiError("synthetic Gmail failure")
            for message in self.messages:
                if message["id"] == message_id:
                    message["labelIds"] = ["TRASH"]
                    break
            return {}
        raise AssertionError(f"unexpected Gmail request: {method} {path}")


def gmail_message(message_id: str, *, trash: bool = False) -> dict:
    return {
        "id": message_id,
        "threadId": f"thread-{message_id}",
        "labelIds": ["TRASH"] if trash else ["INBOX"],
    }


class LiveReferralCleanupTests(unittest.TestCase):
    def write_record(self, record: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        with handle:
            json.dump(record, handle)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_missing_modify_scope_stops_before_any_gmail_call(self):
        api = FakeGmailApi([])
        api.scope_verified = False
        record_path = self.write_record(
            make_record(
                {
                    "internal_referral": "internal-1",
                    "requester_acknowledgement": "ack-1",
                }
            )
        )
        with self.assertRaisesRegex(live_check.LiveCheckError, "gmail.modify"):
            live_check.cleanup_mailbox(record_path, api)
        self.assertEqual(api.calls, [("VERIFY_SCOPE", "")])

    def test_unrecorded_non_trash_copy_stops_before_trashing(self):
        api = FakeGmailApi(
            [
                gmail_message("internal-1"),
                gmail_message("ack-1"),
                gmail_message("unrecorded-copy"),
            ]
        )
        record_path = self.write_record(
            make_record(
                {
                    "internal_referral": "internal-1",
                    "requester_acknowledgement": "ack-1",
                }
            )
        )
        with self.assertRaisesRegex(live_check.LiveCheckError, "unrecorded-copy"):
            live_check.cleanup_mailbox(record_path, api)
        self.assertFalse(any(path.endswith("/trash") for _, path in api.calls))

    def test_success_trashes_only_recorded_messages_and_closes(self):
        api = FakeGmailApi(
            [
                gmail_message("internal-1"),
                gmail_message("forwarded-1"),
                gmail_message("ack-1"),
            ]
        )
        record_path = self.write_record(
            make_record(
                {
                    "internal_referral": "internal-1",
                    "forwarded_referral": "forwarded-1",
                    "requester_acknowledgement": "ack-1",
                }
            )
        )
        result = live_check.cleanup_mailbox(record_path, api)
        self.assertEqual(result["verification"]["status"], "CLOSED")
        self.assertEqual(
            [item["status"] for item in result["deleted"]],
            ["trashed", "trashed", "trashed"],
        )
        trash_ids = {
            path.rsplit("/", 2)[-2]
            for method, path in api.calls
            if method == "POST" and path.endswith("/trash")
        }
        self.assertEqual(
            trash_ids, {"internal-1", "forwarded-1", "ack-1"}
        )

    def test_already_trashed_message_is_reported_without_retrashing(self):
        api = FakeGmailApi(
            [
                gmail_message("internal-1", trash=True),
                gmail_message("ack-1", trash=True),
            ]
        )
        record_path = self.write_record(
            make_record(
                {
                    "internal_referral": "internal-1",
                    "requester_acknowledgement": "ack-1",
                }
            )
        )
        result = live_check.cleanup_mailbox(record_path, api)
        self.assertEqual(
            [item["status"] for item in result["deleted"]],
            ["already_in_trash", "already_in_trash"],
        )
        self.assertFalse(any(method == "POST" for method, _ in api.calls))

    def test_partial_failure_reports_every_role_and_stays_open(self):
        api = FakeGmailApi(
            [
                gmail_message("internal-1"),
                gmail_message("forwarded-1"),
                gmail_message("ack-1"),
            ],
            fail_trash_id="forwarded-1",
        )
        record_path = self.write_record(
            make_record(
                {
                    "internal_referral": "internal-1",
                    "forwarded_referral": "forwarded-1",
                    "requester_acknowledgement": "ack-1",
                }
            )
        )
        result = live_check.cleanup_mailbox(record_path, api)
        self.assertEqual(result["verification"]["status"], "OPEN")
        self.assertEqual(
            [item["status"] for item in result["deleted"]],
            ["trashed", "failed", "not_attempted_after_failure"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)