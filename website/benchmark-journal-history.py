#!/usr/bin/env python3
"""Opt-in synthetic Journal benchmark. Never connects to DATABASE_URL."""
import argparse
import base64
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
import journal_release as jr
import studio_auth


@contextmanager
def disposable_postgres():
    """Use a private Unix socket, no TCP listener or existing database."""
    for binary in ("initdb", "pg_ctl"):
        if not shutil.which(binary):
            raise RuntimeError(f"{binary} is required on PATH")
    with tempfile.TemporaryDirectory(prefix="journal-bench-") as directory:
        root = Path(directory)
        data = root / "data"
        subprocess.run(["initdb", "-D", str(data), "-U", "benchmark", "-A", "trust",
                        "--no-locale", "--encoding=UTF8"], check=True, capture_output=True)
        subprocess.run(["pg_ctl", "-D", str(data), "-l", str(root / "postgres.log"),
                        "-o", f"-k {root} -c listen_addresses='' -c max_connections=10",
                        "-w", "start"], check=True, capture_output=True)
        try:
            def connect():
                return psycopg.connect(host=str(root), dbname="postgres", user="benchmark",
                                       connect_timeout=5, row_factory=dict_row)
            yield connect
        finally:
            subprocess.run(["pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop"],
                           check=True, capture_output=True)


class TracedConnection:
    """Record the production SQL unchanged, without EXPLAIN in timed samples."""
    def __init__(self, connection, statements):
        self.connection = connection
        self.statements = statements

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def execute(self, query, params=None):
        self.statements.append((query, params))
        return self.connection.execute(query, params)


