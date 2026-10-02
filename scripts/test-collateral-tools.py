#!/usr/bin/env python3
"""Test locked optional collateral tools in a disposable Replit workspace.

Run: python3 scripts/test-collateral-tools.py
Only inputs are copied from the real project; all generated assets and package
installs stay in a temporary directory. Requires uv and the Replit Python module.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("build-refer-qr.py", "build-media-kit-qr.py", "build-media-kit-pdf.py")


class CollateralToolsTests(unittest.TestCase):
    def run_command(self, root, *command):
        env = dict(os.environ)
        env["UV_PROJECT_ENVIRONMENT"] = str(root / ".pythonlibs")
        env["UV_CACHE_DIR"] = str(root / ".cache" / "uv")
        # Do not inherit installed workspace packages into the clean fixture.
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        result = subprocess.run(command, cwd=root, env=env, text=True,
                                capture_output=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout + result.stderr, end="")
        return result.stdout

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
        with tempfile.TemporaryDirectory(prefix="elh-collateral-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            for name in ("pyproject.toml", "uv.lock"):
                shutil.copy2(ROOT / name, root / name)
            for name in (*TOOLS, "setup-python-environment.py"):
                shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
            for source in source_assets:
                target = root / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
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
            self.run_command(root, python, "scripts/build-media-kit-pdf.py")
            site_pdf = root / approved_outputs[-2].relative_to(ROOT)
            export_pdf = root / approved_outputs[-1].relative_to(ROOT)
            self.assertEqual(site_pdf.read_bytes(), export_pdf.read_bytes())
            # Verify real PDF page count with the existing Replit system tool.
            info = self.run_command(root, "qpdf", "--show-npages", str(site_pdf))
            self.assertEqual(int(info.strip()), len(pages))

            self.run_command(root, "uv", "sync", "--locked", "--extra", "qr")
            for name in TOOLS[:2]:
                output = self.run_command(root, python, f"scripts/{name}")
                self.assertEqual(output.count(" OK"), 2)
            self.run_command(
                root, python, "-I", "-c",
                "from pathlib import Path; from PIL import Image; "
                f"root = Path({str(root)!r}) / 'website/elh-preview/assets'; "
                "assert all(Image.open(root / f'qr-{n}.png').size == (1480,1480) "
                "for n in ('refer','media-kit')); "
                "assert all(Image.open(root / f'img/qr-{n}-cream.png').size == (1024,1024) "
                "for n in ('refer','media-kit'))",
            )
            # A normal publish after using tools must remove optional packages.
            self.run_command(root, "uv", "sync", "--locked", "--no-default-groups")
            self.run_command(root, python, "-I", "-c", no_tools)
            self.assertEqual((root / "uv.lock").read_bytes(),
                             (ROOT / "uv.lock").read_bytes())
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists()
                 else None for p in protected}
        self.assertEqual(before, after, "Approved assets must remain untouched")


if __name__ == "__main__":
    unittest.main()