#!/usr/bin/env python3
"""Stamp the four official credential logos (CMS, CDPH, ACHC, Epic) onto the
five finished referral-card PDFs in exports/print/, replacing the text-pill
credential rows. Works by rendering transparent-background overlay pages with
chromium (same engine the cards were built with) and merging them onto the
target page with qpdf. Then regenerates the CMYK print-ready copies with gs.

Coordinates are in PDF points, top-down, page = 288 x 594 pt (4.0 x 8.25 in).
"""
import os, shutil, subprocess, sys, tempfile
from collateral_output import output_plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRINT = os.path.join(ROOT, "exports", "print")
CMYK = os.path.join(PRINT, "print-ready-cmyk")
LOGOS = os.path.join(ROOT, "brand-assets", "credential-logos")
FONT = os.path.join(ROOT, "website", "elh-preview", "assets", "fonts", "JostELH-Medium.woff2")

CSS = """
@page { size: 4in 8.25in; margin: 0; }
html,body { margin:0; padding:0; width:4in; height:8.25in; position:relative; }
* { -webkit-print-color-adjust:exact; print-color-adjust:exact; box-sizing:border-box; }
@font-face { font-family:'JostELH'; src:url('JostELH-Medium.woff2') format('woff2'); font-weight:500; }
.abs { position:absolute; }
img { display:block; }
"""
CMS = "cms-centers-for-medicare-medicaid-services.png"
CDPH = "cdph-california-department-of-public-health.png"
ACHC = "achc-accredited-gold-seal.png"
EPIC = "epic-systems.png"
CMS_W = "cms-centers-for-medicare-medicaid-services-white.png"
CDPH_W = "cdph-california-department-of-public-health-white.png"
EPIC_W = "epic-systems-white.png"
PLUM = "#3C1C3B"

def logo_row(top_pt, heights=(17, 24, 30, 18), gap=13):
    imgs = "".join(
        f'<img src="{src}" style="max-height:{h}pt;max-width:52pt">'
        for src, h in zip((CMS, CDPH, ACHC, EPIC), heights))
    return (f'<div class="abs" style="left:24pt;top:{top_pt}pt;width:240pt;height:30pt;'
            f'display:flex;align-items:center;justify-content:center;gap:{gap}pt">{imgs}</div>')

def cream_patch(x, y, w, h):
    return (f'<div class="abs" style="left:{x}pt;top:{y}pt;width:{w}pt;height:{h}pt;'
            f'background:#F5F0EB"></div>')

def tile(x, y, src, cap, logo_h):
    return (f'<div class="abs" style="left:{x}pt;top:{y}pt;width:103pt;height:44pt;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2.5pt">'
            f'<img src="{src}" style="max-height:{logo_h}pt;max-width:84pt">'
            f'<span style="font-family:JostELH;font-size:4.6pt;letter-spacing:0.7pt;'
            f'color:#5B2E59">{cap}</span></div>')

overlays = {
    # card file -> (page_number, body_html)
    "eternal-life-referral-card-1-capability-hero.pdf": (1,
        # white knockout logos directly on the plum header (no plaque)
        f'<div class="abs" style="left:62pt;top:101.5pt;width:164pt;height:51pt;background:{PLUM}"></div>'
        '<div class="abs" style="left:24pt;top:106pt;width:240pt;height:40pt;'
        'display:flex;align-items:center;justify-content:center;gap:15pt">'
        f'<img src="{CMS_W}" style="max-height:14pt;max-width:44pt">'
        f'<img src="{CDPH_W}" style="max-height:22pt">'
        f'<img src="{ACHC}" style="max-height:30pt">'
        f'<img src="{EPIC_W}" style="max-height:15pt;max-width:42pt">'
        '</div>'),
    "eternal-life-referral-card-2-refer-with-confidence.pdf": (2,
        cream_patch(58, 498, 172, 44) + logo_row(505, heights=(15, 21, 27, 16), gap=11)),
    "eternal-life-referral-card-3-minimal-premium.pdf": (2,
        cream_patch(58, 470, 172, 52) + logo_row(481, heights=(15, 21, 27, 16), gap=11)),
    "eternal-life-referral-card-4-credentials-forward.pdf": (1,
        cream_patch(30, 140, 228, 110)
        + tile(36, 146, CMS, "MEDICARE-CERTIFIED", 15)
        + tile(148, 146, CDPH, "STATE-LICENSED", 20)
        + tile(36, 199, ACHC, "ACCREDITED", 26)
        + tile(148, 199, EPIC, "CONNECTED", 14)),
    "eternal-life-referral-card-5-quick-referral-action.pdf": (2,
        logo_row(322, heights=(17, 24, 26, 18))),
}

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(cmd), "\n", r.stdout, r.stderr)
        sys.exit(1)

def configure_parser(parser):
    parser.add_argument("cards", nargs="*", metavar="CARD",
                        help="Optional filename substrings (e.g. card-1 card-5); default: all five.")


def selected_outputs(parser, args):
    for selector in args.cards:
        if not any(selector in card for card in overlays):
            parser.error(f"No referral card matches: {selector}")
    args.selected_cards = [card for card in overlays
                           if not args.cards or any(k in card for k in args.cards)]
    outputs = []
    for card in args.selected_cards:
        cmyk = card.replace(".pdf", "-CMYK.pdf")
        outputs.extend([
            (card, os.path.relpath(os.path.join(PRINT, card), ROOT)),
            (cmyk, os.path.relpath(os.path.join(CMYK, cmyk), ROOT)),
        ])
    return outputs


def main(argv=None):
    plan = output_plan(__doc__, selected_outputs, argv,
                       configure_parser=configure_parser)
    # Validate all sources before rendering; never stamp a newly committed result.
    for card in plan.args.selected_cards:
        src = os.path.join(PRINT, card)
        if not os.path.isfile(src):
            plan.parser.error(f"Missing source PDF: {src}")
    with plan.stage() as paths, tempfile.TemporaryDirectory(prefix="cardlogos-") as work:
        for f in [CMS, CDPH, ACHC, EPIC, CMS_W, CDPH_W, EPIC_W]:
            shutil.copy(os.path.join(LOGOS, f), work)
        shutil.copy(FONT, os.path.join(work, "JostELH-Medium.woff2"))
        for i, card in enumerate(plan.args.selected_cards):
            page, body = overlays[card]
            name = card.replace(".pdf", "")
            html = os.path.join(work, name + ".html")
            with open(html, "w") as f:
                f.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
                        f"<body>{body}</body></html>")
            ov_pdf = os.path.join(work, name + "-overlay.pdf")
            run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
                 "--no-pdf-header-footer", f"--print-to-pdf={ov_pdf}", "file://" + html])
            src = os.path.join(PRINT, card)
            out, cmyk_out = paths[2*i:2*i+2]
            run(["qpdf", src, "--overlay", ov_pdf, "--to=" + str(page), "--", str(out)])
            run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite",
                 "-dProcessColorModel=/DeviceCMYK", "-sColorConversionStrategy=CMYK",
                 "-dOverrideICC=true", "-dPDFSETTINGS=/prepress", "-dAutoRotatePages=/None",
                 "-o", str(cmyk_out), str(out)])
            info = subprocess.run(["pdfinfo", str(out)], capture_output=True, text=True,
                                  check=True).stdout
            size = [l for l in info.splitlines() if "Page size" in l or "Pages" in l]
            print(card, "->", "; ".join(s.strip() for s in size))


if __name__ == "__main__":
    main()
