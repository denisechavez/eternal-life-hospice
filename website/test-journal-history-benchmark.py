#!/usr/bin/env python3
"""Harness checks using tiny, disposable local data, never latency assertions."""
import argparse
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "journal_history_benchmark", Path(__file__).with_name("benchmark-journal-history.py"))
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    def args(self):
        return argparse.Namespace(
            run=True, articles=30, revisions=10, actions=10, samples=1, page_size=2,
            max_history_ms=None, max_queue_ms=None, output="unused.json")

    def test_real_queries_and_payloads_use_expected_indexes(self):
        report = benchmark.run(self.args())
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["queue_before_history"]["response_bytes"],
                         report["queue_after_history"]["response_bytes"])
        self.assertGreater(report["rows"]["journal_review_audit"], 3000)
        self.assertGreater(report["deep_audit_offset"], 500)
        self.assertEqual(set(report["history"]), {"early", "deep"})

    def test_removed_indexes_are_reported_as_regressions(self):
        initialize = benchmark.jr.initialize

        def missing_indexes():
            initialize()
            with benchmark.jr.connect() as db:
                db.execute("DROP INDEX journal_audit_article_page")
                db.execute("DROP INDEX journal_audit_saved_decision")

        with patch.object(benchmark.jr, "initialize", side_effect=missing_indexes):
            report = benchmark.run(self.args())
        for name in ("early", "deep"):
            for index in ("journal_audit_article_page", "journal_audit_saved_decision"):
                self.assertIn(f"{name}: actual query did not use {index}", report["failures"])

    def test_explicit_timing_budgets_report_failures(self):
        # Deliberately tiny user-selected budgets verify the opt-in failure path;
        # this asserts failure reporting, not machine-dependent performance.
        args = self.args()
        args.max_history_ms = args.max_queue_ms = 1e-12
        report = benchmark.run(args)
        self.assertTrue(any("Queue p95 exceeds" in failure for failure in report["failures"]))
        for name in ("early", "deep"):
            self.assertTrue(any(f"{name}: history p95 exceeds" in failure
                                for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()
