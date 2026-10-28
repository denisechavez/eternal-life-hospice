"""Check the social review PDF and render representative pages for inspection."""
import json
from pathlib import Path
import re
import subprocess
try:
    import fitz
except ImportError:
    fitz = None

root = Path(__file__).resolve().parents[2]
folder = root / "generated-artifacts/social-2026-10-27-31"
output = root / "generated-artifacts/social-qa-2026-10-27-31"
output.mkdir(parents=True, exist_ok=True)
posts = json.loads((folder / "posts.json").read_text())
pdf = folder / "Eternal-Social-October-27-31-2026-Review.pdf"
# Use the installed Poppler tools rather than add a production dependency
# solely for this one-off export check.
document = fitz.open(pdf) if fitz else None
texts = ([page.get_text() for page in document] if document else
         [page for page in subprocess.check_output(
             ["pdftotext", "-raw", str(pdf), "-"], text=True).split("\f") if page.strip()])
assert len(texts) == 15, len(texts)
normalize = lambda text: re.sub(r"\s+", "", text)
for number, post in enumerate(posts, 1):
    text = texts[number]
    assert "REVIEWDRAFT" in normalize(text), (number, text[:100])
    assert normalize(post["row"]["Caption"]) in normalize(text), (number, "Caption incomplete")
    if document:
        for block in document[number].get_text("blocks"):
            assert block[3] < document[number].rect.height - 10, (number, "Text below safe page edge")
for number in (0, 3, 6, 9, 14):
    if document:
        document[number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(output / f"page-{number+1}.png")
    else:
        subprocess.run(["pdftoppm", "-f", str(number + 1), "-l", str(number + 1),
                        "-scale-to", "1400", "-png", "-singlefile", str(pdf),
                        str(output / f"page-{number+1}")], check=True)
print(f"PASS: {len(texts)} PDF pages; all 14 complete captions; five QA renders.")
