#!/usr/bin/env bash
set -euo pipefail
if ! python3 website/check-prepublish-seo.py; then
  echo "SEO ADVISORY WARNING: The report could not run; continuing the publish build." >&2
fi
npm ci --ignore-scripts --no-audit --no-fund
npm ci --prefix artifacts/review-design-sandbox --no-audit --no-fund
node website/build-studio.mjs --published
bash website/check-studio-regressions.sh
