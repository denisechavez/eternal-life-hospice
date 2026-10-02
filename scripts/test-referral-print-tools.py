#!/usr/bin/env python3
"""Exercise print protection with real renderers and disposable destinations.

Run: python3 scripts/test-referral-print-tools.py
Requires chromium, qpdf, gs and pdfinfo already available in the workspace.
Never publishes into the real project; hashes all approved print PDFs and inputs.
"""
from contextlib import redirect_stdout, redirect_stderr
import functools
import hashlib
import io
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from collateral_output import output_plan


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("build-referral-card5-print.py", "add-credential-logos-to-referral-cards.py")


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class PrintProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = list((ROOT / "exports/print").rglob("*.pdf"))
        cls.protected += list((ROOT / "brand-assets").rglob("*"))
        cls.protected += list((ROOT / "website/elh-preview/assets/fonts").rglob("*"))
        cls.protected += [ROOT / "website/elh-preview/assets/img/qr-refer-cream.webp"]
        cls.protected = [p for p in cls.protected if p.is_file()]
        cls.before = hashes(cls.protected)

    def tearDown(self):
        self.assertEqual(self.before, hashes(self.protected),
                         "Approved PDFs and source artwork must remain unchanged")

    def load(self, tool, root):
        # Import must not copy, render or write anything.
        with patch("tempfile.mkdtemp", side_effect=AssertionError("unsafe import")), \
                patch("subprocess.run", side_effect=AssertionError("unsafe import")):
            module = runpy.run_path(str(ROOT / "scripts" / tool))
        main = module["main"]
        main.__globals__["output_plan"] = functools.partial(output_plan, project_root=root)
        if tool == TOOLS[0]:
            # The legacy builder expects a PNG that was removed when public
            # images moved to WebP. Chromium sniffs image bytes, so supply the
            # checked-in QR bytes under its historical name ONLY in this fixture.
            assets = root / "fixture-assets"
            (assets / "img").mkdir(parents=True)
            shutil.copytree(ROOT / "website/elh-preview/assets/fonts", assets / "fonts")
            shutil.copy2(ROOT / "website/elh-preview/assets/img/qr-refer-cream.webp",
                         assets / "img/qr-refer-cream.png")
            main.__globals__["ASSETS"] = str(assets)
        return main

    def invoke(self, main, args, expected=None):
        log = io.StringIO()
        with redirect_stdout(log), redirect_stderr(log):
            if expected is None:
                main(args)
            else:
                with self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, expected, log.getvalue())
        return log.getvalue()

    def verify_pdf(self, path):
        info = subprocess.run(["pdfinfo", "-f", "1", "-l", "2", str(path)],
                              capture_output=True, text=True, check=True).stdout
        self.assertIn("Pages:           2", info)
        self.assertEqual(info.count("288 x 594 pts"), 2, info)
        subprocess.run(["qpdf", "--check", str(path)], capture_output=True, check=True)

    def test_real_proofs_and_disposable_publish(self):
        for tool in TOOLS:
            with self.subTest(tool=tool), tempfile.TemporaryDirectory(prefix="elh-print-test-") as tmp:
                root = Path(tmp)
                main = self.load(tool, root)
                # Existing approved destinations are sentinel files in a disposable tree.
                names = ([Path(main.__globals__["CARD"]).name] if tool == TOOLS[0]
                         else list(main.__globals__["overlays"]))
                targets = []
                for name in names:
                    targets.extend([root / "exports/print" / name,
                                    root / "exports/print/print-ready-cmyk"
                                    / name.replace(".pdf", "-CMYK.pdf")])
                for target in targets:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"approved sentinel")
                approved = hashes(targets)
                for args in ([], ["--overwrite"], ["--publish"],
                             ["--publish", "--output-dir", str(root / "proofs")],
                             ["--temp-dir", "--output-dir", str(root / "proofs")]):
                    self.invoke(main, args, expected=2)
                for directory in (root / "exports", root / "website/elh-preview"):
                    directory.mkdir(parents=True, exist_ok=True)
                    alias = root / f"alias-{directory.name}"
                    alias.symlink_to(directory, target_is_directory=True)
                    for dest in (directory, alias):
                        self.invoke(main, ["--output-dir", str(dest), "--overwrite"], expected=2)
                self.assertEqual(approved, hashes(targets))
                proofs = root / "proofs"
                calls = []
                real_run = subprocess.run

                def record(command, *args, **kwargs):
                    calls.append(command)
                    return real_run(command, *args, **kwargs)

                with patch("subprocess.run", side_effect=record):
                    self.invoke(main, ["--output-dir", str(proofs)])
                self.assertEqual({p.name for p in targets}, {p.name for p in proofs.iterdir()})
                for proof in proofs.iterdir():
                    self.verify_pdf(proof)
                gs_calls = [cmd for cmd in calls if cmd[0] == "gs"]
                self.assertEqual(len(gs_calls), len(names))
                for cmd in gs_calls:
                    self.assertIn("-sColorConversionStrategy=CMYK", cmd)
                    self.assertIn("-dProcessColorModel=/DeviceCMYK", cmd)
                    self.assertIn("-dPDFSETTINGS=/prepress", cmd)
                    if tool == TOOLS[0]:
                        for flag in ("-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
                                     "-dDownsampleMonoImages=false", "-dAutoFilterColorImages=false",
                                     "-dAutoFilterGrayImages=false", "-dColorImageFilter=/FlateEncode",
                                     "-dGrayImageFilter=/FlateEncode"):
                            self.assertIn(flag, cmd)
                    else:
                        self.assertIn("-dOverrideICC=true", cmd)
                        self.assertIn("-dAutoRotatePages=/None", cmd)
                proof_hashes = hashes(proofs.iterdir())
                self.invoke(main, ["--output-dir", str(proofs)], expected=2)
                # A late collision is rejected before the first proof can be written.
                first = proofs / targets[0].name
                first.unlink()
                self.invoke(main, ["--output-dir", str(proofs)], expected=2)
                self.assertFalse(first.exists())
                shutil.copy2(targets[0], first)
                proof_hashes = hashes(proofs.iterdir())
                # Fail conversion of the LAST selected card after all prior staging.
                for args, existing in ((["--output-dir", str(proofs), "--overwrite"], proof_hashes),
                                       (["--publish", "--overwrite"], approved)):
                    conversions = 0

                    def fail_last(command, *a, **kw):
                        nonlocal conversions
                        if command[0] == "gs":
                            conversions += 1
                            if conversions == len(names):
                                return subprocess.CompletedProcess(command, 1, "", "forced conversion failure")
                        return real_run(command, *a, **kw)

                    with patch("subprocess.run", side_effect=fail_last):
                        self.invoke(main, args, expected=1)
                    self.assertEqual(existing, hashes(Path(p) for p in existing))
                self.invoke(main, ["--publish", "--overwrite"])
                for target in targets:
                    self.verify_pdf(target)
                self.invoke(main, ["--publish"], expected=2)
                for target in targets:
                    target.unlink()
                self.invoke(main, ["--publish"])
                self.assertTrue(all(p.is_file() for p in targets))

    def test_card_filters_temp_mode_and_explicit_proof_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="elh-print-filter-") as tmp:
            root = Path(tmp)
            main = self.load(TOOLS[1], root)
            self.invoke(main, ["--output-dir", str(root / "proofs"), "no-such-card"], expected=2)
            self.assertFalse((root / "proofs").exists())
            output = self.invoke(main, ["--temp-dir", "card-2"])
            proofs = Path(next(line.split(": ", 1)[1] for line in output.splitlines()
                               if line.startswith("Proof directory (kept for review):")))
            self.addCleanup(shutil.rmtree, proofs)
            self.assertEqual(len(list(proofs.iterdir())), 2)
            self.assertTrue(all("card-2" in p.name for p in proofs.iterdir()))
            self.invoke(main, ["--output-dir", str(proofs), "--overwrite", "card-2"])
            for p in proofs.iterdir():
                self.verify_pdf(p)
            # Filters select only matching approved destinations.
            self.invoke(main, ["--publish", "card-1", "card-5"])
            self.assertEqual(len(list((root / "exports").rglob("*.pdf"))), 4)


if __name__ == "__main__":
    unittest.main()