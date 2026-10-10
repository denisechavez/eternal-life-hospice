"""Apply review-only photo overrides without modifying public article history."""
import json
import re
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "content/journal-image-revisions.json"


def image_revisions():
    return json.loads(MANIFEST.read_text())["images"] if MANIFEST.is_file() else {}


def apply_image_revision(slug, document):
    photo = image_revisions().get(slug)
    if not photo:
        return document
    if photo["originalImage"] not in document and photo["heroImage"] not in document:
        raise ValueError(f"Journal image source no longer matches review: {slug}")
    revised = document.replace(photo["originalImage"], photo["heroImage"])
    for dimension in ("width", "height"):
        revised = re.sub(
            rf'(property="og:image:{dimension}"\s+content=")\d+',
            lambda match: match[1] + str(photo[dimension]),
            revised,
        )
    return revised
