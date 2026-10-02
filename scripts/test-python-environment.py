#!/usr/bin/env python3
"""Exercise publishing and repair in a disposable Replit-shaped project."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ManagedPythonTests(unittest.TestCase):
    def run_command(self, root, *command):
        env = dict(os.environ)
        # Fixtures use the same managed layout without touching workspace tools.
        env["UV_PROJECT_ENVIRONMENT"] = str(root / ".pythonlibs")
        env["UV_CACHE_DIR"] = str(root / ".cache" / "uv")
        result = subprocess.run(command, cwd=root, env=env, text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_partial_environment_repair_extra_install_and_default_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            for name in ("pyproject.toml", "uv.lock"):
                shutil.copy2(ROOT / name, root / name)
            script = root / "scripts" / "setup-python-environment.py"
            shutil.copy2(ROOT / "scripts" / script.name, script)
            managed = root / ".pythonlibs"
            (managed / "bin").mkdir(parents=True)
            base_python = Path(sys.base_prefix) / "bin" / "python3.11"
            (managed / "bin" / "python").symlink_to(base_python)
            sentinel = managed / "keep-existing-tool.txt"
            sentinel.write_text("must survive environment repair")

            # Prime uv's interpreter cache with the original incorrect prefix.
            before = self.run_command(root, "uv", "sync", "--extra",
                                      "newsletter", "--dry-run")
            self.assertIn(str(Path(sys.base_prefix)), before)
            self.run_command(root, str(base_python), str(script))
            self.assertEqual(sentinel.read_text(), "must survive environment repair")
            cfg = (managed / "pyvenv.cfg").read_bytes()
            self.run_command(root, str(base_python), str(script))
            self.assertEqual((managed / "pyvenv.cfg").read_bytes(), cfg)

            self.run_command(root, "uv", "lock")
            self.run_command(root, "uv", "sync", "--extra", "newsletter")
            self.run_command(
                root, str(managed / "bin" / "python"), "-c",
                "import pathlib,sys,sysconfig; from PIL import Image; "
                f"assert pathlib.Path(sys.prefix) == pathlib.Path({str(managed)!r}); "
                "assert pathlib.Path(sysconfig.get_path('purelib')).is_relative_to(sys.prefix); "
                "Image.new('RGB', (32, 16), 'purple').save('newsletter.jpg'); "
                "assert Image.open('newsletter.jpg').size == (32, 16)",
            )
            # Default publishing intentionally excludes internal image tooling.
            self.run_command(root, "uv", "lock")
            self.run_command(root, "uv", "sync")
            self.run_command(root, str(managed / "bin" / "python"), "-c",
                             "import http.server, json, ssl")
            self.assertTrue(sentinel.exists())

    def test_newsletter_builder_reads_real_image_without_changing_body(self):
        sys.path.insert(0, str(ROOT / "website"))
        spec = importlib.util.spec_from_file_location(
            "newsletter_builder", ROOT / "website" / "build-journal-campaign.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            builder.PUBLIC = public
            builder.OUT = public / "blog"
            builder.OUT.mkdir()
            image = public / "assets" / "img" / "test.jpg"
            image.parent.mkdir(parents=True)
            builder.Image.new("RGB", (640, 320), "purple").save(image)
            article = builder.OUT / "test.html"
            body = "<body>Preserve the published copy.</body>"
            article.write_text(
                '<head><meta property="og:image" '
                'content="https://eternallifehospice.com/assets/img/test.jpg">'
                "</head>" + body)
            builder.update_image_dimensions([{"slug": "test"}])
            self.assertIn('content="640"', article.read_text())
            self.assertIn('content="320"', article.read_text())
            self.assertTrue(article.read_text().endswith(body))


if __name__ == "__main__":
    unittest.main()