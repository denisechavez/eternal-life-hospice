#!/usr/bin/env python3
"""Build double-sided business card HTML for Eternal Life Hospice.
Mirrors the rack-card print convention: 3.5x2in trim + 0.125 bleed, page 4.0x2.5in
(288x180pt) with hand-drawn crop ticks, two .page divs (front/back) -> 2-page PDF."""
import sys

# ---- crop ticks (8) in the page margin, aligned to the 3.5x2 trim box ----
# trim lines: L=0.25in R=3.75in T=0.25in B=2.25in ; ticks 0.125in long, in margin
def ticks():
    L, R, T, B = "0.25in", "3.75in", "0.25in", "2.25in"
    Rm, Bm = "3.875in", "2.375in"  # right/bottom margin start
    V = "position:absolute;width:0.7pt;height:0.125in;background:#777;margin-left:-0.35pt;"
    H = "position:absolute;height:0.7pt;width:0.125in;background:#777;margin-top:-0.35pt;"
    d = []
    # top-left
    d.append(f'<div style="{V}left:{L};top:0;"></div>')
    d.append(f'<div style="{H}top:{T};left:0;"></div>')
    # top-right
    d.append(f'<div style="{V}left:{R};top:0;"></div>')
    d.append(f'<div style="{H}top:{T};left:{Rm};"></div>')
    # bottom-left
    d.append(f'<div style="{V}left:{L};top:{Bm};"></div>')
    d.append(f'<div style="{H}top:{B};left:0;"></div>')
    # bottom-right
    d.append(f'<div style="{V}left:{R};top:{Bm};"></div>')
    d.append(f'<div style="{H}top:{B};left:{Rm};"></div>')
    return "\n".join(d)

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
@page{size:4in 2.5in;margin:0}
html,body{background:#fff}
.page{width:4in;height:2.5in;position:relative;overflow:hidden;background:#fff;page-break-after:always}
.page:last-child{page-break-after:auto}
.bleed{position:absolute;left:0.125in;top:0.125in;width:3.75in;height:2.25in;overflow:hidden;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.pad{position:absolute;left:0.28in;top:0.26in;right:0.28in;bottom:0.24in}
/* ---------- FRONT ---------- */
.front{background:#F5F0EB}
.fr-top{display:flex;justify-content:space-between;align-items:flex-start}
.fr-id{padding-top:2pt}
.name{font-family:'Fraunces ELH',Georgia,serif;font-weight:600;font-size:13.5pt;line-height:1.02;color:#5B2E59;letter-spacing:.1pt}
.title{font-family:'Jost ELH',sans-serif;font-weight:600;font-size:6pt;letter-spacing:1.4pt;
  text-transform:uppercase;color:#A07C36;margin-top:3.5pt}
.fr-logo{height:0.62in;width:auto;display:block}
.fr-contact{position:absolute;left:0.28in;right:0.28in;bottom:0.44in;
  font-family:'Jost ELH',sans-serif;font-weight:400;font-size:6.6pt;line-height:1.55;color:#3a2b39}
.fr-contact .lbl{font-weight:600;color:#5B2E59;letter-spacing:.4pt}
.fr-contact .addr{color:#6b5d68;font-size:6.1pt}
.fr-rule{position:absolute;left:0.28in;right:0.28in;bottom:0.375in;height:0.5pt;background:#D8CDBF}
.fr-foot{position:absolute;left:0.28in;right:0.28in;bottom:0.13in;text-align:center;
  font-family:'Jost ELH',sans-serif;font-weight:500;font-size:5pt;letter-spacing:.35pt;line-height:1.55;color:#5A4057}
.fr-foot .cov{color:#A07C36}
/* ---------- BACK ---------- */
.back{background:linear-gradient(135deg,#3C1C3B 0%,#5B2E59 78%)}
.bk-logo{position:absolute;left:50%;top:0.30in;transform:translateX(-50%);height:0.64in;width:auto}
.bk-tag{position:absolute;left:0;right:0;top:1.06in;text-align:center;
  font-family:'Fraunces ELH',Georgia,serif;font-style:italic;font-weight:500;font-size:11.5pt;color:#C9B07E}
.bk-sub{position:absolute;left:0;right:0;top:1.40in;text-align:center;
  font-family:'Jost ELH',sans-serif;font-weight:400;font-size:6pt;letter-spacing:1.6pt;
  text-transform:uppercase;color:#EDE6DE}
.bk-qr{position:absolute;left:0.30in;bottom:0.20in;display:flex;align-items:center;gap:5pt}
.bk-qr img{width:0.52in;height:0.52in;background:#fff;padding:2pt;border-radius:2pt}
.bk-qr-cap{font-family:'Jost ELH',sans-serif;font-weight:400;font-size:5.6pt;line-height:1.5;
  letter-spacing:.3pt;color:#EDE6DE}
.bk-cred{position:absolute;right:0.30in;bottom:0.215in;text-align:right;
  font-family:'Jost ELH',sans-serif;font-weight:500;font-size:5pt;line-height:1.7;
  letter-spacing:.3pt;color:#C9B07E}
.bk-cred span{color:#EDE6DE;display:block;font-weight:400}
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="assets/elh.css">
<style>__CSS__</style></head><body>
<div class="page">__TICKS__
  <div class="bleed front"><div class="pad">
    <div class="fr-top">
      <div class="fr-id">
        <div class="name">__NAME__</div>
        <div class="title">__TITLE__</div>
      </div>
      <img class="fr-logo" src="assets/logo-eternal-trans.png" alt="Eternal Life Hospice">
    </div>
    <div class="fr-rule"></div>
    <div class="fr-contact">
      <div><span class="lbl">24/7</span> &nbsp;805.953.7273 &nbsp;&middot;&nbsp; Fax 805.953.8530</div>
      <div>__EMAIL__ &nbsp;&middot;&nbsp; eternallifehospice.com</div>
      <div class="addr">4165 E Thousand Oaks Blvd, Ste 325B, Westlake Village, CA 91362</div>
    </div>
    <div class="fr-foot">Medicare-Certified &middot; CDPH-Licensed &middot; ACHC-Accredited<br><span class="cov">Serving Ventura &amp; Los Angeles County</span></div>
  </div></div>
</div>
<div class="page">__TICKS__
  <div class="bleed back">
    <img class="bk-logo" src="assets/logo-cream.png" alt="Eternal Life Hospice">
    <div class="bk-tag">Care That Honors Life</div>
    <div class="bk-sub">Here in Moments That Matter Most</div>
    <div class="bk-qr">
      <img src="assets/qr-eternallifehospice.png" alt="Scan to refer or learn more">
      <div class="bk-qr-cap">Refer &amp; learn more<br>eternallifehospice.com</div>
    </div>
    <div class="bk-cred">Medicare-Certified<span>CDPH-Licensed &middot; ACHC-Accredited</span></div>
  </div>
</div>
</body></html>"""

def build(name, title, email):
    return (PAGE.replace("__CSS__", CSS).replace("__TICKS__", ticks())
            .replace("__NAME__", name).replace("__TITLE__", title)
            .replace("__EMAIL__", email))

CARDS = {
    "eternal-life-business-card-aleksandra-dubina": (
        "Aleksandra Dubina", "Chief Executive Officer", "aleksandra@eternallifehospice.com"),
    "eternal-life-business-card-TEMPLATE": (
        "Full Name", "Title / Role", "name@eternallifehospice.com"),
}

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    for slug, (n, t, e) in CARDS.items():
        with open(f"{outdir}/{slug}.html", "w") as f:
            f.write(build(n, t, e))
        print(f"wrote {outdir}/{slug}.html")
