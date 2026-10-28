#!/usr/bin/env python3
"""Package the approved full-photo test graphics and copy for manual posting."""
import csv
import io
import json
from pathlib import Path
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
NAME = "Eternal-Manual-Social-October-27-31-2026"
OUT = ROOT / "generated-artifacts" / NAME
CSV = ROOT / "generated-artifacts/Eternal-Thryv-October-27-31-2026-SEO-Daily-All-Platforms.csv"
FORMATS = {
    "GBP": (1200, 900),
    "Facebook": (1080, 1350),
    "LinkedIn": (1200, 627),
    "Pinterest": (1000, 1500),
}


def main():
    topics = json.loads((ROOT / "exports/social/october-27-31-2026-copy.json").read_text())
    articles = {row["slug"]: row for row in json.loads(
        (ROOT / "website/content/30-day-journal/additional-2026-q4.json").read_text())}
    credits = {row["slug"]: row for row in json.loads(
        (ROOT / "website/content/journal-q4-photo-sources.json").read_text())}
    with CSV.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    row_lookup = {}
    for row in rows:
        platform, date, _ = row["Title"].split(" | ", 2)
        assert (date, platform) not in row_lookup
        row_lookup[date, platform] = row
    assert len(row_lookup) == 20
    OUT.mkdir(parents=True, exist_ok=True)
    all_copy, credit_notes, table, expected = [], [], [], set()
    for topic in topics:
        date, slug = topic["date"], topic["slug"]
        article, credit = articles[slug], credits[slug]
        credit_notes.append(
            f"{date} — {article['title']}\n"
            f"Photographer: {credit['author']}\nLicense: {credit['license']}\n"
            f"Source: {credit['sourceUrl']}\nLicense URL: {credit['licenseUrl']}\n"
            "Adaptations: cropped, resized and overlaid with headline/branding.\n"
        )
        assert set(topic["posts"]) == set(FORMATS)
        for platform, spec in topic["posts"].items():
            row = row_lookup[date, platform]
            assert row["Approved"] == "FALSE" and not row["Schedule"]
            caption = row["Caption"].replace(
                "Photo: Niceley, CC BY-SA 4.0; resized.",
                "Photo: Niceley, CC BY-SA 4.0; cropped and color-adjusted.")
            limit = {"GBP": 1500, "Facebook": 63206, "LinkedIn": 3000, "Pinterest": 500}[platform]
            assert len(caption) <= limit, (date, platform, len(caption))
            if platform == "Pinterest":
                assert len(spec["title"]) <= 100
            if credit["license"] == "CC BY-SA 4.0":
                assert credit["sourceUrl"] in caption
                assert "https://creativecommons.org/licenses/by-sa/4.0/" in caption
            image_file = f"{platform}/{date}.jpg"
            caption_file = f"{platform}/{date}-caption.txt"
            details_file = f"{platform}/{date}-details.txt"
            with Image.open(OUT / image_file) as image:
                assert image.size == FORMATS[platform], (image_file, image.size)
                image.verify()
            (OUT / caption_file).write_text(caption + "\n", encoding="utf-8")
            headline = topic["headline"].replace("\n", " ")
            alt = f"{article['heroImageAlt']} Full-photo graphic headline: {headline}"
            title_label = "PINTEREST PIN TITLE" if platform == "Pinterest" else "INTERNAL POST REFERENCE"
            details = (
                f"{platform} | {date}\n\n"
                f"{title_label}\n{spec['title']}\n\n"
                f"ARTICLE LINK\n{row['Link']}\n\n"
                f"IMAGE FILE\n{date}.jpg\n"
                f"IMAGE SIZE\n{FORMATS[platform][0]} × {FORMATS[platform][1]}\n\n"
                f"CAPTION FILE\n{date}-caption.txt\n\n"
                f"SUGGESTED IMAGE ALT TEXT\n{alt}\n\n"
                "REVIEW NOTE\nThis is a prepared manual-posting draft, not an approved or scheduled post.\n"
                "Confirm the matching article is publicly available before posting its link.\n"
                "Keep the photo attribution in the caption where supplied.\n"
            )
            if platform == "GBP":
                details += "\nGBP BUTTON\nUse Learn more with the ARTICLE LINK above.\n"
            (OUT / details_file).write_text(details, encoding="utf-8")
            table.append({"Date": date, "Platform": platform, "Title": spec["title"],
                          "Caption": caption, "Link": row["Link"], "ImageFile": image_file,
                          "CaptionFile": caption_file, "DetailsFile": details_file, "AltText": alt})
            all_copy.append(
                f"{'=' * 72}\n{platform.upper()} | {date}\n"
                f"Title/reference: {spec['title']}\nImage: {image_file}\n"
                f"Article link: {row['Link']}\n\nCAPTION TO COPY:\n{caption}\n\n"
            )
            expected.update((image_file, caption_file, details_file))
    assert len(table) == 20
    assert len(expected) == 60
    (OUT / "ALL-CAPTIONS.txt").write_text("".join(all_copy), encoding="utf-8")
    (OUT / "PHOTO-CREDITS.txt").write_text("\n".join(credit_notes), encoding="utf-8")
    with (OUT / "MANUAL-CONTENT.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    instructions = """ETERNAL LIFE HOSPICE — MANUAL SOCIAL TEST RUN
October 27–31, 2026 | Style 1: Full photograph

20 prepared posts: one daily on GBP, Facebook, LinkedIn and Pinterest.
These files are for manual uploading. Nothing has been posted, approved or
scheduled. The ZIP does not require Thryv or publicly hosted image files.

1. Unzip this download.
2. Open the folder for the platform you want to post on.
3. Upload the JPEG named for the date.
4. Open the matching -caption.txt and paste that text into the post.
5. Use -details.txt for the article link, Pinterest title and optional alt text.
6. Preview the post on the correct profile and review it before publishing.

The caption files contain only the public caption, not internal instructions.
For Pinterest, paste the Pin title and article link from the details file into
their separate fields. For GBP, use Learn more with the article link.

ALL-CAPTIONS.txt combines every caption for convenient review.
MANUAL-CONTENT.csv is an optional spreadsheet reference, NOT a Thryv import.
PHOTO-CREDITS.txt records the source and license for each photograph.

Keep the photo credit and license/source links in October 27 captions.
The source photos are illustrative; do not present them as Eternal patients.
Check that each article is publicly available before sharing its link.
Dates are proposed posting dates in America/Los_Angeles; no times are set.

IMAGE SIZES
GBP: 1200 × 900
Facebook: 1080 × 1350
LinkedIn: 1200 × 627
Pinterest: 1000 × 1500

All graphics use the selected full-photo direction with the Eternal logo at
bottom right. No eyebrow, descriptive subline or detached lower text panel.
"""
    (OUT / "00-START-HERE.txt").write_text(instructions, encoding="utf-8")
    expected.update(("00-START-HERE.txt", "ALL-CAPTIONS.txt", "PHOTO-CREDITS.txt",
                     "MANUAL-CONTENT.csv", "image-manifest.json"))
    assert (OUT / "image-manifest.json").is_file()
    archive_path = OUT.with_suffix(".zip")
    # Explicit allowlist: no source code, unapproved variants or temporary files.
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(expected):
            archive.write(OUT / relative, f"{NAME}/{relative}")
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 65
        for relative in sorted(expected):
            assert archive.read(f"{NAME}/{relative}") == (OUT / relative).read_bytes()
        for row in table:
            decoded = archive.read(f"{NAME}/{row['CaptionFile']}").decode("utf-8").rstrip("\n")
            assert decoded == row["Caption"]
            with Image.open(io.BytesIO(archive.read(f"{NAME}/{row['ImageFile']}"))) as image:
                assert image.size == FORMATS[row["Platform"]]
    print(f"Verified {len(table)} posts, 20 JPEGs, complete captions, dimensions and ZIP integrity.")
    print(f"{archive_path.relative_to(ROOT)} ({archive_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
