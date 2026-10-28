#!/usr/bin/env python3
"""Build three private Facebook image explorations for Eternal Life Hospice."""
from pathlib import Path
import io
import json

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-artifacts/facebook-style-exploration"
PHOTO_PATH = ROOT / "website/elh-preview/assets/img/journal/q4/westlake-village-who-will-be-home-between-hospice-visits.jpg"
LOGO_PATH = ROOT / "website/elh-preview/assets/logo-eternal-trans.png"
FONT_DIR = ROOT / "website/elh-preview/assets/fonts"
W, H = 1080, 1350
PLUM = "#48213F"
CREAM = "#F5F0EB"
GOLD = "#C9B07E"
HEADLINE = "Who will be there between visits?"


def pillow_font(path, size, weight=None):
    font = TTFont(path)
    if weight is not None and "fvar" in font:
        axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
        axes["wght"] = weight
        font = instantiateVariableFont(font, axes, inplace=False)
    font.flavor = None
    stream = io.BytesIO()
    font.save(stream)
    return ImageFont.truetype(io.BytesIO(stream.getvalue()), size)


def contain_crop(image, box, centering=(0.5, 0.5)):
    x0, y0, x1, y1 = box
    return ImageOps.fit(image, (x1 - x0, y1 - y0), method=Image.Resampling.LANCZOS, centering=centering)


def source_photo():
    # Exclude the lowest right-hand corner where the aircraft/propeller enters.
    source = Image.open(PHOTO_PATH).convert("RGB")
    return source.crop((0, 0, 1510, 1190))


def logo_asset(reverse=False):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    if reverse:
        alpha = logo.getchannel("A")
        recolored = Image.new("RGBA", logo.size, CREAM)
        recolored.putalpha(alpha)
        return recolored
    return logo


def fitted_logo(logo, width):
    result = logo.copy()
    result.thumbnail((width, 135), Image.Resampling.LANCZOS)
    return result


def wrap_words(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def draw_headline(draw, text, font, x, y, max_width, fill, line_gap=12, align="left"):
    lines = wrap_words(draw, text, font, max_width)
    for line in lines:
        width = draw.textlength(line, font=font)
        xx = x + (max_width - width) / 2 if align == "center" else x
        draw.text((xx, y), line, font=font, fill=fill, stroke_width=0)
        box = draw.textbbox((xx, y), line, font=font)
        y = box[3] + line_gap
    return y


def photo_led(photo, cream_logo):
    # A dramatic full-bleed portrait crop, anchored left of the aircraft and
    # overlaid only where needed to let the headline sit directly on the view.
    image = contain_crop(photo, (0, 0, W, H), centering=(0.40, 0.47)).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = shade.load()
    for y in range(H):
        # Deepen the upper left gradually without dimming the full landscape.
        for x in range(W):
            strength = max(0, 1 - x / 890) * max(0, 1 - y / 880)
            pixels[x, y] = (43, 26, 39, int(138 * strength))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image)
    font = pillow_font(FONT_DIR / "Fraunces-var.woff2", 84, 560)
    draw_headline(draw, HEADLINE, font, 76, 105, 860, CREAM, line_gap=8)
    # Restrained gold hairline is part of the image composition, not a label.
    draw.line((80, 382, 196, 382), fill=GOLD, width=4)
    brand = fitted_logo(cream_logo, 178)
    # Ground the official reverse mark with a quiet, transparent plum wash.
    draw.rounded_rectangle((W - 222, H - 192, W - 25, H - 22), radius=14, fill=(72, 33, 63, 146))
    image.alpha_composite(brand, (W - brand.width - 36, H - brand.height - 38))
    return image.convert("RGB")


def editorial(photo, plum_logo):
    # A measured editorial split: cream typography field and a full-height,
    # tall photograph that reads as a deliberate companion rather than a banner.
    image = Image.new("RGB", (W, H), CREAM)
    split = 590
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, split, H), fill=CREAM)
    # Right-side portrait uses a focused lake-and-neighborhood crop.
    panel = contain_crop(photo, (split, 0, W, H), centering=(0.52, 0.43))
    image.paste(panel, (split, 0))
    draw.rectangle((split - 5, 0, split + 5, H), fill=GOLD)
    # Fraunces has editorial warmth; deliberately open leading and short lines.
    font = pillow_font(FONT_DIR / "Fraunces-var.woff2", 67, 520)
    draw.line((72, 244, 154, 244), fill=GOLD, width=5)
    draw_headline(draw, HEADLINE, font, 72, 290, 455, PLUM, line_gap=19)
    # Logo lives over the photo itself; its discreet cream backing is a brand
    # footing, not a lower copy panel.
    brand = fitted_logo(plum_logo, 176)
    pad = 16
    bx, by = W - brand.width - 26, H - brand.height - 31
    draw.rounded_rectangle((bx - pad, by - pad, W - 18, H - 17), radius=5, fill=CREAM)
    image.paste(brand, (bx, by), brand)
    return image


