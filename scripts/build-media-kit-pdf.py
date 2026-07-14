#!/usr/bin/env python3
"""Build the digital press/media-kit PDF from the kit page images.

The page ORDER here must mirror the on-page flipbook in
website/elh-preview/media-kit.html (book anatomy): front cover, inside front
cover (welcome), the four Eternal Standard pillar cards front+back, inside back
cover (coverage), back cover. Keeping this list in sync with the flipbook is what
prevents the viewer and the download from diverging.

Writes the PDF to the live site downloads folder and mirrors it to exports/digital/.
"""
import os
import shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "website", "elh-preview", "assets", "kit")
SITE_PDF = os.path.join(ROOT, "website", "elh-preview", "assets", "downloads",
                        "eternal-life-press-kit-digital.pdf")
EXPORT_PDF = os.path.join(ROOT, "exports", "digital",
                          "eternal-life-press-kit-digital.pdf")

# Order = the physical book/folder reading order (matches the flipbook DOM order).
PAGES = [
    "01-front-cover.png",     # front cover
    "02-welcome.jpg",         # inside front cover (welcome letter)
    "05-clinical-front.jpg",  # pillar 1 — Clinical Confidence (front)
    "06-clinical-back.jpg",   # pillar 1 (back)
    "07-guided-front.jpg",    # pillar 2 — Guided Presence (front)
    "08-guided-back.jpg",     # pillar 2 (back)
    "09-comfort-front.jpg",   # pillar 3 — Whole-Person Comfort (front)
    "10-comfort-back.jpg",    # pillar 3 (back)
    "11-compliance-front.jpg",# pillar 4 — Compliance-Led Care (front)
    "12-compliance-back.jpg", # pillar 4 (back)
    "03-coverage.png",        # inside back cover (coverage / insurance)
    "13-back-cover.png",      # back cover
]

RESOLUTION = 300.0  # DPI -> ~5.4in wide x ~8.3in tall pages, aspect preserved
QUALITY = 90


def load(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")


def main():
    imgs = [load(os.path.join(KIT, f)) for f in PAGES]
    os.makedirs(os.path.dirname(SITE_PDF), exist_ok=True)
    imgs[0].save(
        SITE_PDF, "PDF", save_all=True, append_images=imgs[1:],
        resolution=RESOLUTION, quality=QUALITY, optimize=True,
        title="Eternal Life Hospice — Media Kit",
        author="Eternal Life Hospice, Inc.",
    )
    os.makedirs(os.path.dirname(EXPORT_PDF), exist_ok=True)
    shutil.copy2(SITE_PDF, EXPORT_PDF)
    size = os.path.getsize(SITE_PDF)
    print(f"Built {len(PAGES)}-page PDF ({size/1024/1024:.2f} MB)")
    print(f"  -> {SITE_PDF}")
    print(f"  -> {EXPORT_PDF}")


if __name__ == "__main__":
    main()
