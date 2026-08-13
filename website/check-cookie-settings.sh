#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# check-cookie-settings.sh
# Flags any .html file under elh-preview/ that is missing a "Cookie Settings"
# link.  Run this before every publish / Netlify deploy.
#
# Usage:  bash website/check-cookie-settings.sh
# Exit:   0 = all clear,  1 = one or more files missing the link
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PREVIEW_DIR="$(dirname "$0")/elh-preview"

# ── Pages that intentionally omit Cookie Settings ────────────────────────────
# aleksandradubina.html: noindex/nofollow, no analytics loaded, pure utility
EXCLUDE=(
  "aleksandradubina.html"
)

# ── Sentinel self-test ───────────────────────────────────────────────────────
# Verifies the guard correctly detects a page missing the Cookie Settings link.
# If the grep logic were broken (e.g. always returns 0), this exits 1 instead
# of silently passing the deploy.
_st_tmp="$(mktemp /tmp/elh-cs-sentinel-XXXXXX.html)"
printf '<html><body><p>Page without any cookie link here</p></body></html>\n' > "$_st_tmp"
if grep -q "Cookie Settings" "$_st_tmp"; then
  echo "❌  SELF-TEST FAILED: guard accepted a page that is missing the Cookie Settings link" >&2
  rm -f "$_st_tmp"
  exit 1
fi
rm -f "$_st_tmp"
echo "SENTINEL: check-cookie-settings.sh self-test OK"

# ─────────────────────────────────────────────────────────────────────────────
missing=()

while IFS= read -r -d '' file; do
  basename_file="$(basename "$file")"

  # Check exclusion list
  skip=0
  for ex in "${EXCLUDE[@]}"; do
    [[ "$basename_file" == "$ex" ]] && { skip=1; break; }
  done
  [[ "$skip" -eq 1 ]] && continue

  # Check for the Cookie Settings string
  if ! grep -q "Cookie Settings" "$file"; then
    missing+=("$file")
  fi
done < <(find "$PREVIEW_DIR" -maxdepth 1 -name "*.html" -print0 | sort -z)

# ─────────────────────────────────────────────────────────────────────────────
if [[ ${#missing[@]} -eq 0 ]]; then
  echo "✅  All checked pages include the Cookie Settings link."
  exit 0
else
  echo "❌  The following pages are missing 'Cookie Settings':"
  for f in "${missing[@]}"; do
    echo "    $(basename "$f")"
  done
  echo ""
  echo "Add the foot-bottom-links block from the template in:"
  echo "    website/elh-preview/FOOTER-SNIPPET.md"
  exit 1
fi
