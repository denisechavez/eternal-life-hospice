"""Offline regression suite; all exports go to a disposable workspace.

Run: python3 -m unittest discover -s .agents/scripts -p test_manual_social_package.py
"""
import contextlib
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

from social_copy_contract import (
    expected_rows, LICENSE_URL, MANUAL_CREDIT, manual_caption,
    THRYV_CREDIT, thryv_caption, validate_rows,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".agents/scripts"
spec = importlib.util.spec_from_file_location(
    "manual_package", SCRIPTS / "package-manual-social-test.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
COPY = "exports/social/october-27-31-2026-copy.json"
ARTICLES = "website/content/30-day-journal/additional-2026-q4.json"
CREDITS = "website/content/journal-q4-photo-sources.json"
POSTS = "generated-artifacts/social-2026-10-27-31/posts.json"
CSV_NAME = "generated-artifacts/Eternal-Thryv-October-27-31-2026-SEO-Daily-All-Platforms.csv"


class ManualSocialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.topics = json.loads((ROOT / COPY).read_text())
        cls.articles = {r["slug"]: r for r in json.loads((ROOT / ARTICLES).read_text())}
        cls.credits = {r["slug"]: r for r in json.loads((ROOT / CREDITS).read_text())}
        cls.posts = json.loads((ROOT / POSTS).read_text())
        cls.expected = expected_rows(cls.topics, cls.articles, cls.credits, cls.posts)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in (COPY, ARTICLES, CREDITS, POSTS, "website/content/seo-keyword-master.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        scripts = self.root / ".agents/scripts"
        scripts.mkdir(parents=True)
        for name in ("create-thryv-upload-csv.py", "social_copy_contract.py"):
            shutil.copyfile(SCRIPTS / name, scripts / name)
        self.out = self.root / "generated-artifacts" / package.NAME
        self.out.mkdir()
        self.manifest = []
        for topic in self.topics:
            for platform, size in package.FORMATS.items():
                relative = f"{platform}/{topic['date']}.jpg"
                path = self.out / relative
                path.parent.mkdir(exist_ok=True)
                Image.new("RGB", size, "#663366").save(path)
                self.manifest.append({
                    "date": topic["date"], "platform": platform, "image_file": relative,
                    "dimensions": {"width": size[0], "height": size[1]},
                    "source_photo": "website/elh-preview" + self.articles[topic["slug"]]["heroImage"],
                    "headline": topic["headline"].replace("\n", " "),
                })
        self.write_manifest()
        self.rows = list(copy.deepcopy(self.expected).values())
        self.write_csv()
        original = package.ROOT, package.OUT, package.CSV
        package.ROOT, package.OUT, package.CSV = self.root, self.out, self.root / CSV_NAME
        self.addCleanup(self.restore, original)

    @staticmethod
    def restore(original):
        package.ROOT, package.OUT, package.CSV = original

    def write_manifest(self):
        (self.out / "image-manifest.json").write_text(json.dumps(self.manifest))

    def write_csv(self):
        with (self.root / CSV_NAME).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.expected.values())[0])
            writer.writeheader()
            writer.writerows(self.rows)

    def run_package(self):
        with contextlib.redirect_stdout(io.StringIO()):
            package.main()

    def assert_rejected_before_output(self, message):
        # A rejected rebuild must not replace an earlier download or caption.
        archive = self.out.with_suffix(".zip")
        caption = self.out / "GBP/2026-10-27-caption.txt"
        archive.write_bytes(b"previous archive")
        caption.write_text("previous caption")
        with self.assertRaisesRegex(ValueError, message):
            self.run_package()
        self.assertEqual(archive.read_bytes(), b"previous archive")
        self.assertEqual(caption.read_text(), "previous caption")

    def test_changed_source_caption_rejects_stale_csv(self):
        topics = copy.deepcopy(self.topics)
        topics[0]["posts"]["GBP"]["caption"] += "\nRevised draft."
        (self.root / COPY).write_text(json.dumps(topics))
        self.assert_rejected_before_output("Stale CSV Caption")

    def test_changed_csv_fields_are_rejected(self):
        for field in ("Caption", "Title", "Link", "Image", "Approved", "Recycle", "Schedule"):
            with self.subTest(field=field):
                rows = copy.deepcopy(self.rows)
                rows[0][field] += " changed"
                with self.assertRaisesRegex(ValueError, f"Stale CSV {field}"):
                    validate_rows(rows, self.expected)

    def test_shuffled_rows_and_complete_archive(self):
        random.Random(990).shuffle(self.rows)
        self.write_csv()
        (self.out / "private-notes.txt").write_text("must not export")
        (self.out / "GBP/old-caption.txt").write_text("must not export")
        self.run_package()
        names = {"00-START-HERE.txt", "ALL-CAPTIONS.txt", "PHOTO-CREDITS.txt",
                 "MANUAL-CONTENT.csv", "image-manifest.json"}
        for date, platform in self.expected:
            names.update(f"{platform}/{date}{suffix}" for suffix in
                         (".jpg", "-caption.txt", "-details.txt"))
        with zipfile.ZipFile(self.out.with_suffix(".zip")) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 65)
            self.assertEqual(set(archive.namelist()), {f"{package.NAME}/{n}" for n in names})
            table = list(csv.DictReader(io.StringIO(
                archive.read(f"{package.NAME}/MANUAL-CONTENT.csv").decode("utf-8-sig"))))
            self.assertEqual(len(table), 20)
            for row in table:
                expected = self.expected[row["Date"], row["Platform"]]
                self.assertEqual(row["Caption"], manual_caption(expected["Caption"]))
                self.assertEqual(row["Link"], expected["Link"])
                caption = archive.read(f"{package.NAME}/{row['CaptionFile']}").decode()
                self.assertEqual(caption, row["Caption"] + "\n")
                details = archive.read(f"{package.NAME}/{row['DetailsFile']}").decode()
                self.assertIn(row["Title"], details)
                self.assertIn(row["Link"], details)
                self.assertIn(row["Caption"], archive.read(
                    f"{package.NAME}/ALL-CAPTIONS.txt").decode())
                with Image.open(io.BytesIO(archive.read(
                        f"{package.NAME}/{row['ImageFile']}"))) as image:
                    self.assertEqual(image.size, package.FORMATS[row["Platform"]])

    def test_missing_pair(self):
        self.rows.pop()
        self.write_csv()
        self.assert_rejected_before_output("Missing CSV pairs")

    def test_duplicate_replacing_pair_at_same_count(self):
        self.rows[-1] = self.rows[0]
        self.write_csv()
        self.assert_rejected_before_output("Duplicate CSV pair")

    def test_unexpected_pair(self):
        self.rows[0]["Title"] = "GBP | 2026-11-01 | Unexpected"
        self.write_csv()
        self.assert_rejected_before_output("Unexpected CSV pair")

    def test_malformed_title(self):
        self.rows[0]["Title"] = "broken"
        self.write_csv()
        self.assert_rejected_before_output("Malformed CSV Title")

    def test_url_slug_and_source_date_mismatch(self):
        for field, value, message in (
            ("slug", "different-slug", "Missing source article link"),
            ("proposedDate", "2026-11-01", "Source link/date mismatch"),
            ("link", "https://eternallifehospice.com/blog/wrong", "URL/slug mismatch"),
        ):
            posts = copy.deepcopy(self.posts)
            for post in posts:
                if post["slug"] == self.topics[0]["slug"]:
                    if field == "link":
                        post["row"]["Link"] = value
                    else:
                        post[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                expected_rows(self.topics, self.articles, self.credits, posts)

    def test_license_credit_transformations(self):
        for topic in self.topics:
            credit = self.credits[topic["slug"]]
            for platform, spec in topic["posts"].items():
                row = self.expected[topic["date"], platform]
                manual = manual_caption(row["Caption"])
                if credit["license"] == "CC BY-SA 4.0":
                    self.assertEqual(row["Caption"].count(THRYV_CREDIT), 1)
                    self.assertEqual(manual.count(MANUAL_CREDIT), 1)
                    self.assertIn(credit["sourceUrl"], manual)
                    self.assertIn(LICENSE_URL, manual)
                    self.assertNotIn(THRYV_CREDIT, manual)
                else:
                    self.assertEqual(row["Caption"], spec["caption"].replace("{url}", row["Link"]))
                    self.assertEqual(manual, row["Caption"])
                self.assertEqual(manual_caption(manual), manual)
        credit = self.credits[self.topics[0]["slug"]]
        cropped = thryv_caption({"caption": "CC BY-SA 4.0; cropped."}, "https://example.org", credit)
        self.assertTrue(cropped.startswith("CC BY-SA 4.0; resized."))
        with self.assertRaisesRegex(ValueError, "Unsupported CC BY-SA credit"):
            thryv_caption({"caption": "Test"}, "", {**credit, "author": "Someone else"})

    def test_stale_headline_manifest(self):
        topics = copy.deepcopy(self.topics)
        topics[0]["headline"] = "A revised headline"
        (self.root / COPY).write_text(json.dumps(topics))
        self.assert_rejected_before_output("Stale image manifest headline")

    def test_incomplete_or_mismatched_manifest(self):
        original = copy.deepcopy(self.manifest)
        for mutation, message in (
            (lambda m: m.pop(), "Missing image manifest pairs"),
            (lambda m: m.__setitem__(-1, m[0]), "Duplicate or unexpected"),
            (lambda m: m[0].update(source_photo="wrong.jpg"), "Stale image manifest source_photo"),
        ):
            self.manifest = copy.deepcopy(original)
            mutation(self.manifest)
            self.write_manifest()
            with self.subTest(message=message):
                self.assert_rejected_before_output(message)

    def test_missing_image_fails_before_writing(self):
        (self.out / "Pinterest/2026-10-31.jpg").unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_package()
        self.assertFalse((self.out / "GBP/2026-10-27-caption.txt").exists())

    def test_generator_and_packager_agree(self):
        result = subprocess.run(
            [sys.executable, str(self.root / ".agents/scripts/create-thryv-upload-csv.py")],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (self.root / CSV_NAME).open(encoding="utf-8-sig", newline="") as stream:
            generated = list(csv.DictReader(stream))
        self.assertEqual(len(validate_rows(generated, self.expected)), 20)
        self.run_package()


if __name__ == "__main__":
    unittest.main()