def graphic_crop(photo, plum_logo):
    # Contemporary art direction: oversized plum typography shares the field
    # with a stepped, sweeping photographic cutout, rather than a rectangular
    # photo panel. A narrow gold arc gives the crop a tactile edge.
    image = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, W, H), fill=CREAM)
    # Set a strongly vertical photo crop; sweeping left edge opens into the type.
    photo_layer = contain_crop(photo, (130, 362, 1080, 1260), centering=(0.49, 0.47)).convert("RGBA")
    mask = Image.new("L", photo_layer.size, 0)
    md = ImageDraw.Draw(mask)
    md.polygon([
        (258, 0), (950, 0), (950, 898), (155, 898), (102, 790),
        (48, 635), (18, 468), (30, 315), (105, 174), (188, 65)
    ], fill=255)
    photo_layer.putalpha(mask)
    image = image.convert("RGBA")
    image.alpha_composite(photo_layer, (130, 362))
    draw = ImageDraw.Draw(image)
    # A gold contour follows the photo's leftward curve without becoming a frame.
    draw.arc((142, 427, 612, 1124), 102, 258, fill=GOLD, width=5)
    font = pillow_font(FONT_DIR / "Fraunces-var.woff2", 73, 570)
    # Intentional stacked rhythm gives this concept a distinct, poster-like pulse.
    lines = ["Who will", "be there", "between", "visits?"]
    y = 106
    for index, line in enumerate(lines):
        x = 82 + (22 if index in (1, 3) else 0)
        draw.text((x, y), line, font=font, fill=PLUM)
        y = draw.textbbox((x, y), line, font=font)[3] + 2
    brand = fitted_logo(plum_logo, 166)
    # Official plum logo rests on a small quiet cream footing over the photograph.
    bx, by = W - brand.width - 33, H - brand.height - 34
    draw.rounded_rectangle((bx - 15, by - 12, W - 20, H - 20), radius=5, fill=CREAM)
    image.alpha_composite(brand, (bx, by))
    return image.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    photo = source_photo()
    plum_logo, cream_logo = logo_asset(False), logo_asset(True)
    designs = [
        ("01-full-photo.jpg", photo_led(photo, cream_logo)),
        ("02-editorial.jpg", editorial(photo, plum_logo)),
        ("03-graphic-crop.jpg", graphic_crop(photo, plum_logo)),
    ]
    for filename, image in designs:
        assert image.size == (1080, 1350)
        image.save(OUT / filename, quality=94, optimize=True, subsampling=0)

    # A single-row overview at a useful review scale, with no extra artwork text.
    thumb_w, thumb_h, gap = 360, 450, 18
    sheet = Image.new("RGB", (3 * thumb_w + 4 * gap, thumb_h + 2 * gap), CREAM)
    for i, (filename, _) in enumerate(designs):
        tile = Image.open(OUT / filename).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(tile, (gap + i * (thumb_w + gap), gap))
    sheet.save(OUT / "contact-sheet.jpg", quality=92, optimize=True, subsampling=0)
    (OUT / "caption-credit.txt").write_text(
        "Photo: Niceley, CC BY-SA 4.0; cropped and color-adjusted.\n"
        "https://commons.wikimedia.org/wiki/File:Aerial-of-Westlake-Lake-in-Westlake-Village.jpg\n"
        "https://creativecommons.org/licenses/by-sa/4.0/\n",
        encoding="utf-8",
    )
    (OUT / "designs.json").write_text(json.dumps([
        {
            "name": "01 — Full photo",
            "hypothesis": "Photo-led invitation: full-bleed Westlake landscape, high-contrast headline integrated into a restrained shaded sky zone, and the reverse official mark grounded over the photograph.",
            "file": "01-full-photo.jpg",
            "dimensions": [1080, 1350],
        },
        {
            "name": "02 — Editorial split",
            "hypothesis": "A calm editorial relationship: generous plum Fraunces typography on warm cream at left, paired with a tall uninterrupted local-photo crop at right.",
            "file": "02-editorial.jpg",
            "dimensions": [1080, 1350],
        },
        {
            "name": "03 — Graphic crop",
            "hypothesis": "Contemporary poster composition: four-beat oversized headline rhythm meets a sweeping, asymmetric photographic cutout edged with restrained gold.",
            "file": "03-graphic-crop.jpg",
            "dimensions": [1080, 1350],
        },
    ], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created {len(designs)} image explorations in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
