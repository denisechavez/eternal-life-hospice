#!/usr/bin/env python3
"""Render the approved full-photo style as a manual-upload test package."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-artifacts/Eternal-Manual-Social-October-27-31-2026"
QA_OUT = ROOT / "generated-artifacts/social-manual-test-qa/contact-sheet.jpg"
COPY_PATH = ROOT / "exports/social/october-27-31-2026-copy.json"
ARTICLES_PATH = ROOT / "website/content/30-day-journal/additional-2026-q4.json"
APPROVED_FB = ROOT / "generated-artifacts/facebook-style-exploration/01-full-photo.jpg"
HELPER_PATH = ROOT / ".agents/scripts/build-fb-style-exploration.py"

PLUM = (72, 33, 63)
CREAM = "#F5F0EB"
GOLD = "#C9B07E"
PLATFORM_SIZES = {
    "GBP": (1200, 900),
    "Facebook": (1080, 1350),
    "LinkedIn": (1200, 627),
    "Pinterest": (1000, 1500),
}


def load_helper():
    spec = importlib.util.spec_from_file_location("approved_fb_style", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load approved style helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_path(hero_image: str) -> Path:
    return ROOT / "website/elh-preview" / hero_image.lstrip("/")


def tint_mask(size: tuple[int, int]) -> Image.Image:
    """A gentle upper-left vignette, matching the approved local contrast wash."""
    width, height = size
    horizontal = Image.linear_gradient("L").transpose(Image.Transpose.ROTATE_90)
    vertical = ImageOps.invert(Image.linear_gradient("L"))
    horizontal = horizontal.resize((width, height), Image.Resampling.BILINEAR)
    vertical = vertical.resize((width, height), Image.Resampling.BILINEAR)
    # Hold contrast across the complete headline, including bright walls;
    # fade smoothly outside the title area without adding a text panel.
    horizontal = horizontal.point(lambda value: min(255, round(value * 2.5)))
    vertical = vertical.point(lambda value: min(255, round(value * 1.3)))
    strength = ImageChops.multiply(horizontal, vertical)
    return strength.point(lambda value: round(value * 175 / 255))


def fit_headline(draw, lines, font_path, safe_width, safe_height, initial_size):
    """Choose the largest Fraunces size that fits every supplied headline line."""
    size = initial_size
    while size >= 24:
        font = ImageFont.truetype(str(font_path), size=size)
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        widths = [draw.textlength(line, font=font) for line in lines]
        text_height = sum(box[3] - box[1] for box in boxes) + (len(lines) - 1) * max(5, size // 12)
        if max(widths, default=0) <= safe_width and text_height <= safe_height:
            return font, boxes, text_height
        size -= 2
    raise ValueError(f"Headline does not fit its title-safe area: {lines!r}")


def render_full_photo(photo, headline: str, platform: str, helper):
    width, height = PLATFORM_SIZES[platform]
    # The landscape Westlake source needs its approved aircraft-free crop.
    if platform == "Facebook" and headline.replace("\n", " ") == "Who will be there between visits?":
        # This branch is intentionally not used here; the approved FB artwork is
        # copied verbatim in main(), while other formats use the safe source.
        pass

    image = helper.contain_crop(photo, (0, 0, width, height), centering=(0.40, 0.47)).convert("RGBA")
    shade = Image.new("RGBA", image.size, (43, 26, 39, 0))
    shade.putalpha(tint_mask(image.size))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)

    lines = [line.strip() for line in headline.splitlines() if line.strip()]
    font_path = helper.FONT_DIR / "Fraunces-var.woff2"
    left = round(width * 0.071)
    top = round(height * 0.078)
    # A deliberately narrower measure on LinkedIn keeps the title and lower-right
    # brand mark in separate visual zones despite the short canvas.
    title_width = round(width * (0.63 if platform == "LinkedIn" else 0.79))
    title_height = round(height * (0.51 if platform == "LinkedIn" else 0.46))
    size_ratio = min(width / 1080, height / 1350)
    initial_size = 62 if platform == "LinkedIn" else max(35, round(84 * size_ratio))
    font, boxes, block_height = fit_headline(
        draw, lines, font_path, title_width, title_height, initial_size
    )

    line_gap = max(5, round(font.size * 0.10))
    y = top
    rendered_bounds = []
    for line in lines:
        box = draw.textbbox((left, y), line, font=font)
        draw.text((left, y), line, font=font, fill=CREAM, stroke_width=0)
        rendered_bounds.append(box)
        y = box[3] + line_gap

    title_bounds = (
        min(box[0] for box in rendered_bounds),
        min(box[1] for box in rendered_bounds),
        max(box[2] for box in rendered_bounds),
        max(box[3] for box in rendered_bounds),
    )
    safe_title = (left, top, left + title_width, top + title_height)
    if not (
        title_bounds[0] >= safe_title[0]
        and title_bounds[1] >= safe_title[1]
        and title_bounds[2] <= safe_title[2]
        and title_bounds[3] <= safe_title[3]
    ):
        raise ValueError(f"{platform} headline exceeds title-safe bounds: {title_bounds}")

    gold_y = min(title_bounds[3] + max(16, round(font.size * 0.22)), round(height * 0.60))
    draw.line((left + 3, gold_y, left + round(width * 0.11), gold_y), fill=GOLD, width=max(2, round(width / 300)))

    logo = helper.fitted_logo(helper.logo_asset(reverse=True), round(width * 0.165))
    pad_x = round(width * 0.021)
    pad_y = round(height * 0.013)
    margin = round(min(width, height) * 0.026)
    logo_x = width - logo.width - margin
    logo_y = height - logo.height - margin
    backing = (logo_x - pad_x, logo_y - pad_y, width - margin + pad_x, height - margin + pad_y)
    draw.rounded_rectangle(backing, radius=max(5, round(width * 0.012)), fill=(72, 33, 63, 146))
    image.alpha_composite(logo, (logo_x, logo_y))
    logo_bounds = (logo_x, logo_y, logo_x + logo.width, logo_y + logo.height)
    if title_bounds[2] >= logo_bounds[0] and title_bounds[3] >= logo_bounds[1]:
        raise ValueError(f"{platform} headline overlaps logo: {title_bounds} / {logo_bounds}")

    return image.convert("RGB"), safe_title, (backing[0], backing[1], backing[2], backing[3])


def build_contact_sheet(records):
    """Labeled thumbnails for review; labels sit outside the image artwork."""
    cell_w, cell_h = 244, 340
    outer, gap, label_h = 18, 14, 28
    columns = 5
    rows = 4
    sheet = Image.new(
        "RGB",
        (outer * 2 + columns * cell_w + (columns - 1) * gap,
         outer * 2 + rows * (cell_h + label_h) + (rows - 1) * gap),
        CREAM,
    )
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    platform_order = list(PLATFORM_SIZES)
    dates = sorted({record["date"] for record in records})
    by_key = {(record["platform"], record["date"]): record for record in records}
    for row, platform in enumerate(platform_order):
        for col, date in enumerate(dates):
            x = outer + col * (cell_w + gap)
            y = outer + row * (cell_h + label_h + gap)
            draw.text((x, y), f"{date}  ·  {platform}", font=label_font, fill=PLUM)
            record = by_key[(platform, date)]
            with Image.open(OUT / record["image_file"]) as source:
                thumb = ImageOps.contain(source.convert("RGB"), (cell_w, cell_h), Image.Resampling.LANCZOS)
            px = x + (cell_w - thumb.width) // 2
            py = y + label_h + (cell_h - thumb.height) // 2
            sheet.paste(thumb, (px, py))
    QA_OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(QA_OUT, quality=92, optimize=True, subsampling=0)


def main():
    helper = load_helper()
    copy_data = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    article_data = json.loads(ARTICLES_PATH.read_text(encoding="utf-8"))
    article_by_slug = {article["slug"]: article for article in article_data}
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_records = []

    for day in copy_data:
        date = day["date"]
        article = article_by_slug.get(day["slug"])
        if not article:
            raise ValueError(f"No journal photo mapping for {day['slug']}")
        photo_file = source_path(article["heroImage"])
        if not photo_file.is_file():
            raise FileNotFoundError(photo_file)

        for platform, dimensions in PLATFORM_SIZES.items():
            relative_file = f"{platform}/{date}.jpg"
            output_path = OUT / relative_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            title_safe = None
            logo_safe = None

            # Preserve the exact approved 1080×1350 Facebook image for Oct 27.
            if date == "2026-10-27" and platform == "Facebook":
                shutil.copyfile(APPROVED_FB, output_path)
                title_safe = [76, 105, 936, 505]
                logo_safe = [858, 1158, 1055, 1328]
            else:
                photo = Image.open(photo_file).convert("RGB")
                if day["slug"] == "westlake-village-who-will-be-home-between-hospice-visits":
                    photo = photo.crop((0, 0, 1510, 1190))
                image, title_safe, logo_safe = render_full_photo(photo, day["headline"], platform, helper)
                if image.size != dimensions:
                    raise ValueError(f"Unexpected render size for {relative_file}: {image.size}")
                image.save(output_path, quality=94, optimize=True, subsampling=0)

            with Image.open(output_path) as verify:
                verify.load()
                if verify.size != dimensions or verify.format != "JPEG":
                    raise ValueError(f"Invalid output image: {relative_file} {verify.size} {verify.format}")
            manifest_records.append({
                "platform": platform,
                "date": date,
                "image_file": relative_file,
                "dimensions": {"width": dimensions[0], "height": dimensions[1]},
                "source_photo": str(photo_file.relative_to(ROOT)),
                "headline": day["headline"].replace("\n", " "),
                "title_safe_bounds": {
                    "x": title_safe[0], "y": title_safe[1],
                    "width": title_safe[2] - title_safe[0],
                    "height": title_safe[3] - title_safe[1],
                },
                "logo_safe_bounds": {
                    "x": logo_safe[0], "y": logo_safe[1],
                    "width": logo_safe[2] - logo_safe[0],
                    "height": logo_safe[3] - logo_safe[1],
                },
            })

    if len(manifest_records) != 20:
        raise AssertionError(f"Expected 20 images, created {len(manifest_records)}")
    (OUT / "image-manifest.json").write_text(
        json.dumps(manifest_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    build_contact_sheet(manifest_records)
    print(f"Rendered {len(manifest_records)} JPEGs in {OUT.relative_to(ROOT)}")
    print(f"Manifest: {(OUT / 'image-manifest.json').relative_to(ROOT)}")
    print(f"QA contact sheet: {QA_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
