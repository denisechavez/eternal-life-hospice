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
import shlex
import subprocess
import sys
import tempfile
import tomllib

source = Path(sys.argv[1])
# Exercise the real phone/footer completion runners before wrapper output stubs.
# This regression mocks unittest results, not their completion output.
subprocess.run([sys.executable, "-B", str(source / "test-contact-suite-runners.py")],
               check=True)
retry = "node --experimental-websocket ../test-care-brief-signup-retry.mjs"
layout = "node --experimental-websocket ../test-care-brief-layout.mjs"
footer = "python3 ../check-footer-parity.py"
ack = "python3 ../test-acknowledgments.py"
ack_sentinel = "SENTINEL: test-acknowledgments.py OK"
phone = "python3 ../test-website-phone.py"
phone_config = "python3 ../test-website-phone-config.py"
phone_config_sentinel = "SENTINEL: test-website-phone-config.py OK"
phone_sentinel = "SENTINEL: test-website-phone.py OK"
footer_contact = "python3 ../test-footer-contact.py"
footer_contact_sentinel = "SENTINEL: test-footer-contact.py OK"
tracker = "python3 ../test-tracker-policy.py"
tracker_sentinel = "SENTINEL: test-tracker-policy.py OK"
tracker_browser = "node --experimental-websocket ../test-cookie-browser.mjs"
tracker_browser_sentinel = "SENTINEL: test-cookie-browser.mjs OK"
landing_browser = "node --experimental-websocket ../test-landing-consent-browser.mjs"
landing_browser_sentinel = "SENTINEL: test-landing-consent-browser.mjs OK"
analytics = "node ../test-submission-analytics.cjs"
analytics_sentinel = "SENTINEL: test-submission-analytics.cjs OK"
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
assert commands.count(tracker) == 1, "Tracker policy suite must run exactly once"
assert commands.count(tracker_browser) == 1, "Synthetic tracker runtime suite must run exactly once"
assert commands.index(tracker_browser) == commands.index(tracker) + 1
assert wrapper.count('"' + tracker_browser_sentinel + '"') == 1, "Require browser runtime sentinel"
assert commands.count(landing_browser) == 1, "Real-page consent suite must run exactly once"
assert commands.index(landing_browser) == commands.index(tracker_browser) + 1
assert wrapper.count('"' + landing_browser_sentinel + '"') == 1, "Require real-page consent sentinel"
assert wrapper.count('"' + tracker_sentinel + '"') == 1, "Wrapper must require tracker policy sentinel"
assert commands.count(analytics) == 1, "Synthetic submission analytics suite must run exactly once"
assert commands.index(analytics) < commands.index("node assets/build-search-index.js --check")
assert not any("test-intake-nimbata.mjs" in command for command in commands), "Keep live browser tracking checks separate from synthetic publishing checks"
assert wrapper.count('"' + analytics_sentinel + '"') == 1, "Wrapper must require submission analytics sentinel"
assert commands.index(ack) < commands.index("node assets/build-search-index.js --check")
assert wrapper.count('"' + ack_sentinel + '"') == 1, "Wrapper must require acknowledgment sentinel"
assert commands.count(phone) == 1, "Phone-role suite must run exactly once"
assert commands.count(phone_config) == 1, "Phone configuration suite must run exactly once"
assert commands.count(footer_contact) == 1, "Footer contact suite must run exactly once"
assert commands.index(phone_config) == commands.index(ack) + 1, "Phone configuration guard must follow acknowledgment guard"
assert commands.index(phone) == commands.index(phone_config) + 1, "Phone guard must follow configuration guard"
assert commands.index(footer_contact) == commands.index(phone) + 1, "Footer contact guard must follow phone guard"
assert commands.index(footer_contact) < commands.index("node assets/build-search-index.js --check")
assert commands.index(phone) < commands.index("node assets/build-search-index.js --check")
assert wrapper.count('"' + phone_sentinel + '"') == 1, "Wrapper must require phone sentinel"
assert wrapper.count('"' + phone_config_sentinel + '"') == 1, "Wrapper must require phone configuration sentinel"
assert wrapper.count('"' + footer_contact_sentinel + '"') == 1, "Wrapper must require footer contact sentinel"
smoke = (source / "test-predeploy-chain.sh").read_text()
assert smoke.count('  "' + sentinel + '"') == 1, "Smoke test must require retry sentinel"
assert smoke.count('  "' + ack_sentinel + '"') == 1, "Smoke test must require acknowledgment sentinel"
assert smoke.count('  "' + phone_sentinel + '"') == 1, "Smoke test must require phone sentinel"
assert smoke.count('  "' + phone_config_sentinel + '"') == 1, "Smoke test must require phone configuration sentinel"
assert smoke.count('  "' + footer_contact_sentinel + '"') == 1, "Smoke test must require footer contact sentinel"
assert smoke.count('  "' + analytics_sentinel + '"') == 1, "Smoke test must require submission analytics sentinel"

