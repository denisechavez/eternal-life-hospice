#!/usr/bin/env bash
set -euo pipefail
# Keep Autoscale startup short; build Studio during the approved publish build.
python3 website/migrate-journal.py
exec python3 website/devserver.py