def measure(call, samples):
    call()  # Warm caches and any publication maintenance before measuring.
    elapsed = []
    for _ in range(samples):
        start = time.perf_counter()
        result = call()
        encoded = json.dumps(result, ensure_ascii=False).encode("utf-8")
        elapsed.append((time.perf_counter() - start) * 1000)
    return result, {
        "samples_ms": elapsed,
        "median_ms": statistics.median(elapsed),
        "p95_ms": sorted(elapsed)[max(0, (95 * len(elapsed) + 99) // 100 - 1)],
        "response_bytes": len(encoded),
    }


def plan_nodes(node):
    yield node
    for child in node.get("Plans", []):
        yield from plan_nodes(child)


def explain(connect, statements):
    plans = []
    with connect() as db:
        for query, params in statements:
            if not query.lstrip().upper().startswith("SELECT"):
                raise AssertionError("Benchmark only explains read queries")
            result = db.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query,
                                params).fetchone()["QUERY PLAN"][0]
            plans.append({"sql": query.strip(), "parameters": params, **result})
    return plans


def seed_current(connect, articles, document):
    with connect() as db:
        db.execute("""
            INSERT INTO journal_decisions
                (slug,revision,release_date,document,state,reviewer,decided_at)
            SELECT 'bench-article-' || a,'current',DATE '2100-01-01',%s,
                CASE WHEN a%%2=0 THEN 'approved' ELSE 'held' END,
                'synthetic-reviewer',TIMESTAMPTZ '2026-01-01 UTC'
            FROM generate_series(1,%s) a
        """, (document, articles))


def seed_history(connect, args, document):
    with connect() as db:
        # A hot article has ten times the revision depth of the rest.
        db.execute("""
            INSERT INTO journal_decisions
                (slug,revision,release_date,document,state,reviewer,decided_at)
            SELECT 'bench-article-' || a,'old-' || lpad(r::text,6,'0'),
                DATE '2100-01-01',%s,
                CASE WHEN r%%2=0 THEN 'approved' ELSE 'held' END,
                'synthetic-reviewer',
                TIMESTAMPTZ '2025-01-01 UTC' + r * INTERVAL '1 second'
            FROM generate_series(1,%s) a
            CROSS JOIN LATERAL generate_series(1,CASE WHEN a=1 THEN %s ELSE %s END) r
        """, (document, args.articles, args.revisions * 10, args.revisions))
        # Every fifth revision is a legacy saved state with no audit counterpart.
        # Repeated decisions share timestamps, exercising the id tie-breaker.
        db.execute("""
            INSERT INTO journal_review_audit
                (slug,revision,action,reviewer,occurred_at,environment)
            SELECT d.slug,d.revision,
                CASE WHEN n%%2=0 THEN 'approve' ELSE 'hold' END,d.reviewer,
                d.decided_at,CASE WHEN n%%3=0 THEN NULL ELSE 'workspace' END
            FROM journal_decisions d
            CROSS JOIN generate_series(1,%s) n
            WHERE d.revision='current'
                OR substring(d.revision FROM 5)::int %% 5 <> 0
        """, (args.actions,))
    # Collect real planner statistics; never disable sequential scans or force indexes.
    with connect() as db:
        db.autocommit = True
        for table in ("journal_decisions", "journal_review_audit", "journal_releases"):
            db.execute("VACUUM (ANALYZE) " + table)


def deep_cursor(connect, slug, fraction):
    """Fixture setup only: OFFSET locates a real boundary outside timed queries."""
    with connect() as db:
        total = db.execute("SELECT count(*) AS n FROM journal_review_audit WHERE slug=%s",
                           (slug,)).fetchone()["n"]
        offset = int(total * fraction)
        row = db.execute("""
            SELECT id,revision,occurred_at FROM journal_review_audit
            WHERE slug=%s ORDER BY occurred_at DESC,id DESC OFFSET %s LIMIT 1
        """, (slug, offset)).fetchone()
    cursor = base64.urlsafe_b64encode(json.dumps({
        "slug": slug, "id": str(row["id"]), "revision": row["revision"],
        "at": row["occurred_at"].isoformat(),
    }).encode()).decode().rstrip("=")
    return cursor, offset


def run(args):
    document = "<h1>Synthetic benchmark article</h1><p>" + "fixture " * 1024 + "</p>"
    candidates = {
        f"bench-article-{n}": {"slug": f"bench-article-{n}", "revision": "current",
                             "date": "2100-01-01", "title": f"Synthetic article {n}",
                             "html": document}
        for n in range(1, args.articles + 1)
    }
    report = {"synthetic_only": True, "configuration": vars(args).copy(),
              "failures": [], "history": {}}
    failures = report["failures"]
    with disposable_postgres() as connect, ExitStack() as stack:
        stack.enter_context(patch.object(jr, "connect", connect))
        stack.enter_context(patch.object(jr, "candidates", return_value=candidates))
        stack.enter_context(patch.object(jr, "history", return_value={}))
        stack.enter_context(patch.object(jr, "now", return_value=datetime(2026, 10, 15, tzinfo=timezone.utc)))
        # Identity-provider latency and real directory data are intentionally excluded.
        stack.enter_context(patch.object(studio_auth, "reviewer_label", side_effect=lambda actor: actor))
        jr.initialize()
        seed_current(connect, args.articles, document)
        baseline, report["queue_before_history"] = measure(jr.review_items, args.samples)
        seed_history(connect, args, document)
        with connect() as db:
            report["postgres_version"] = db.execute("SHOW server_version").fetchone()["server_version"]
            report["rows"] = {
                table: db.execute("SELECT count(*) AS n FROM " + table).fetchone()["n"]
                for table in ("journal_decisions", "journal_review_audit")
            }
        queue, report["queue_after_history"] = measure(jr.review_items, args.samples)
        if queue != baseline:
            failures.append("Queue content/size changed solely because old history was added")
        if len(queue) != args.articles or any("approvalHistory" in item for item in queue):
            failures.append("Queue is missing articles or embeds audit history")
        queue_statements = []
        with patch.object(jr, "connect", side_effect=lambda: TracedConnection(connect(), queue_statements)):
            jr.review_items()
        report["queue_plans"] = explain(connect, queue_statements)
        if any("journal_review_audit" in sql for sql, _ in queue_statements):
            failures.append("Queue queries the audit log")
        slug = "bench-article-1"
        cursor, skipped = deep_cursor(connect, slug, 0.9)
        report["deep_audit_offset"] = skipped
        for name, boundary in (("early", None), ("deep", cursor)):
            call = lambda: jr.article_history(slug, args.page_size, boundary)
            page, stats = measure(call, args.samples)
            statements = []
            with patch.object(jr, "connect", side_effect=lambda: TracedConnection(connect(), statements)):
                call()
            stats["plans"] = explain(connect, statements)
            stats["events"] = len(page["events"])
            report["history"][name] = stats
            if len(page["events"]) != args.page_size or not page["nextCursor"]:
                failures.append(f"{name}: page is not bounded/full or lacks its next cursor")
            if stats["response_bytes"] > args.page_size * 1024 + 2048:
                failures.append(f"{name}: history payload exceeds the per-page byte budget")
            if any("fixture " in json.dumps(event) for event in page["events"]):
                failures.append(f"{name}: history contains document bytes")
            for marker, index in (
                ("'audit' AS source", "journal_audit_article_page"),
                ("'saved-decision' AS source", "journal_audit_saved_decision"),
            ):
                matching = [p for p in stats["plans"] if marker in p["sql"]]
                if not matching or not all(
                    any(n.get("Index Name") == index for n in plan_nodes(p["Plan"]))
                    for p in matching
                ):
                    failures.append(f"{name}: actual query did not use {index}")
                for plan in matching:
                    if "OFFSET" in plan["sql"].upper() or plan["parameters"][-1] != args.page_size + 1:
                        failures.append(f"{name}: history query lost its bounded keyset limit")
                    if marker == "'audit' AS source":
                        nodes = list(plan_nodes(plan["Plan"]))
                        if any(n["Node Type"] in ("Sort", "Seq Scan") for n in nodes):
                            failures.append(f"{name}: audit page sorts or scans the whole log")
                        if boundary and not any(
                            n.get("Index Name") == index and "occurred_at" in n.get("Index Cond", "")
                            and "id" in n.get("Index Cond", "") for n in nodes
                        ):
                            failures.append(f"{name}: cursor boundary is not an index condition")
            if args.max_history_ms and stats["p95_ms"] > args.max_history_ms:
                failures.append(f"{name}: history p95 exceeds {args.max_history_ms} ms")
        if args.max_queue_ms and report["queue_after_history"]["p95_ms"] > args.max_queue_ms:
            failures.append(f"Queue p95 exceeds {args.max_queue_ms} ms")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Required explicit opt-in")
    parser.add_argument("--articles", type=int, default=500)
    parser.add_argument("--revisions", type=int, default=40, help="Old revisions per article; hot article gets 10x")
    parser.add_argument("--actions", type=int, default=25, help="Repeated actions per audited revision")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--max-history-ms", type=float, help="Optional environment-specific p95 budget")
    parser.add_argument("--max-queue-ms", type=float, help="Optional environment-specific p95 budget")
    parser.add_argument("--output", default="generated-artifacts/journal-history-benchmark.json")
    args = parser.parse_args()
    if not args.run:
        parser.error("Pass --run to start a disposable PostgreSQL benchmark")
    if (args.articles < 2 or args.revisions < 5 or args.actions < 2 or args.samples < 1
            or not 1 <= args.page_size <= 100):
        parser.error("Need articles>=2, revisions>=5, actions>=2, samples>=1, page-size=1..100")
    for budget in (args.max_history_ms, args.max_queue_ms):
        if budget is not None and not 0 < budget < float("inf"):
            parser.error("Timing budgets must be finite positive milliseconds")
    report = run(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"Synthetic rows: {report['rows']}")
    for name in ("queue_before_history", "queue_after_history"):
        stats = report[name]
        print(f"{name}: {stats['response_bytes']} bytes; p95 {stats['p95_ms']:.2f} ms")
    for name, stats in report["history"].items():
        print(f"history {name}: {stats['response_bytes']} bytes; p95 {stats['p95_ms']:.2f} ms")
    print(f"Full query plans and measurements: {output}")
    if report["failures"]:
        raise SystemExit("\n".join(report["failures"]))
    print("PASS: bounded payloads and required indexes; no default latency threshold")


if __name__ == "__main__":
    main()
