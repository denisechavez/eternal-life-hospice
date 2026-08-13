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
if bash -c "$COMMAND"; then
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "✅  All pre-deploy checks PASSED — safe to deploy."
  echo "══════════════════════════════════════════════════════════════════════"
  exit 0
else
  STATUS=$?
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo "❌  Pre-deploy chain FAILED (exit $STATUS) — do not deploy until fixed."
  echo "══════════════════════════════════════════════════════════════════════"
  exit "$STATUS"
fi
