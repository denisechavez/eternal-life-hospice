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
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.candidate_patch.stop)

    def approve(self):
        jr.decide(self.record["slug"], self.record["revision"], "approve", "reviewer-1")

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
        with patch.object(studio_auth, "reviewer", return_value="reviewer-1"):
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
            with patch.object(studio_auth, "reviewer", return_value=reviewer), \
                 patch.object(studio_auth, "reviewer_label", side_effect=lambda identity: identity), \
                 patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "0"}):
                status, body, headers = self.request("/api/studio/journal", "POST", data,
                                                     {"Origin": "https://eternallifehospice.com"})
            self.assertEqual(status, 200, body)
            self.assertIn("no-store", headers["Cache-Control"])
        item = json.loads(body)["items"][0]
        events = item["approvalHistory"]["events"]
        self.assertEqual([event["reviewerId"] for event in events],
                         ["user_Denise", "user_Denise", "user_Aleksandra"])
        self.assertEqual([event["action"] for event in events], ["approve", "hold", "approve"])
        self.assertEqual({event["revision"] for event in events}, {self.record["revision"]})
        self.assertEqual({event["environment"] for event in events}, {"workspace"})
        self.assertEqual(events[0]["occurredAt"], self.now_mock.return_value.isoformat())
        self.assertEqual(item["approvalHistory"]["recordEnvironment"], "workspace")
        self.assertEqual(item["status"], "Approved")
        self.assertIsNone(item["approvalHistory"]["publishedVersion"])
        self.assertIsNone(item["approvalHistory"]["preStudioVersion"])
        with patch.object(studio_auth, "reviewer", side_effect=PermissionError("Not authorized")):
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

    def test_history_keeps_pre_studio_original_separate_from_pending_revision(self):
        slug = next(iter(self.originals))
        original = self.originals[slug]
        self.record.update(slug=slug, revision="changed-draft")
        item = jr.review_items()[0]
        saved = item["approvalHistory"]
        self.assertEqual(item["status"], "Needs review")
        self.assertTrue(item["hasPublishedVersion"])
        self.assertEqual(saved["publishedVersion"]["revision"], original["revision"])
        self.assertEqual(saved["preStudioVersion"], {"revision": original["revision"], "date": original["date"]})
        self.assertEqual(saved["events"], [])
        jr.decide(slug, "changed-draft", "hold", "reviewer-2")
        item = jr.review_items()[0]
        self.assertTrue(item["held"])
        self.assertEqual(item["approvalHistory"]["publishedVersion"]["revision"], original["revision"])
        self.assertEqual(item["approvalHistory"]["events"][0]["revision"], "changed-draft")
        self.assertEqual(jr.released()[0][slug]["html"], jr.unpack(original))

    def test_history_retains_released_studio_version_while_revision_waits(self):
        self.approve()
        self.now_mock.return_value = self.due
        original_revision = self.record["revision"]
        self.record["revision"] = "pending-new-version"
        item = jr.review_items()[0]
        self.assertEqual(item["status"], "Needs review")
        self.assertEqual(item["approvalHistory"]["publishedVersion"]["revision"], original_revision)
        self.assertEqual(item["approvalHistory"]["events"][0]["revision"], original_revision)
        self.assertIsNone(item["approvalHistory"]["preStudioVersion"])
        jr.decide(self.record["slug"], "pending-new-version", "hold", "reviewer-2")
        item = jr.review_items()[0]
        self.assertEqual(item["approvalHistory"]["publishedVersion"]["revision"], original_revision)
        self.assertEqual([e["action"] for e in item["approvalHistory"]["events"]], ["hold", "approve"])

    def test_legacy_saved_decision_is_not_invented_audit_or_environment(self):
        self.approve()
        with jr.connect() as db:
            db.execute("TRUNCATE journal_review_audit")
        item = jr.review_items()[0]
        event = item["approvalHistory"]["events"][0]
        self.assertEqual(event["source"], "saved-decision")
        self.assertEqual(event["reviewerId"], "reviewer-1")
        self.assertEqual(event["occurredAt"], self.now_mock.return_value.isoformat())
        self.assertIsNone(event["environment"])
        with jr.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) AS n FROM journal_review_audit").fetchone()["n"], 0)
        self.now_mock.return_value += timedelta(seconds=1)
        with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1"}):
            jr.decide(self.record["slug"], self.record["revision"], "hold", "reviewer-2")
            item = jr.review_items()[0]
        self.assertEqual(item["approvalHistory"]["events"][0]["environment"], "production")
        self.assertEqual(item["approvalHistory"]["recordEnvironment"], "production")
        with jr.connect() as db:
            db.execute("UPDATE journal_review_audit SET environment=NULL")
        self.assertIsNone(jr.review_items()[0]["approvalHistory"]["events"][0]["environment"])

    def test_production_studio_login_public_but_draft_bundles_protected(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            (build / "assets").mkdir()
            (build / ".vite").mkdir()
            (build / "index.html").write_text("<h1>Eternal Studio sign-in</h1>")
            (build / "assets/login.js").write_text("public sign-in only")
            (build / "assets/drafts.js").write_text("UNAPPROVED_PRIVATE_ARTICLE")
            (build / ".vite/manifest.json").write_text(json.dumps({
                "index.html":{"file":"assets/login.js","isEntry":True,"dynamicImports":["drafts"]},
                "drafts":{"file":"assets/drafts.js","isDynamicEntry":True}}))
            with patch.object(studio_site, "BUILD", build):
                self.assertEqual(self.request("/studio/")[0], 200)
                self.assertEqual(self.request("/studio/sign-in")[0], 200)
                self.assertEqual(self.request("/studio/assets/login.js")[0], 200)
                for route in ("/studio/assets/drafts.js", "/studio/assets/%64rafts.js",
                              "/studio/assets/../assets/drafts.js"):
                    status, body, _ = self.request(route)
                    self.assertEqual(status, 401)
                    self.assertNotIn("UNAPPROVED_PRIVATE_ARTICLE", body)
                with patch.object(studio_auth, "reviewer", return_value="reviewer-1"):
                    self.assertIn("UNAPPROVED_PRIVATE_ARTICLE", self.request("/studio/assets/drafts.js")[1])

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
        user = {"email_addresses":[]}
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
                    for request_call in remote.call_args_list[-2:]:
                        request = request_call.args[0]
                        self.assertEqual(request.get_header("User-agent"), "Eternal-Studio/1.0")
                        self.assertEqual(request.get_header("Accept"), "application/json")
                    user["email_addresses"][0]["verification"]["status"] = "unverified"
                    remote.side_effect = [response(session),response(user)]
                    with self.assertRaises(PermissionError):
                        studio_auth.reviewer(headers)
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
