#!/usr/bin/env python3
"""Test-only real intake handler, disposable local PostgreSQL and fake providers.

Started by intake-browser-fixture.mjs; stdin EOF tears everything down. No
project database, credentials, production switches or live mail are used.
"""
import getpass
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch
import uuid


def main():
    if os.environ.get("REPLIT_DEPLOYMENT") == "1":
        raise RuntimeError("Never run browser fixtures in production")
    # Scrub credentials before importing application modules. Keep only runtime
    # paths; even an inherited DATABASE_URL/PGOPTIONS cannot select a real DB.
    runtime = {key: os.environ[key] for key in
               ("PATH", "HOME", "LANG", "LD_LIBRARY_PATH", "PYTHONPATH")
               if key in os.environ}
    os.environ.clear()
    os.environ.update(runtime)

    import psycopg
    from psycopg.rows import dict_row

    with tempfile.TemporaryDirectory(prefix="elh-browser-pg-") as temp:
        base = Path(temp)
        data = base / "data"
        started = False

        def pg(command):
            subprocess.run(command, check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            pg(["initdb", "-D", str(data), "-A", "trust", "--no-locale", "--encoding=UTF8"])
            pg(["pg_ctl", "-D", str(data), "-l", str(base / "postgres.log"),
                "-o", f"-k {base} -h '' -p 5432", "-w", "start"])
            started = True
            dsn = f"host={base} port=5432 dbname=postgres user={getpass.getuser()}"
            schema = "browser_" + uuid.uuid4().hex
            with psycopg.connect(dsn) as db:
                db.execute(f'CREATE SCHEMA "{schema}"')
            os.environ.update(
                DATABASE_URL=dsn, PGOPTIONS=f"-c search_path={schema}",
                SESSION_SECRET="synthetic-browser-signing-key-not-a-live-secret",
                TURNSTILE_SITE_KEY="synthetic-site-key",
                TURNSTILE_SECRET_KEY="synthetic-provider-secret")

            import devserver
            import form_antispam as guard
            import form_intake

            state = {"mail": 0, "provider": 0, "blocked_network": 0}

            class SyntheticMailer:
                def send(self, payload):
                    # Both clinical-team delivery and visitor acknowledgment
                    # remain synthetic; exercise the real submission processor.
                    state["mail"] += 1
                    return "synthetic-mail-id"

            def submit(fields, files):
                return form_intake.process_submission(fields, files, mailer=SyntheticMailer(),
                    acknowledgement_mailer=SyntheticMailer())

            def verify(request, **kwargs):
                if request.full_url != guard.VERIFY_URL:
                    raise AssertionError("Unexpected verification transport")
                payload = json.loads(request.data)
                if payload != {"secret": "synthetic-provider-secret",
                               "response": "synthetic-provider-token"}:
                    raise AssertionError("Unexpected synthetic provider payload")
                state["provider"] += 1
                return io.BytesIO(json.dumps({
                    "success": True, "hostname": "127.0.0.1", "action": "intake"
                }).encode())

            real_connect = socket.socket.connect

            def connect(sock, address):
                if sock.family != socket.AF_UNIX:
                    state["blocked_network"] += 1
                    raise AssertionError("External network forbidden in browser fixture")
                return real_connect(sock, address)

            class Handler(devserver.PrettyURLHandler):
                def log_message(self, *args):
                    pass

                def do_GET(self):
                    if self.path == "/__fixture__/state":
                        with guard.connect() as db:
                            rows = db.execute(
                                "SELECT count(*) AS n FROM intake_abuse_guard").fetchone()["n"]
                        self._send_json(200, {**state, "guard_rows": rows})
                    elif self.path.startswith("/api/form-security?"):
                        super().do_GET()
                    else:
                        self._send_json(500, {"error": "unexpected_fixture_route"})

                def do_POST(self):
                    if self.path == "/api/form-submit":
                        super().do_POST()
                    else:
                        self._send_json(500, {"error": "unexpected_fixture_route"})

            # No bypass of issue/reserve, origin checks, token age/replay,
            # validation or PostgreSQL. Only outbound service boundaries change.
            with patch.object(devserver, "process_submission", submit), \
                    patch.object(guard, "urlopen", verify), \
                    patch.object(socket.socket, "connect", connect):
                guard.initialize()
                server = devserver.QuietHTTPServer(("127.0.0.1", 0), Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                print(json.dumps({"port": server.server_port}), flush=True)
                try:
                    # Parent closes stdin on success, failure or early exit.
                    sys.stdin.read()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()
            with psycopg.connect(dsn) as db:
                db.execute(f'DROP SCHEMA "{schema}" CASCADE')
        finally:
            if started:
                pg(["pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop"])


if __name__ == "__main__":
    main()
