#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# elh-predeploy.sh
#
# Netlify build wrapper — runs all pre-deploy checks and verifies that every
# check script printed its SENTINEL self-test line.
#
# A check script that has been accidentally emptied (or whose self-test section
# was removed) will exit 0 without printing its SENTINEL.  The sentinel-grep
# step at the end catches that case and blocks the deploy.
#
# Run from website/elh-preview/ (Netlify's build.base directory):
#     bash ../elh-predeploy.sh
#
# Also called indirectly by website/test-predeploy-chain.sh when it reads the
# command from netlify.toml — so local smoke-tests exercise this same path.
#
# Exit: 0 = all checks passed + all sentinels present,  1 = any failure
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

TMPOUT="$(mktemp)"
trap 'rm -f "$TMPOUT"' EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║             ELH Netlify pre-deploy checks                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# ── Run the check chain, capturing output for sentinel verification ────────────
# pipefail is temporarily suspended so tee's exit code never masks the real one.

set +o pipefail
(
  git fetch --unshallow 2>/dev/null || true
  bash ../check-cookie-settings.sh
  node assets/test-chat-teaser.js
  python3 ../check-city-scripts.py
  python3 ../check-header-parity.py
  python3 ../check-footer-parity.py
  python3 ../test-google-reviews.py
  node assets/build-search-index.js
  node assets/update-sitemap-dates.js
) 2>&1 | tee "$TMPOUT"
CHAIN_STATUS="${PIPESTATUS[0]}"
set -o pipefail

if [[ "$CHAIN_STATUS" -ne 0 ]]; then
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "❌  Pre-deploy chain FAILED (exit $CHAIN_STATUS) — deploy blocked."
  echo "══════════════════════════════════════════════════════════════════════"
  exit "$CHAIN_STATUS"
fi

# ── Verify every script's sentinel self-test actually ran ─────────────────────
# Each check script prints a unique SENTINEL line only after its internal
# self-test confirms the guard correctly caught a known-bad input.  If a
# script were accidentally emptied or its self-test section removed, the
# sentinel would be absent and the deploy is blocked here.

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo "  Verifying sentinel self-tests …"
echo ""

SENTINELS=(
  "SENTINEL: check-cookie-settings.sh self-test OK"
  "SENTINEL: test-chat-teaser.js self-test OK"
  "SENTINEL: check-city-scripts.py self-test OK"
  "SENTINEL: check-header-parity.py self-test OK"
  "SENTINEL: check-footer-parity.py self-test OK"
  "SENTINEL: test-google-reviews.py OK"
)

SENTINEL_FAIL=0
for sentinel in "${SENTINELS[@]}"; do
  if grep -qF "$sentinel" "$TMPOUT"; then
    echo "  ✓  $sentinel"
  else
    echo "  ✗  MISSING: $sentinel"
    SENTINEL_FAIL=1
  fi
done

if [[ "$SENTINEL_FAIL" -ne 0 ]]; then
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "❌  One or more sentinel self-tests did not run — a check script may"
  echo "    have been emptied or its self-test section removed.  Deploy blocked."
  echo "══════════════════════════════════════════════════════════════════════"
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "✅  All pre-deploy checks and sentinel self-tests PASSED."
echo "══════════════════════════════════════════════════════════════════════"
exit 0
