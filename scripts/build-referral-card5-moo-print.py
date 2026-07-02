#!/usr/bin/env python3
"""Referral card 5 (Quick-Referral Action) sized for MOO's rack card: trim
3.67x8.5in, full-bleed file 3.74x8.58in (MOO spec, no crop marks - MOO trims).
Design is anchored to the top; a dashed gold cut guide sits at the 7.75in line
(inside the waste strip) so the user can make ONE bottom cut for a final
3.67x7.75in card. The guide is removed by the cut itself.

v2 layout per user direction (July 2026):
- FRONT: full-bleed cream band holding the four credential logos in FULL COLOR
  (no white knockouts, no floating plaque), larger logos, larger body copy.
- BACK: same content as v1 but with body copy sized up throughout.
Page 4.0x8.25in (trim 3.5x7.75 + 0.125 bleed + crop marks), chromium
print-to-pdf (vector), then a CMYK copy for MOO in print-ready-cmyk/.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = "/home/runner/workspace"
PRINT = os.path.join(ROOT, "exports", "print")
LOGOS = os.path.join(ROOT, "brand-assets", "credential-logos")
ASSETS = os.path.join(ROOT, "website", "elh-preview", "assets")
CARD = os.path.join(PRINT, "eternal-life-referral-card-5-MOO-rack.pdf")
CMYK = os.path.join(PRINT, "print-ready-cmyk",
                    "eternal-life-referral-card-5-MOO-rack-CMYK.pdf")

WORK = tempfile.mkdtemp(prefix="c5moo-")
for f in ["cms-centers-for-medicare-medicaid-services.png",
          "cdph-california-department-of-public-health.png",
          "achc-accredited-gold-seal.png", "epic-systems.png"]:
    shutil.copy(os.path.join(LOGOS, f), WORK)
shutil.copy(os.path.join(ROOT, "brand-assets", "Medical",
                         "eternal-life-hospice-infinity-cream-hires.png"),
            os.path.join(WORK, "infinity-cream.png"))
shutil.copy(os.path.join(ASSETS, "img", "qr-refer-cream.png"), WORK)
for f in ["Fraunces-var.woff2", "Fraunces-Italic-var.woff2",
          "JostELH-Regular.woff2", "JostELH-Medium.woff2", "JostELH-SemiBold.woff2"]:
    shutil.copy(os.path.join(ASSETS, "fonts", f), WORK)

DEEP = "#3C1C3B"; PLUM = "#5B2E59"; GOLD = "#C9B07E"; CREAM = "#F5F0EB"
PANEL = "#EDE6DE"; BORDER = "#D8CDBF"; STEEL = "#6793AC"

CMS = "cms-centers-for-medicare-medicaid-services.png"
CDPH = "cdph-california-department-of-public-health.png"
ACHC = "achc-accredited-gold-seal.png"
EPIC = "epic-systems.png"

def cut_guide():
    # MOO page: 269.28x617.76pt, trim 3.67x8.5in (bleed 2.52pt sides / 2.88pt
    # top+bottom). User cut line = 7.75in below top trim -> y = 560.88pt.
    # Guide + label live entirely BELOW the cut line (in the discarded strip).
    return (
      f'<div style="position:absolute;left:0;top:563.76pt;width:100%;height:0;'
      f'border-top:0.9pt dashed {GOLD};opacity:0.9"></div>'
      f'<div style="position:absolute;left:0;top:581pt;width:100%;text-align:center;'
      f'font-family:Jost;font-weight:600;font-size:6.4pt;letter-spacing:1.2pt;'
      f'color:{CREAM};opacity:0.85">&#9986;&nbsp;&nbsp;CUT&nbsp;ALONG&nbsp;DASHED&nbsp;LINE&nbsp;&nbsp;&mdash;&nbsp;&nbsp;FINAL&nbsp;3.67&nbsp;&times;&nbsp;7.75&nbsp;IN</div>')

FRONT = f"""
<div class="page">
  <div class="art" style="background:{DEEP}">
    <div style="display:flex;flex-direction:column;align-items:center;text-align:center;height:100%">
      <img src="infinity-cream.png" style="width:95pt;margin-top:15pt">
      <div style="margin-top:2pt;display:inline-block;text-align:center">
        <div style="font-family:Fraunces;font-weight:480;font-size:30pt;color:{CREAM};line-height:1">Eternal</div>
        <div style="margin-top:3pt;width:73%;margin-left:auto;margin-right:auto;display:flex;justify-content:space-between;
                    font-family:Jost;font-weight:600;font-size:8.2pt;color:{CREAM}"><span>L</span><span>I</span><span>F</span><span>E</span><span> </span><span>H</span><span>O</span><span>S</span><span>P</span><span>I</span><span>C</span><span>E</span></div>
      </div>
      <div style="margin-top:13pt;background:{GOLD};color:{DEEP};font-family:Jost;font-weight:600;
                  font-size:8.5pt;letter-spacing:2.2pt;padding:4pt 13pt 3.4pt;border-radius:10pt">SAME-DAY&nbsp;ADMISSION</div>
      <div style="margin-top:9pt;font-family:Fraunces;font-weight:560;font-size:22.5pt;line-height:1;color:{CREAM}">Refer in One Call,</div>
      <div style="margin-top:4pt;font-family:Fraunces;font-weight:500;font-size:15.5pt;line-height:1;color:{CREAM}">Scan, Fax or E-mail</div>
      <div style="margin-top:5pt;font-family:Jost;font-weight:500;font-size:11pt;letter-spacing:0.6pt;color:#D9CBD8">Answered 24/7 by a hospice nurse</div>
      <div style="margin-top:9pt;font-family:Fraunces;font-weight:620;font-size:33.5pt;letter-spacing:0.5pt;color:{GOLD}">805.953.7273</div>
      <div style="margin-top:6pt;font-family:Jost;font-weight:500;font-size:10.5pt;color:{CREAM}">Fax referrals &middot; 805.953.8530</div>
      <div style="margin-top:12pt;background:{CREAM};border-radius:13pt;padding:6pt">
        <img src="qr-refer-cream.png" style="width:98pt;display:block;border-radius:8pt"></div>
      <div style="margin-top:9pt;font-family:Jost;font-weight:600;font-size:9pt;letter-spacing:2.6pt;color:{GOLD}">SCAN&nbsp;TO&nbsp;REFER&nbsp;ONLINE</div>
    </div>
    <!-- full-bleed cream credential band: spans the whole art/bleed width -->
    <div style="position:absolute;left:0;top:456.76pt;width:100%;height:56pt;background:{CREAM};
                display:flex;align-items:center;justify-content:center;gap:17pt">
      <img src="{CMS}" style="max-height:24pt;max-width:64pt">
      <img src="{CDPH}" style="max-height:50pt">
      <img src="{ACHC}" style="max-height:34pt">
      <img src="{EPIC}" style="max-height:24pt;max-width:64pt">
    </div>
    <div style="position:absolute;left:0;top:512.76pt;width:100%;height:51pt;
                display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2.5pt;text-align:center">
      <div style="font-family:Jost;font-weight:600;font-size:11pt;color:{CREAM}">referral@eternallifehospice.com</div>
      <div style="font-family:Jost;font-weight:400;font-size:8.5pt;color:#D9CBD8">4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362</div>
      <div style="font-family:Jost;font-weight:600;font-size:7.5pt;letter-spacing:2pt;color:{GOLD};margin-top:1.5pt">SERVING&nbsp;VENTURA&nbsp;&amp;&nbsp;LOS&nbsp;ANGELES&nbsp;COUNTY</div>
    </div>
    {cut_guide()}
  </div>