def required_sentinels(script):
    arrays = re.findall(r"^SENTINELS=\(\n(.*?)^\)", script, re.M | re.S)
    assert len(arrays) == 1, "Expected exactly one required SENTINELS array"
    values = shlex.split(arrays[0], comments=True)
    assert values and all(value.startswith("SENTINEL: ") for value in values), "Invalid sentinel list"
    assert len(values) == len(set(values)), "Duplicate required sentinel"
    return values


def assert_sentinel_parity(required, local):
    missing = sorted(set(required) - set(local))
    extra = sorted(set(local) - set(required))
    assert not (missing or extra), f"Local sentinel drift: missing={missing}; extra={extra}"


sentinels = required_sentinels(wrapper)
local_sentinels = required_sentinels(smoke)
assert_sentinel_parity(sentinels, local_sentinels)
# Prove the parity assertion catches every omission and future wrapper-only
# additions, without running checks, APIs or publication generators.
for omitted in sentinels:
    try:
        assert_sentinel_parity(sentinels, [value for value in local_sentinels if value != omitted])
    except AssertionError as error:
        assert omitted in str(error)
    else:
        raise AssertionError("Parity assertion accepted missing sentinel: " + omitted)
future_sentinel = "SENTINEL: future-required-guard.py OK"
for required, local in ((sentinels + [future_sentinel], local_sentinels),
                        (sentinels, local_sentinels + [future_sentinel])):
    try:
        assert_sentinel_parity(required, local)
    except AssertionError as error:
        assert future_sentinel in str(error)
    else:
        raise AssertionError("Parity assertion accepted sentinel drift")
print(f"PASS: local sentinel parity and omission checks ({len(sentinels)} required guards)")
publish = (source / "build-published-site.sh").read_text()
config = tomllib.loads((source.parent / ".replit").read_text())
assert config["deployment"]["build"] == ["bash", "website/build-published-site.sh"]
publish_analytics = "node website/test-submission-analytics.cjs"
assert publish.count(publish_analytics) == 1, "Configured publish build must run analytics exactly once"
assert analytics_sentinel in publish, "Configured publish build must require analytics completion"
assert "test-intake-nimbata.mjs" not in publish, "Publish build must not run browser tracking checks"

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
            if is_target and os.environ["CHAIN_MODE"] == "prefixed":
                print("Diagnostic: expected " + sentinel)
            elif is_target and os.environ["CHAIN_MODE"] == "suffixed":
                print(sentinel + " (not actually completed)")
            else:
                print(sentinel)
