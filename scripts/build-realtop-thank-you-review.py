#!/usr/bin/env python3
"""Build the unpublished Google PPC thank-you review from existing sources."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "artifacts/review-design-sandbox/public/elh-realtop-thank-you-review.html"
NOTES = ROOT / "exports/realtop-thank-you/RealTop-Implementation-Notes.html"
README = ROOT / "exports/realtop-thank-you/README.md"
OUTPUT = ROOT / "generated-artifacts/google-ppc-thank-you"
STEM = "ELH-Google-PPC-Thank-You-Review"
NOTES_NAME = "Google-PPC-Implementation-Notes.html"


def run(args):
    return subprocess.run(
        [str(arg) for arg in args], check=True, capture_output=True,
        text=True, timeout=90,
    ).stdout


def page_count(path):
    info = run(["pdfinfo", path])
    match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not determine PDF page count: {path.name}")
    return int(match.group(1))


def render(source, destination):
    run([
        "chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-background-networking", "--no-first-run",
        "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=2500", f"--print-to-pdf={destination}",
        source.as_uri(),
    ])
    if page_count(destination) != 1:
        raise RuntimeError(f"{source.name} must print on exactly one page.")


def main():
    for path in (DESIGN, NOTES, README):
        if not path.is_file():
            raise FileNotFoundError(path)
    design = DESIGN.read_text()
    if "<script" in design.lower():
        raise RuntimeError("Review HTML must not contain scripts or tracking.")
    if 'tel:+18059537273' not in design:
        raise RuntimeError("Missing the approved external-page phone link.")
    if "noindex" not in design or "Not connected to the live form" not in design:
        raise RuntimeError("The review status and indexing protection are required.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".build-", dir=OUTPUT) as tmp:
        stage = Path(tmp)
        html = stage / f"{STEM}.html"
        shutil.copyfile(DESIGN, html)
        shutil.copyfile(NOTES, stage / NOTES_NAME)
        shutil.copyfile(README, stage / README.name)
        render(html, stage / "design.pdf")
        render(stage / NOTES_NAME, stage / "notes.pdf")
        packet = stage / f"{STEM}.pdf"
        run(["pdfunite", stage / "design.pdf", stage / "notes.pdf", packet])
        if page_count(packet) != 2:
            raise RuntimeError("The review packet must contain exactly two pages.")
        archive = stage / f"{STEM}-Handoff.zip"
        deliverables = (html, packet, stage / NOTES_NAME, stage / README.name)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in deliverables:
                zipped.write(path, arcname=path.name)
        for path in (*deliverables, archive):
            destination = OUTPUT / path.name
            shutil.copyfile(path, destination)
            print(f"{destination.relative_to(ROOT)} ({destination.stat().st_size:,} bytes)")
    print("SENTINEL: Google PPC review packet built; 2 pages; no live integration.")


if __name__ == "__main__":
    main()