</div>"""

def check(txt):
    return (f'<div style="display:flex;gap:7pt;align-items:baseline">'
            f'<span style="font-family:Jost;font-weight:600;font-size:9.5pt;color:{GOLD.replace("#C9B07E","#A8874F")}">&#10003;</span>'
            f'<span style="font-family:Jost;font-weight:500;font-size:10.6pt;color:#3a2b39;line-height:1.5">{txt}</span></div>')

def chip(txt):
    return (f'<span style="background:#ffffff;border:0.8pt solid {BORDER};border-radius:11pt;'
            f'padding:3.4pt 9.5pt 3pt;font-family:Jost;font-weight:500;font-size:9.6pt;color:{PLUM};'
            f'white-space:nowrap">{txt}</span>')

def crow(lab, val, vstyle=""):
    return (f'<div style="display:flex;gap:7pt;align-items:baseline">'
            f'<span style="flex:0 0 42pt;white-space:nowrap;font-family:Jost;font-weight:600;'
            f'font-size:6.4pt;letter-spacing:0.9pt;color:{STEEL}">{lab}</span>'
            f'<span style="font-family:Jost;font-weight:500;font-size:8.4pt;color:#3a2b39;'
            f'line-height:1.4;{vstyle}">{val}</span></div>')

BACK = f"""
<div class="page">
  <div class="art" style="background:{CREAM}">
    <div style="padding:14pt 27pt 0;text-align:center">
      <div style="font-family:Jost;font-weight:600;font-size:8.5pt;letter-spacing:3pt;color:#A8874F">QUICK&nbsp;REFERRAL&nbsp;GUIDE</div>
      <div style="margin-top:5pt;font-family:Fraunces;font-weight:580;font-size:21pt;color:{PLUM};white-space:nowrap">Signs It May Be Time</div>
    </div>
    <div style="margin:9pt 22pt 0;background:{PANEL};border-radius:12pt;padding:8pt 14pt;
                display:flex;flex-direction:column;gap:4pt">
      {check("Repeated hospital stays or ER visits")}
      {check("Weight loss or a drop in appetite")}
      {check("Recurrent infections")}
      {check("Decline despite ongoing treatment")}
      {check("More help needed with daily activities")}
      {check("A shift toward comfort-focused goals")}
    </div>
    <div style="margin:8pt 25pt 0;background:{DEEP};border-radius:12pt;padding:9pt 13pt;
                display:flex;flex-direction:column;gap:4pt">
      <div style="font-family:Jost;font-weight:600;font-size:7.5pt;letter-spacing:2.4pt;color:{GOLD};text-align:center;margin-bottom:2pt">THE&nbsp;ETERNAL&nbsp;DIFFERENCE</div>
      <div style="display:flex;gap:7pt;align-items:baseline">
        <span style="font-family:Jost;font-weight:600;font-size:8.5pt;color:{GOLD}">&#10022;</span>
        <span style="font-family:Jost;font-weight:500;font-size:9.8pt;color:{CREAM};line-height:1.4">A full line of integrative services</span></div>
      <div style="display:flex;gap:7pt;align-items:baseline">
        <span style="font-family:Jost;font-weight:600;font-size:8.5pt;color:{GOLD}">&#10022;</span>
        <span style="font-family:Jost;font-weight:500;font-size:9.8pt;color:{CREAM};line-height:1.4">Clinical &amp; mobile services at no expense to families</span></div>
      <div style="display:flex;gap:7pt;align-items:baseline">
        <span style="font-family:Jost;font-weight:600;font-size:8.5pt;color:{GOLD}">&#10022;</span>
        <span style="font-family:Jost;font-weight:500;font-size:9.8pt;color:{CREAM};line-height:1.4">Zero complaints in 11 years of care</span></div>
    </div>
    <div style="margin:3pt 27pt 0;text-align:center;font-family:Jost;font-weight:500;font-size:8.2pt;
                letter-spacing:0.4pt;color:{PLUM};line-height:1.5">Same-day admission &middot; Transport &middot; 24/7 nurse<br>Physician-led &middot; Placement &middot; Bereavement</div>
    <div style="margin:4pt 0 0;display:flex;align-items:center;justify-content:center;gap:15pt">
      <img src="{CMS}" style="max-height:22pt;max-width:60pt">
      <img src="{CDPH}" style="max-height:46pt">
      <img src="{ACHC}" style="max-height:30pt">
      <img src="{EPIC}" style="max-height:22pt;max-width:60pt">
    </div>
    <div style="margin:5pt 25pt 0;background:{PANEL};border-radius:12pt;padding:8pt 12pt;
                display:flex;flex-direction:column;gap:5pt">
      <div style="display:flex;gap:11pt;align-items:center">
        <div style="flex:0 0 auto;background:#ffffff;border-radius:9pt;padding:4.5pt">
          <img src="qr-refer-cream.png" style="width:52pt;display:block;border-radius:5pt"></div>
        <div style="display:flex;flex-direction:column;gap:3.5pt;min-width:0">
          <div style="font-family:Jost;font-weight:600;font-size:7.5pt;letter-spacing:2.2pt;color:#A8874F">REFER&nbsp;24/7</div>
          {crow("CALL 24/7", "805.953.7273", f"font-weight:600;font-size:9.6pt;color:{PLUM};white-space:nowrap")}
          {crow("FAX", "805.953.8530", f"font-weight:600;font-size:9.6pt;color:{PLUM};white-space:nowrap")}
        </div>
      </div>
      <div style="border-top:0.8pt solid {BORDER};padding-top:5pt;display:flex;gap:7pt;align-items:baseline">
        <span style="flex:0 0 42pt;white-space:nowrap;font-family:Jost;font-weight:600;
                     font-size:6.4pt;letter-spacing:0.9pt;color:{STEEL}">EMAIL</span>
        <span style="font-family:Jost;font-weight:600;font-size:9.4pt;color:{PLUM};white-space:nowrap">referral@eternallifehospice.com</span>
      </div>
    </div>
    <div style="margin:3pt 25pt 0;padding:0 12pt;display:flex;gap:7pt;align-items:baseline">
      <span style="flex:0 0 42pt;font-family:Jost;font-weight:600;font-size:6.4pt;
                   letter-spacing:0.9pt;color:{STEEL}">OFFICE</span>
      <span style="font-family:Jost;font-weight:500;font-size:8.2pt;color:#3a2b39;line-height:1.4">4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362</span>
    </div>
    <div style="margin-top:2.5pt;text-align:center;font-family:Jost;font-weight:500;font-size:7.4pt;
                letter-spacing:1.4pt;color:{PLUM}">SERVING&nbsp;VENTURA&nbsp;&amp;&nbsp;LOS&nbsp;ANGELES&nbsp;COUNTY</div>
    <div style="position:absolute;left:0;top:526.76pt;width:100%;height:96.76pt;background:{DEEP};
                display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2.5pt;padding-bottom:58.76pt">
      <div style="font-family:Jost;font-weight:600;font-size:6.7pt;letter-spacing:1pt;color:{CREAM};white-space:nowrap">MEDICARE-CERTIFIED&nbsp;&middot;&nbsp;CDPH-LICENSED&nbsp;&middot;&nbsp;ACHC-ACCREDITED</div>
      <div style="font-family:FrauncesItalic;font-style:italic;font-weight:540;font-size:12pt;color:{GOLD}">Care That Honors Life</div>
    </div>
    {cut_guide()}
  </div>
