#!/usr/bin/env python3
"""Bounded, fail-closed storage setup before an approved publication.

There is deliberately no degraded-startup mode: intake protection and Journal
approval storage must both be ready before the web process is launched.
"""
import subprocess
import sys
import time
from pathlib import Path

STARTUP_SECONDS = 25


def worker():
    # Imports and filesystem/image work are inside the parent's wall-clock bound,
    # not just individual database calls. Never log raw DB exceptions or DSNs.
    stage = "imports"
    started = time.monotonic()
    try:
        from journal_release import initialize
        from journal_owner_approval import apply_all
        from form_antispam import initialize as initialize_intake_security

        for stage, operation in (
            ("journal_schema", initialize),
            ("intake_security_schema", initialize_intake_security),
            ("owner_approval", apply_all),
        ):
            print(f"Storage startup: stage={stage} starting", flush=True)
            operation()
            print(f"Storage startup: stage={stage} ready elapsed={time.monotonic()-started:.2f}s",
                  flush=True)
    except Exception as error:
        code = getattr(error, "sqlstate", None)
        # SQLSTATE is a fixed machine code; exception text can contain secrets.
        code = code if isinstance(code, str) and len(code) == 5 and code.isalnum() else "none"
        print(f"Storage startup failed: stage={stage} sqlstate={code}; "
              "website not started; retry after storage recovers.", file=sys.stderr, flush=True)
        return 1
    print("Journal approval storage ready", flush=True)
    return 0


def main():
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            timeout=STARTUP_SECONDS, check=False)
        return result.returncode if result.returncode >= 0 else 1
    except subprocess.TimeoutExpired:
        # subprocess.run kills and reaps the worker. PostgreSQL rolls back its
        # uncommitted transaction on disconnect; committed additive DDL is safe
        # to repeat. No detached approval writer remains after a failed start.
        print(f"Storage startup deadline exceeded ({STARTUP_SECONDS}s); "
              "website not started; retry after storage recovers.",
              file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(worker() if sys.argv[1:] == ["--worker"] else main())
