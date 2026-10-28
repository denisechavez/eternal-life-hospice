#!/usr/bin/env python3
"""Build Facebook image explorations 05–07 for Eternal Life Hospice."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-artifacts/facebook-style-exploration"
HELPER_PATH = ROOT / ".agents/scripts/build-fb-style-exploration.py"
W, H = 1080, 1350
PLUM = "#48213F"
CREAM = "#F5F0EB"
GOLD = "#C9B07E"
HEADLINE = "Who will be there between visits?"
CREDIT = (
    "Photo Niceley, CC BY-SA 4.0, cropped/color-adjusted; "
    "https://commons.wikimedia.org/wiki/File:Aerial-of-Westlake-Lake-in-Westlake-Village.jpg ; "
    "https://creativecommons.org/licenses/by-sa/4.0/"
)


def load_helpers():
    spec = spec_from_file_location("fb_style_helpers_additional", HELPER_PATH)
    helpers = module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers


def draw_lines(draw, lines, font, x, y, color, leading=8, align="left"):
    for line in lines:
        width = draw.textlength(line, font=font)
        xx = x - width / 2 if align == "center" else x
        draw.text((xx, y), line, font=font, fill=color)
        y = draw.textbbox((xx, y), line, font=font)[3] + leading
    return y


def vertical_window(helpers, photo, plum_logo):
    image = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(image)
    # A gallery-like arch turns the local landscape into a tall, intimate view.
    box = (176, 292, 904, 1190)
    x0, y0, x1, y1 = box
    pw, ph = x1 - x0, y1 - y0
    panel = helpers.contain_crop(photo, (0, 0, pw, ph), centering=(0.48, 0.48)).convert("RGBA")
    mask = Image.new("L", (pw, ph), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle((0, pw // 2, pw, ph), fill=255)
    md.ellipse((0, 0, pw, pw), fill=255)
    panel.putalpha(mask)
    # Fine offset strokes frame, but do not box in, the arched photograph.
    draw.arc((x0 - 12, y0 - 12, x1 + 12, y0 + pw + 12), 180, 360, fill=GOLD, width=4)
    draw.line((x0 - 12, y0 + pw // 2, x0 - 12, y1 + 10), fill=GOLD, width=4)
    draw.line((x1 + 12, y0 + pw // 2, x1 + 12, y1 + 10), fill=GOLD, width=4)
    image = image.convert("RGBA")
    image.alpha_composite(panel, (x0, y0))
    draw = ImageDraw.Draw(image)
    # Airy title sits in the generous gallery margin above the arch.
    font = helpers.pillow_font(helpers.FONT_DIR / "Fraunces-var.woff2", 69, 540)
    draw_lines(draw, ["Who will be there", "between visits?"], font, 540, 68, PLUM, 4, "center")
    # A small gold marker gives the title a quiet editorial anchor.
    draw.rounded_rectangle((489, 243, 591, 249), radius=3, fill=GOLD)
    brand = helpers.fitted_logo(plum_logo, 172)
    image.alpha_composite(brand, (W - brand.width - 46, H - brand.height - 34))
    return image.convert("RGB")


def immersive(helpers, photo, cream_logo):
    image = helpers.contain_crop(photo, (0, 0, W, H), centering=(0.52, 0.47)).convert("RGBA")
    # A soft, directional lower veil supports type without flattening the landscape.
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = shade.load()
    for y in range(H):
        t = max(0.0, min(1.0, (y - 640) / 560))
        alpha = int(150 * (t * t * (3 - 2 * t)))
        for x in range(W):
            side = 0.72 + 0.28 * (1 - x / W)
            pixels[x, y] = (45, 25, 40, int(alpha * side))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)
    # Deliberately low and right-shifted: very different from the upper-left treatment.
    font = helpers.pillow_font(helpers.FONT_DIR / "Fraunces-var.woff2", 83, 545)
    draw_lines(draw, ["Who will be", "there between", "visits?"], font, 492, 790, CREAM, 2)
    # Restrained gold line keys the lettering into the image rather than adding copy.
    draw.rounded_rectangle((496, 1099, 610, 1105), radius=3, fill=GOLD)
    brand = helpers.fitted_logo(cream_logo, 174)
    # A light, soft-edged footing keeps the real reversed logo clear over the photo.
    footing = Image.new("RGBA", (brand.width + 38, brand.height + 30), (72, 33, 63, 0))
    ImageDraw.Draw(footing).rounded_rectangle(
        (0, 0, footing.width - 1, footing.height - 1), radius=12, fill=(72, 33, 63, 148)
    )
    footing.alpha_composite(brand, (19, 15))
    image.alpha_composite(footing, (W - footing.width - 31, H - footing.height - 24))
    return image.convert("RGB")


def offset_frame(helpers, photo, plum_logo):
    image = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(image)
    # Typographic alignment is intentionally left-biased and staggered.
    font = helpers.pillow_font(helpers.FONT_DIR / "Fraunces-var.woff2", 75, 550)
    draw.text((78, 87), "Who will be", font=font, fill=PLUM)
    draw.text((156, 178), "there between", font=font, fill=PLUM)
    draw.text((78, 269), "visits?", font=font, fill=PLUM)
    # Offset backing layers create a tactile, stepped frame rather than a flat panel.
    photo_box = (194, 418, 1002, 1124)
    draw.polygon(
        [(228, 399), (1017, 399), (1017, 1111), (228, 1111), (180, 1081), (180, 459)],
        fill=PLUM,
    )
    draw.polygon(
        [(205, 411), (1006, 411), (1006, 1123), (205, 1123), (156, 1093), (156, 471)],
        fill=GOLD,
    )
    x0, y0, x1, y1 = photo_box
    panel = helpers.contain_crop(photo, (0, 0, x1 - x0, y1 - y0), centering=(0.51, 0.50)).convert("RGBA")
    mask = Image.new("L", panel.size, 0)
    ImageDraw.Draw(mask).polygon(
        [(34, 0), (panel.width - 1, 0), (panel.width - 1, panel.height - 1),
         (34, panel.height - 1), (0, panel.height - 42), (0, 42)],
        fill=255,
    )
    panel.putalpha(mask)
    image = image.convert("RGBA")
    image.alpha_composite(panel, (x0, y0))
    draw = ImageDraw.Draw(image)
    # An open gold hairline continues the frame, keeping its offset deliberate.
    draw.line((124, 496, 124, 1092), fill=GOLD, width=3)
    brand = helpers.fitted_logo(plum_logo, 178)
    image.alpha_composite(brand, (W - brand.width - 45, H - brand.height - 30))
    return image.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    helpers = load_helpers()
    photo = helpers.source_photo()
    plum_logo = helpers.logo_asset(False)
    cream_logo = helpers.logo_asset(True)
    designs = [
        ("05-vertical-window.jpg", vertical_window(helpers, photo, plum_logo)),
        ("06-immersive.jpg", immersive(helpers, photo, cream_logo)),
        ("07-offset-frame.jpg", offset_frame(helpers, photo, plum_logo)),
    ]
    for filename, artwork in designs:
        assert artwork.size == (W, H)
        artwork.save(OUT / filename, quality=94, optimize=True, subsampling=0)

    thumb_w, thumb_h, gap = 360, 450, 18
    sheet = Image.new("RGB", (3 * thumb_w + 4 * gap, thumb_h + 2 * gap), CREAM)
    for index, (filename, _) in enumerate(designs):
        tile = Image.open(OUT / filename).convert("RGB").resize(
            (thumb_w, thumb_h), Image.Resampling.LANCZOS
        )
        sheet.paste(tile, (gap + index * (thumb_w + gap), gap))
    sheet.save(OUT / "contact-sheet-05-07.jpg", quality=92, optimize=True, subsampling=0)

    hypotheses = [
        (
            "05 — Vertical window",
            "A gallery-like, tall arched Westlake photograph is framed with restrained gold strokes; a centered two-line headline occupies the open upper margin, making the landscape feel intimate and carefully collected.",
            "05-vertical-window.jpg",
        ),
        (
            "06 — Immersive",
            "A natural-color, full-bleed landscape holds a large, lower-right Fraunces headline over a soft directional shade; the reverse official mark anchors the opposite corner for an expansive, cinematic invitation.",
            "06-immersive.jpg",
        ),
        (
            "07 — Offset frame",
            "A staggered, asymmetrically aligned headline leads into a sharply stepped photographic frame with offset plum and gold layers; the composition feels tactile and architectural rather than split-column or poster-flat.",
            "07-offset-frame.jpg",
        ),
    ]
    metadata = [
        {
            "name": name,
            "hypothesis": hypothesis,
            "file": filename,
            "dimensions": [W, H],
            "credit": CREDIT,
        }
        for name, hypothesis, filename in hypotheses
    ]
    (OUT / "designs-05-07.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Created styles 05–07, contact sheet, and metadata.")


if __name__ == "__main__":
    main()