</div>"""

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: 3.83in 8.66in; margin: 0; }}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
@font-face {{ font-family:'Fraunces'; src:url('Fraunces-var.woff2') format('woff2'); font-weight:100 900; }}
@font-face {{ font-family:'FrauncesItalic'; src:url('Fraunces-Italic-var.woff2') format('woff2'); font-weight:100 900; font-style:italic; }}
@font-face {{ font-family:'Jost'; src:url('JostELH-Regular.woff2') format('woff2'); font-weight:400; }}
@font-face {{ font-family:'Jost'; src:url('JostELH-Medium.woff2') format('woff2'); font-weight:500; }}
@font-face {{ font-family:'Jost'; src:url('JostELH-SemiBold.woff2') format('woff2'); font-weight:600; }}
.page {{ position:relative; width:275.76pt; height:623.52pt; overflow:hidden; page-break-after:always; }}
.page:last-child {{ page-break-after:auto; }}
.art {{ position:absolute; left:0; top:0; width:275.76pt; height:623.52pt; overflow:hidden; }}
img {{ display:block; }}
</style></head><body>{FRONT}{BACK}</body></html>"""

with open(os.path.join(WORK, "card5.html"), "w") as fh:
    fh.write(HTML)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=WORK)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(cmd), "\n", r.stdout, r.stderr)
        sys.exit(1)
    return r

