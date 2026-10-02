#!/usr/bin/env python3
"""Card 5 refinements: logo plaque on the front + rebuilt, aligned contact
panel on the back (keeps existing QR tile, cropped from the master)."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
from collateral_output import output_plan

ROOT = str(Path(__file__).resolve().parents[1])
PRINT = os.path.join(ROOT, "exports", "print")
CMYK = os.path.join(PRINT, "print-ready-cmyk")
LOGOS = os.path.join(ROOT, "brand-assets", "credential-logos")
FDIR = os.path.join(ROOT, "website", "elh-preview", "assets", "fonts")
CARD = os.path.join(PRINT, "eternal-life-referral-card-5-quick-referral-action.pdf")

def prepare_work(work, qr_tile):
    for f in ["cms-centers-for-medicare-medicaid-services.png",
              "cdph-california-department-of-public-health.png",
              "achc-accredited-gold-seal.png", "epic-systems.png",
              "cms-centers-for-medicare-medicaid-services-white.png",
              "cdph-california-department-of-public-health-white.png",
              "epic-systems-white.png"]:
        shutil.copy(os.path.join(LOGOS, f), work)
    shutil.copy(os.path.join(FDIR, "JostELH-Medium.woff2"), work)
    shutil.copy(os.path.join(FDIR, "JostELH-SemiBold.woff2"), work)
    shutil.copy(qr_tile, os.path.join(work, "qr-tile.png"))

CSS = """
@page { size: 4in 8.25in; margin: 0; }
html,body { margin:0; padding:0; width:4in; height:8.25in; position:relative; }
* { -webkit-print-color-adjust:exact; print-color-adjust:exact; box-sizing:border-box; }
@font-face { font-family:'JostELH'; src:url('JostELH-Medium.woff2') format('woff2'); font-weight:500; }
@font-face { font-family:'JostELH'; src:url('JostELH-SemiBold.woff2') format('woff2'); font-weight:600; }
body { font-family:'JostELH'; font-weight:500; }
.abs { position:absolute; }
img { display:block; }
"""
CMS = "cms-centers-for-medicare-medicaid-services.png"
CDPH = "cdph-california-department-of-public-health.png"
ACHC = "achc-accredited-gold-seal.png"
EPIC = "epic-systems.png"

# ---------- FRONT: white knockout logos directly on the plum band ----------
CMS_W = "cms-centers-for-medicare-medicaid-services-white.png"
CDPH_W = "cdph-california-department-of-public-health-white.png"
EPIC_W = "epic-systems-white.png"
front = (
    '<div class="abs" style="left:38pt;top:414pt;width:212pt;height:58pt;background:#3C1C3B"></div>'
    '<div class="abs" style="left:24pt;top:422pt;width:240pt;height:42pt;'
    'display:flex;align-items:center;justify-content:center;gap:14pt">'
    f'<img src="{CMS_W}" style="max-height:14pt;max-width:44pt">'
    f'<img src="{CDPH_W}" style="max-height:22pt">'
    f'<img src="{ACHC}" style="max-height:30pt">'
    f'<img src="{EPIC_W}" style="max-height:15pt;max-width:42pt">'
    '</div>')

# ---------- BACK: repaint + rebuild the contact panel, aligned ----------
row = lambda lab, val, vstyle="": (
    f'<div style="display:flex;gap:6pt;align-items:baseline">'
    f'<span style="flex:0 0 38pt;white-space:nowrap;font-weight:600;font-size:5.4pt;'
    f'letter-spacing:0.8pt;color:#6793AC">{lab}</span>'
    f'<span style="font-size:7pt;color:#3a2b39;line-height:1.35;{vstyle}">{val}</span></div>')

logo_row_p2 = (
    '<div class="abs" style="left:24pt;top:316pt;width:240pt;height:40pt;background:#F5F0EB"></div>'
    '<div class="abs" style="left:24pt;top:321pt;width:240pt;height:30pt;'
    'display:flex;align-items:center;justify-content:center;gap:13pt">'
    f'<img src="{CMS}" style="max-height:17pt;max-width:52pt">'
    f'<img src="{CDPH}" style="max-height:24pt">'
    f'<img src="{ACHC}" style="max-height:30pt">'
    f'<img src="{EPIC}" style="max-height:18pt;max-width:52pt">'
    '</div>')

back = logo_row_p2 + (
    # erase the old panel (page-cream patch, clear of the plum band at y542)
    '<div class="abs" style="left:28pt;top:395pt;width:232pt;height:146pt;background:#F5F0EB"></div>'
    # new panel
    '<div class="abs" style="left:35pt;top:401pt;width:219pt;height:139pt;'
    'background:#EDE6DE;border-radius:12pt;padding:12pt 12pt 9pt;'
    'display:flex;flex-direction:column">'
      '<div style="display:flex;gap:11pt;flex:1">'
        # QR tile (white rounded backing + original QR crop)
        '<div style="flex:0 0 62pt;height:62pt;background:#ffffff;border-radius:8pt;'
        'display:flex;align-items:center;justify-content:center">'
        '<img src="qr-tile.png" style="width:58pt;height:58pt;border-radius:6pt"></div>'
        # contact column
        '<div style="display:flex;flex-direction:column;gap:3.6pt;min-width:0;flex:1">'
          '<div style="font-weight:600;font-size:6pt;letter-spacing:1.6pt;'
          'color:#AD8C50">REFER 24/7</div>'
          + row("CALL 24/7", "805.953.7273", "font-weight:600;font-size:8pt")
          + row("FAX", "805.953.8530")
          + row("EMAIL", "info@eternallifehospice.com")
          + row("OFFICE", "4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362")
        + '</div>'
      '</div>'
      '<div style="text-align:center;font-weight:600;font-size:5pt;white-space:nowrap;'
      'letter-spacing:0.9pt;color:#5B2E59;margin-top:6pt">'
      'SERVING VENTURA &amp; LOS ANGELES COUNTY &middot; SCAN TO REFER</div>'
    '</div>')

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd), "\n", r.stdout, r.stderr); sys.exit(1)
    return r


def build(card, cmyk, work, source_card, qr_tile):
    prepare_work(work, qr_tile)
    # Snapshot the input before overlaying; never overlay the approved file in place.
    source = os.path.join(work, "source.pdf")
    shutil.copy(source_card, source)
    pdfs = {}
    for name, body in (("front", front), ("back", back)):
        html = os.path.join(work, name + ".html")
        with open(html, "w") as fh:
            fh.write(f"<!doctype html><html><head><meta charset='utf-8'>"
                     f"<style>{CSS}</style></head><body>{body}</body></html>")
        pdf = os.path.join(work, name + ".pdf")
        run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
             "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + html])
        pdfs[name] = pdf

    s1 = os.path.join(work, "s1.pdf")
    run(["qpdf", source, "--overlay", pdfs["front"], "--to=1", "--", s1])
    run(["qpdf", s1, "--overlay", pdfs["back"], "--to=2", "--", str(card)])
    run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite",
         "-dProcessColorModel=/DeviceCMYK", "-sColorConversionStrategy=CMYK",
         "-dOverrideICC=true", "-dPDFSETTINGS=/prepress", "-dAutoRotatePages=/None",
         "-o", str(cmyk), str(card)])
    info = run(["pdfinfo", str(card)]).stdout
    print([l for l in info.splitlines() if "Pages" in l or "Page size" in l])
    print("OK")


def configure_parser(parser):
    parser.add_argument("--source-card", type=Path, default=Path(CARD),
                        help="Master PDF to overlay (read-only; defaults to approved card).")
    parser.add_argument("--qr-tile", type=Path, default=Path("/tmp/qr-tile.png"),
                        help="Original cropped QR tile (required input; no artwork substitution).")


def main(argv=None):
    cmyk_name = "eternal-life-referral-card-5-quick-referral-action-CMYK.pdf"
    plan = output_plan(__doc__, [
        (os.path.basename(CARD), os.path.relpath(CARD, ROOT)),
        (cmyk_name, os.path.relpath(os.path.join(CMYK, cmyk_name), ROOT)),
    ], argv, configure_parser=configure_parser)
    for source in (plan.args.source_card, plan.args.qr_tile):
        if not source.is_file():
            plan.parser.error(f"Required input not found: {source}")
    with plan.stage() as (card, cmyk), tempfile.TemporaryDirectory(prefix="c5fix-") as work:
        build(card, cmyk, work, plan.args.source_card, plan.args.qr_tile)


if __name__ == "__main__":
    main()
