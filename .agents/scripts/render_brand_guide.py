from pathlib import Path

import fitz


PDF = Path("attached_assets/Westlake-Village-Hospice-Brand-Guide-Final-v4_1789375102335.pdf")
OUTPUT = Path(".agents/outputs/wvh-brand-guide")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    document = fitz.open(PDF)
    text_parts = []

    for index, page in enumerate(document):
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        pixmap.save(OUTPUT / f"page-{index + 1:02d}.png")
        text_parts.append(f"\n--- PAGE {index + 1} ---\n{page.get_text()}")

    (OUTPUT / "extracted-text.txt").write_text("".join(text_parts), encoding="utf-8")
    print(f"Rendered {document.page_count} pages to {OUTPUT}")


if __name__ == "__main__":
    main()