run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
     "--force-color-profile=srgb", "--no-pdf-header-footer",
     "--print-to-pdf=" + os.path.join(WORK, "card5.pdf"), "card5.html"])

info = subprocess.run(["pdfinfo", os.path.join(WORK, "card5.pdf")],
                      capture_output=True, text=True).stdout
pages = [l for l in info.splitlines() if l.startswith(("Pages", "Page size"))]
print(pages)
assert "Pages:           2" in info and "276 x 624" in info, "wrong page count/size"

shutil.copy(os.path.join(WORK, "card5.pdf"), CARD)
run(["gs", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
     "-sColorConversionStrategy=CMYK", "-dProcessColorModel=/DeviceCMYK",
     "-dPDFSETTINGS=/prepress",
     "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
     "-dDownsampleMonoImages=false",
     "-dAutoFilterColorImages=false", "-dAutoFilterGrayImages=false",
     "-dColorImageFilter=/FlateEncode", "-dGrayImageFilter=/FlateEncode",
     "-sOutputFile=" + CMYK, CARD])
rgb = subprocess.run(["bash", "-c",
    f"gs -o /dev/null -sDEVICE=inkcov '{CMYK}' 2>/dev/null | grep -c DeviceRGB || true"],
    capture_output=True, text=True).stdout.strip()
print("OK", CARD, "| CMYK done | DeviceRGB refs:", rgb)
