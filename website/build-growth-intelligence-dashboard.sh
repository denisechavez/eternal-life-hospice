#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="$ROOT/artifacts/review-design-sandbox"
TARGET="$ROOT/website/canvas-hub/dashboard"

cd "$SANDBOX"
PORT=21921 \
BASE_PATH=/canvas-hub/dashboard/ \
VITE_DEFAULT_COMPONENT=elh-marketing-hub/Hub \
npm run build

rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -R "$SANDBOX/dist/." "$TARGET/"

npx esbuild "$SANDBOX/reportingCli.ts" \
  --bundle \
  --platform=node \
  --format=esm \
  --outfile="$ROOT/website/growth-intelligence-reporting.mjs"

echo "Built Eternal Growth Intelligence at /canvas-hub/dashboard/"