#!/usr/bin/env bash
set -euo pipefail
# Keep Autoscale startup short; build Studio during the approved publish build.
# Fail closed: never bind the public port with incomplete approval/intake setup.
# Outer process-group watchdog also covers a stalled Python supervisor. The
# migration normally finishes/fails within its own 25-second wall-clock budget.
if timeout --kill-after=2s 30s python3 website/migrate-journal.py; then
  :
else
  status=$?
  echo "Storage startup failed (exit=${status}); refusing to start website." >&2
  exit "$status"
fi
exec python3 website/devserver.py
