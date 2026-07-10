#!/usr/bin/env python3
"""Crop-mark press file for referral card 5 (non-MOO commercial printer).

The MOO upload file (eternal-life-referral-card-5-MOO-rack.pdf) is built
full-bleed with NO crop marks because MOO auto-trims from the bleed edge. A
different printer needs a press file with standard crop/trim marks. This script
produces that SEPARATE file and never touches the MOO output.

It reuses the LOCKED MOO artwork (front + back, same bullets/spacing/fonts) by
importing build-referral-card5-moo-print.py, which is import-safe (its render
pipeline only runs under __main__). FRONT, BACK and CARD_CSS come straight from
that module, so the two files can never drift.

Geometry (72pt/in):
- Trim  3.67 x 8.5in  (264.24 x 612pt)   - the card's native finished size.
- Bleed 3.92 x 8.75in (282.24 x 630pt)   - +0.125in symmetric bleed per side.
- Sheet 4.42 x 9.25in (318.24 x 666pt)   - adds a 0.25in margin around the
  bleed to hold crop marks placed just outside the bleed edge.

The locked art natively bleeds ~0.08in past trim (MOO spec: 3.83x8.66 bleed on a
3.67x8.5 trim). It cannot simply be re-rendered on a 3.92x8.75 canvas because the
authored layout would have to reflow to a different bleed aspect ratio (out of
scope). So each card is placed 1:1 at the exact trim position (crisp, correct
size, zero distortion) and the remaining ~0.045in bleed ring is filled by
edge-clamp: for each of the 4 sides and 4 corners a 1pt slice of the card's own
edge is stretched outward to the bleed edge. Because the card edges are solid
color fields, this reproduces the true edge color deterministically. Everything
outside the 1:1 card is bleed that the printer trims off. Each locked card is
first rasterized (chromium print-to-pdf of the exact standalone layout, then
pdftoppm at 600 DPI) and placed as a fixed <img>, so nested-container reflow can
never shift content past the trim. Assembled sheet is print-to-pdf'd via chromium,
then a CMYK copy is written to print-ready-cmyk/.
"""
import os, shutil, subprocess, importlib.util

ROOT = "/home/runner/workspace"
PRINT = os.path.join(ROOT, "exports", "print")
OUT = os.path.join(PRINT, "eternal-life-referral-card-5-crop-marks-press.pdf")
CMYK = os.path.join(PRINT, "print-ready-cmyk",
                    "eternal-life-referral-card-5-crop-marks-press-CMYK.pdf")

# Import the locked MOO artwork builder (import-safe: does not render).
spec = importlib.util.spec_from_file_location(
    "c5moo", os.path.join(ROOT, "scripts", "build-referral-card5-moo-print.py"))
moo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(moo)
WORK = moo.WORK  # tempdir already populated with all fonts + images

# --- geometry in points (72pt/in) ---
BLEED = 9.0     # 0.125in target bleed per side
MARGIN = 18.0   # 0.25in margin around the bleed for crop marks
CW, CH = 275.76, 623.52          # full-bleed MOO card render (visual) size
TRW, TRH = 264.24, 612.0         # trim 3.67 x 8.5in
BW, BH = TRW + 2 * BLEED, TRH + 2 * BLEED       # bleed box 282.24 x 630
SW, SH = BW + 2 * MARGIN, BH + 2 * MARGIN       # sheet 318.24 x 666

# The 1:1 card already bleeds this much past trim (MOO native bleed ~0.08in):
NATIVE_BLEED = (CW - TRW) / 2                    # 5.76pt
RING = BLEED - NATIVE_BLEED                      # 3.24pt extra bleed to fill
assert RING > 0, "card already covers target bleed"
SLICE = 1.0                                      # edge slice sampled (pt)
SC = RING / SLICE                                # stretch factor for the slice

# 1:1 card position (centered in the bleed box, which sits at MARGIN in the sheet)
FGL = MARGIN + (BW - CW) / 2                     # 21.24
FGT = MARGIN + (BH - CH) / 2                     # 21.24
FGR, FGB = FGL + CW, FGT + CH                    # 297.0, 644.76