'''
    for name in ("node", "python3", "npm", "cookie-stub"):
        executable = bindir / name
        executable.write_text(stub)
        executable.chmod(0o755)
    (root / "check-cookie-settings.sh").write_text('exec cookie-stub "$@"\n')
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
               CHAIN_LOG=str(log),
               CHAIN_SENTINELS="\n".join(sentinels))
    scenarios = [(retry, sentinel, "success"),
                 (retry, sentinel, "failure"), (retry, sentinel, "missing"),
                 (retry, sentinel, "prefixed"), (retry, sentinel, "suffixed"),
                 (ack, ack_sentinel, "failure"), (ack, ack_sentinel, "missing"),
                 (phone_config, phone_config_sentinel, "success"),
                 (phone_config, phone_config_sentinel, "failure"),
                 (phone_config, phone_config_sentinel, "missing"),
                 (phone, phone_sentinel, "failure"), (phone, phone_sentinel, "missing"),
                 (footer_contact, footer_contact_sentinel, "success"),
                 (footer_contact, footer_contact_sentinel, "failure"),
                 (footer_contact, footer_contact_sentinel, "missing"),
                 (tracker, tracker_sentinel, "failure"), (tracker, tracker_sentinel, "missing"),
                 (tracker_browser, tracker_browser_sentinel, "success"),
                 (tracker_browser, tracker_browser_sentinel, "failure"),
                 (tracker_browser, tracker_browser_sentinel, "missing"),
                 (landing_browser, landing_browser_sentinel, "success"),
                 (landing_browser, landing_browser_sentinel, "failure"),
                 (landing_browser, landing_browser_sentinel, "missing"),
                 (analytics, analytics_sentinel, "success"),
                 (analytics, analytics_sentinel, "failure"), (analytics, analytics_sentinel, "missing")]
    for script in ("test-journal-campaign.py", "test-journal-photo-notes-e2e.py",
                   "test-service-photo-notes-e2e.py",
                   "test-google-reviews.py", "test-replit-chat-coverage.py"):
        for mode in ("failure", "missing"):
            scenarios.append((f"python3 ../{script}", f"SENTINEL: {script} OK", mode))
    for target, target_sentinel, mode in scenarios:
        log.write_text("")
        before = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
        result = subprocess.run([shutil.which("bash"), "../elh-predeploy.sh"],
                                cwd=site, env=dict(env, CHAIN_MODE=mode, TARGET_COMMAND=target),
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        actual = log.read_text().splitlines()
        expected = commands[:commands.index(target) + 1] if mode == "failure" else commands
        assert actual == expected, f"{mode}: wrong command order: {actual}"
        expected_status = {"success": 0, "failure": 37, "missing": 1,
                           "prefixed": 1, "suffixed": 1}[mode]
        assert result.returncode == expected_status, f"{mode}: {result.stdout}"
        if mode == "failure":
            assert "Injected check failure: " + target in result.stdout
            assert "Pre-deploy chain FAILED (exit 37)" in result.stdout
        if mode in ("missing", "prefixed", "suffixed"):
            assert "MISSING: " + target_sentinel in result.stdout, result.stdout
            missing = re.findall(r"^\s*✗  MISSING: (.+)$", result.stdout, re.M)
            assert missing == [target_sentinel], f"Expected only target output missing: {result.stdout}"
            assert "All pre-deploy checks and sentinel self-tests PASSED" not in result.stdout
        after = {p.relative_to(site): p.read_bytes() for p in site.rglob("*") if p.is_file()}
        assert after == before, f"{mode}: changed publication fixture"
        print(f"PASS: isolated pre-deploy chain {target}: {mode}")
    # Exercise the actual .replit build entry point without installs, app APIs
    # or builds. Failures must stop before even the advisory SEO check runs.
    website = root / "website"
    website.mkdir()
    (website / "build-published-site.sh").write_text(publish)
    (website / "check-studio-regressions.sh").write_text("exit 0\n")
    publish_commands = [
        publish_analytics,
        "python3 website/check-prepublish-seo.py",
        "npm ci --ignore-scripts --no-audit --no-fund",
        "npm ci --prefix artifacts/review-design-sandbox --no-audit --no-fund",
        "node website/build-studio.mjs --published",
    ]
    for mode in ("success", "failure", "missing"):
        log.write_text("")
        result = subprocess.run([shutil.which("bash"), "website/build-published-site.sh"],
                                cwd=root, env=dict(env, CHAIN_MODE=mode, TARGET_COMMAND=publish_analytics),
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        expected = publish_commands if mode == "success" else [publish_analytics]
        assert log.read_text().splitlines() == expected, result.stdout
        assert result.returncode == {"success": 0, "failure": 37, "missing": 1}[mode], result.stdout
        if mode == "missing":
            assert "MISSING: " + analytics_sentinel in result.stdout, result.stdout
        if mode == "failure":
            assert "Submission analytics check failed" in result.stdout, result.stdout
        print(f"PASS: isolated configured publish build analytics: {mode}")

    # Run an unchanged copy without --isolated to exercise the local shell loop.
    # Stub its Python preflight to avoid recursively running this harness, and
    # replace the publishing wrapper entirely: no application command can run.
    local_root = root / "local-smoke"
    local_root.mkdir()
    local_site = local_root / "elh-preview"
    local_site.mkdir()
    (local_site / "dummy.html").write_text("<!doctype html><title>Fixture only</title>\n")
    (local_root / "test-predeploy-chain.sh").write_text(smoke)
    local_log = local_root / "commands.log"
    local_bin = local_root / "bin"
    local_bin.mkdir()
    local_tmp = local_root / "tmp"
    local_tmp.mkdir()
    preflight_stub = f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import sys
command = Path(sys.argv[0]).name
if command != "python3" or sys.argv[1:] != ["-", os.environ["LOCAL_ROOT"]]:
    sys.exit("Unexpected application command: " + repr(sys.argv))
sys.stdin.read()
with open(os.environ["LOCAL_LOG"], "a") as output:
    output.write("preflight-stub\\n")
'''
    for name in ("python3", "node", "npm"):
        executable = local_bin / name
        executable.write_text(preflight_stub)
        executable.chmod(0o755)
    (local_root / "elh-predeploy.sh").write_text('''#!/usr/bin/env bash
set -euo pipefail
[[ "$PWD" == "$LOCAL_ROOT/elh-preview" ]] || exit 99
printf '%s\\n' wrapper-stub >> "$LOCAL_LOG"
while IFS= read -r value; do
  if [[ "$value" != "$LOCAL_OMITTED" ]]; then
    printf '%s\\n' "$value"
  elif [[ "$LOCAL_MODE" == "prefixed" ]]; then
    printf 'Diagnostic: expected %s\\n' "$value"
  elif [[ "$LOCAL_MODE" == "suffixed" ]]; then
    printf '%s (not actually completed)\\n' "$value"
  fi
done <<< "$LOCAL_SENTINELS"
exit "$LOCAL_STATUS"
''')
    local_env = dict(os.environ,
                     PATH=str(local_bin) + os.pathsep + os.environ["PATH"],
                     LOCAL_ROOT=str(local_root), LOCAL_LOG=str(local_log),
                     LOCAL_SENTINELS="\n".join(local_sentinels),
                     TMPDIR=str(local_tmp))
    local_cases = [("complete output", "", 0, "success")]
    # Every required completion must be a whole line, not a diagnostic that
    # merely contains it. Exercise both boundaries in the real local shell loop.
    local_cases += [(mode + " " + value, value, 0, mode)
                    for value in local_sentinels
                    for mode in ("missing", "prefixed", "suffixed")]
    local_cases += [("wrapper failure", "", 37, "success"),
                    ("wrapper failure with missing sentinel", local_sentinels[0], 37, "missing")]
    before = {p.relative_to(local_site): p.read_bytes() for p in local_site.rglob("*") if p.is_file()}
    for label, omitted, status, mode in local_cases:
        local_log.write_text("")
        result = subprocess.run(
            [shutil.which("bash"), str(local_root / "test-predeploy-chain.sh")],
            cwd=root, env=dict(local_env, LOCAL_OMITTED=omitted,
                               LOCAL_STATUS=str(status), LOCAL_MODE=mode),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        expected_status = status or (1 if omitted else 0)
        assert result.returncode == expected_status, f"{label}: {result.stdout}"
        assert local_log.read_text().splitlines() == ["preflight-stub", "wrapper-stub"], result.stdout
        if status:
            assert f"Pre-deploy chain FAILED (exit {status})" in result.stdout, result.stdout
            assert "Verifying sentinel self-tests" not in result.stdout, result.stdout
        else:
            assert "Verifying sentinel self-tests" in result.stdout, result.stdout
            for value in local_sentinels:
                marker = "  ✗  MISSING: " if value == omitted else "  ✓  "
                assert marker + value in result.stdout.splitlines(), f"{label}: {result.stdout}"
            if omitted:
                assert "One or more sentinel self-tests did not run" in result.stdout, result.stdout
        assert ("All pre-deploy checks PASSED" in result.stdout) == (expected_status == 0), result.stdout
        after = {p.relative_to(local_site): p.read_bytes() for p in local_site.rglob("*") if p.is_file()}
        assert after == before, f"{label}: changed local site fixture"
        assert not list(local_tmp.iterdir()), f"{label}: leaked smoke-test output"
        print(f"PASS: isolated local smoke branch: {label}")
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
  "SENTINEL: test-tracker-policy.py OK"
  "SENTINEL: test-cookie-browser.mjs OK"
  "SENTINEL: test-landing-consent-browser.mjs OK"
  "SENTINEL: test-submission-analytics.cjs OK"
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
  "SENTINEL: test-journal-campaign.py OK"
  "SENTINEL: test-journal-photo-notes-e2e.py OK"
  "SENTINEL: test-service-photo-notes-e2e.py OK"
  "SENTINEL: check-internal-links.py self-test OK"
  "SENTINEL: test-internal-link-journeys.py browser checks OK"
  "SENTINEL: test-google-reviews.py OK"
  "SENTINEL: test-replit-chat-coverage.py OK"
  "SENTINEL: test-public-artifact-exposure.py OK"
  "SENTINEL: test-growth-intelligence-access.py OK"
  "SENTINEL: test-acknowledgments.py OK"
  "SENTINEL: test-website-phone-config.py OK"
  "SENTINEL: test-website-phone.py OK"
  "SENTINEL: test-footer-contact.py OK"
)

SENTINEL_FAIL=0
for sentinel in "${SENTINELS[@]}"; do
  # Only a standalone completion line counts, never quoted diagnostic text.
  if grep -qxF "$sentinel" "$TMPOUT"; then
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
