#!/usr/bin/env python3
"""Card 5 refinements: logo plaque on the front + rebuilt, aligned contact
panel on the back (keeps existing QR tile, cropped from the master)."""
import os, shutil, subprocess, sys, tempfile

ROOT = "/home/runner/workspace"
PRINT = os.path.join(ROOT, "exports", "print")
CMYK = os.path.join(PRINT, "print-ready-cmyk")
LOGOS = os.path.join(ROOT, "brand-assets", "credential-logos")
FDIR = os.path.join(ROOT, "website", "elh-preview", "assets", "fonts")
CARD = os.path.join(PRINT, "eternal-life-referral-card-5-quick-referral-action.pdf")

WORK = tempfile.mkdtemp(prefix="c5fix-")
for f in ["cms-centers-for-medicare-medicaid-services.png",
          "cdph-california-department-of-public-health.png",
          "achc-accredited-gold-seal.png", "epic-systems.png"]:
    shutil.copy(os.path.join(LOGOS, f), WORK)
shutil.copy(os.path.join(FDIR, "JostELH-Medium.woff2"), WORK)
shutil.copy(os.path.join(FDIR, "JostELH-SemiBold.woff2"), WORK)
shutil.copy("/tmp/qr-tile.png", WORK)

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

# ---------- FRONT: cream credential plaque in the empty plum band ----------
front = (
    '<div class="abs" style="left:44pt;top:420pt;width:200pt;height:46pt;'
    'background:#F5F0EB;border-radius:10pt;display:flex;align-items:center;'
    'justify-content:center;gap:11pt;padding:0 8pt">'
    f'<img src="{CMS}" style="max-height:14pt;max-width:42pt">'
    f'<img src="{CDPH}" style="max-height:21pt">'
    f'<img src="{ACHC}" style="max-height:28pt">'
    f'<img src="{EPIC}" style="max-height:15pt;max-width:40pt">'
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

pdfs = {}
for name, body in (("front", front), ("back", back)):
    html = os.path.join(WORK, name + ".html")
    open(html, "w").write(f"<!doctype html><html><head><meta charset='utf-8'>"
                          f"<style>{CSS}</style></head><body>{body}</body></html>")
    pdf = os.path.join(WORK, name + ".pdf")
    run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
         "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + html])
    pdfs[name] = pdf

s1 = os.path.join(WORK, "s1.pdf"); s2 = os.path.join(WORK, "s2.pdf")
run(["qpdf", CARD, "--overlay", pdfs["front"], "--to=1", "--", s1])
run(["qpdf", s1, "--overlay", pdfs["back"], "--to=2", "--", s2])
shutil.move(s2, CARD)
run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite",
     "-dProcessColorModel=/DeviceCMYK", "-sColorConversionStrategy=CMYK",
     "-dOverrideICC=true", "-dPDFSETTINGS=/prepress", "-dAutoRotatePages=/None",
     "-o", os.path.join(CMYK, "eternal-life-referral-card-5-quick-referral-action-CMYK.pdf"), CARD])
info = subprocess.run(["pdfinfo", CARD], capture_output=True, text=True).stdout
print([l for l in info.splitlines() if "Pages" in l or "Page size" in l])
print("OK", WORK)
