#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# test-predeploy-chain.sh
#
# Local smoke-test for the Netlify build command.
#
# Reads the `command` value from netlify.toml, changes into the configured
# `base` directory (website/elh-preview), then runs the exact command string.
# Every check in the chain must exit 0; the first failure halts and reports
# which step broke.
#
# Usage (from repo root):
#     bash website/test-predeploy-chain.sh
#
# Exit: 0 = all checks passed,  1 = at least one check failed
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Locate repo root (the directory that contains netlify.toml) ───────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOML="$REPO_ROOT/netlify.toml"

if [[ ! -f "$TOML" ]]; then
  echo "❌  netlify.toml not found at $TOML"
  exit 1
fi

# ── Extract build.base and build.command from netlify.toml ────────────────────
# We use Python (always available in this environment) so we don't need tomlq.
BASE_DIR="$( python3 - "$TOML" <<'PY'
import sys, re

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

# Find [build] section and extract base = "..."
m = re.search(r'^\[build\](.+?)(?=^\[|\Z)', text, re.MULTILINE | re.DOTALL)
if not m:
    sys.exit("ERROR: [build] section not found in netlify.toml")

section = m.group(1)

bm = re.search(r'^\s*base\s*=\s*"([^"]+)"', section, re.MULTILINE)
print(bm.group(1) if bm else ".")
PY
)"

COMMAND="$( python3 - "$TOML" <<'PY'
import sys, re

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

m = re.search(r'^\[build\](.+?)(?=^\[|\Z)', text, re.MULTILINE | re.DOTALL)
if not m:
    sys.exit("ERROR: [build] section not found in netlify.toml")

section = m.group(1)

# command may span multiple lines via TOML line-continuation (backslash) or
# be a simple single-line string.  Extract everything between the quotes.
cm = re.search(r'^\s*command\s*=\s*"((?:[^"\\]|\\.)*)"', section, re.MULTILINE | re.DOTALL)
if not cm:
    sys.exit("ERROR: command not found in [build] section of netlify.toml")

# Un-escape any backslash-newline sequences used for TOML readability
cmd = cm.group(1).replace('\\\n', ' ')
print(cmd)
PY
)"

BASE_ABS="$REPO_ROOT/$BASE_DIR"

if [[ ! -d "$BASE_ABS" ]]; then
  echo "❌  build.base directory not found: $BASE_ABS"
  exit 1
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          Netlify pre-deploy chain — local smoke-test                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  netlify.toml   : $TOML"
echo "  build.base     : $BASE_DIR  →  $BASE_ABS"
echo ""
echo "  command:"
# Pretty-print each && step on its own line
echo "$COMMAND" | sed 's/ && /\n    && /g' | sed 's/^/    /'
echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo ""

# ── Run the command from the configured base directory ────────────────────────
cd "$BASE_ABS"

# Execute the full command string in a bash subprocess so &&-chaining,
# redirections (2>/dev/null), and || true work exactly as they do on Netlify.
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
  "SENTINEL: check-city-scripts.py self-test OK"
  "SENTINEL: check-header-parity.py self-test OK"
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