# trim lines within the sheet
TX1, TX2 = MARGIN + BLEED, MARGIN + BLEED + TRW          # 27.0, 291.24
TY1, TY2 = MARGIN + BLEED, MARGIN + BLEED + TRH          # 27.0, 639.0
# bleed edges within the sheet
BE_L, BE_T = MARGIN, MARGIN                              # 18, 18
BE_R, BE_B = MARGIN + BW, MARGIN + BH                    # 300.24, 648
ML = 12.0   # crop mark length
GAP = 3.0   # gap between a crop mark and the bleed edge

# The card + bleed pieces live INSIDE .bleed (itself offset by MARGIN), so they
# must use bleed-LOCAL coordinates = sheet coord - MARGIN. Crop marks live in
# .sheet and keep sheet coordinates above.
FL, FT = FGL - MARGIN, FGT - MARGIN                      # 3.24, 3.24  card top-left
FR, FB = FGR - MARGIN, FGB - MARGIN                      # 279.0, 626.76 card bottom-right
BL, BT = 0.0, 0.0                                        # bleed box top-left (local)

# --- rasterize each locked card to a high-DPI PNG (pixel-identical to the MOO
# artwork) so the crop-mark sheet can place it as a FIXED <img> that cannot
# reflow. Rendering the card in a nested/absolutely-positioned container caused
# its content to shift vs. the standalone layout, which pushed the bottom tagline
# past the trim line. A raster of the exact standalone render eliminates that
# entirely and keeps the trim/safe-area precisely where the locked layout intends. ---
RASTER_DPI = 600


def rasterize(card, name):
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'@page {{ size:{CW}pt {CH}pt; margin:0; }}'
            f'*{{margin:0;padding:0;box-sizing:border-box;'
            f'-webkit-print-color-adjust:exact;print-color-adjust:exact;}}'
            f'{moo.CARD_CSS}</style></head><body>{card}</body></html>')
    with open(os.path.join(WORK, name + ".html"), "w") as fh:
        fh.write(html)
    moo.run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
             "--force-color-profile=srgb", "--no-pdf-header-footer",
             "--print-to-pdf=" + os.path.join(WORK, name + ".pdf"), name + ".html"])
    subprocess.run(["pdftoppm", "-png", "-r", str(RASTER_DPI), "-singlefile",
                    os.path.join(WORK, name + ".pdf"),
                    os.path.join(WORK, name)], check=True)
    return name + ".png"


FRONT_PNG = rasterize(moo.FRONT, "cardfront")
BACK_PNG = rasterize(moo.BACK, "cardback")


def vmark(x, top):
    return (f'<div class="cm" style="left:{x - 0.25:.2f}pt;top:{top:.2f}pt;'
            f'width:0.5pt;height:{ML}pt"></div>')


def hmark(y, left):
    return (f'<div class="cm" style="left:{left:.2f}pt;top:{y - 0.25:.2f}pt;'
            f'width:{ML}pt;height:0.5pt"></div>')


marks = "".join([
    vmark(TX1, BE_T - GAP - ML), vmark(TX2, BE_T - GAP - ML),   # top verticals
    vmark(TX1, BE_B + GAP),      vmark(TX2, BE_B + GAP),        # bottom verticals
    hmark(TY1, BE_L - GAP - ML), hmark(TY2, BE_L - GAP - ML),   # left horizontals
    hmark(TY1, BE_R + GAP),      hmark(TY2, BE_R + GAP),        # right horizontals
])


def clamp(clip_style, pg_style, png):
    """A clipped, single/dual-axis-stretched copy of the card that replicates
    one edge (or corner) outward into the bleed ring."""
    return (f'<div class="clip" style="{clip_style}">'
            f'<img class="pg" src="{png}" '
            f'style="width:{CW}pt;height:{CH}pt;{pg_style}"></div>')


