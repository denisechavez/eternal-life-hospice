# Generate collateral proofs safely

These tools keep the existing artwork, colors, sizes, QR destinations and
12-page media-kit reading order. They require an explicit output mode; running
without options does not write anything.

## Proofs (normal staff workflow)

Install the locked optional tools into the existing managed Python environment:

```sh
python3 scripts/setup-python-environment.py
uv sync --locked --extra qr --extra print
```

Use an outside proof directory:

```sh
python3 scripts/build-refer-qr.py --output-dir /tmp/elh-proofs
python3 scripts/build-media-kit-qr.py --output-dir /tmp/elh-proofs
python3 scripts/build-media-kit-pdf.py --output-dir /tmp/elh-proofs
```

Each QR builder writes two PNGs directly in that directory: the white master
(1480×1480) and `-cream` master (1024×1024). The PDF builder writes one
`eternal-life-press-kit-digital.pdf`. Source artwork is read from the project,
regardless of the current working directory.

Alternatively, use `--temp-dir` on any builder to create a unique system
temporary directory. The printed directory is kept for review, not deleted at
exit; remove it when done. Temporary directories are not permanent storage.

Existing proof files are protected. To deliberately rebuild them, repeat the
proof command with `--overwrite`. Proof destinations inside
`website/elh-preview/` or `exports/` (including symlink aliases) are rejected
even with `--overwrite`.

QR builds decode **both** PNGs and require the exact intended URL before
releasing any outputs. A decoding failure leaves previous outputs untouched.
Check the PDF with:

```sh
qpdf --show-npages /tmp/elh-proofs/eternal-life-press-kit-digital.pdf
```

The result must be 12. Visually review the proof PDF's reading order and PNG
badge artwork before approving replacement.

## Intentional approved-asset replacement

Only after approval:

```sh
python3 scripts/build-refer-qr.py --publish --overwrite
python3 scripts/build-media-kit-qr.py --publish --overwrite
python3 scripts/build-media-kit-pdf.py --publish --overwrite
```

**These commands replace approved files.** `--publish` selects the original
website destinations and, for the PDF, the identical `exports/digital/` mirror.
It is mutually exclusive with proof-directory options. `--publish` without
`--overwrite` refuses existing files. Symlink destinations are refused.
Generation finishes in staging before writing final files; replacement is
atomic per file, not a transaction across all destinations.

This mode writes repository assets; it does **not** deploy the website.

## Referral-card print proofs

The two legacy print tools follow the same explicit modes. They use the
workspace's existing `chromium`, `qpdf`, `gs` and `pdfinfo` system tools, with
no additional Python packages.

```sh
python3 scripts/build-referral-card5-print.py --output-dir /tmp/elh-print-proofs
python3 scripts/add-credential-logos-to-referral-cards.py --output-dir /tmp/elh-logo-proofs
# Optional filename substrings select cards; omit to stamp all five.
python3 scripts/add-credential-logos-to-referral-cards.py --temp-dir card-1 card-5
```

Each selected card produces a flat RGB PDF and a `-CMYK.pdf` in the proof
directory. The logo tool reads approved RGB PDFs but never modifies them in
proof mode. All selected RGB and CMYK outputs finish in staging before any
destination is written, so rendering or conversion failure leaves existing
outputs unchanged. Scratch HTML and overlays are deleted automatically.
Proof files remain for review.

**These scripts contain legacy artwork, not necessarily the current approved
design.** Review proofs before publishing; these safety changes do not update
artwork. Page geometry (two pages, 288×594pt), crop-mark coordinates and each
tool's existing CMYK conversion settings are unchanged.

The legacy card-5 builder still expects `assets/img/qr-refer-cream.png`.
The repository currently keeps the WebP version instead; absent the historical
PNG, a real build fails explicitly and leaves outputs untouched. Do not restore
or regenerate approved QR assets just to run a proof. The regression test
supplies the checked-in WebP bytes under the historical filename in a disposable
input fixture (Chromium recognizes the image format from its contents).

Only after approval, intentional replacement uses:

```sh
python3 scripts/build-referral-card5-print.py --publish --overwrite
python3 scripts/add-credential-logos-to-referral-cards.py --publish --overwrite card-1
```

These commands replace RGB files in `exports/print/` and CMYK files in
`exports/print/print-ready-cmyk/`. Card filters also limit publish preflight
and replacement. An unmatched filter fails explicitly without writing files.

## Regression check

```sh
python3 scripts/test-collateral-tools.py
python3 scripts/test-referral-print-tools.py
```

The check executes the actual builders without copying their scripts, verifies
proof dimensions, QR decoding, PDF page count and isolated publishing behavior,
and checks that approved inputs and outputs retain their original hashes.
No approved assets are regenerated by the test.