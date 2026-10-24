"""Export the current Journal article's GBP graphic; does not publish."""
import importlib.util
import io
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "social_template", ROOT / "exports/social/build-october-26-week.py"
)
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)
template.FONTS = {}
for key, filename in [
    ("serif", "fraunces-latin.woff2"),
    ("sans", "JostELH-Regular.woff2"),
]:
    font = TTFont(template.PUBLIC / "assets/fonts" / filename)
    font.flavor = None
    buffer = io.BytesIO()
    font.save(buffer)
    template.FONTS[key] = buffer.getvalue()

slug = "a-death-doula-and-a-hospice-nurse-different-roles-shared-support"
source = Image.open(
    template.PUBLIC / f"assets/img/journal/q4/{slug}.jpg"
).convert("RGB")
logo = Image.open(template.PUBLIC / "assets/logo-eternal-trans.png").convert("RGBA")
logo = logo.crop(logo.getbbox())
topic = {
    "date": "2026-10-23",
    "headline": "Different roles. Shared support.",
    "support": "A hospice nurse and an end-of-life doula:\nunderstanding how each can help",
}
output = ROOT / "generated-artifacts/social-2026-10-23"
output.mkdir(parents=True, exist_ok=True)
image = template.graphic(topic, "GBP", source, logo)
assert image.size == (1200, 900)
image.save(output / "2026-10-23-gbp.jpg", quality=94, subsampling=0)
print(output / "2026-10-23-gbp.jpg")
