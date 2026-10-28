#!/usr/bin/env python3
"""Full-corpus startup regression. Uses disposable PostgreSQL, never DATABASE_URL.

Timing is diagnostic, not a machine-dependent pass/fail threshold. Scan and SQL
budgets fail deterministically. Run from any directory; no article files change.
Historical owner approvals are checked separately from synthetic bulk fixtures:
current review drafts may legitimately differ from the approved versions.
"""
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time
import unittest
from unittest.mock import patch

import journal_owner_approval as owner
import journal_release as jr

spec = importlib.util.spec_from_file_location(
    "journal_history_benchmark", Path(__file__).with_name("benchmark-journal-history.py"))
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)

REPORT = Path(__file__).resolve().parents[1] / "generated-artifacts/journal-catchup.json"
TABLES = ("journal_decisions", "journal_releases", "journal_review_audit", "journal_photos")


def local_photos(document):
    """Independent accounting of local images whose bytes need freezing."""
    assets = set(re.findall(r'(?:src=["\']|url\(["\']?)([^"\')\s]+)', document))
    photos = {}
    for asset in sorted(assets):
        if asset.startswith(("https:", "http:", "data:")):
            continue
        relative = asset.split("?")[0]
        target = ((jr.PUBLIC / relative.lstrip("/")) if asset.startswith("/")
                  else (jr.PUBLIC / "blog" / relative)).resolve()
        if (target.is_relative_to(jr.PUBLIC) and target.is_file()
                and target.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}):
            photos[asset] = target
    return photos


def pinned_requests():
    """Independent expectation for the bounded, real owner instructions."""
    request = owner.REQUEST
    rows = [(request["date"], request["slug"], request["revision"], request["reviewer"], True)]
    rows += [(day, slug, revision,
              "Owner-directed October reconciliation — 2026-10-21 (outside Studio)", False)
             for day, slug, revision in owner.OCTOBER_REQUESTS]
    manifest = json.loads(
        (jr.BASE / "content/30-day-journal-manifest.json").read_text())["articles"]
    for day, revision in sorted(owner.YEAR_END_REVISIONS.items()):
        matches = [r for r in manifest if r["date"] == day]
        if "2026-11-01" <= day <= "2026-12-31" and len(matches) == 1:
            rows.append((day, matches[0]["slug"], revision,
                         "Owner-directed through-December-31 approval (outside Studio)", False))
    return rows


class CatchupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = []
        # This helper starts a private cluster, not an isolated schema in the
        # configured database. Even an accidentally production DATABASE_URL is unused.
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.local_connect = staticmethod(cls.stack.enter_context(storage.disposable_postgres()))
        cls.stack.enter_context(patch.object(jr, "connect", cls.local_connect))
        cls.records = jr.candidates()  # Actual corpus, including real image hashing.
        cls.owner_requests = pinned_requests()
        if len(cls.records) < 83 or len(cls.owner_requests) < 83:
            raise AssertionError("Full owner-consent corpus unexpectedly shrank")
        # Synthetic permissions exist only in this disposable database. Do not
        # re-pin real owner approvals or equate a changed draft with consent.
        cls.requests = [
            (record["date"], slug, record["revision"],
             "Synthetic catch-up regression approval", False)
            for slug, record in sorted(cls.records.items())
        ]
        jr.initialize()

    @classmethod
    def tearDownClass(cls):
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps({
            "disposable_storage_only": True,
            "corpus_articles": len(cls.records),
            "owner_pins": len(cls.owner_requests),
            "synthetic_approvals": len(cls.requests),
            "runs": cls.reports,
        }, indent=2) + "\n")

    def setUp(self):
        with self.local_connect() as db:
            db.execute("TRUNCATE " + ",".join(TABLES) + " RESTART IDENTITY")
        self.instant = datetime(2026, 10, 24, 13, 29, tzinfo=timezone.utc)
        self.addCleanup(patch.stopall)
        patch.object(jr, "environment", return_value="production").start()
        self.clock = patch.object(jr, "now", return_value=self.instant).start()

    def snapshot(self):
        with self.local_connect() as db:
            return {table: db.execute("SELECT * FROM " + table + " ORDER BY 1,2").fetchall()
                    for table in TABLES}

    def measure(self, label, call, expected, *, corpus_size=None, candidate_source=None):
        statements = []
        real_candidates = candidate_source or jr.candidates
        real_revision = jr.revision
        real_freeze = jr.freeze_photos
        real_read = Path.read_bytes
        reads = Counter()

        def read(path):
            reads[str(path)] += 1
            return real_read(path)

        connections = []

        def connect():
            connections.append(1)
            return storage.TracedConnection(self.local_connect(), statements)

        with patch.object(jr, "connect", side_effect=connect), \
             patch.object(jr, "candidates", wraps=real_candidates) as candidates, \
             patch.object(jr, "revision", wraps=real_revision) as revisions, \
             patch.object(jr, "freeze_photos", wraps=real_freeze) as freezes, \
             patch.object(Path, "read_bytes", read):
            start = time.perf_counter()
            result = call()  # No warmup: this must measure the first startup.
            elapsed = (time.perf_counter() - start) * 1000
        stats = {
            "label": label, "elapsed_ms": elapsed, "applied": result,
            "connections": len(connections), "candidate_scans": candidates.call_count,
            "revision_hashes": revisions.call_count, "photo_freezes": freezes.call_count,
            "asset_reads": sum(reads.values()), "sql_statements": len(statements),
        }
        self.reports.append(stats)
        print(json.dumps(stats), flush=True)
        self.assertEqual(result, expected)
        self.assertEqual(len(connections), 1, "Startup regressed to per-article transactions")
        self.assertLessEqual(sum(query.lstrip().upper().startswith("SELECT")
                                 for query, _ in statements), 5 if expected else 3,
                             "Repeated decision/materialization reads")
        if expected:
            self.assertEqual(candidates.call_count, 1, "Repeated full candidate/image scan")
            self.assertEqual(revisions.call_count, corpus_size or len(self.records))
            self.assertEqual(freezes.call_count, expected)
            # One hash pass + one freeze per approved article; shared logos/fonts
            # are legitimately read once per document, not once per asset path.
            workload = max(expected, corpus_size or len(self.records))
            hash_reads = sum(len(local_photos(r["html"])) for r in self.records.values())
            freeze_reads = sum(len(local_photos(call.args[1])) for call in freezes.call_args_list)
            self.assertEqual(sum(reads.values()), hash_reads + freeze_reads,
                             "Image bytes were read more than once per hash/freeze pass")
            self.assertLessEqual(len(statements), freeze_reads + 4 * workload + 8,
                                 "SQL grew beyond the linear first-start budget")
        else:
            self.assertEqual(candidates.call_count, 0, "No-op restart rescanned candidates")
            self.assertEqual(revisions.call_count, 0)
            self.assertEqual(freezes.call_count, 0)
            self.assertEqual(sum(reads.values()), 0, "No-op restart reread image bytes")
            # materialize may upsert each already-due approval once; no other
            # writes or per-article decision/audit lookups are needed.
            with self.local_connect() as db:
                due = sum(jr.release_at(r["release_date"].isoformat()) <= self.clock.return_value
                          for r in db.execute(
                              "SELECT release_date FROM journal_decisions WHERE state='approved'"))
            self.assertLessEqual(len(statements), due + 3)
            for query, _ in statements:
                normalized = " ".join(query.lower().split())
                self.assertFalse(any("insert into " + table in normalized
                                     for table in ("journal_decisions", "journal_review_audit",
                                                   "journal_photos")))
        return stats

    def assert_saved(self, requests, protected=None):
        saved = self.snapshot()
        decisions = {r["slug"]: r for r in saved["journal_decisions"]}
        releases = {r["slug"]: r for r in saved["journal_releases"]}
        audits = saved["journal_review_audit"]
        self.assertEqual(set(decisions), {r[1] for r in requests} | set(protected or {}))
        self.assertEqual(len(audits), len(decisions))
        photos = {r["digest"]: r for r in saved["journal_photos"]}
        for digest, row in photos.items():
            self.assertEqual(hashlib.sha256(bytes(row["body"])).hexdigest(), digest)
        expected_releases = set()
        for day, slug, revision, source, immediate in requests:
            row = decisions[slug]
            self.assertEqual((row["revision"], row["release_date"].isoformat(), row["state"],
                              row["reviewer"], row["decided_at"], row["reviewer_name"]),
                             (revision, day, "approved", source, self.instant, None))
            audit = [r for r in audits if r["slug"] == slug]
            self.assertEqual(len(audit), 1)
            self.assertEqual(
                tuple(audit[0][k] for k in ("revision", "action", "reviewer", "occurred_at",
                                           "environment", "reviewer_name")),
                (revision, "approve", source, self.instant, "production", None))
            # Assert the exact frozen HTML, not just matching revision metadata.
            record = self.active_records[slug]
            frozen = record["html"]
            for asset, path in local_photos(frozen).items():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                frozen = frozen.replace(asset, "/api/journal-photo/" + digest)
            self.assertEqual(row["document"], frozen)
            self.assertIn("/api/journal-photo/", frozen)
            for digest in re.findall(r"/api/journal-photo/([a-f0-9]{64})", frozen):
                self.assertIn(digest, photos)
            due = jr.release_at(day)
            if immediate or due <= self.instant:
                expected_releases.add(slug)
                release = releases[slug]
                self.assertEqual((release["revision"], release["document"],
                                  release["release_date"].isoformat(), release["released_at"]),
                                 (revision, frozen, day,
                                  self.instant if immediate else max(self.instant, due)))
        if protected:
            for slug, row in protected.items():
                self.assertEqual(decisions[slug], row)
                if row["state"] == "approved" and jr.release_at(
                        row["release_date"].isoformat()) <= self.instant:
                    expected_releases.add(slug)
        self.assertEqual(set(releases), expected_releases)
        return saved

    def test_full_corpus_first_start_and_noop_restart(self):
        self.active_records = self.records
        apply = lambda: jr.apply_owner_batch(self.requests)
        self.measure("full-first-start", apply, len(self.requests))
        before = self.assert_saved(self.requests)
        self.measure("full-noop-restart", apply, 0)
        self.assertEqual(self.snapshot(), before, "Restart changed saved decisions/photos/audit")
        # The daily release boundary remains 06:30 Pacific, including post-DST dates.
        for day in ("2026-10-24", "2026-11-15", "2026-12-31"):
            request = next(r for r in self.requests if r[0] == day)
            due = jr.release_at(day)
            for instant, public in ((due - timedelta(microseconds=1), False), (due, True)):
                self.clock.return_value = instant
                released, healthy = jr.released(instant)
                self.assertTrue(healthy)
                self.assertEqual(request[1] in released, public)
                if public:
                    self.assertEqual(released[request[1]]["date"], day)

    def test_full_batch_scales_linearly_and_deduplicates(self):
        stats = []
        for factor in (1, 2):
            with self.subTest(factor=factor):
                with self.local_connect() as db:
                    db.execute("TRUNCATE " + ",".join(TABLES) + " RESTART IDENTITY")
                self.active_records = {
                    f"{slug}-copy-{i}": {**r, "slug": f"{slug}-copy-{i}"}
                    for i in range(factor) for slug, r in self.records.items()
                }
                requests = [(r["date"], slug, r["revision"], "Synthetic scaling fixture", False)
                            for slug, r in self.active_records.items()]
                actual_candidates = jr.candidates

                def expanded():
                    # Still scan/hash the real on-disk corpus on each invocation;
                    # synthetic copies increase SQL/freeze workload, not permissions.
                    actual_candidates()
                    return self.active_records

                call = lambda: jr.apply_owner_batch(requests + requests)
                stats.append(self.measure(f"scale-{factor}-first-start", call, len(requests),
                                          corpus_size=len(self.records), candidate_source=expanded))
                before = self.assert_saved(requests)
                self.measure(f"scale-{factor}-noop-restart", call, 0,
                             candidate_source=expanded)
                self.assertEqual(self.snapshot(), before)
        self.assertLessEqual(stats[1]["sql_statements"], 2 * stats[0]["sql_statements"] + 8)
        self.assertLessEqual(stats[1]["asset_reads"], 2 * stats[0]["asset_reads"])

    def test_full_corpus_preserves_studio_decisions_and_rejects_drift(self):
        self.active_records = self.records
        held, approved, audit_only, wrong_pin, wrong_date, missing = self.requests[:6]
        old = self.instant - timedelta(days=1)
        self.clock.return_value = old
        for request, action in ((held, "hold"), (approved, "approve"), (audit_only, "hold")):
            jr.decide(request[1], request[2], action, "synthetic-studio-reviewer")
        with self.local_connect() as db:
            db.execute("DELETE FROM journal_decisions WHERE slug=%s", (audit_only[1],))
        original = self.snapshot()
        protected = {r["slug"]: r for r in original["journal_decisions"]}
        self.clock.return_value = self.instant
        requests = [tuple(r) for r in self.requests]
        requests[3] = (wrong_pin[0], wrong_pin[1], "0" * 64, *wrong_pin[3:])
        requests[4] = ("2027-01-01", *wrong_date[1:])
        requests[5] = (missing[0], "missing-catchup-fixture", *missing[2:])
        expected = self.requests[6:]
        self.measure("full-mixed-decisions", lambda: jr.apply_owner_batch(requests), len(expected))
        saved = self.snapshot()
        decisions = {r["slug"]: r for r in saved["journal_decisions"]}
        for slug, row in protected.items():
            self.assertEqual(decisions[slug], row)
        for request in (audit_only, wrong_pin, wrong_date, missing):
            self.assertNotIn(request[1], decisions)
        self.assertNotIn("missing-catchup-fixture", decisions)
        self.assertEqual(len(decisions), len(expected) + 2)
        self.assertEqual(len(saved["journal_review_audit"]), len(expected) + 3)
        for row in original["journal_review_audit"]:
            self.assertIn(row, saved["journal_review_audit"])
        # Verify every newly written pin/date/source/time, and no invented audit.
        for day, slug, revision, source, _ in expected:
            row = decisions[slug]
            self.assertEqual((row["revision"], str(row["release_date"]), row["decided_at"]),
                             (revision, day, self.instant))
            events = [r for r in saved["journal_review_audit"] if r["slug"] == slug]
            self.assertEqual(len(events), 1)
            self.assertEqual((events[0]["reviewer"], events[0]["occurred_at"],
                              events[0]["action"], events[0]["environment"]),
                             (source, self.instant, "approve", "production"))

    def test_full_catchup_failure_rolls_back_and_retry_is_idempotent(self):
        before = self.snapshot()
        write = jr._write_decision
        written = []

        def fail_at_end(*args, **kwargs):
            write(*args, **kwargs)
            written.append(args[1]["slug"])
            if len(written) == len(self.requests):
                raise RuntimeError("Synthetic last-article storage failure")

        with patch.object(jr, "_write_decision", side_effect=fail_at_end):
            with self.assertRaisesRegex(RuntimeError, "Synthetic last-article"):
                jr.apply_owner_batch(self.requests)
        self.assertEqual(len(written), len(self.requests))
        self.assertEqual(self.snapshot(), before, "Partial approvals/photos/audit escaped rollback")
        self.active_records = self.records
        apply = lambda: jr.apply_owner_batch(self.requests)
        self.measure("full-retry-after-rollback", apply, len(self.requests))
        saved = self.assert_saved(self.requests)
        self.measure("full-retry-noop", apply, 0)
        self.assertEqual(self.snapshot(), saved)

    def test_real_owner_requests_only_approve_matching_current_versions(self):
        # These expectations use the original owner pins, not synthetic ones.
        # Staged edits and photo replacements must remain pending fresh review.
        expected = [
            request for request in self.owner_requests
            if request[1] in self.records
            and (self.records[request[1]]["date"], self.records[request[1]]["revision"])
            == (request[0], request[2])
        ]
        self.active_records = self.records
        with patch.object(jr, "_write_decision", wraps=jr._write_decision) as writes:
            self.assertEqual(owner.apply_all(), len(expected))
            self.assertEqual(writes.call_count, len(expected))
        saved = self.assert_saved(expected)
        self.assertEqual(owner.apply_all(), 0)
        self.assertEqual(self.snapshot(), saved)

    def test_real_owner_requests_do_not_authorize_changed_review_drafts(self):
        # Deliberately drift every candidate without editing the public corpus
        # or production approval constants. No old pin can authorize this set.
        changed = {
            slug: {**record, "revision": "0" * 64}
            for slug, record in self.records.items()
        }
        before = self.snapshot()
        with patch.object(jr, "candidates", return_value=changed), \
             patch.object(jr, "_write_decision", wraps=jr._write_decision) as writes:
            self.assertEqual(owner.apply_all(), 0)
            writes.assert_not_called()
        self.assertEqual(self.snapshot(), before,
                         "Changed drafts gained approvals, releases, photos or audit records")


if __name__ == "__main__":
    unittest.main()
