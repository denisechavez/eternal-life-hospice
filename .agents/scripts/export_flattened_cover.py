"""Make a portable, image-based cover proof with no live PDF transparency.

The reviewed Chromium PDF is composited by Poppler at 300 dpi, then each
finished RGB page is embedded in the replacement PDF as a single image.
The artwork and page size are retained; text is intentionally not selectable.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--width", type=float, default=17, help="Flat width in inches")
    parser.add_argument("--height", type=float, default=11, help="Flat height in inches")
    parser.add_argument("--concept", default="Garden", help="Concept name for PDF metadata")
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0:
        parser.error("Page dimensions must be positive")
    expected_pixels = (round(args.width * 300), round(args.height * 300))
    if not args.source.is_file():
        parser.error("Source PDF does not exist")
    if args.source.resolve() == args.destination.resolve():
        parser.error("Keep the original review PDF; choose a different destination")
    args.destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="elh-cover-flat-") as directory:
        prefix = Path(directory) / "page"
        subprocess.run(
            ["pdftoppm", "-r", "300", "-png", str(args.source), str(prefix)],
            check=True,
        )
        images = []
        try:
            paths = sorted(Path(directory).glob("page-*.png"))
            if len(paths) != 2:
                raise ValueError(f"Expected two cover spreads, found {len(paths)}")
            for path in paths:
                with Image.open(path) as image:
                    if image.size != expected_pixels:
                        raise ValueError(
                            f"Expected {args.width:g}×{args.height:g} at 300 dpi "
                            f"({expected_pixels}), got {image.size}"
                        )
                    images.append(image.convert("RGB"))
            images[0].save(
                args.destination,
                "PDF",
                save_all=True,
                append_images=images[1:],
                resolution=300,
                quality=97,
                subsampling=0,
                title=f"Eternal Life Hospice — {args.concept} Cover — {args.width:g} × {args.height:g} Review Proof",
                author="Eternal Life Hospice",
                subject="Outside and inside cover spreads; flattened for viewer compatibility",
            )
        finally:
            for image in images:
                image.close()
    print(args.destination)
    print(
        f"Two {args.width:g} × {args.height:g}-inch RGB spreads, "
        "flattened at 300 dpi; no live transparency."
    )


if __name__ == "__main__":
    main()
