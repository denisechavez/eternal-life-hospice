#!/usr/bin/env python3
"""Create a dated, 20-image-per-page Journal reference PDF using Chromium."""
import hashlib
import html
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "generated-artifacts/journal-oct08-dec31-2026"
OUTPUT = ROOT / "generated-artifacts/journal-images-oct08-dec31-2026.pdf"


def build():
    articles = json.loads((SOURCE / "journal-content.json").read_text())["articles"]
    assert len(articles) == 85
    assert articles[0]["date"] == "2026-10-08"
    assert articles[-1]["date"] == "2026-12-31"
    sheets = []
    for start in range(0, len(articles), 20):
        group = articles[start:start + 20]
        tiles = []
        for record in group:
            path = SOURCE / record["image"]["Image file in package"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record["image"]["SHA256"]
            label = date.fromisoformat(record["date"]).strftime("%B %d, %Y")
            tiles.append(
                '<div class="tile"><div class="photo"><img src="' +
                html.escape(path.as_uri(), quote=True) + '" alt="' +
                html.escape(record["title"], quote=True) +
                '"></div><div class="date">' + label + '</div></div>')
        number = start // 20 + 1
        sheets.append(
            '<section class="sheet"><header><div class="brand">ETERNAL LIFE HOSPICE</div>'
            '<h1>Journal image reference</h1><p>Oct 8 - Dec 31, 2026</p></header>'
            '<div class="grid">' + "".join(tiles) + '</div><footer>'
            '<span>Existing source photographs; final approval not verified.</span>'
            '<span>Page ' + str(number) + ' of 5 | ' + str(len(group)) +
            ' images</span></footer></section>')
    markup = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>Eternal Journal - Dated Image Reference</title><style>'
        '@page{size:Letter portrait;margin:0}*{box-sizing:border-box}'
        'html,body{margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;color:#252525}'
        '.sheet{width:8.5in;height:11in;padding:.32in;break-after:page;'
        'display:flex;flex-direction:column;overflow:hidden}'
        '.sheet:last-child{break-after:auto}header{height:.77in;flex-shrink:0}'
        '.brand{font-size:8pt;letter-spacing:1.4px;color:#593a59}'
        'h1{font-size:16pt;margin:5px 0 3px;color:#493149}'
        'header p{font-size:9pt;margin:0;color:#555}'
        '.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        'grid-template-rows:repeat(5,minmax(0,1fr));gap:.13in .12in;flex:1;min-height:0}'
        '.tile{display:flex;flex-direction:column;min-height:0}'
        '.photo{flex:1;min-height:0;border:1px solid #dedede;background:#fafafa}'
        '.photo img{display:block;width:100%;height:100%;object-fit:contain}'
        '.date{flex-shrink:0;height:.23in;padding-top:5px;text-align:center;font-size:9.5pt;font-weight:600}'
        'footer{height:.3in;padding-top:12px;flex-shrink:0;display:flex;justify-content:space-between;'
        'font-size:7pt;color:#666}'
        '*{-webkit-print-color-adjust:exact;print-color-adjust:exact}'
        '</style></head><body>' + "".join(sheets) + '</body></html>')
    source_html = OUTPUT.with_suffix(".html")
    source_html.write_text(markup)
    chrome = shutil.which("chromium") or shutil.which("chromium-browser")
    assert chrome, "Chromium is required to create the PDF"
    result = subprocess.run([
        chrome, "--headless", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--no-pdf-header-footer",
        "--print-to-pdf=" + str(OUTPUT), source_html.as_uri(),
    ], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and OUTPUT.is_file(), result.stderr[-2000:]
    info = subprocess.check_output(["pdfinfo", str(OUTPUT)], text=True)
    assert "Pages:           5" in info, info
    text = subprocess.check_output(["pdftotext", "-layout", str(OUTPUT), "-"], text=True)
    pages = [page for page in text.split("\f") if page.strip()]
    assert len(pages) == 5
    counts = []
    for index, page in enumerate(pages):
        group = articles[index * 20:(index + 1) * 20]
        for record in group:
            label = date.fromisoformat(record["date"]).strftime("%B %d, %Y")
            assert page.count(label) == 1, (index + 1, label)
        counts.append(len(group))
    assert counts == [20, 20, 20, 20, 5]
    print("PASS: 5 Letter pages, 85 verified source photos and unique matching date labels")
    print("Images per page:", counts)
    print("PDF:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
