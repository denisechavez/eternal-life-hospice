#!/usr/bin/env bash
# Required publish gate: synthetic reviewer fixtures only; no production sessions.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
output="$(mktemp)"
trap 'rm -f "$output"' EXIT
(
  set -e
  python3 website/test-studio-access.py
  node --experimental-websocket website/test-studio-entry-ui.mjs
) 2>&1 | tee "$output"
for sentinel in \
  "SENTINEL: test-studio-access.py protected access checks OK" \
  "SENTINEL: test-studio-entry-ui.mjs authenticated checks OK"; do
  if ! grep -qF "$sentinel" "$output"; then
    echo "Studio publish gate failed: missing $sentinel" >&2
    exit 1
  fi
done
echo "Studio protected access and authenticated entry regressions passed."
