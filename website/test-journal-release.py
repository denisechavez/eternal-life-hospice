#!/usr/bin/env python3
"""Journal release integration tests, isolated from real approvals and sends."""
import copy
import importlib.util
import json
import html
import os
import threading
import unittest
import uuid
import tempfile
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg
from psycopg.rows import dict_row
import journal_release as jr
import journal_owner_approval as owner_approval
import studio_auth
import studio_site
import journal_discovery
from devserver import PrettyURLHandler

spec = importlib.util.spec_from_file_location("release_monitor", jr.BASE / "check-journal-release.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("REPLIT_DEPLOYMENT") == "1":
            raise RuntimeError("Tests must not run against a production deployment")
        cls.real_connect = jr.connect
        cls.schema = "journal_test_" + uuid.uuid4().hex
        with cls.real_connect() as db:
            db.execute(f'CREATE SCHEMA "{cls.schema}"')
        def isolated():
            return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5,
                                  options=f"-c search_path={cls.schema}", row_factory=dict_row)
        cls.connect_patch = patch.object(jr, "connect", isolated)
        cls.connect_patch.start()
        jr.initialize()
        cls.originals = jr.history()
        cls.all_candidates = jr.candidates()
        cls.record = copy.deepcopy(next(r for slug, r in cls.all_candidates.items() if slug not in cls.originals))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), PrettyURLHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.site = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.connect_patch.stop()
        with cls.real_connect() as db:
            db.execute(f'DROP SCHEMA "{cls.schema}" CASCADE')

    def setUp(self):
        with jr.connect() as db:
            db.execute("TRUNCATE journal_decisions,journal_releases,journal_review_audit,journal_photos")
        self.record = copy.deepcopy(type(self).record)
        self.due = jr.release_at(self.record["date"]).astimezone(timezone.utc)
        self.clock = patch.object(jr, "now", return_value=self.due - timedelta(minutes=1))
        self.now_mock = self.clock.start()
        self.candidate_patch = patch.object(jr, "candidates", side_effect=lambda: {self.record["slug"]: self.record})
        self.candidate_patch.start()
        self.schedule_patch = patch.object(
            jr, "scheduled_dates",
            side_effect=lambda instant: {self.record["date"]} if instant >= self.due else set())
        self.schedule_patch.start()
        self.addCleanup(self.schedule_patch.stop)
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.candidate_patch.stop)

    def approve(self):
        jr.decide(self.record["slug"], self.record["revision"], "approve", "reviewer-1")

    def owner_approval(self):
        request = {"slug": self.record["slug"], "date": self.record["date"], "revision": self.record["revision"],
                   "reviewer": "Owner request — October 15, 2026 (outside Studio)"}
        with patch.object(owner_approval, "REQUEST", request), patch.object(jr, "environment", return_value="production"):
            return owner_approval.apply()

    def test_owner_request_releases_now_and_records_its_real_source(self):
        self.assertTrue(self.owner_approval())
        self.assertEqual(jr.released()[0][self.record["slug"]]["revision"], self.record["revision"])
        status, body, _ = self.request("/blog/" + self.record["slug"])
        self.assertEqual(status, 200)
        self.assertIn(self.record["title"], html.unescape(body))
        self.assertIn("/api/journal-photo/", body)
        with jr.connect() as db:
            first_release = db.execute("SELECT released_at FROM journal_releases WHERE slug=%s", (self.record["slug"],)).fetchone()
        self.assertEqual(first_release["released_at"], self.due - timedelta(minutes=1))
        self.now_mock.return_value = self.due
        self.assertEqual(jr.released()[0][self.record["slug"]]["revision"], self.record["revision"])
        with jr.connect() as db:
            events = db.execute("SELECT * FROM journal_review_audit").fetchall()
            self.assertEqual(db.execute("SELECT released_at FROM journal_releases WHERE slug=%s", (self.record["slug"],)).fetchone(),
                             first_release)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["environment"], "production")
        self.assertIn("outside Studio", events[0]["reviewer"])

    def test_ordinary_approvals_remain_scheduled(self):
        self.approve()
        self.assertNotIn(self.record["slug"], jr.released()[0])
        with self.assertRaisesRegex(ValueError, "single-use owner"):
            jr.decide(self.record["slug"], self.record["revision"], "approve", "reviewer-1",
                      release_immediately=True)

    def reconcile_october(self):
        requests = ((self.record["date"], self.record["slug"], self.record["revision"]),)
        with patch.object(owner_approval, "OCTOBER_REQUESTS", requests), \
                patch.object(jr, "environment", return_value="production"):
            return owner_approval.apply_october()

    def test_october_reconciliation_keeps_clock_and_is_idempotent(self):
        self.assertEqual(self.reconcile_october(), 1)
        self.assertNotIn(self.record["slug"], jr.released()[0])
        self.assertEqual(self.reconcile_october(), 0)
        self.now_mock.return_value = self.due
        self.assertIn(self.record["slug"], jr.released()[0])
        with jr.connect() as db:
            events = db.execute("SELECT * FROM journal_review_audit").fetchall()
        self.assertEqual(len(events), 1)
        self.assertIn("outside Studio", events[0]["reviewer"])
        self.assertEqual(events[0]["environment"], "production")

    def test_october_reconciliation_preserves_hold(self):
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        self.assertEqual(self.reconcile_october(), 0)
        self.now_mock.return_value = self.due
        self.assertNotIn(self.record["slug"], jr.released()[0])

    def test_october_reconciliation_rejects_changes_and_workspace(self):
        requests = ((self.record["date"], self.record["slug"], "stale"),)
        with patch.object(owner_approval, "OCTOBER_REQUESTS", requests), \
                patch.object(jr, "environment", return_value="production"):
            self.assertEqual(owner_approval.apply_october(), 0)
        with patch.object(jr, "environment", return_value="workspace"), \
                patch.object(jr, "decide") as decide:
            self.assertEqual(owner_approval.apply_october(), 0)
            decide.assert_not_called()

    def test_year_end_consent_retains_dates_and_real_audit_time(self):
        self.record["date"] = "2026-12-31"
        due = jr.release_at(self.record["date"]).astimezone(timezone.utc)
        self.now_mock.return_value = due - timedelta(days=10)
        consent_time = jr.now()
        with patch.object(owner_approval, "YEAR_END_REVISIONS", {
                self.record["date"]: self.record["revision"]}), \
                patch.object(jr, "environment", return_value="production"):
            self.assertEqual(owner_approval.apply_year_end(), 1)
            self.assertEqual(owner_approval.apply_year_end(), 0)
        self.assertNotIn(self.record["slug"], jr.released()[0])
        self.now_mock.return_value = due
        self.assertIn(self.record["slug"], jr.released()[0])
        with jr.connect() as db:
            audit = db.execute("SELECT * FROM journal_review_audit").fetchone()
        self.assertEqual(audit["occurred_at"], consent_time)
        self.assertIn("outside Studio", audit["reviewer"])

    def test_year_end_consent_preserves_hold_and_rejects_changed_versions(self):
        self.record["date"] = "2026-11-01"
        with patch.object(owner_approval, "YEAR_END_REVISIONS", {
                self.record["date"]: "stale"}), \
                patch.object(jr, "environment", return_value="production"):
            self.assertEqual(owner_approval.apply_year_end(), 0)
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        with patch.object(owner_approval, "YEAR_END_REVISIONS", {
                self.record["date"]: self.record["revision"]}), \
                patch.object(jr, "environment", return_value="production"):
            self.assertEqual(owner_approval.apply_year_end(), 0)

    def test_year_end_consent_denies_workspace_and_out_of_scope_dates(self):
        with patch.object(jr, "environment", return_value="workspace"), \
                patch.object(jr, "decide") as decide:
            self.assertEqual(owner_approval.apply_year_end(), 0)
            decide.assert_not_called()
        self.record["date"] = "2027-01-01"
        with patch.object(owner_approval, "YEAR_END_REVISIONS", {
                self.record["date"]: self.record["revision"]}), \
                patch.object(jr, "environment", return_value="production"), \
                patch.object(jr, "decide") as decide:
            self.assertEqual(owner_approval.apply_year_end(), 0)
            decide.assert_not_called()

    def test_schedule_gap_alerts_without_approval_and_respects_hold(self):
        self.now_mock.return_value = self.due
        state, failures = monitor.check(self.site)
        self.assertEqual(state, "missed")
        self.assertTrue(any(self.record["date"] in f for f in failures))
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        state, failures = monitor.check(self.site)
        self.assertEqual(state, "missed")
        self.assertNotIn(self.record["slug"], jr.released()[0])
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT state FROM journal_decisions").fetchone()["state"], "held")

    def test_future_schedule_has_no_false_gap(self):
        self.assertEqual(jr.release_status()["scheduleGaps"], [])

    def test_schedule_gap_does_not_leak_private_draft_details(self):
        self.now_mock.return_value = self.due
        payload = jr.release_status()
        self.assertEqual(payload["scheduleGaps"], [self.record["date"]])
        self.assertNotIn(self.record["title"], json.dumps(payload))
        self.assertNotIn(self.record["slug"], json.dumps(payload))

    def test_owner_request_is_idempotent_even_after_content_changes(self):
        self.assertTrue(self.owner_approval())
        self.record["revision"] = "changed-after-approval"
        self.assertFalse(self.owner_approval())
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS total FROM journal_review_audit").fetchone()["total"], 1)

    def test_owner_request_never_overrides_a_studio_hold(self):
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        self.assertFalse(self.owner_approval())
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT state FROM journal_decisions").fetchone()["state"], "held")

    def test_owner_request_rejects_changed_version_and_is_production_only(self):
        with patch.object(jr, "environment", return_value="workspace"), patch.object(jr, "decide") as decide:
            self.assertFalse(owner_approval.apply())
            decide.assert_not_called()
        with patch.object(jr, "environment", return_value="production"), patch.object(owner_approval, "REQUEST", {
            "slug": self.record["slug"], "date": self.record["date"], "revision": "not-the-requested-version", "reviewer": "Owner request"
        }):
            self.assertFalse(owner_approval.apply())
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS total FROM journal_decisions").fetchone()["total"], 0)

    def test_owner_request_rejects_rescheduling(self):
        request = {"slug": self.record["slug"], "date": "2099-01-01",
                   "revision": self.record["revision"], "reviewer": "Owner request"}
        with patch.object(jr, "environment", return_value="production"), patch.object(owner_approval, "REQUEST", request):
            self.assertFalse(owner_approval.apply())
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS total FROM journal_review_audit").fetchone()["total"], 0)

    def test_concurrent_owner_request_startups_save_only_one_event(self):
        from concurrent.futures import ThreadPoolExecutor
        request = {"slug": self.record["slug"], "date": self.record["date"],
                   "revision": self.record["revision"], "reviewer": "Owner request"}
        with patch.object(jr, "environment", return_value="production"), patch.object(owner_approval, "REQUEST", request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: owner_approval.apply(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS total FROM journal_review_audit").fetchone()["total"], 1)

    def request(self, path, method="GET", data=None, headers=None):
        request = Request(self.site + path, method=method,
                          data=json.dumps(data).encode() if data is not None else None,
                          headers=headers or {})
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, response.read().decode(), response.headers
        except HTTPError as error:
            return error.code, error.read().decode(), error.headers

    def test_dst_spring_and_autumn(self):
        expectations = {"2026-03-07":"14:30", "2026-03-08":"13:30",
                        "2026-10-31":"13:30", "2026-11-01":"14:30"}
        for day, expected in expectations.items():
            self.assertEqual(jr.release_at(day).astimezone(timezone.utc).strftime("%H:%M"), expected)

    def test_exact_release_boundary_and_persistence(self):
        self.approve()
        self.assertNotIn(self.record["slug"], jr.released()[0])
        self.now_mock.return_value = self.due
        self.assertEqual(jr.released()[0][self.record["slug"]]["revision"], self.record["revision"])
        # A new connection (simulated process restart) sees the same decision.
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_releases").fetchone()["n"], 1)
        self.assertEqual(jr.review_items()[0]["status"], "Published")

    def test_held_draft_is_not_expected(self):
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        self.now_mock.return_value = self.due + timedelta(days=3)
        self.assertEqual(jr.release_status()["expected"], [])
        self.assertNotIn(self.record["slug"], jr.released()[0])

    def test_approval_can_be_held_before_due(self):
        self.approve()
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        self.now_mock.return_value = self.due
        self.assertNotIn(self.record["slug"], jr.released()[0])

    def test_hold_cannot_withdraw_already_published_history(self):
        self.approve()
        self.now_mock.return_value = self.due
        jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-1")
        self.assertIn(self.record["slug"], jr.released()[0])

    def test_late_approval_releases_immediately_on_original_date(self):
        self.now_mock.return_value = self.due + timedelta(days=5)
        self.approve()
        self.assertEqual(jr.released()[0][self.record["slug"]]["date"], self.record["date"])

    def test_stale_revision_never_approves_new_copy(self):
        stale = self.record["revision"]
        self.record["html"] += "<p>A new clinical disclosure</p>"
        self.record["revision"] = jr.revision(self.record["html"])
        with self.assertRaises(ValueError):
            jr.decide(self.record["slug"], stale, "approve", "reviewer-1")
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_decisions").fetchone()["n"], 0)

    def test_approved_snapshot_does_not_silently_publish_changed_draft(self):
        approved_revision = self.record["revision"]
        self.approve()
        self.record["html"] += "<p>UNAPPROVED_NEW_COPY</p>"
        self.record["revision"] = jr.revision(self.record["html"])
        self.now_mock.return_value = self.due
        published = jr.released()[0][self.record["slug"]]
        self.assertNotIn("UNAPPROVED_NEW_COPY", published["html"])
        self.assertEqual(published["revision"], approved_revision)
        self.assertEqual(jr.review_items()[0]["status"], "Needs review")

    def test_transaction_failure_leaves_no_partial_approval(self):
        with patch.object(jr, "freeze_photos", side_effect=RuntimeError("test")):
            with self.assertRaises(RuntimeError):
                self.approve()
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_decisions").fetchone()["n"], 0)
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_review_audit").fetchone()["n"], 0)

    def test_photos_private_until_release_then_frozen(self):
        self.approve()
        with jr.connect() as db:
            asset = db.execute("SELECT * FROM journal_photos LIMIT 1").fetchone()
        self.assertIsNotNone(asset)
        self.assertIsNone(jr.photo(asset["digest"]))
        self.now_mock.return_value = self.due
        self.assertEqual(jr.photo(asset["digest"])["body"], asset["body"])
        self.assertIn("/api/journal-photo/", jr.released()[0][self.record["slug"]]["html"])

    def test_public_get_head_alias_and_encoded_paths_are_held(self):
        self.now_mock.return_value = self.due + timedelta(days=1)
        slug = self.record["slug"]
        for path in (f"/blog/{slug}", f"/blog/{slug}.html", f"/blog/%2e%2e/blog/{slug}",
                     f"/blog/{slug.replace('-', '%252d')}"):
            for method in ("GET", "HEAD"):
                self.assertEqual(self.request(path, method)[0], 404, (path, method))

    def test_discovery_hides_unapproved_due_post(self):
        self.now_mock.return_value = self.due + timedelta(days=10)
        slug = self.record["slug"]
        for path in ("/blog", "/resources", "/assets/search-index.json", "/sitemap.xml"):
            status, body, _ = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertNotIn("/blog/" + slug, body, path)
            self.assertNotIn('href="blog/' + slug, body, path)

    def test_approved_due_post_is_served_and_discoverable(self):
        self.approve()
        self.now_mock.return_value = self.due
        slug = self.record["slug"]
        status, body, headers = self.request("/blog/" + slug)
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Journal-Revision"], self.record["revision"])
        self.assertIn("<h1", body)
        self.assertEqual(self.request("/blog/" + slug, "HEAD")[1], "")
        for path in ("/blog", "/sitemap.xml", "/assets/search-index.json"):
            status, body, _ = self.request(path)
            self.assertEqual(status, 200)
            self.assertIn(slug, body, path)
        state, failures = monitor.check(self.site)
        self.assertEqual((state, failures), ("healthy", []))

    def test_existing_published_original_survives_storage_outage(self):
        slug = next(iter(self.originals))
        with patch.object(jr, "connect", side_effect=RuntimeError("test outage")):
            published, healthy = jr.released()
            self.assertFalse(healthy)
            self.assertEqual(published[slug]["html"], jr.unpack(self.originals[slug]))
            self.assertEqual(self.request("/blog/" + slug)[0], 200)
            self.assertEqual(self.request("/api/journal-release-status")[0], 503)

    def test_approval_api_rejects_unsigned_and_cross_origin_writes(self):
        self.assertEqual(self.request("/api/studio/journal")[0], 401)
        data = {"slug":self.record["slug"],"revision":self.record["revision"],"action":"approve"}
        self.assertEqual(self.request("/api/studio/journal", "POST", data)[0], 401)
        with patch.object(studio_auth, "reviewer_identity",
                          return_value=studio_auth.ReviewerIdentity("reviewer-1", "Verified Reviewer")):
            self.assertEqual(self.request("/api/studio/journal", "POST", data,
                                          {"Origin":"https://untrusted.example","Cookie":"__session=test"})[0], 403)
            status, body, _ = self.request("/api/studio/journal", "POST", data,
                                          {"Origin":"https://eternallifehospice.com"})
            self.assertEqual(status, 200, body)
            self.assertEqual(json.loads(body)["items"][0]["status"], "Approved")
            data["revision"] = "stale"
            self.assertEqual(self.request("/api/studio/journal", "POST", data,
                                         {"Origin":"https://eternallifehospice.com"})[0], 409)

    def test_private_history_records_both_reviewers_and_repeated_actions(self):
        data = {"slug": self.record["slug"], "revision": self.record["revision"], "action": "approve"}
        for reviewer, action in (("user_Aleksandra", "approve"), ("user_Denise", "hold"),
                                 ("user_Denise", "approve")):
            data["action"] = action
            self.now_mock.return_value += timedelta(seconds=1)
            with patch.object(studio_auth, "reviewer_identity",
                              return_value=studio_auth.ReviewerIdentity(reviewer, reviewer + " saved name")), \
                 patch.object(studio_auth, "reviewer_label", side_effect=lambda identity: identity), \
                 patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
                status, body, headers = self.request("/api/studio/journal", "POST", data,
                                                     {"Origin": "https://eternallifehospice.com"})
            self.assertEqual(status, 200, body)
            self.assertIn("no-store", headers["Cache-Control"])
        item = json.loads(body)["items"][0]
        self.assertNotIn("approvalHistory", item)
        saved = jr.article_history(self.record["slug"])
        events = saved["events"]
        self.assertEqual([event["reviewerId"] for event in events],
                         ["user_Denise", "user_Denise", "user_Aleksandra"])
        self.assertEqual([event["action"] for event in events], ["approve", "hold", "approve"])
        self.assertEqual({event["revision"] for event in events}, {self.record["revision"]})
        self.assertEqual({event["environment"] for event in events}, {"workspace"})
        self.assertEqual(events[0]["occurredAt"], self.now_mock.return_value.isoformat())
        self.assertEqual([event["reviewerNameSnapshot"] for event in events],
                         ["user_Denise saved name", "user_Denise saved name", "user_Aleksandra saved name"])
        self.assertEqual(saved["recordEnvironment"], "workspace")
        self.assertEqual(item["status"], "Approved")
        self.assertIsNone(saved["publishedVersion"])
        self.assertIsNone(saved["preStudioVersion"])
        with patch.object(studio_auth, "reviewer_identity", side_effect=PermissionError("Not authorized")):
            for method in ("GET", "HEAD", "POST"):
                status, body, _ = self.request("/api/studio/journal", method,
                                               data if method == "POST" else None,
                                               {"Cookie": "__session=unauthorized"})
                self.assertEqual(status, 403)
                self.assertNotIn("user_Denise", body)
                self.assertNotIn("approvalHistory", body)
        for method in ("GET", "HEAD"):
            self.assertEqual(self.request("/api/studio/journal", method)[0], 401)
        self.assertNotIn("reviewer", self.request("/api/journal-release-status")[1].lower())

    def test_saved_names_survive_rename_deletion_and_repeated_decisions(self):
        slug, revision = self.record["slug"], self.record["revision"]
        jr.decide(slug, revision, "approve", "user_actor", reviewer_name="Original Name")
        self.now_mock.return_value += timedelta(seconds=1)
        jr.decide(slug, revision, "hold", "user_actor", reviewer_name="Renamed Reviewer")
        for current_label in ("Renamed Reviewer", "user_actor"):
            with self.subTest(directory=current_label), \
                 patch.object(studio_auth, "reviewer_label", return_value=current_label):
                events = jr.article_history(slug)["events"]
            self.assertEqual([e["reviewerNameSnapshot"] for e in events],
                             ["Renamed Reviewer", "Original Name"])
            self.assertEqual({e["reviewerId"] for e in events}, {"user_actor"})
            self.assertEqual({e["reviewerLabel"] for e in events}, {current_label})
        with jr.connect() as db:
            row = db.execute("SELECT reviewer_name FROM journal_decisions").fetchone()
            self.assertEqual(row["reviewer_name"], "Renamed Reviewer")
            db.execute("TRUNCATE journal_review_audit")
        with patch.object(studio_auth, "reviewer_label", return_value="user_actor"):
            event = jr.article_history(slug)["events"][0]
        self.assertEqual(event["source"], "saved-decision")
        self.assertEqual(event["reviewerNameSnapshot"], "Renamed Reviewer")

    def test_api_does_not_accept_browser_supplied_actor_or_name(self):
        payload = {"slug": self.record["slug"], "revision": self.record["revision"],
                   "action": "hold", "reviewer": "user_forged", "reviewer_name": "Forged Name",
                   "reviewerNameSnapshot": "Forged Name", "environment": "production"}
        with patch.object(studio_auth, "reviewer_identity",
                          return_value=studio_auth.ReviewerIdentity("user_verified", "Verified Name")), \
             patch.object(studio_auth, "reviewer_label", return_value="Current Name"), \
             patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
            status, body, _ = self.request("/api/studio/journal", "POST", payload,
                                          {"Origin": "https://eternallifehospice.com"})
            self.assertEqual(status, 200, body)
            self.assertNotIn("approvalHistory", json.loads(body)["items"][0])
            status, body, _ = self.request("/api/studio/journal/history?slug=" + self.record["slug"])
        self.assertEqual(status, 200, body)
        event = json.loads(body)["events"][0]
        self.assertEqual(event["reviewerId"], "user_verified")
        self.assertEqual(event["reviewerNameSnapshot"], "Verified Name")
        self.assertEqual(event["environment"], "workspace")

    def test_additive_name_migration_does_not_backfill_legacy_names(self):
        self.approve()
        with jr.connect() as db:
            db.execute("ALTER TABLE journal_decisions DROP COLUMN reviewer_name")
            db.execute("ALTER TABLE journal_review_audit DROP COLUMN reviewer_name")
        jr.initialize()
        jr.initialize()
        with patch.object(studio_auth, "reviewer_label", return_value="Today's Name"):
            event = jr.article_history(self.record["slug"])["events"][0]
        self.assertIsNone(event["reviewerNameSnapshot"])
        self.assertEqual(event["reviewerLabel"], "Today's Name")
        self.assertEqual(event["reviewerId"], "reviewer-1")
        with jr.connect() as db:
            self.assertIsNone(db.execute("SELECT reviewer_name FROM journal_decisions").fetchone()["reviewer_name"])

    def test_missing_name_is_not_replaced_with_email_or_id(self):
        self.assertIsNone(studio_auth.display_name({"email_addresses": [{"email_address": "private@example.org"}]}))
        self.assertIsNone(studio_auth.display_name({"first_name": " ", "last_name": None}))
        self.assertEqual(studio_auth.display_name({"first_name": " Single "}), "Single")

    def test_history_keeps_pre_studio_original_separate_from_pending_revision(self):
        slug = next(iter(self.originals))
        original = self.originals[slug]
        self.record.update(slug=slug, revision="changed-draft")
        item = jr.review_items()[0]
        saved = jr.article_history(slug)
        self.assertEqual(item["status"], "Needs review")
        self.assertTrue(item["hasPublishedVersion"])
        self.assertEqual(saved["publishedVersion"]["revision"], original["revision"])
        self.assertEqual(saved["preStudioVersion"], {"revision": original["revision"], "date": original["date"]})
        self.assertEqual(saved["events"], [])
        jr.decide(slug, "changed-draft", "hold", "reviewer-2")
        item = jr.review_items()[0]
        self.assertTrue(item["held"])
        saved = jr.article_history(slug)
        self.assertEqual(saved["publishedVersion"]["revision"], original["revision"])
        self.assertEqual(saved["events"][0]["revision"], "changed-draft")
        self.assertEqual(jr.released()[0][slug]["html"], jr.unpack(original))

    def test_history_pages_repeated_decisions_without_loading_audit_in_queue(self):
        self.approve()
        slug = self.record["slug"]
        with jr.connect() as db:
            # Repeated actions at the exact same instant must not collapse.
            db.execute("""
                INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at,environment)
                SELECT %s,%s,CASE WHEN n%%2=0 THEN 'approve' ELSE 'hold' END,
                    'actor-' || n,%s,CASE WHEN n%%3=0 THEN NULL ELSE 'workspace' END
                FROM generate_series(1,350) n
            """, (slug, self.record["revision"], self.now_mock.return_value))
            db.execute("""
                INSERT INTO journal_review_audit (id,slug,revision,action,reviewer,occurred_at)
                VALUES (9007199254740993,%s,%s,'hold','large-id-actor',%s)
            """, (slug, self.record["revision"], self.now_mock.return_value))
            db.execute("""
                INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at)
                VALUES ('another-article','other-version','hold','private-other-actor',%s)
            """, (self.now_mock.return_value,))
            expected = db.execute("""
                SELECT id,reviewer,action,occurred_at,environment FROM journal_review_audit
                WHERE slug=%s ORDER BY occurred_at DESC,id DESC
            """, (slug,)).fetchall()
        with patch.object(studio_auth, "reviewer_label", side_effect=AssertionError("Queue resolved private actors")):
            queue = jr.review_items()
        self.assertNotIn("approvalHistory", queue[0])
        self.assertNotIn("large-id-actor", json.dumps(queue))
        self.assertNotIn("private-other-actor", json.dumps(queue))
        cursor = None
        events = []
        while True:
            with patch.object(studio_auth, "reviewer_label", side_effect=lambda actor: actor) as label:
                page = jr.article_history(slug, 17, cursor)
            self.assertLessEqual(len(page["events"]), 17)
            self.assertLessEqual(label.call_count, 17)
            events.extend(page["events"])
            if cursor is None:
                self.assertEqual(page["events"][0]["id"], "9007199254740993")
                # A new event after page one must not shift subsequent pages.
                with jr.connect() as db:
                    db.execute("""
                        INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at)
                        VALUES (%s,'new-version','hold','newer-actor',%s)
                    """, (slug, self.now_mock.return_value + timedelta(seconds=1)))
            cursor = page["nextCursor"]
            if not cursor:
                break
        self.assertEqual([e["id"] for e in events], [str(r["id"]) for r in expected])
        self.assertEqual([e["reviewerId"] for e in events], [r["reviewer"] for r in expected])
        self.assertEqual([e["action"] for e in events], [r["action"] for r in expected])
        self.assertEqual([e["occurredAt"] for e in events], [r["occurred_at"].isoformat() for r in expected])
        self.assertEqual([e["environment"] for e in events], [r["environment"] for r in expected])
        self.assertEqual({e["revision"] for e in events}, {self.record["revision"]})
        self.assertEqual(len(events), 352)

    def test_history_paginates_legacy_states_and_checks_original_beyond_page(self):
        slug = next(iter(self.originals))
        original = self.originals[slug]
        self.record.update(slug=slug, revision=original["revision"])
        self.approve()
        with jr.connect() as db:
            # Legacy rows are saved states, not fabricated audit events.
            db.execute("""
                INSERT INTO journal_decisions (slug,revision,release_date,document,state,reviewer,decided_at)
                SELECT %s,'legacy-' || n,%s,'','held','legacy-actor',%s FROM generate_series(1,55) n
            """, (slug, self.record["date"], self.now_mock.return_value + timedelta(seconds=1)))
        events = []
        cursor = None
        while True:
            page = jr.article_history(slug, 5, cursor)
            self.assertIsNone(page["preStudioVersion"])
            self.assertEqual(page["publishedVersion"]["revision"], original["revision"])
            events.extend(page["events"])
            cursor = page["nextCursor"]
            if not cursor:
                break
        self.assertEqual(len(events), 56)
        self.assertEqual(len({e["id"] for e in events}), 56)
        self.assertEqual(len([e for e in events if e["source"] == "audit"]), 1)
        self.assertTrue(all(e["environment"] is None for e in events if e["source"] == "saved-decision"))

    def test_history_endpoint_authorization_validation_and_private_headers(self):
        route = "/api/studio/journal/history?slug=" + self.record["slug"]
        with patch.object(jr, "article_history") as query:
            for headers, expected in (({}, 401), ({"Cookie": "__session=other"}, 403)):
                with patch.object(studio_auth, "reviewer_identity", side_effect=PermissionError("Not authorized")):
                    for method in ("GET", "HEAD", "POST"):
                        self.assertEqual(self.request(route, method, headers=headers)[0], expected)
            query.assert_not_called()
        with patch.object(studio_auth, "reviewer_identity",
                          return_value=studio_auth.ReviewerIdentity("reviewer-1")):
            for method in ("GET", "HEAD"):
                status, body, headers = self.request(route, method)
                self.assertEqual(status, 200)
                self.assertIn("no-store", headers["Cache-Control"])
                if method == "GET":
                    self.assertEqual(json.loads(body)["events"], [])
                    self.assertIsNone(json.loads(body)["nextCursor"])
                else:
                    self.assertEqual(body, "")
            self.assertEqual(self.request(route, "POST")[0], 405)
            for suffix in ("&limit=0", "&limit=101", "&limit=bad", "&limit=",
                           "&cursor=not-a-cursor", "&cursor=W10", "&limit=1&limit=2"):
                self.assertEqual(self.request(route + suffix)[0], 400, suffix)
            self.assertEqual(self.request("/api/studio/journal/history?slug=absent-article")[0], 404)
            self.assertEqual(self.request("/api/studio/journal/history")[0], 400)
            self.approve()
            jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-2")
            page = jr.article_history(self.record["slug"], 1)
            self.assertIsNotNone(page["nextCursor"])
            other = next(iter(self.originals))
            self.assertEqual(self.request("/api/studio/journal/history?slug=" + other
                                          + "&cursor=" + page["nextCursor"])[0], 400)
        for route in ("/api/journal-release-status", "/assets/search-index.json", "/blog/"):
            status, body, _ = self.request(route)
            self.assertEqual(status, 200)
            for private in ("reviewerId", "occurredAt", "nextCursor", "approvalHistory", "reviewer-2"):
                self.assertNotIn(private, body)

    def test_history_retains_released_studio_version_while_revision_waits(self):
        self.approve()
        self.now_mock.return_value = self.due
        original_revision = self.record["revision"]
        self.record["revision"] = "pending-new-version"
        item = jr.review_items()[0]
        self.assertEqual(item["status"], "Needs review")
        saved = jr.article_history(self.record["slug"])
        self.assertEqual(saved["publishedVersion"]["revision"], original_revision)
        self.assertEqual(saved["events"][0]["revision"], original_revision)
        self.assertIsNone(saved["preStudioVersion"])
        jr.decide(self.record["slug"], "pending-new-version", "hold", "reviewer-2")
        saved = jr.article_history(self.record["slug"])
        self.assertEqual(saved["publishedVersion"]["revision"], original_revision)
        self.assertEqual([e["action"] for e in saved["events"]], ["hold", "approve"])

    def test_history_projects_due_metadata_without_materializing_or_unpacking(self):
        self.approve()
        slug = self.record["slug"]
        with patch.object(jr, "materialize", side_effect=AssertionError("History acquired publication lock")), \
             patch.object(jr, "unpack", side_effect=AssertionError("History unpacked article HTML")):
            self.assertIsNone(jr.article_history(slug)["publishedVersion"])
            self.now_mock.return_value = self.due
            self.assertEqual(jr.article_history(slug)["publishedVersion"],
                             {"revision": self.record["revision"], "date": self.record["date"]})
            original_slug, original = next(iter(self.originals.items()))
            self.assertEqual(jr.article_history(original_slug)["publishedVersion"],
                             {"revision": original["revision"], "date": original["date"]})
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_releases").fetchone()["n"], 0)
        # Public serving still persists the same approved, frozen release.
        self.assertEqual(jr.released()[0][slug]["revision"], self.record["revision"])

    def test_history_metadata_matches_materialization_across_versions(self):
        slug = self.record["slug"]
        self.assertTrue(self.owner_approval())
        self.assertEqual(jr.article_history(slug)["publishedVersion"]["revision"], self.record["revision"])
        # Re-approving the same version must not move its persisted release time.
        self.now_mock.return_value = self.due
        self.approve()
        self.record["revision"] = "replacement"
        self.record["html"] += "<p>Replacement snapshot</p>"
        self.now_mock.return_value += timedelta(seconds=1)
        self.approve()
        self.record["revision"] = "unapproved-edit"
        self.record["html"] += "<p>Not yet reviewed</p>"
        projected = jr.article_history(slug)["publishedVersion"]
        published = jr.released()[0][slug]
        self.assertEqual(projected, {key: published[key] for key in ("revision", "date")})
        self.assertEqual(projected["revision"], "replacement")
        jr.decide(slug, "unapproved-edit", "hold", "reviewer-2")
        self.assertEqual(jr.article_history(slug)["publishedVersion"], projected)
        self.assertNotIn("Not yet reviewed", jr.released()[0][slug]["html"])

    def test_history_readers_do_not_wait_for_decisions_or_scheduled_releases(self):
        from concurrent.futures import ThreadPoolExecutor
        slug = self.record["slug"]
        real_materialize = jr.materialize
        # Pause the actual writer after it holds the global transaction lock
        # and has made uncommitted release writes, not a stand-in Python lock.
        for work in ("decision", "scheduled"):
            with self.subTest(work=work):
                with jr.connect() as db:
                    db.execute("TRUNCATE journal_decisions,journal_releases,journal_review_audit")
                self.now_mock.return_value = self.due - timedelta(minutes=1)
                self.approve()
                self.now_mock.return_value = self.due
                entered, resume = threading.Event(), threading.Event()

                def paused_materialize(db, instant):
                    real_materialize(db, instant)
                    entered.set()
                    if not resume.wait(10):
                        raise TimeoutError("Publication test was not resumed")

                with ThreadPoolExecutor(max_workers=3) as pool, \
                     patch.object(jr, "materialize", side_effect=paused_materialize), \
                     patch.object(studio_auth, "reviewer_identity", return_value={"id":"reviewer-1","name":"Reviewer"}), \
                     patch.object(studio_auth, "reviewer_label", side_effect=lambda actor: actor):
                    writer = pool.submit(jr.decide, slug, self.record["revision"], "hold", "reviewer-2") \
                        if work == "decision" else pool.submit(jr.released)
                    try:
                        self.assertTrue(entered.wait(5), "Writer did not acquire publication lock")
                        # Both the first page and a subsequent page must finish
                        # before the writer commits or releases its advisory lock.
                        first = pool.submit(self.request,
                                            f"/api/studio/journal/history?slug={slug}&limit=1").result(timeout=3)
                        self.assertEqual(first[0], 200, first[1])
                        page = json.loads(first[1])
                        self.assertEqual(page["publishedVersion"]["revision"], self.record["revision"])
                        self.assertIn("no-store", first[2]["Cache-Control"])
                        # Add committed audit events on an independent connection
                        # to exercise an actual older-page cursor.
                        with jr.connect() as db:
                            db.execute("""
                                INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at)
                                VALUES (%s,%s,'approve','earlier-reviewer',%s)
                            """, (slug, self.record["revision"], self.due - timedelta(days=1)))
                        first = pool.submit(jr.article_history, slug, 1).result(timeout=3)
                        self.assertIsNotNone(first["nextCursor"])
                        older = pool.submit(jr.article_history, slug, 1, first["nextCursor"]).result(timeout=3)
                        self.assertEqual(older["events"][0]["reviewerId"], "earlier-reviewer")
                    finally:
                        resume.set()
                    writer.result(timeout=5)
                self.assertEqual(jr.article_history(slug)["publishedVersion"]["revision"], self.record["revision"])

    def test_history_snapshot_does_not_mix_uncommitted_or_later_decisions(self):
        self.approve()
        self.now_mock.return_value = self.due
        slug = self.record["slug"]
        real_metadata = jr.publication_metadata

        def metadata_then_hold(db, *args):
            metadata = real_metadata(db, *args)
            # A separate transaction commits after the history snapshot began.
            jr.decide(slug, self.record["revision"], "hold", "reviewer-2")
            return metadata

        with patch.object(jr, "publication_metadata", side_effect=metadata_then_hold):
            page = jr.article_history(slug)
        self.assertEqual([e["action"] for e in page["events"]], ["approve"])
        self.assertEqual(page["publishedVersion"]["revision"], self.record["revision"])
        self.assertEqual([e["action"] for e in jr.article_history(slug)["events"]], ["hold", "approve"])

    def test_legacy_saved_decision_is_not_invented_audit_or_environment(self):
        self.approve()
        with jr.connect() as db:
            db.execute("TRUNCATE journal_review_audit")
        event = jr.article_history(self.record["slug"])["events"][0]
        self.assertEqual(event["source"], "saved-decision")
        self.assertEqual(event["reviewerId"], "reviewer-1")
        self.assertEqual(event["occurredAt"], self.now_mock.return_value.isoformat())
        self.assertIsNone(event["environment"])
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_review_audit").fetchone()["n"], 0)
        self.now_mock.return_value += timedelta(seconds=1)
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-2")
            saved = jr.article_history(self.record["slug"])
        self.assertEqual(saved["events"][0]["environment"], "production")
        self.assertEqual(saved["recordEnvironment"], "production")
        with jr.connect() as db:
            db.execute("UPDATE journal_review_audit SET environment=NULL")
        self.assertIsNone(jr.article_history(self.record["slug"])["events"][0]["environment"])

    def test_production_studio_login_public_but_draft_bundles_protected(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            (build / "assets").mkdir()
            (build / ".vite").mkdir()
            (build / "index.html").write_text("<h1>Eternal Studio sign-in</h1>")
            (build / "assets/login.js").write_text("public sign-in only")
            (build / "assets/drafts.js").write_text("UNAPPROVED_PRIVATE_ARTICLE")
            (build / "assets/drafts.css").write_text(".studio{color:plum}")
            (build / ".vite/manifest.json").write_text(json.dumps({
                "index.html":{"file":"assets/login.js","isEntry":True,"dynamicImports":["drafts"]},
                "drafts":{"file":"assets/drafts.js","css":["assets/drafts.css"],"isDynamicEntry":True}}))
            with patch.object(studio_site, "BUILD", build):
                self.assertEqual(self.request("/studio/")[0], 200)
                self.assertEqual(self.request("/studio/sign-in")[0], 200)
                self.assertEqual(self.request("/studio/assets/login.js")[0], 200)
                status, body, headers = self.request("/studio/assets/drafts.css")
                self.assertEqual(status, 200)
                self.assertIn("text/css", headers["Content-Type"])
                for route in ("/studio/assets/drafts.js", "/studio/assets/%64rafts.js",
                              "/studio/assets/../assets/drafts.js"):
                    status, body, _ = self.request(route)
                    self.assertEqual(status, 401)
                    self.assertNotIn("UNAPPROVED_PRIVATE_ARTICLE", body)
                with patch.object(studio_auth, "reviewer", return_value="reviewer-1"):
                    self.assertIn("UNAPPROVED_PRIVATE_ARTICLE", self.request("/studio/assets/drafts.js")[1])

    def test_studio_session_requires_verified_reviewer(self):
        self.assertEqual(self.request("/api/studio/session")[0], 401)
        with patch.object(studio_auth, "reviewer_identity", side_effect=PermissionError("Not authorized")):
            self.assertEqual(self.request("/api/studio/session", headers={"Cookie":"__session=unauthorized"})[0], 403)
        with patch.object(studio_auth, "reviewer_identity", return_value={"id":"reviewer-1","name":"Reviewer"}):
            status, body, _ = self.request("/api/studio/session")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"verified": True})
            self.assertEqual(self.request("/api/studio/session", "POST", {})[0], 405)

    def test_discovery_uses_released_copy_not_pending_same_url_revision(self):
        document = """<html><section class="hero"><h1>Approved headline</h1>
        <p>Approved summary.</p></section><style>.hero{background-image:url('/api/journal-photo/abc')}</style></html>"""
        row = {"html":document,"date":"2026-10-10","revision":"approved-sha"}
        featured = '<div class="blog-featured" data-publish-date="2026-10-10"><a class="bf-img" href="/blog/a-story" style="background-image:url(pending.jpg)" aria-label="Pending headline"></a><div class="bf-body"><h2><a href="/blog/a-story">Pending headline</a></h2><p>Pending summary.</p></div></div>'
        source = '<a class="rc" data-publish-date="2026-10-10" href="/blog/a-story" data-featured="'+html.escape(featured,quote=True)+'"><h3 class="rc-title">Pending headline</h3><p class="rc-ex">Pending summary.</p></a>'
        archive = journal_discovery.archive(featured + source, {"a-story":row})
        self.assertNotIn("Pending", archive)
        self.assertNotIn("pending.jpg", archive)
        self.assertIn("Approved headline", archive)
        self.assertIn("/api/journal-photo/abc", archive)


class AuthTests(unittest.TestCase):
    def test_managed_production_keys_use_allowlisted_proxy_and_matching_issuer(self):
        import jwt
        studio_auth.verifier.cache_clear()
        try:
            with patch.object(jwt, "PyJWKClient") as client:
                issuer, _ = studio_auth.verifier("unused-production-key", "https://eternallifehospice.com")
                self.assertEqual(issuer, "https://clerk.eternallifehospice.com")
                self.assertEqual(client.call_args.args[0],
                                 "https://eternallifehospice.com/api/__clerk/.well-known/jwks.json")
                self.assertIn("User-Agent", client.call_args.kwargs["headers"])
                with self.assertRaises(PermissionError):
                    studio_auth.verifier("unused-production-key", "https://evil.example")
                self.assertEqual(client.call_count, 1)
        finally:
            studio_auth.verifier.cache_clear()

    def test_directory_labels_never_guess_signers_or_break_history(self):
        studio_auth._reviewer_label.cache_clear()
        with patch.object(studio_auth, "urlopen") as remote:
            result = Mock()
            result.read.return_value = json.dumps({"id": "user_actual", "first_name": "Actual",
                                                    "last_name": "Reviewer"}).encode()
            result.__enter__ = Mock(return_value=result)
            result.__exit__ = Mock(return_value=False)
            remote.return_value = result
            with patch.dict(os.environ, {"CLERK_SECRET_KEY": "test"}):
                self.assertEqual(studio_auth.reviewer_label("user_actual"), "Actual Reviewer")
                self.assertEqual(studio_auth.reviewer_label("unknown-id"), "unknown-id")
                remote.side_effect = OSError("Directory unavailable")
                self.assertEqual(studio_auth.reviewer_label("user_deleted"), "user_deleted")
        studio_auth._reviewer_label.cache_clear()

    def test_reviewer_requires_signed_active_verified_clerk_session(self):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        instant = datetime.now(timezone.utc)
        claims = {"iss":"https://test.clerk.accounts.dev","sub":"user_1","sid":"sess_1",
                  "azp":"https://eternallifehospice.com","iat":instant,"nbf":instant,
                  "exp":instant+timedelta(minutes=10)}
        token = jwt.encode(claims, key, algorithm="RS256")
        client = Mock()
        client.get_signing_key_from_jwt.return_value.key = key.public_key()
        def response(payload):
            result = Mock()
            result.read.return_value = json.dumps(payload).encode()
            result.__enter__ = Mock(return_value=result)
            result.__exit__ = Mock(return_value=False)
            return result
        session = {"status":"active","user_id":"user_1"}
        user = {"id": "user_1", "first_name": " Verified ", "last_name": "Reviewer",
                "email_addresses":[]}
        with patch.object(studio_auth, "verifier", return_value=(claims["iss"],client)), \
             patch.dict(os.environ, {"CLERK_PUBLISHABLE_KEY":"test","CLERK_SECRET_KEY":"test"}), \
             patch.object(studio_auth, "urlopen") as remote:
            headers = {"Cookie":"__session="+token}
            self.assertEqual(studio_auth.REVIEWER_EMAILS, {
                "aleksandra@eternallifehospice.com", "denise@eternallifehospice.com"})
            for address in ("ALEKSANDRA@eternallifehospice.com", "denise@eternallifehospice.com"):
                with self.subTest(reviewer=address):
                    user["email_addresses"] = [{"email_address":address,"verification":{"status":"verified"}}]
                    remote.side_effect = [response(session),response(user)]
                    self.assertEqual(studio_auth.reviewer(headers), "user_1")
                    remote.side_effect = [response(session), response(user)]
                    self.assertEqual(studio_auth.reviewer_identity(headers),
                                     studio_auth.ReviewerIdentity("user_1", "Verified Reviewer"))
                    for request_call in remote.call_args_list[-2:]:
                        request = request_call.args[0]
                        self.assertEqual(request.get_header("User-agent"), "Eternal-Studio/1.0")
                        self.assertEqual(request.get_header("Accept"), "application/json")
                    user["email_addresses"][0]["verification"]["status"] = "unverified"
                    remote.side_effect = [response(session),response(user)]
                    with self.assertRaises(PermissionError):
                        studio_auth.reviewer(headers)
            user["id"] = "user_mismatch"
            remote.side_effect = [response(session), response(user)]
            with self.assertRaises(PermissionError):
                studio_auth.reviewer_identity(headers)
            user["id"] = "user_1"
            user["email_addresses"] = [{"email_address":"other@example.org","verification":{"status":"verified"}},
                                       {"email_address":"denise@eternallifehospice.com","verification":{"status":"unverified"}}]
            remote.side_effect = [response(session),response(user)]
            with self.assertRaises(PermissionError):
                studio_auth.reviewer(headers)
            user["email_addresses"] = [{"email_address":"other@example.org","verification":{"status":"verified"}}]
            remote.side_effect = [response(session),response(user)]
            with self.assertRaises(PermissionError):
                studio_auth.reviewer(headers)
            session["status"] = "revoked"
            remote.side_effect = [response(session)]
            with self.assertRaises(PermissionError):
                studio_auth.reviewer(headers)
            bad = jwt.encode({**claims,"azp":"https://evil.example"},key,algorithm="RS256")
            with self.assertRaises(PermissionError):
                studio_auth.reviewer({"Cookie":"__session="+bad})
            expired = jwt.encode({**claims,"exp":instant-timedelta(minutes=1)},key,algorithm="RS256")
            with self.assertRaises(PermissionError):
                studio_auth.reviewer({"Cookie":"__session="+expired})
            with self.assertRaises(PermissionError):
                studio_auth.reviewer({"Cookie":"__session="+token[:-5]+"wrong"})


class MonitorTests(unittest.TestCase):
    def test_daily_schedule_tracks_dst_even_when_job_is_delayed(self):
        for day, hour in (("2026-03-08",13),("2026-11-01",14)):
            delayed = jr.release_at(day).astimezone(timezone.utc) + timedelta(hours=2)
            self.assertTrue(monitor.scheduled_today(f"45 {hour} * * *", delayed))
            self.assertFalse(monitor.scheduled_today(f"45 {27-hour} * * *", delayed))

    def test_held_drafts_do_not_trigger_discovery_checks_or_alerts(self):
        getter = Mock(side_effect=[
            (json.dumps({"timezone":"America/Los_Angeles","releaseTime":"06:30","expected":[]}), {}),
            ('<script type="module" src="/studio/assets/login.js"></script>', {}),
        ])
        self.assertEqual(monitor.check("https://test", getter), ("healthy",[]))
        self.assertEqual(getter.call_count, 2)

    def test_missing_studio_is_detected_even_without_approved_posts(self):
        getter = Mock(side_effect=[
            (json.dumps({"timezone":"America/Los_Angeles","releaseTime":"06:30","expected":[]}), {}),
            HTTPError("https://test/studio/", 503, "Studio build unavailable", {}, None),
        ])
        with self.assertRaises(HTTPError):
            monitor.check("https://test", getter)

    def test_missing_studio_sends_monitoring_failure_email_not_publication_failure(self):
        with patch.object(monitor, "check", side_effect=HTTPError(
                "https://test/studio/", 503, "Studio build unavailable", {}, None)), \
             patch.object(monitor, "notify") as notify, \
             patch.object(monitor.sys, "argv", ["monitor", "--site", "https://test"]):
            self.assertEqual(monitor.main(), 1)
            self.assertTrue(notify.call_args.kwargs["monitoring_unavailable"])

    def test_studio_error_document_is_not_a_healthy_review_app(self):
        getter = Mock(side_effect=[
            (json.dumps({"timezone":"America/Los_Angeles","releaseTime":"06:30","expected":[]}), {}),
            ('{"message":"Studio build unavailable"}', {}),
        ])
        with self.assertRaisesRegex(ValueError, "Studio"):
            monitor.check("https://test", getter)

    def test_missed_version_email_and_rejected_email_are_explicit(self):
        payload = {"timezone":"America/Los_Angeles","releaseTime":"06:30",
                   "expected":[{"slug":"approved-story","date":"2026-11-01","revision":"expected","available":False}]}
        def getter(url):
            if url.endswith("release-status"):
                return json.dumps(payload), {}
            if url.endswith("/studio/"):
                return '<script type="module" src="/studio/assets/login.js"></script>', {}
            if url.endswith("search-index.json"):
                return "[]", {}
            return "<h1>Wrong version</h1>", {"X-Journal-Revision":"wrong"}
        state, failures = monitor.check("https://test", getter)
        self.assertEqual(state, "missed")
        self.assertIn("version does not match approval", failures[0])
        with patch.dict(os.environ, {"BREVO_API":"test-only"}), patch.object(monitor.email, "send_alert") as send:
            monitor.notify(failures)
            message = send.call_args.args[1]
            self.assertEqual(message["to"][0]["email"], "denise@eternallifehospice.com")
            self.assertIn("held or unapproved", message["textContent"].lower())
            send.side_effect = OSError("test rejection")
            with self.assertRaises(OSError):
                monitor.notify(failures)


if __name__ == "__main__":
    unittest.main(verbosity=2)
