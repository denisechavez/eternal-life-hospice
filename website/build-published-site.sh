#!/usr/bin/env bash
set -euo pipefail

# This fast VM suite must pass before any install or build side effects.
analytics_output="$(node website/test-submission-analytics.cjs)" || {
  status=$?
  printf '%s\n' "$analytics_output"
  echo "Submission analytics check failed — publish blocked." >&2
  exit "$status"
}
printf '%s\n' "$analytics_output"
if ! grep -qxF "SENTINEL: test-submission-analytics.cjs OK" <<< "$analytics_output"; then
  echo "MISSING: SENTINEL: test-submission-analytics.cjs OK — publish blocked." >&2
  exit 1
fi

if ! python3 website/check-prepublish-seo.py; then
  echo "SEO ADVISORY WARNING: The report could not run; continuing the publish build." >&2
fi
npm ci --ignore-scripts --no-audit --no-fund
npm ci --prefix artifacts/review-design-sandbox --no-audit --no-fund
node website/build-studio.mjs --published
bash website/check-studio-regressions.sh
