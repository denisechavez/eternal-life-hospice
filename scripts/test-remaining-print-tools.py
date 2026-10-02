#!/usr/bin/env python3
"""Safety regression tests for MOO, crop-mark, refinement and business builders.

Run: python3 scripts/test-remaining-print-tools.py
Real rendering requires chromium, gs, qpdf, pdfinfo and pdftoppm.
All outputs, including publish tests, go to disposable destinations.
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
TOOLS = (
    "build-referral-card5-moo-print.py",
    "build-referral-card5-cropmarks-press.py",
    "refine-referral-card5-front-back.py",
    "build-business-cards.py",
)


def snapshot(root):
    paths = list((root / "exports").rglob("*"))
    paths += list((root / "brand-assets").rglob("*"))
    paths += list((root / "website/elh-preview/assets").rglob("*"))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


class RemainingPrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = snapshot(ROOT)

    def tearDown(self):
        self.assertEqual(self.before, snapshot(ROOT),
                         "Approved assets, PDFs and source artwork must not change")

    def load(self, tool, root):
        with patch("tempfile.mkdtemp", side_effect=AssertionError("scratch during import")), \
                patch("shutil.copy", side_effect=AssertionError("copy during import")), \
                patch("subprocess.run", side_effect=AssertionError("command during import")), \
                patch("builtins.open", side_effect=AssertionError("file IO during import")):
            module = runpy.run_path(str(ROOT / "scripts" / tool))
        main = module["main"]
        main.__globals__["output_plan"] = functools.partial(output_plan, project_root=root)
        return module

    def invoke(self, main, args, expected=None):
        stream = io.StringIO()
        with redirect_stdout(stream), redirect_stderr(stream):
            if expected is None:
                main(args)
            else:
                with self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, expected, stream.getvalue())
        return stream.getvalue()

    def targets(self, module, root):
        if "CARDS" in module:
            return [root / "exports/print" / f"{slug}.html" for slug in module["CARDS"]]
        card = Path(module.get("CARD", module.get("OUT")))
        cmyk = Path(module["CMYK"])
        if cmyk.suffix != ".pdf":
            cmyk /= card.name.replace(".pdf", "-CMYK.pdf")
        return [root / card.relative_to(ROOT), root / cmyk.relative_to(ROOT)]

    def fixture_inputs(self, module, root):
        # Keep the missing legacy QR name out of the real tree. Supplying existing
        # artwork under that name here exercises the renderer without changing
        # its input policy (handled separately from this safety maintenance).
        if "prepare_work" in module and "ASSETS" in module:
            owner = module["main"].__globals__
        elif "moo" in module:
            owner = module["moo"].__dict__
        else:
            owner = None
        if owner is not None:
            assets = root / "fixture-assets"
            (assets / "img").mkdir(parents=True)
            shutil.copytree(ROOT / "website/elh-preview/assets/fonts", assets / "fonts")
            shutil.copy2(ROOT / "website/elh-preview/assets/img/qr-refer-cream.webp",
                         assets / "img/qr-refer-cream.png")
            owner["ASSETS"] = str(assets)
        if "source_card" in module["build"].__code__.co_varnames:
            source = root / "original.pdf"
            shutil.copy2(ROOT / "exports/print/eternal-life-referral-card-5-quick-referral-action.pdf",
                         source)
            qr = root / "original-qr.png"
            shutil.copy2(ROOT / "website/elh-preview/assets/qr-refer.png", qr)
            return ["--source-card", str(source), "--qr-tile", str(qr)]
        return []

    def test_explicit_modes_collisions_and_failed_full_sets(self):
        for tool in TOOLS:
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                module = self.load(tool, root)
                main = module["main"]
                targets = self.targets(module, root)
                for target in targets:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"approved sentinel")
                old = [p.read_bytes() for p in targets]
                for args in ([], ["--overwrite"], ["--publish"],
                             ["--publish", "--output-dir", str(root / "proofs")],
                             ["--temp-dir", "--output-dir", str(root / "proofs")],
                             [str(root / "legacy-positional")]):
                    with patch("tempfile.mkdtemp", side_effect=AssertionError("scratch before preflight")):
                        self.invoke(main, args, 2)
                for protected in (root / "exports", root / "website/elh-preview"):
                    protected.mkdir(parents=True, exist_ok=True)
                    alias = root / f"alias-{protected.name}"
                    alias.symlink_to(protected, target_is_directory=True)
                    for destination in (protected, alias):
                        self.invoke(main, ["--output-dir", str(destination), "--overwrite"], 2)
                # A later collision must not cause the first output to appear.
                targets[0].unlink()
                self.invoke(main, ["--publish"], 2)
                self.assertFalse(targets[0].exists())
                targets[0].write_bytes(old[0])
                proofs = root / "proofs"
                proofs.mkdir()
                for target in targets:
                    (proofs / target.name).write_bytes(b"old proof")
                extra = self.fixture_inputs(module, root)

                def failed_build(*args):
                    if tool == TOOLS[-1]:
                        # First HTML is already staged when the second fails.
                        if args[0] == "Full Name":
                            raise RuntimeError("forced final output failure")
                        return "first proof"
                    args[0].write_bytes(b"staged RGB")
                    raise RuntimeError("forced final output failure")

                with patch.dict(main.__globals__, build=failed_build):
                    for args in (["--publish", "--overwrite"],
                                 ["--output-dir", str(proofs), "--overwrite"]):
                        with self.assertRaisesRegex(RuntimeError, "forced final output failure"):
                            self.invoke(main, args + extra)
                        self.assertEqual(old, [p.read_bytes() for p in targets])
                        self.assertTrue(all(p.read_bytes() == b"old proof" for p in proofs.iterdir()))

                def successful_build(*args):
                    if tool == TOOLS[-1]:
                        return "verified HTML"
                    for path in args[:2]:
                        path.write_bytes(b"verified PDF")

                with patch.dict(main.__globals__, build=successful_build):
                    self.invoke(main, ["--publish", "--overwrite"] + extra)
                    self.assertTrue(all(b"verified" in p.read_bytes() for p in targets))
                    self.invoke(main, ["--output-dir", str(proofs), "--overwrite"] + extra)
                    self.assertTrue(all(b"verified" in p.read_bytes() for p in proofs.iterdir()))
                    for target in targets:
                        target.unlink()
                    self.invoke(main, ["--publish"] + extra)
                    self.assertTrue(all(p.is_file() for p in targets))
                    log = self.invoke(main, ["--temp-dir"] + extra)
                    temp = Path(next(line.split(": ", 1)[1] for line in log.splitlines()
                                     if line.startswith("Proof directory")))
                    self.addCleanup(shutil.rmtree, temp)
                    self.assertEqual(len(list(temp.iterdir())), len(targets))

    def test_real_proofs_geometry_and_conversion_failure(self):
        dimensions = ("276 x 624 pts", "318 x 666 pts", "288 x 594 pts", None)
        for tool, size in zip(TOOLS, dimensions):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                module = self.load(tool, root)
                main = module["main"]
                extra = self.fixture_inputs(module, root)
                proofs = root / "proofs"
                real_run = subprocess.run
                calls = []

                def record(command, *args, **kwargs):
                    calls.append(command)
                    return real_run(command, *args, **kwargs)

                with patch("subprocess.run", side_effect=record):
                    self.invoke(main, ["--output-dir", str(proofs)] + extra)
                self.assertEqual({p.name for p in self.targets(module, root)},
                                 {p.name for p in proofs.iterdir()})
                for proof in proofs.iterdir():
                    if size is None:
                        html = proof.read_text()
                        self.assertEqual(html.count('<div class="page">'), 2)
                        self.assertIn("@page{size:4in 2.5in;margin:0}", html)
                        self.assertIn((ROOT / "website/elh-preview/assets").as_uri(), html)
                    else:
                        info = real_run(["pdfinfo", "-f", "1", "-l", "2", str(proof)],
                                        capture_output=True, text=True, check=True).stdout
                        self.assertIn("Pages:           2", info)
                        self.assertEqual(info.count(size), 2, info)
                        real_run(["qpdf", "--check", str(proof)], capture_output=True, check=True)
                conversions = [c for c in calls if c[0] == "gs"]
                self.assertEqual(len(conversions), 0 if size is None else 1)
                for cmd in conversions:
                    for flag in ("-sColorConversionStrategy=CMYK", "-dProcessColorModel=/DeviceCMYK",
                                 "-dPDFSETTINGS=/prepress"):
                        self.assertIn(flag, cmd)
                    if tool in TOOLS[:2]:
                        for flag in ("-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
                                     "-dDownsampleMonoImages=false", "-dAutoFilterColorImages=false",
                                     "-dAutoFilterGrayImages=false", "-dColorImageFilter=/FlateEncode",
                                     "-dGrayImageFilter=/FlateEncode"):
                            self.assertIn(flag, cmd)
                    else:
                        for flag in ("-dSAFER", "-dOverrideICC=true", "-dAutoRotatePages=/None"):
                            self.assertIn(flag, cmd)
                if tool == TOOLS[1]:
                    raster = [c for c in calls if c[0] == "pdftoppm"]
                    self.assertEqual(len(raster), 2)
                    self.assertTrue(all(c[c.index("-r") + 1] == "600" for c in raster))
                before = {p.name: p.read_bytes() for p in proofs.iterdir()}
                self.invoke(main, ["--output-dir", str(proofs)] + extra, 2)
                if size is not None:
                    def fail_conversion(command, *args, **kwargs):
                        if command[0] == "gs":
                            return subprocess.CompletedProcess(command, 1, "", "forced failure")
                        return real_run(command, *args, **kwargs)
                    with patch("subprocess.run", side_effect=fail_conversion):
                        self.invoke(main, ["--output-dir", str(proofs), "--overwrite"] + extra, 1)
                    self.assertEqual(before, {p.name: p.read_bytes() for p in proofs.iterdir()})

    def test_artwork_is_unchanged(self):
        expected = {
            TOOLS[0]: {
                "FRONT": "eb6c4b0cb32fb4406d4e32e7427bc06e5f5e15b56d3d6070c307b2e26e81f6ac",
                "BACK": "66d718064804e0ac23462d97478197d60413dfd84d323acde284cc70f8813057",
                "CARD_CSS": "a0a713e2d32649730cd39b01266175c5be812438cf1baf6bed23571e3f7b7562",
                "HTML": "d2963d0653a6ad983a048719810f19a94b9c6d0aaa6e902ddb4640ac9a5f034e",
            },
            TOOLS[2]: {
                "CSS": "8005c3086520d8b67738d854f481fa238db4f68e7b01ca8bd18285785477e3e6",
                "front": "ded2c8a83a4426c443d6c07e557b5f3fa904a90d476f1e65e24c1caa0a2ad080",
                "back": "a0e6d7f28df1ea1f1fdb3ca95a3591a0302098b2ee5575920e14c83f96d694b2",
            },
            TOOLS[3]: {
                "CSS": "e3e19ce890aaca9e8b02b54ffd7be401b4d63d4b1af9b511be8148694d3e01a3",
                "PAGE": "5c7340088ba77aac17c4dba0e705655425a49be14ce68e0f5e3b6a09e08f08a6",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            for tool, constants in expected.items():
                module = self.load(tool, Path(tmp))
                for key, digest in constants.items():
                    self.assertEqual(hashlib.sha256(module[key].encode()).hexdigest(), digest)
            crop = self.load(TOOLS[1], Path(tmp))
            html = crop["build_html"]("cardfront.png", "cardback.png")
            # Baseline includes every mark, edge-clamp slice and coordinate.
            self.assertEqual(hashlib.sha256(html.encode()).hexdigest(),
                             "afd87d9d96e2a25c5c8838d21af0f67a11bed8326285e7a523dfc12776d8b14b")


if __name__ == "__main__":
    unittest.main()