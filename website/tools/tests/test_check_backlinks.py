#!/usr/bin/env python3
"""
Tests for check-backlinks.py authority scoring logic.

Covers:
  - OPR high / medium / low scores take precedence
  - OPR-missing domains fall back to Tranco (the key regression fixed in this task)
  - Absent from both OPR and Tranco → no penalty
  - OPR-missing + absent Tranco → small OPR-missing penalty
  - apply_tranco() tier assignment
  - _load_tranco_csv() parsing
"""

import importlib.util
import os
import sys
import tempfile
import unittest

# check-backlinks.py has a hyphen so we can't use a normal import
_tool_path = os.path.join(os.path.dirname(__file__), '..', 'check-backlinks.py')
_spec = importlib.util.spec_from_file_location('check_backlinks', _tool_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

DomainResult    = _mod.DomainResult
_load_tranco_csv = _mod._load_tranco_csv
apply_tranco    = _mod.apply_tranco
compute_scores  = _mod.compute_scores


def _make_domain(domain='example.com', opr_score=None, opr_error='',
                 tranco_rank=None, tranco_tier='', authoritative=False):
    r = DomainResult(domain=domain)
    r.opr_score = opr_score
    r.opr_error = opr_error
    r.tranco_rank = tranco_rank
    r.tranco_tier = tranco_tier
    r.authoritative = authoritative
    return r


class TestComputeScores(unittest.TestCase):

    # ------------------------------------------------------------------
    # OPR takes precedence when a score is present
    # ------------------------------------------------------------------

    def test_opr_high_gives_green(self):
        r = _make_domain(opr_score=8.5)
        compute_scores([r])
        self.assertEqual(r.score, 8.0)   # 5.0 base + 3
        self.assertEqual(r.verdict, 'GREEN')
        self.assertTrue(any('OPR' in f and 'high' in f for f in r.flags))

    def test_opr_medium_stays_amber(self):
        r = _make_domain(opr_score=5.0)
        compute_scores([r])
        self.assertEqual(r.score, 5.0)   # no adjustment
        self.assertEqual(r.verdict, 'AMBER')
        self.assertTrue(any('OPR' in f and 'medium' in f for f in r.flags))

    def test_opr_low_drops_score(self):
        r = _make_domain(opr_score=1.5)
        compute_scores([r])
        self.assertEqual(r.score, 2.0)   # 5.0 − 3
        self.assertEqual(r.verdict, 'RED')
        self.assertTrue(any('OPR' in f and 'low' in f for f in r.flags))

    # ------------------------------------------------------------------
    # OPR missing → Tranco fallback (the main regression fixed here)
    # ------------------------------------------------------------------

    def test_opr_missing_tranco_high_gives_green(self):
        """When OPR has no data but Tranco says top-100k, domain should score GREEN."""
        r = _make_domain(opr_error='not in OPR index',
                         tranco_rank=50_000, tranco_tier='high')
        compute_scores([r])
        self.assertEqual(r.score, 8.0)   # 5.0 + 3 from Tranco high
        self.assertEqual(r.verdict, 'GREEN')
        self.assertTrue(any('Tranco' in f and 'high' in f for f in r.flags))
        # OPR-missing penalty must NOT be applied
        self.assertFalse(any('not in OPR' in f for f in r.flags))

    def test_opr_missing_tranco_medium_stays_amber(self):
        """When OPR has no data and Tranco says 100k–1M, score stays neutral."""
        r = _make_domain(opr_error='not in OPR index',
                         tranco_rank=500_000, tranco_tier='medium')
        compute_scores([r])
        self.assertEqual(r.score, 5.0)   # no adjustment
        self.assertEqual(r.verdict, 'AMBER')
        self.assertTrue(any('Tranco' in f and 'medium' in f for f in r.flags))

    def test_opr_missing_tranco_absent_applies_penalty(self):
        """When OPR has no data AND domain is absent from Tranco, apply small OPR penalty."""
        r = _make_domain(opr_error='not in OPR index')
        compute_scores([r])
        self.assertEqual(r.score, 4.0)   # 5.0 − 1
        self.assertTrue(any('not in OPR' in f for f in r.flags))

    def test_no_opr_no_tranco_no_penalty(self):
        """When OPR wasn't queried and Tranco has no data, score stays at neutral 5."""
        r = _make_domain()
        compute_scores([r])
        self.assertEqual(r.score, 5.0)
        self.assertEqual(r.verdict, 'AMBER')

    # ------------------------------------------------------------------
    # OPR score beats Tranco even when Tranco is high
    # ------------------------------------------------------------------

    def test_opr_score_beats_tranco(self):
        """OPR score should be used and Tranco ignored when both are present."""
        r = _make_domain(opr_score=1.0,   # low OPR
                         tranco_rank=10_000, tranco_tier='high')  # high Tranco
        compute_scores([r])
        self.assertEqual(r.score, 2.0)   # OPR low: 5.0 − 3
        self.assertTrue(any('OPR' in f and 'low' in f for f in r.flags))
        # No Tranco flag should appear
        self.assertFalse(any('Tranco' in f for f in r.flags))

    # ------------------------------------------------------------------
    # Authoritative domains are skipped
    # ------------------------------------------------------------------

    def test_authoritative_skipped(self):
        r = _make_domain(authoritative=True)
        r.score = 10.0
        r.verdict = 'GREEN'
        compute_scores([r])
        self.assertEqual(r.score, 10.0)   # unchanged
        self.assertEqual(r.verdict, 'GREEN')


class TestApplyTranco(unittest.TestCase):

    def test_high_tier_assignment(self):
        r = _make_domain()
        apply_tranco([r], {'example.com': 1_000}, opr_active=False)
        self.assertEqual(r.tranco_rank, 1_000)
        self.assertEqual(r.tranco_tier, 'high')

    def test_medium_tier_assignment(self):
        r = _make_domain()
        apply_tranco([r], {'example.com': 500_000}, opr_active=False)
        self.assertEqual(r.tranco_rank, 500_000)
        self.assertEqual(r.tranco_tier, 'medium')

    def test_absent_domain_no_tier(self):
        r = _make_domain()
        apply_tranco([r], {}, opr_active=False)
        self.assertIsNone(r.tranco_rank)
        self.assertEqual(r.tranco_tier, '')

    def test_authoritative_skipped(self):
        r = _make_domain(authoritative=True)
        apply_tranco([r], {'example.com': 1_000}, opr_active=False)
        self.assertIsNone(r.tranco_rank)   # authoritative domains are excluded


class TestLoadTrancoCsv(unittest.TestCase):

    def test_parses_rank_domain(self):
        csv_content = "1,google.com\n2,youtube.com\n3,facebook.com\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as fh:
            fh.write(csv_content)
            path = fh.name
        try:
            data = _load_tranco_csv(path)
            self.assertEqual(data['google.com'], 1)
            self.assertEqual(data['youtube.com'], 2)
            self.assertEqual(data['facebook.com'], 3)
        finally:
            os.unlink(path)

    def test_ignores_blank_lines(self):
        csv_content = "1,google.com\n\n2,youtube.com\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as fh:
            fh.write(csv_content)
            path = fh.name
        try:
            data = _load_tranco_csv(path)
            self.assertEqual(len(data), 2)
        finally:
            os.unlink(path)

    def test_ignores_malformed_lines(self):
        csv_content = "1,google.com\nnot-a-rank,bad\n3,facebook.com\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as fh:
            fh.write(csv_content)
            path = fh.name
        try:
            data = _load_tranco_csv(path)
            self.assertNotIn('bad', data)
            self.assertEqual(data['google.com'], 1)
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self):
        data = _load_tranco_csv('/tmp/nonexistent-tranco-file-xyz.csv')
        self.assertEqual(data, {})


if __name__ == '__main__':
    unittest.main()
