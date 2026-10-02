#!/usr/bin/env python3
"""Test locked optional collateral tools in a disposable Replit workspace.

Run: python3 scripts/test-collateral-tools.py
Runs the actual builders against checked-in inputs, using proof options.
All generated assets and package installs stay in a temporary directory.
Requires uv and the Replit Python module.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
import io
from collateral_output import output_plan


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("build-refer-qr.py", "build-media-kit-qr.py", "build-media-kit-pdf.py")


class OutputProtectionTests(unittest.TestCase):
    def test_protection_and_explicit_publish_in_disposable_tree(self):
        with tempfile.TemporaryDirectory(prefix="elh-output-policy-") as directory:
            root = Path(directory)
            outputs = [
                ("proof.png", "website/elh-preview/assets/master.png"),
                ("proof.png", "exports/digital/master.png"),
            ]
            targets = [root / approved for _, approved in outputs]
            for target in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"approved")

            def plan(*args):
                return output_plan("Test output policy", outputs, args, root)

            def refused(*args):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    plan(*args)
                self.assertEqual(error.exception.code, 2)
                self.assertTrue(all(p.read_bytes() == b"approved" for p in targets))

            refused()
            refused("--overwrite")
            refused("--publish")
            refused("--publish", "--output-dir", str(root / "proofs"))
            # A collision in a later mirror must be found before any writes.
            targets[0].unlink()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                plan("--publish")
            self.assertFalse(targets[0].exists())
            self.assertEqual(targets[1].read_bytes(), b"approved")
            targets[0].write_bytes(b"approved")
            for protected in (root / "website/elh-preview", root / "exports"):
                refused("--output-dir", str(protected), "--overwrite")
                alias = root / f"alias-{protected.name}"
                alias.symlink_to(protected, target_is_directory=True)
                refused("--output-dir", str(alias), "--overwrite")
            refused("--output-dir", str(root / "website/elh-preview/../elh-preview"))

            proof_dir = root / "proofs"
            proof = proof_dir / "proof.png"
            with plan("--output-dir", str(proof_dir)).stage() as paths:
                self.assertEqual(len(paths), 1)
                paths[0].write_bytes(b"first proof")
                self.assertFalse(proof.exists())
            self.assertEqual(proof.read_bytes(), b"first proof")
            refused("--output-dir", str(proof_dir))
            with plan("--output-dir", str(proof_dir), "--overwrite").stage() as paths:
                paths[0].write_bytes(b"updated proof")
            self.assertEqual(proof.read_bytes(), b"updated proof")
            # Failed generation must leave every old approved destination intact.
            with self.assertRaisesRegex(RuntimeError, "failed build"):
                with plan("--publish", "--overwrite").stage() as paths:
                    paths[0].write_bytes(b"unverified")
                    raise RuntimeError("failed build")
            self.assertTrue(all(p.read_bytes() == b"approved" for p in targets))
            with plan("--publish", "--overwrite").stage() as paths:
                for path in paths:
                    path.write_bytes(b"verified")
            self.assertTrue(all(p.read_bytes() == b"verified" for p in targets))
            # Publishing a missing destination is intentional but needs no overwrite.
            for target in targets:
                target.unlink()
            with plan("--publish").stage() as paths:
                for path in paths:
                    path.write_bytes(b"new approved")
            self.assertTrue(all(p.read_bytes() == b"new approved" for p in targets))
            # Reject symlink files even when overwrite is requested.
            proof.unlink()
            proof.symlink_to(targets[0])
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                plan("--output-dir", str(proof_dir), "--overwrite")
            self.assertEqual(targets[0].read_bytes(), b"new approved")
            # A directory symlink cannot redirect publish writes.
            targets[0].unlink()
            targets[0].parent.rmdir()
            targets[0].parent.symlink_to(proof_dir, target_is_directory=True)
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                plan("--publish", "--overwrite")

    def test_exclusive_creation_protects_output_created_during_build(self):
        with tempfile.TemporaryDirectory(prefix="elh-output-race-") as directory:
            root = Path(directory)
            plan = output_plan("Race test", [("proof.png", "exports/master.png")],
                               ["--output-dir", str(root)], root)
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                with plan.stage() as paths:
                    paths[0].write_bytes(b"generated")
                    (root / "proof.png").write_bytes(b"someone else's file")
            self.assertEqual((root / "proof.png").read_bytes(), b"someone else's file")


class CollateralToolsTests(unittest.TestCase):
    def run_command(self, root, *command, expected=0):
        env = dict(os.environ)
        env["UV_PROJECT_ENVIRONMENT"] = str(root / ".pythonlibs")
        env["UV_CACHE_DIR"] = str(root / ".cache" / "uv")
        # Do not inherit installed workspace packages into the clean fixture.
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        result = subprocess.run(command, cwd=root, env=env, text=True,
                                capture_output=True, timeout=240)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        print(result.stdout + result.stderr, end="")
        return result.stdout + result.stderr

    def test_fresh_optional_installs_and_temporary_outputs(self):
        # Reading the PDF tool's page list imports Pillow, so use the AST instead.
        import ast
        tree = ast.parse((ROOT / "scripts" / "build-media-kit-pdf.py").read_text())
        pages = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "PAGES"
                             for t in node.targets))
        source_assets = [ROOT / "website/elh-preview/assets/img/qr-cream.webp"]
        source_assets += [ROOT / "website/elh-preview/assets/kit" / p for p in pages]
        approved_outputs = [
            ROOT / "website/elh-preview/assets/qr-refer.png",
            ROOT / "website/elh-preview/assets/img/qr-refer-cream.png",
            ROOT / "website/elh-preview/assets/qr-media-kit.png",
            ROOT / "website/elh-preview/assets/img/qr-media-kit-cream.png",
            ROOT / "website/elh-preview/assets/downloads/eternal-life-press-kit-digital.pdf",
            ROOT / "exports/digital/eternal-life-press-kit-digital.pdf",
        ]
        protected = source_assets + approved_outputs
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists()
                  else None for p in protected}
        def assert_approved_unchanged():
            after = {p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists()
                     else None for p in protected}
            self.assertEqual(before, after, "Approved assets must remain untouched")
        self.addCleanup(assert_approved_unchanged)
        with tempfile.TemporaryDirectory(prefix="elh-collateral-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            for name in ("pyproject.toml", "uv.lock"):
                shutil.copy2(ROOT / name, root / name)
            for name in ("setup-python-environment.py",):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            (root / "website").mkdir()
            for name in ("devserver", "chat_api", "coverage_api", "form_intake",
                         "google_reviews", "journal_preview"):
                shutil.copy2(ROOT / "website" / f"{name}.py",
                             root / "website" / f"{name}.py")
            for name in ("city-data.json", "city-aliases.json"):
                shutil.copy2(ROOT / "website" / name, root / "website" / name)
            base_python = Path(sys.base_prefix) / "bin" / (
                f"python{sys.version_info.major}.{sys.version_info.minor}")
            self.run_command(root, str(base_python),
                             "scripts/setup-python-environment.py")
            python = str(root / ".pythonlibs/bin/python")
            self.run_command(root, "uv", "sync", "--locked", "--no-default-groups")
            no_tools = (
                "import importlib.util,sys; "
                "assert sys.prefix != sys.base_prefix; "
                "assert all(importlib.util.find_spec(n) is None "
                "for n in ('PIL','numpy','qrcode','cv2')); "
                f"sys.path.insert(0, {str(root / 'website')!r}); "
                "import devserver; "
                "print('Website runtime imports OK: no tool packages')"
            )
            self.run_command(root, python, "-I", "-c", no_tools)

            # PDF-only installations must not pull in QR tooling.
            self.run_command(root, "uv", "sync", "--locked", "--extra", "print")
            self.run_command(
                root, python, "-I", "-c",
                "import importlib.util; from PIL import features; "
                "assert features.check('jpg'); "
                "assert all(importlib.util.find_spec(n) is None "
                "for n in ('numpy','qrcode','cv2'))",
            )
            pdf_tool = str(ROOT / "scripts" / TOOLS[2])
            proof_dir = root / "proofs"
            self.run_command(root, python, pdf_tool, "--output-dir", str(proof_dir))
            site_pdf = proof_dir / approved_outputs[-2].name
            # Verify real PDF page count with the existing Replit system tool.
            info = self.run_command(root, "qpdf", "--show-npages", str(site_pdf))
            self.assertEqual(int(info.strip()), len(pages))
            self.run_command(root, python, pdf_tool, "--output-dir", str(proof_dir),
                             expected=2)
            self.run_command(root, python, pdf_tool, "--output-dir", str(proof_dir),
                             "--overwrite")
            # Run the real PDF main and its mirror path, but redirect the policy's
            # project root into the disposable fixture, never into approved assets.
            publish_fixture = (
                "import functools,runpy,sys; "
                f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
                "import collateral_output; "
                "collateral_output.output_plan = functools.partial("
                f"collateral_output.output_plan, project_root={str(root)!r}); "
                f"sys.argv = [{pdf_tool!r}, '--publish']; "
                f"runpy.run_path({pdf_tool!r}, run_name='__main__')"
            )
            self.run_command(root, python, "-c", publish_fixture)
            published_site = root / approved_outputs[-2].relative_to(ROOT)
            published_export = root / approved_outputs[-1].relative_to(ROOT)
            self.assertEqual(published_site.read_bytes(), published_export.read_bytes())
            self.run_command(root, python, "-c", publish_fixture, expected=2)
            self.run_command(root, python, "-c",
                             publish_fixture.replace("'--publish'];",
                                                     "'--publish', '--overwrite'];"))
            self.assertEqual(published_site.read_bytes(), published_export.read_bytes())

            self.run_command(root, "uv", "sync", "--locked", "--extra", "qr")
            for name in TOOLS[:2]:
                output = self.run_command(root, python, str(ROOT / "scripts" / name),
                                          "--output-dir", str(proof_dir))
                self.assertEqual(output.count(" OK"), 2)
            self.run_command(
                root, python, "-I", "-c",
                "from pathlib import Path; from PIL import Image; "
                f"root = Path({str(proof_dir)!r}); "
                "assert all(Image.open(root / f'qr-{n}.png').size == (1480,1480) "
                "for n in ('refer','media-kit')); "
                "assert all(Image.open(root / f'qr-{n}-cream.png').size == (1024,1024) "
                "for n in ('refer','media-kit'))",
            )
            for name in TOOLS:
                tool = str(ROOT / "scripts" / name)
                self.run_command(root, python, tool, expected=2)
                self.run_command(root, python, tool, "--output-dir", str(proof_dir),
                                 expected=2)
                self.run_command(root, python, tool, "--output-dir",
                                 str(ROOT / "website/elh-preview/assets"),
                                 "--overwrite", expected=2)
                output = self.run_command(root, python, tool, "--temp-dir")
                temp_proofs = Path(next(
                    line.split(": ", 1)[1] for line in output.splitlines()
                    if line.startswith("Proof directory (kept for review): ")
                ))
                self.addCleanup(shutil.rmtree, temp_proofs)
                self.assertTrue(temp_proofs.is_dir())
                self.assertEqual(len(list(temp_proofs.iterdir())),
                                 1 if name == TOOLS[2] else 2)
                if name != TOOLS[2]:
                    qr_publish = publish_fixture.replace(repr(pdf_tool), repr(tool))
                    self.run_command(root, python, "-c", qr_publish)
                    self.run_command(root, python, "-c", qr_publish, expected=2)
                    output = self.run_command(
                        root, python, "-c",
                        qr_publish.replace("'--publish'];",
                                           "'--publish', '--overwrite'];"))
                    self.assertEqual(output.count(" OK"), 2)
            # Force decoder failure in the actual QR main: prior proofs survive.
            qr_tool = str(ROOT / "scripts" / TOOLS[0])
            failed_proofs = {p: p.read_bytes() for p in proof_dir.glob("qr-refer*.png")}
            failed_decode = (
                "import runpy,sys; from unittest.mock import patch; "
                f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
                f"tool = runpy.run_path({qr_tool!r}); "
                "main = tool['main']; "
                "patcher = patch.dict(main.__globals__, verify=lambda path: False); "
                "patcher.start(); "
                f"main(['--output-dir', {str(proof_dir)!r}, '--overwrite'])"
            )
            self.run_command(root, python, "-c", failed_decode, expected=1)
            self.assertTrue(all(p.read_bytes() == data for p, data in failed_proofs.items()))
            # A normal publish after using tools must remove optional packages.
            self.run_command(root, "uv", "sync", "--locked", "--no-default-groups")
            self.run_command(root, python, "-I", "-c", no_tools)
            self.assertEqual((root / "uv.lock").read_bytes(),
                             (ROOT / "uv.lock").read_bytes())


if __name__ == "__main__":
    unittest.main()