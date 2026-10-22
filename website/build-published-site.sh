#!/usr/bin/env bash
set -euo pipefail
npm ci --ignore-scripts --no-audit --no-fund
npm ci --prefix artifacts/review-design-sandbox --no-audit --no-fund
node website/build-studio.mjs --published
bash website/check-studio-regressions.sh
