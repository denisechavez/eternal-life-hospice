#!/usr/bin/env python3
"""Offline rendering regressions. Run: python3 -m unittest discover -s .agents/scripts/tests -v

Fixtures are deliberately procedural (no network, random seed or photo licensing).
Use the real checked-in Fraunces font, crop helper and reverse Eternal logo.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageColor, ImageDraw, ImageOps


SCRIPT = Path(__file__).resolve().parents[1] / "render-full-photo-social-test.py"
SPEC = importlib.util.spec_from_file_location("full_photo_social", SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)

# Independent expectations: changing production sizes must not silently change tests.
SIZES = {
    "GBP": (1200, 900),
    "Facebook": (1080, 1350),
    "LinkedIn": (1200, 627),
    "Pinterest": (1000, 1500),
}
HEADLINES = (
    "Who will be there\nbetween visits?",
    "Understanding hospice care and coverage\nQuestions for your family's care team\nBefore signing, make room for questions.",
)
APPROVED_SHA256 = "7763f7d0c6abc3e225e1de641a26da35ea4f65f02561dcdbebae9d130f1810e1"


def fixture(name):
    """Local bright architecture, mottled foliage and dark-room stress fixtures."""
    image = Image.new("RGB", (640, 480), {
        "bright-wall": (255, 252, 245),
        "foliage": (49, 83, 35),
        "dark-room": (24, 22, 30),
    }[name])
    draw = ImageDraw.Draw(image)
    if name == "bright-wall":
        for y in range(0, 480, 80):
            draw.line((0, y, 640, y), fill=(225, 222, 216), width=2)
        draw.rectangle((500, 80, 580, 400), fill=(185, 180, 171))
    elif name == "foliage":
        for y in range(-20, 480, 45):
            for x in range(-20, 640, 55):
                draw.ellipse((x, y, x + 70, y + 30), fill=(173, 199, 114))
                draw.ellipse((x + 20, y + 25, x + 45, y + 60), fill=(31, 67, 29))
    else:
        draw.rectangle((480, 80, 580, 340), fill=(112, 102, 86))
        draw.rectangle((40, 370, 420, 475), fill=(48, 39, 45))
    return image


def luminance(rgb):
    channels = [v / 255 for v in rgb[:3]]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
              for v in channels]
    return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))


class FullPhotoRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = renderer.load_helper()

    def assert_upper_left(self, mask):
        w, h = mask.size
        self.assertEqual(mask.mode, "L")
        self.assertEqual(mask.getpixel((0, 0)), 175)
        self.assertEqual(mask.getpixel((w - 1, h - 1)), 0)
        # Check both axes independently; the old bottom-facing gradient fails here.
        for fraction in (0.08, 0.25, 0.45):
            x, y = round(w * fraction), round(h * fraction)
            self.assertGreater(mask.getpixel((x, y)), mask.getpixel((w - 1, y)))
            self.assertGreater(mask.getpixel((x, y)), mask.getpixel((x, h - 1)))
        for y in (0, h // 4, h // 2):
            values = [mask.getpixel((x, y)) for x in range(0, w, max(1, w // 20))]
            self.assertEqual(values, sorted(values, reverse=True))
        for x in (0, w // 4, w // 2):
            values = [mask.getpixel((x, y)) for y in range(0, h, max(1, h // 20))]
            self.assertEqual(values, sorted(values, reverse=True))

    def test_upper_left_gradient_all_aspects(self):
        for platform, size in SIZES.items():
            with self.subTest(platform=platform):
                self.assert_upper_left(renderer.tint_mask(size))

    def check_render(self, name, platform, headline):
        """Measure real glyphs, not self-reported safe rectangles or cream pixels."""
        calls = []
        original_text = ImageDraw.ImageDraw.text

        def record(draw, xy, text, *args, **kwargs):
            calls.append((xy, text, kwargs["font"]))
            return original_text(draw, xy, text, *args, **kwargs)

        photo = fixture(name)
        with patch.object(ImageDraw.ImageDraw, "text", record):
            image, title, logo = renderer.render_full_photo(photo, headline, platform, self.helper)
        self.assertEqual(image.size, SIZES[platform])
        self.assertEqual(image.mode, "RGB")
        width, height = SIZES[platform]
        left, top = round(width * 0.071), round(height * 0.078)
        self.assertEqual(title, (
            left, top,
            left + round(width * (0.63 if platform == "LinkedIn" else 0.79)),
            top + round(height * (0.51 if platform == "LinkedIn" else 0.46)),
        ))
        self.assertEqual([text for _, text, _ in calls], headline.splitlines())
        if headline == HEADLINES[1]:
            # This fixture must exercise font reduction, not just ordinary placement.
            w, h = SIZES[platform]
            initial = 62 if platform == "LinkedIn" else max(35, round(84 * min(w / 1080, h / 1350)))
            self.assertLess(calls[0][2].size, initial)

        # The second pass retains the real crop, tint, hairline and logo but omits
        # headline paint, giving the exact background beneath every glyph.
        with patch.object(ImageDraw.ImageDraw, "text", return_value=None):
            background, _, _ = renderer.render_full_photo(photo, headline, platform, self.helper)
        glyphs = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(glyphs)
        for xy, text, font in calls:
            draw.text(xy, text, font=font, fill=255)
        bounds = glyphs.getbbox()
        self.assertIsNotNone(bounds)
        self.assertGreaterEqual(bounds[0], title[0])
        self.assertGreaterEqual(bounds[1], title[1])
        self.assertLessEqual(bounds[2], title[2])
        self.assertLessEqual(bounds[3], title[3])
        w, h = image.size
        self.assertGreaterEqual(logo[0], 0)
        self.assertGreaterEqual(logo[1], 0)
        # The translucent backing may intentionally bleed past the right edge
        # on landscape crops. The actual official mark must remain fully inside.
        brand = self.helper.fitted_logo(self.helper.logo_asset(reverse=True), round(w * 0.165))
        margin = round(min(w, h) * 0.026)
        ink_box = (w - brand.width - margin, h - brand.height - margin, w - margin, h - margin)
        self.assertGreaterEqual(ink_box[0], 0)
        self.assertGreaterEqual(ink_box[1], 0)
        self.assertLess(ink_box[2], w)
        self.assertLess(ink_box[3], h)
        opaque_logo_pixels = 0
        for ly in range(brand.height):
            for lx in range(brand.width):
                if brand.getpixel((lx, ly))[3] == 255:
                    opaque_logo_pixels += 1
                    self.assertEqual(image.getpixel((ink_box[0] + lx, ink_box[1] + ly)),
                                     brand.getpixel((lx, ly))[:3])
        self.assertGreater(opaque_logo_pixels, 100)
        # Keep a measurable gap from the entire backing, not only the logo ink.
        self.assertGreaterEqual(logo[1] - bounds[3], round(h * 0.10))

        cream = ImageColor.getrgb(renderer.CREAM)
        cream_luminance = luminance(cream)
        pixels, mask, painted = background.load(), glyphs.load(), image.load()
        minimum = float("inf")
        solid = 0
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                if mask[x, y] >= 250:
                    solid += 1
                    # WCAG large-text minimum: 3:1 on the fully shaded photo.
                    bg = luminance(pixels[x, y])
                    minimum = min(minimum, (cream_luminance + 0.05) / (bg + 0.05))
                    self.assertLessEqual(max(abs(a - b) for a, b in zip(painted[x, y], cream)), 5)
        self.assertGreater(solid, 100)
        self.assertGreaterEqual(minimum, 3.0, f"Headline contrast {minimum:.2f}:1")
        return image, minimum

    def test_fixture_matrix_contrast_bounds_and_clearance(self):
        for name in ("bright-wall", "foliage", "dark-room"):
            for platform in SIZES:
                for headline in HEADLINES:
                    with self.subTest(fixture=name, platform=platform, headline=headline):
                        self.check_render(name, platform, headline)

    def test_unfittable_headline_fails_explicitly(self):
        for platform in SIZES:
            with self.subTest(platform=platform):
                with self.assertRaisesRegex(ValueError, "does not fit"):
                    renderer.render_full_photo(fixture("bright-wall"), "W" * 500, platform, self.helper)

    def test_orientation_check_rejects_bottom_and_right_facing_gradients(self):
        # Negative controls: detect both the reported vertical regression and
        # the horizontal reversal found in the checked-out renderer.
        for size in SIZES.values():
            for transform in (ImageOps.flip, ImageOps.mirror):
                with self.subTest(size=size, transform=transform.__name__):
                    with self.assertRaises(AssertionError):
                        self.assert_upper_left(transform(renderer.tint_mask(size)))

    def test_contrast_check_rejects_missing_and_reversed_shading(self):
        original = renderer.tint_mask
        for bad_mask in (lambda size: Image.new("L", size, 0),
                         lambda size: ImageOps.flip(original(size))):
            with self.subTest(mask=bad_mask):
                with patch.object(renderer, "tint_mask", bad_mask):
                    with self.assertRaisesRegex(AssertionError, "Headline contrast"):
                        self.check_render("bright-wall", "LinkedIn", HEADLINES[0])

    def test_approved_october_27_file_is_unchanged_when_available(self):
        # The real approval lives in ignored generated-artifacts, not Git.
        # This optional pin never regenerates or overwrites that artwork.
        if not renderer.APPROVED_FB.is_file():
            self.skipTest("Local approved artwork absent; copy branch is tested offline below")
        self.assertEqual(hashlib.sha256(renderer.APPROVED_FB.read_bytes()).hexdigest(), APPROVED_SHA256)
        with Image.open(renderer.APPROVED_FB) as image:
            self.assertEqual((image.format, image.size), ("JPEG", SIZES["Facebook"]))

    def test_main_copies_approved_facebook_bytes_without_rerendering(self):
        # Always runs, even on a clean checkout without private generated assets.
        # Exercise main's actual branch and manifest using a local JPEG sentinel.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "output"
            source = root / "photo.png"
            fixture("bright-wall").save(source)
            approved = root / "approved.jpg"
            Image.new("RGB", SIZES["Facebook"], (37, 29, 43)).save(approved, quality=91)
            approved_bytes = approved.read_bytes()
            days = [{"date": f"2026-10-{day}", "slug": f"local-{day}", "headline": HEADLINES[0]}
                    for day in range(27, 32)]
            copy_path, articles_path = root / "copy.json", root / "articles.json"
            copy_path.write_text(json.dumps(days))
            articles_path.write_text(json.dumps([
                {"slug": day["slug"], "heroImage": "/local.png"} for day in days
            ]))
            rendered = []

            def stand_in(photo, headline, platform, helper):
                rendered.append(platform)
                return Image.new("RGB", SIZES[platform]), (1, 2, 100, 200), (800, 400, 900, 500)

            with contextlib.ExitStack() as stack:
                for key, value in {
                    "ROOT": root, "OUT": out, "QA_OUT": root / "contact.jpg", "COPY_PATH": copy_path,
                    "ARTICLES_PATH": articles_path, "APPROVED_FB": approved,
                }.items():
                    stack.enter_context(patch.object(renderer, key, value))
                stack.enter_context(patch.object(renderer, "source_path", return_value=source))
                render = stack.enter_context(patch.object(renderer, "render_full_photo", side_effect=stand_in))
                contact = stack.enter_context(patch.object(renderer, "build_contact_sheet"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                renderer.main()
            self.assertEqual(render.call_count, 19)
            self.assertEqual(rendered.count("Facebook"), 4)
            self.assertEqual((out / "Facebook/2026-10-27.jpg").read_bytes(), approved_bytes)
            self.assertEqual(approved.read_bytes(), approved_bytes)
            records = json.loads((out / "image-manifest.json").read_text())
            self.assertEqual(len(records), 20)
            approved_record = next(r for r in records if r["platform"] == "Facebook" and r["date"] == "2026-10-27")
            self.assertEqual(approved_record["title_safe_bounds"], {"x": 76, "y": 105, "width": 860, "height": 400})
            self.assertEqual(approved_record["logo_safe_bounds"], {"x": 858, "y": 1158, "width": 197, "height": 170})
            contact.assert_called_once_with(records)


if __name__ == "__main__":
    unittest.main()
