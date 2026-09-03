#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# test-predeploy-chain.sh
#
# Local smoke-test for the Replit publish validation chain.
#
# Usage (from repo root):
#     bash website/test-predeploy-chain.sh
#
# Exit: 0 = all checks passed,  1 = at least one check failed
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Locate the site and validation wrapper ────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_ABS="$SCRIPT_DIR/elh-preview"
COMMAND="bash ../elh-predeploy.sh"

if [[ ! -d "$BASE_ABS" ]]; then
  echo "❌  build.base directory not found: $BASE_ABS"
  exit 1
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          Replit pre-deploy chain — local smoke-test                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  site directory : $BASE_ABS"
echo ""
echo "  command:"
# Pretty-print each && step on its own line
echo "$COMMAND" | sed 's/ && /\n    && /g' | sed 's/^/    /'
echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo ""

# ── Run the command from the configured base directory ────────────────────────
cd "$BASE_ABS"

# Execute the command in a bash subprocess and capture its output.
# We tee all output to a temp file so we can verify that every script's
# sentinel self-test line appeared — a missing sentinel means a script exited
# without actually exercising its guard (the "silent skip" failure mode).
TMPOUT="$(mktemp)"

# Run with pipefail temporarily disabled so tee never masks a real exit code.
set +o pipefail
bash -c "$COMMAND" 2>&1 | tee "$TMPOUT"
CHAIN_STATUS="${PIPESTATUS[0]}"
set -o pipefail

if [[ "$CHAIN_STATUS" -ne 0 ]]; then
  rm -f "$TMPOUT"
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "❌  Pre-deploy chain FAILED (exit $CHAIN_STATUS) — do not deploy until fixed."
  echo "══════════════════════════════════════════════════════════════════════"
  exit "$CHAIN_STATUS"
fi

# ── Verify every script's sentinel self-test actually ran ─────────────────────
# Each check script prints a unique SENTINEL line only after its internal
# self-test confirms the guard correctly caught a known-bad input.  If a
# script were accidentally emptied or its self-test section removed, the
# sentinel would be absent and the chain would stop here.
echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo "  Verifying sentinel self-tests …"
echo ""

SENTINELS=(
  "SENTINEL: check-cookie-settings.sh self-test OK"
  "SENTINEL: test-chat-teaser.js self-test OK"
  "SENTINEL: test-a11y-forms.js self-test OK"
  "SENTINEL: check-city-scripts.py self-test OK"
  "SENTINEL: check-structured-data.py self-test OK"
  "SENTINEL: check-blog-schema.py self-test OK"
  "SENTINEL: check-og-metadata.py self-test OK"
  "SENTINEL: check-img-alt.py self-test OK"
  "SENTINEL: check-sitemap.py self-test OK"
  "SENTINEL: check-header-parity.py self-test OK"
  "SENTINEL: test-header-mobile.py browser checks OK"
  "SENTINEL: check-footer-parity.py self-test OK"
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

rm -f "$TMPOUT"

if [[ "$SENTINEL_FAIL" -ne 0 ]]; then
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "❌  One or more sentinel self-tests did not run — a check script may"
  echo "    have been emptied or its self-test section removed.  Fix before"
  echo "    deploying."
  echo "══════════════════════════════════════════════════════════════════════"
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "✅  All pre-deploy checks PASSED — safe to deploy."
echo "══════════════════════════════════════════════════════════════════════"
exit 0
