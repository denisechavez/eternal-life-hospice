# Safe print-builder outputs

These tools require an explicit output mode:

- `build-referral-card5-moo-print.py`
- `build-referral-card5-cropmarks-press.py`
- `refine-referral-card5-front-back.py`
- `build-business-cards.py` (HTML only; does not render PDFs)

Run from the project root, for example:

```sh
python3 scripts/build-referral-card5-moo-print.py --output-dir /tmp/elh-moo-proof
python3 scripts/build-referral-card5-cropmarks-press.py --temp-dir
python3 scripts/build-business-cards.py --output-dir /tmp/elh-business-proof
```

`--temp-dir` prints a persistent proof directory for review. Proof directories
must be outside `website/elh-preview` and `exports`, including symlink aliases.
Existing proofs require `--overwrite`. No arguments, `--overwrite` alone, and
the business builder's old positional destination are rejected.

`--publish` explicitly selects the approved `exports/print` destinations.
Replacing existing approved files requires **both `--publish --overwrite`**.
This writes files, not a website deployment. Do not use it for safety tests.
Every output is built in scratch storage before any final file is replaced;
failed rendering or conversion leaves the existing output set intact.

MOO and crop-mark builds retain their existing artwork, geometry and conversion
settings. They still require the historical `assets/img/qr-refer-cream.png` input;
if unavailable, they fail without publishing. QR input compatibility is separate
maintenance, not a reason to regenerate approved cards.

The legacy refinement tool reads the existing master and original cropped QR
tile, then stages both the overlaid RGB PDF and CMYK copy. Inputs are never
overlaid in place. To supply disposable inputs:

```sh
python3 scripts/refine-referral-card5-front-back.py \
  --source-card /tmp/original.pdf --qr-tile /tmp/original-qr-tile.png \
  --output-dir /tmp/elh-refinement-proof
```

Defaults remain the approved master and `/tmp/qr-tile.png`. A missing input is an
explicit error; this tool does not substitute QR artwork. Overlays accumulate
when the input already contains an earlier refinement.

Business-card HTML references the workspace's approved assets with read-only
file URLs, so it can render outside the website directory. It is local print
source, not portable public website HTML. Card copy and layout are unchanged.

Run `python3 scripts/test-remaining-print-tools.py` to check all four builders.
It renders real proofs in disposable directories, checks PDF geometry and print
flags, injects failed conversions, exercises explicit publishing against
disposable sentinel files, and verifies before/after approved-asset hashes.
No approved PDF is regenerated or replaced.