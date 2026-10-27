#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# test-predeploy-chain.sh
#
# Local smoke-test for the Replit publish validation chain.
#
# Usage (from repo root):
#     bash website/test-predeploy-chain.sh
#     bash website/test-predeploy-chain.sh --isolated  # No app APIs or site writes
#
# Exit: 0 = all checks passed,  1 = at least one check failed
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Locate the site and validation wrapper ────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_ABS="$SCRIPT_DIR/elh-preview"
COMMAND="bash ../elh-predeploy.sh"

# Exercise the real wrapper with temporary command stubs. Never run application
# APIs, providers, generators or publication jobs in this regression check.
python3 - "$SCRIPT_DIR" <<'PY'
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

source = Path(sys.argv[1])
retry = "node --experimental-websocket ../test-care-brief-signup-retry.mjs"
layout = "node --experimental-websocket ../test-care-brief-layout.mjs"
footer = "python3 ../check-footer-parity.py"
ack = "python3 ../test-acknowledgments.py"
ack_sentinel = "SENTINEL: test-acknowledgments.py OK"
sentinel = "SENTINEL: test-care-brief-signup-retry.mjs browser checks OK"
wrapper = (source / "elh-predeploy.sh").read_text()
chain = wrapper.split("set +o pipefail\n(\n", 1)[1].split("\n) 2>&1", 1)[0]
commands = [line.strip() for line in chain.splitlines() if line.strip()]
assert commands.count(retry) == 1, "Retry suite must run exactly once with WebSocket support"
assert commands.index(retry) == commands.index(layout) + 1, "Retry suite must follow layout guard"
assert commands.index(footer) == commands.index(retry) + 1, "Retry suite must precede footer guard"
assert commands.index(retry) < commands.index("node assets/build-search-index.js --check")
assert wrapper.count('"' + sentinel + '"') == 1, "Wrapper must require retry sentinel"
assert commands.count(ack) == 1, "Acknowledgment suite must run exactly once"
assert commands.index(ack) < commands.index("node assets/build-search-index.js --check")
assert wrapper.count('"' + ack_sentinel + '"') == 1, "Wrapper must require acknowledgment sentinel"
smoke = (source / "test-predeploy-chain.sh").read_text()
assert smoke.count('  "' + sentinel + '"') == 1, "Smoke test must require retry sentinel"
assert smoke.count('  "' + ack_sentinel + '"') == 1, "Smoke test must require acknowledgment sentinel"
sentinels = re.findall(r'^  "(SENTINEL: .+)"$', wrapper, re.M)

with tempfile.TemporaryDirectory(prefix="elh-predeploy-chain-") as temp:
    root = Path(temp)
    site = root / "elh-preview"
    site.mkdir()
    (root / "elh-predeploy.sh").write_text(wrapper)
    log = root / "commands.log"
    bindir = root / "bin"
    bindir.mkdir()
    # Use the real interpreter path so PATH shims cannot recursively invoke
    # themselves. Every command is logged, including the Node feature flag.
    stub = f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import sys
command = Path(sys.argv[0]).name + " " + " ".join(sys.argv[1:])
if Path(sys.argv[0]).name == "cookie-stub":
    command = "bash ../check-cookie-settings.sh"
with open(os.environ["CHAIN_LOG"], "a") as output:
    output.write(command + "\\n")
is_target = command == os.environ["TARGET_COMMAND"]
if is_target and os.environ["CHAIN_MODE"] == "failure":
    print("Injected check failure: " + command, flush=True)
    sys.exit(37)
if not (is_target and os.environ["CHAIN_MODE"] == "missing"):
    for sentinel in os.environ["CHAIN_SENTINELS"].splitlines():
        if sentinel.split(": ", 1)[1].split(" ", 1)[0] in command:
            print(sentinel)
'''
    for name in ("node", "python3", "cookie-stub"):
        executable = bindir / name
        executable.write_text(stub)
        executable.chmod(0o755)
    (root / "check-cookie-settings.sh").write_text('exec cookie-stub "$@"\n')
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
               CHAIN_LOG=str(log),
               CHAIN_SENTINELS="\n".join(sentinels))
    scenarios = [(retry, sentinel, "success"),
                 (retry, sentinel, "failure"), (retry, sentinel, "missing"),
                 (ack, ack_sentinel, "failure"), (ack, ack_sentinel, "missing")]
    for target, target_sentinel, mode in scenarios:
        log.write_text("")
        before = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
        result = subprocess.run([shutil.which("bash"), "../elh-predeploy.sh"],
                                cwd=site, env=dict(env, CHAIN_MODE=mode, TARGET_COMMAND=target),
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        actual = log.read_text().splitlines()
        expected = commands[:commands.index(target) + 1] if mode == "failure" else commands
        assert actual == expected, f"{mode}: wrong command order: {actual}"
        expected_status = {"success": 0, "failure": 37, "missing": 1}[mode]
        assert result.returncode == expected_status, f"{mode}: {result.stdout}"
        if mode == "failure":
            assert "Injected check failure: " + target in result.stdout
            assert "Pre-deploy chain FAILED (exit 37)" in result.stdout
        if mode == "missing":
            assert "MISSING: " + target_sentinel in result.stdout, result.stdout
        after = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
        assert after == before, f"{mode}: changed publication fixture"
        print(f"PASS: isolated pre-deploy chain {target}: {mode}")
print("SENTINEL: test-predeploy-chain.sh isolated checks OK")
PY

if [[ "${1:-}" == "--isolated" ]]; then
  exit 0
fi

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
  "SENTINEL: check-analytics-version.py self-test OK"
  "SENTINEL: check-structured-data.py self-test OK"
  "SENTINEL: check-blog-schema.py self-test OK"
  "SENTINEL: check-og-metadata.py self-test OK"
  "SENTINEL: check-img-alt.py self-test OK"
  "SENTINEL: check-care-brief-signup.py self-test OK"
  "SENTINEL: check-sitemap.py self-test OK"
  "SENTINEL: check-header-parity.py self-test OK"
  "SENTINEL: test-header-mobile.py browser checks OK"
  "SENTINEL: test-care-brief-layout.mjs browser checks OK"
  "SENTINEL: test-care-brief-signup-retry.mjs browser checks OK"
  "SENTINEL: check-footer-parity.py self-test OK"
  "SENTINEL: check-agency-separation.py OK"
  "SENTINEL: test-service-publication.py OK"
  "SENTINEL: test-public-artifact-exposure.py OK"
  "SENTINEL: test-growth-intelligence-access.py OK"
  "SENTINEL: test-acknowledgments.py OK"
  "SENTINEL: check-internal-links.py self-test OK"
  "SENTINEL: test-internal-link-journeys.py browser checks OK"
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
