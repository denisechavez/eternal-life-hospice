#!/usr/bin/env python3
"""Startup fault tests on a disposable local PostgreSQL, never a project DB.

Run: python3 website/test-startup-storage.py
Requires the project's PostgreSQL binaries and psycopg. Every test gets a new
schema; the cluster has no TCP listener and is removed after the suite.
"""
import getpass
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

import psycopg
from psycopg.rows import dict_row

import journal_release as journal

ROOT = Path(__file__).resolve().parent.parent
MIGRATE = ROOT / "website/migrate-journal.py"
spec = importlib.util.spec_from_file_location("startup_migration", MIGRATE)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class StartupStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="elh-startup-")
        cls.base = Path(cls.temp.name)
        cls.data = cls.base / "data"
        # No existing DATABASE_URL, credentials, project schemas or production
        # services are used by the cluster or the child migration processes.
        cls.env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PG", "DATABASE_", "REPLIT_DEPLOYMENT"))}
        for command in (
            ["initdb", "-D", str(cls.data), "-A", "trust", "--no-locale", "--encoding=UTF8"],
            ["pg_ctl", "-D", str(cls.data), "-l", str(cls.base / "postgres.log"),
             "-o", f"-k {cls.base} -h '' -p 5432", "-w", "start"],
        ):
            result = subprocess.run(command, env=cls.env, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=20)
            if result.returncode:
                cls.temp.cleanup()
                raise RuntimeError("Disposable PostgreSQL setup failed")
        cls.dsn = f"host={cls.base} port=5432 dbname=postgres user={getpass.getuser()}"

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["pg_ctl", "-D", str(cls.data), "-m", "immediate", "-w", "stop"],
                       env=cls.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10, check=True)
        cls.temp.cleanup()

    def setUp(self):
        self.schema = "startup_" + uuid.uuid4().hex
        with psycopg.connect(self.dsn) as db:
            db.execute(f'CREATE SCHEMA "{self.schema}"')
        self.child_env = dict(self.env, DATABASE_URL=self.dsn,
                              PGOPTIONS=f"-c search_path={self.schema}",
                              REPLIT_DEPLOYMENT="1")
        self.environment = patch.dict(os.environ, self.child_env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def tearDown(self):
        with psycopg.connect(self.dsn) as db:
            db.execute(f'DROP SCHEMA "{self.schema}" CASCADE')

    def db(self):
        return psycopg.connect(self.dsn, options=f"-c search_path={self.schema}",
                              row_factory=dict_row)

    def migrate(self):
        return subprocess.run([sys.executable, str(MIGRATE)], cwd=ROOT,
                              env=self.child_env, capture_output=True, text=True, timeout=29)

    def assert_failed(self, result, stage):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(stage, result.stdout + result.stderr)
        self.assertNotIn(self.dsn, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def counts(self):
        with self.db() as db:
            return tuple(db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
                         for table in ("journal_decisions", "journal_review_audit",
                                       "journal_releases", "journal_photos"))

    def test_unavailable_database_refuses_web_start_without_secrets(self):
        # A private, nonexistent Unix socket is deterministic and cannot reach
        # any real server. Include a canary password to check log redaction.
        self.child_env["DATABASE_URL"] = (
            f"host={self.base}/missing dbname=postgres user=postgres password=CANARY_SECRET")
        started = time.monotonic()
        result = subprocess.run(["bash", "website/start-published-site.sh"], cwd=ROOT,
                                env=self.child_env, capture_output=True, text=True, timeout=10)
        self.assert_failed(result, "journal_schema")
        self.assertNotIn("CANARY_SECRET", result.stdout + result.stderr)
        self.assertIn("refusing to start website", result.stderr)
        self.assertLess(time.monotonic() - started, 8)

    def test_unresponsive_connection_handshake_is_bounded(self):
        # A socket that accepts but never speaks PostgreSQL exercises the
        # connection deadline, rather than only an immediate connection refusal.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            stop = threading.Event()

            def stall():
                with listener.accept()[0]:
                    stop.wait(12)

            thread = threading.Thread(target=stall, daemon=True)
            thread.start()
            self.child_env["DATABASE_URL"] = (
                f"host=127.0.0.1 port={listener.getsockname()[1]} "
                "dbname=postgres user=postgres password=CANARY_SECRET sslmode=disable")
            started = time.monotonic()
            try:
                result = self.migrate()
                self.assert_failed(result, "stage=journal_schema")
                self.assertNotIn("CANARY_SECRET", result.stdout + result.stderr)
                self.assertLess(time.monotonic() - started, 9)
            finally:
                stop.set()
                thread.join(timeout=2)

    def test_concurrent_fresh_startups_are_idempotent(self):
        processes = [subprocess.Popen([sys.executable, str(MIGRATE)], cwd=ROOT,
                                     env=self.child_env, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            for process in processes:
                out, err = process.communicate(timeout=29)
                self.assertEqual(process.returncode, 0, out + err)
            before = self.counts()
            self.assertGreater(before[0], 0)
            self.assertEqual(before[0], before[1])
            result = self.migrate()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.counts(), before)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_schema_advisory_contention_times_out_then_recovers(self):
        with self.db() as blocker:
            blocker.execute("SELECT pg_advisory_xact_lock(630631)")
            started = time.monotonic()
            result = self.migrate()
            self.assert_failed(result, "stage=journal_schema sqlstate=55P03")
            self.assertLess(time.monotonic() - started, 7)
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_approval_lock_timeout_preserves_saved_decisions(self):
        result = self.migrate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = self.counts()
        with self.db() as blocker:
            blocker.execute("SELECT pg_advisory_xact_lock(630630)")
            result = self.migrate()
            self.assert_failed(result, "stage=owner_approval sqlstate=55P03")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(self.counts(), before)

    def test_intake_schema_wait_fails_closed(self):
        self.assertEqual(self.migrate().returncode, 0)
        with self.db() as blocker:
            blocker.execute("LOCK intake_abuse_guard IN ACCESS EXCLUSIVE MODE")
            result = self.migrate()
            self.assert_failed(result, "stage=intake_security_schema sqlstate=55P03")
        self.assertEqual(self.migrate().returncode, 0)

    def test_statement_timeout_rolls_back_whole_approval_batch(self):
        import journal_owner_approval as owner
        journal.initialize()
        with self.db() as db:
            db.execute("""CREATE FUNCTION stall_audit() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN PERFORM pg_sleep(20); RETURN NEW; END $$;
                CREATE TRIGGER slow_audit BEFORE INSERT ON journal_review_audit
                FOR EACH ROW EXECUTE FUNCTION stall_audit()""")
        started = time.monotonic()
        result = self.migrate()
        self.assert_failed(result, "stage=owner_approval sqlstate=57014")
        self.assertLess(time.monotonic() - started, 13)
        self.assertEqual(self.counts(), (0, 0, 0, 0))
        with self.db() as db:
            db.execute("DROP TRIGGER slow_audit ON journal_review_audit")
        owner.apply_all()
        before = self.counts()
        self.assertGreater(before[0], 0)
        owner.apply_all()
        self.assertEqual(self.counts(), before)

    def test_later_studio_hold_is_not_overwritten_on_retry(self):
        self.assertEqual(self.migrate().returncode, 0)
        with self.db() as db:
            record = db.execute(
                "SELECT slug, revision FROM journal_decisions LIMIT 1").fetchone()
        journal.decide(record["slug"], record["revision"], "hold", "isolated-test-reviewer")
        before = self.counts()
        self.assertEqual(self.migrate().returncode, 0)
        self.assertEqual(self.counts(), before)
        with self.db() as db:
            saved = db.execute(
                "SELECT state, reviewer FROM journal_decisions WHERE slug=%s AND revision=%s",
                (record["slug"], record["revision"])).fetchone()
        self.assertEqual(saved, {"state": "held", "reviewer": "isolated-test-reviewer"})

    def test_wall_deadline_kills_worker_and_releases_transaction(self):
        # Inject a blocking import into ONLY this test's child interpreter.
        # The real supervisor must kill/reap it, not merely cancel a future.
        hook = self.base / "hook"
        hook.mkdir(exist_ok=True)
        (hook / "sitecustomize.py").write_text("""
import os, sys, time
if sys.argv[1:] == ["--worker"]:
    import psycopg
    db = psycopg.connect(os.environ["DATABASE_URL"])
    db.execute("CREATE TABLE must_rollback (id integer)")
    db.execute("SELECT pg_advisory_xact_lock(630630)")
    open(os.environ["WORKER_STARTED"], "w").write(str(os.getpid()))
    time.sleep(60)
""")
        marker = self.base / "worker-started"
        with patch.dict(os.environ, {"PYTHONPATH": str(hook), "WORKER_STARTED": str(marker)}), \
                patch.object(migration, "STARTUP_SECONDS", 2):
            started = time.monotonic()
            self.assertEqual(migration.main(), 1)
            self.assertLess(time.monotonic() - started, 5)
        self.assertTrue(marker.exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)
        with self.db() as db:
            self.assertTrue(db.execute(
                "SELECT pg_try_advisory_xact_lock(630630) AS ok").fetchone()["ok"])
            self.assertIsNone(db.execute(
                "SELECT to_regclass('must_rollback') AS t").fetchone()["t"])


if __name__ == "__main__":
    unittest.main()
