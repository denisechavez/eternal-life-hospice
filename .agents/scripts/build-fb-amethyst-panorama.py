#!/usr/bin/env python3
"""Build the fourth, amethyst-panorama Facebook image exploration."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / ".agents/scripts/build-fb-style-exploration.py"
OUT = ROOT / "generated-artifacts/facebook-style-exploration"
W, H = 1080, 1350
AMETHYST = "#48213F"
CREAM = "#F5F0EB"
GOLD = "#C9B07E"
HEADLINE = "Who will be there between visits?"


def load_helpers():
    spec = spec_from_file_location("fb_style_helpers", HELPER_PATH)
    helpers = module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers


def build():
    helpers = load_helpers()
    image = Image.new("RGB", (W, H), AMETHYST)
    draw = ImageDraw.Draw(image)

    # A confident cover-like title occupies the upper field in two readable
    # lines; the line break preserves the exact headline wording.
    title_font = helpers.pillow_font(
        helpers.FONT_DIR / "Fraunces-var.woff2", 88, 560
    )
    lines = ("Who will be there", "between visits?")
    title_x = 64
    title_y = 82
    for line in lines:
        draw.text((title_x, title_y), line, font=title_font, fill=CREAM)
        title_y = draw.textbbox((title_x, title_y), line, font=title_font)[3] + 4

    # A small gold editorial stroke separates title from the cinematic view.
    draw.rounded_rectangle((67, 352, 182, 359), radius=3, fill=GOLD)

    photo = helpers.source_photo()
    photo_box = (42, 424, 1038, 1123)
    photo_panel = helpers.contain_crop(
        photo, photo_box, centering=(0.52, 0.56)
    ).convert("RGBA")
    mask = Image.new("L", photo_panel.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, photo_panel.width - 1, photo_panel.height - 1),
        radius=22,
        fill=255,
    )
    photo_panel.putalpha(mask)
    image = image.convert("RGBA")
    image.alpha_composite(photo_panel, (photo_box[0], photo_box[1]))
    draw = ImageDraw.Draw(image)

    # The official reverse logo is used as supplied, with only its alpha
    # retained for a cream recolor on the amethyst ground.
    logo = helpers.fitted_logo(helpers.logo_asset(reverse=True), 194)
    logo_x = W - logo.width - 52
    logo_y = 1190
    image.alpha_composite(logo, (logo_x, logo_y))

    return image.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    image = build()
    assert image.size == (W, H), f"Unexpected image size: {image.size}"
    image_path = OUT / "04-amethyst-panorama.jpg"
    image.save(image_path, quality=94, optimize=True, subsampling=0)

    metadata = {
        "name": "04 — Amethyst panorama",
        "hypothesis": (
            "A confident publication-cover direction: warm-cream Fraunces "
            "headline set directly into a bold amethyst field, above a generous "
            "cinematic Westlake panorama with the official reverse mark below."
        ),
        "dimensions": [W, H],
        "source_image": (
            "website/elh-preview/assets/img/journal/q4/"
            "westlake-village-who-will-be-home-between-hospice-visits.jpg"
        ),
        "credit": (
            "Photo Niceley, CC BY-SA 4.0, cropped and color-adjusted, source "
            "https://commons.wikimedia.org/wiki/"
            "File:Aerial-of-Westlake-Lake-in-Westlake-Village.jpg and license "
            "https://creativecommons.org/licenses/by-sa/4.0/."
        ),
    }
    (OUT / "04-amethyst-panorama.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Created {image_path.relative_to(ROOT)} ({image.size[0]}x{image.size[1]})")


if __name__ == "__main__":
    main()