def sheet(png):
    # Edge-clamp bleed pieces: 4 sides + 4 corners, each stretching a 1pt slice
    # of the card's edge across the RING gap out to the bleed edge.
    pieces = [
        # left side
        clamp(f"left:{BL}pt;top:{FT}pt;width:{RING}pt;height:{CH}pt",
              f"left:0;top:0;transform-origin:left top;transform:scaleX({SC})", png),
        # right side
        clamp(f"left:{FR}pt;top:{FT}pt;width:{RING}pt;height:{CH}pt",
              f"right:0;top:0;transform-origin:right top;transform:scaleX({SC})", png),
        # top side
        clamp(f"left:{FL}pt;top:{BT}pt;width:{CW}pt;height:{RING}pt",
              f"left:0;top:0;transform-origin:left top;transform:scaleY({SC})", png),
        # bottom side
        clamp(f"left:{FL}pt;top:{FB}pt;width:{CW}pt;height:{RING}pt",
              f"left:0;bottom:0;transform-origin:left bottom;transform:scaleY({SC})", png),
        # top-left corner
        clamp(f"left:{BL}pt;top:{BT}pt;width:{RING}pt;height:{RING}pt",
              f"left:0;top:0;transform-origin:left top;transform:scale({SC},{SC})", png),
        # top-right corner
        clamp(f"left:{FR}pt;top:{BT}pt;width:{RING}pt;height:{RING}pt",
              f"right:0;top:0;transform-origin:right top;transform:scale({SC},{SC})", png),
        # bottom-left corner
        clamp(f"left:{BL}pt;top:{FB}pt;width:{RING}pt;height:{RING}pt",
              f"left:0;bottom:0;transform-origin:left bottom;transform:scale({SC},{SC})", png),
        # bottom-right corner
        clamp(f"left:{FR}pt;top:{FB}pt;width:{RING}pt;height:{RING}pt",
              f"right:0;bottom:0;transform-origin:right bottom;transform:scale({SC},{SC})", png),
    ]
    fg = (f'<img class="cardfg" src="{png}" '
          f'style="left:{FL}pt;top:{FT}pt;width:{CW}pt;height:{CH}pt">')
    return (f'<div class="sheet">{marks}'
            f'<div class="bleed">{"".join(pieces)}{fg}</div></div>')


HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: {SW}pt {SH}pt; margin: 0; }}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
img {{ display:block; }}
.sheet {{ position:relative; width:{SW}pt; height:{SH}pt; overflow:hidden; background:#ffffff; page-break-after:always; }}
.sheet:last-child {{ page-break-after:auto; }}
.bleed {{ position:absolute; left:{MARGIN}pt; top:{MARGIN}pt; width:{BW}pt; height:{BH}pt; overflow:hidden; }}
.clip {{ position:absolute; overflow:hidden; }}
.clip .pg {{ position:absolute; }}
.cardfg {{ position:absolute; }}
.cm {{ position:absolute; background:#000000; }}
</style></head><body>{sheet(FRONT_PNG)}{sheet(BACK_PNG)}</body></html>"""

with open(os.path.join(WORK, "cropcard5.html"), "w") as fh:
    fh.write(HTML)

moo.run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
         "--force-color-profile=srgb", "--no-pdf-header-footer",
         "--print-to-pdf=" + os.path.join(WORK, "cropcard5.pdf"), "cropcard5.html"])

info = subprocess.run(["pdfinfo", os.path.join(WORK, "cropcard5.pdf")],
                      capture_output=True, text=True).stdout
print([l for l in info.splitlines() if l.startswith(("Pages", "Page size"))])
assert "Pages:           2" in info, "wrong page count"
assert "318 x 666" in info, "wrong page size (expected 318 x 666 pts / 4.42 x 9.25in)"

shutil.copy(os.path.join(WORK, "cropcard5.pdf"), OUT)
moo.run(["gs", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
         "-sColorConversionStrategy=CMYK", "-dProcessColorModel=/DeviceCMYK",
         "-dPDFSETTINGS=/prepress",
         "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
         "-dDownsampleMonoImages=false",
         "-dAutoFilterColorImages=false", "-dAutoFilterGrayImages=false",
         "-dColorImageFilter=/FlateEncode", "-dGrayImageFilter=/FlateEncode",
         "-sOutputFile=" + CMYK, OUT])
rgb = subprocess.run(["bash", "-c",
    f"gs -o /dev/null -sDEVICE=inkcov '{CMYK}' 2>/dev/null | grep -c DeviceRGB || true"],
    capture_output=True, text=True).stdout.strip()
assert rgb == "0", f"CMYK output still has DeviceRGB references: {rgb}"
print("OK", OUT, "| CMYK done | DeviceRGB refs:", rgb)
