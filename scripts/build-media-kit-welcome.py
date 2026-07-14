#!/usr/bin/env python3
"""Regenerate the media-kit Welcome page image (assets/kit/02-welcome.jpg).

This page (inside-front cover of the press kit / opening left page of the
/media-kit flipbook) was originally a flat, externally-authored raster that had
baked-in guide lines and soft, low-res text. It is now rebuilt from an HTML
template rendered by headless Chromium at 2x, so the text, logos and dividers
are razor sharp and there are no stray lines.

Source assets live next to this script in scripts/media-kit-welcome/:
  - welcome-script.png       the "Welcome" script wordmark (transparent)
  - aleksandra-signature.png the founder's handwritten signature (transparent)
  - aleks-cut.png            the founder portrait, background removed

The real portrait is capped at its source resolution, so it is placed at
native-ish scale (never AI-altered); the crispness win is the vector text.

Output aspect ratio (0.648) is kept identical to the other kit pages so the
flipbook and the PDF builder (build-media-kit-pdf.py) stay in sync.
"""
import os
import subprocess
import tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "media-kit-welcome")
FONTS = os.path.join(ROOT, "website", "elh-preview", "assets", "fonts")
BRAND = os.path.join(ROOT, "brand-assets")
IMG = os.path.join(ROOT, "website", "elh-preview", "assets", "img")
OUT = os.path.join(ROOT, "website", "elh-preview", "assets", "kit", "02-welcome.jpg")

# Authoring coordinate space (matches the original page); rendered at 2x then
# supersampled down for smooth anti-aliasing.
CSS_W, CSS_H = 1620, 2500
OUT_W, OUT_H = 2430, 3750  # 1.5x — high-res but keeps the portrait upscale modest


def f(*parts):
    return "file://" + os.path.join(*parts)


HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Fraunces';src:url('{f(FONTS,'Fraunces-var.woff2')}') format('woff2');font-weight:100 900;font-style:normal;font-display:block;}}
@font-face{{font-family:'Fraunces';src:url('{f(FONTS,'Fraunces-Italic-var.woff2')}') format('woff2');font-weight:100 900;font-style:italic;font-display:block;}}
@font-face{{font-family:'Jost';src:url('{f(FONTS,'JostELH-Light.woff2')}') format('woff2');font-weight:300;font-style:normal;font-display:block;}}
@font-face{{font-family:'Jost';src:url('{f(FONTS,'JostELH-Regular.woff2')}') format('woff2');font-weight:400;font-style:normal;font-display:block;}}
@font-face{{font-family:'Jost';src:url('{f(FONTS,'JostELH-Medium.woff2')}') format('woff2');font-weight:500;font-style:normal;font-display:block;}}
@font-face{{font-family:'Jost';src:url('{f(FONTS,'JostELH-SemiBold.woff2')}') format('woff2');font-weight:600;font-style:normal;font-display:block;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{margin:0;padding:0;}}
:root{{--plum:#3e1a35;--cream:#f4ecdf;--gold:#b18a4f;--lav:#e6d8e6;--lav-soft:#d9c7d9;}}
.page{{position:relative;width:{CSS_W}px;height:{CSS_H}px;overflow:hidden;font-family:'Jost',sans-serif;
  background:radial-gradient(130% 70% at 26% 6%,rgba(158,126,142,.55) 0%,rgba(96,64,90,.20) 34%,rgba(60,26,52,0) 60%),
  linear-gradient(163deg,#5a3450 0%,#472440 18%,#3d1b35 44%,#38152f 78%,#350f2a 100%);}}
.portrait{{position:absolute;top:96px;right:-96px;height:1500px;z-index:1;}}
.portrait img{{height:100%;width:auto;display:block;}}
.photo-blend{{position:absolute;inset:0;z-index:2;pointer-events:none;
  background:linear-gradient(to right,rgba(61,27,53,0) 0%,rgba(61,27,53,0) 30%,
  rgba(61,27,53,.98) 41%,rgba(61,27,53,.72) 48%,rgba(61,27,53,.28) 55%,rgba(61,27,53,0) 65%);}}
.photo-tint{{position:absolute;inset:0;z-index:2;pointer-events:none;mix-blend-mode:soft-light;
  background:radial-gradient(60% 55% at 74% 34%,rgba(120,58,104,.34) 0%,rgba(120,58,104,0) 70%);}}
.letter{{position:absolute;left:70px;top:70px;width:660px;z-index:3;}}
.wordmark{{width:560px;display:block;margin:0 0 26px -6px;}}
.headline{{font-family:'Fraunces',serif;font-weight:600;font-size:46px;line-height:1.16;color:#f6efe2;letter-spacing:.2px;margin-bottom:30px;}}
.salutation{{font-weight:500;font-size:25px;letter-spacing:.6px;color:var(--lav);margin-bottom:22px;}}
.body p{{font-weight:300;font-size:25.5px;line-height:1.52;color:#e7dae7;margin-bottom:19px;}}
.body em{{font-family:'Fraunces',serif;font-style:italic;font-weight:500;color:#f3e7d6;font-size:26px;}}
.signoff{{font-weight:400;font-size:25px;color:var(--lav);margin-top:20px;}}
.sig{{width:360px;display:block;margin:6px 0 2px -6px;}}
.name{{font-family:'Fraunces',serif;font-weight:600;font-size:41px;color:#f6efe2;letter-spacing:.3px;margin-top:6px;}}
.titles{{font-weight:400;font-size:22px;line-height:1.5;color:var(--lav-soft);margin-top:8px;}}
.credbar{{position:absolute;left:0;right:0;bottom:0;height:560px;z-index:4;}}
.credbar svg.wave{{position:absolute;top:-58px;left:0;width:1620px;height:120px;display:block;}}
.credbar .panel{{position:absolute;top:60px;left:0;right:0;bottom:0;background:var(--cream);}}
.credtitle{{font-family:'Fraunces',serif;font-weight:600;font-size:50px;color:var(--plum);text-align:center;letter-spacing:.4px;padding-top:64px;}}
.divider{{display:flex;align-items:center;justify-content:center;gap:22px;margin:22px auto 0;width:640px;}}
.divider .ln{{height:2px;flex:1;background:linear-gradient(to var(--dir,right),rgba(177,138,79,0) 0%,var(--gold) 60%);}}
.divider .ln.r{{--dir:left;}}
.divider img{{width:66px;height:auto;display:block;opacity:.9;}}
.logos{{display:flex;justify-content:center;align-items:flex-end;gap:96px;margin-top:54px;}}
.logo{{display:flex;flex-direction:column;align-items:center;gap:22px;width:340px;}}
.logo .art{{height:132px;display:flex;align-items:center;justify-content:center;}}
.logo .art img{{max-height:132px;max-width:300px;width:auto;height:auto;display:block;}}
.logo.achc .art img{{max-height:150px;}}
.pill{{font-weight:500;font-size:20px;letter-spacing:.5px;color:var(--cream);background:var(--plum);border-radius:999px;padding:9px 26px;white-space:nowrap;}}
</style></head><body>
<div class="page">
  <div class="portrait"><img src="{f(SRC,'aleks-cut.png')}" alt=""></div>
  <div class="photo-blend"></div>
  <div class="photo-tint"></div>
  <div class="letter">
    <img class="wordmark" src="{f(SRC,'welcome-script.png')}" alt="Welcome">
    <div class="headline">Every life chapter deserves<br>clarity, comfort and dignity</div>
    <div class="salutation">Dear Families and Care Partners,</div>
    <div class="body">
      <p>Thank you for considering Eternal Life Hospice. Whether you are seeking support for yourself or for someone you love, you deserve clear answers, steady guidance and care that feels whole, attentive, and dignified.</p>
      <p>This work is deeply personal to me. I was drawn to hospice after losing my grandmother in care and have spent more than a decade devoted to this calling. Having walked through my own open-heart surgery, I understand what it is to be vulnerable in the moments that matter most.</p>
      <p><em>The Eternal Standard</em> is the foundation of how we serve. It is rooted in four pillars of care: <em>Clinical Confidence</em>, <em>Guided Presence</em>, <em>Whole-Person Comfort</em>, and <em>Compliance-Led Care</em>&mdash;each designed to protect dignity through every call, visit and family conversation.</p>
      <p>Our commitment is that you are informed, supported and always seen as you make deeply personal decisions for someone you love.</p>
      <p>Whatever brings you here, you will be received with the respect, expertise and presence each moment requires.</p>
      <p>Thank you for allowing us to walk beside you and those you love, during this sensitive and meaningful time.</p>
    </div>
    <div class="signoff">Sincerely,</div>
    <img class="sig" src="{f(SRC,'aleksandra-signature.png')}" alt="Aleksandra Dubina signature">
    <div class="name">Aleksandra Dubina</div>
    <div class="titles">Founder and Chief Executive Officer<br>Certified Hospice Administrator</div>
  </div>
  <div class="credbar">
    <svg class="wave" viewBox="0 0 1620 120" preserveAspectRatio="none"><path d="M0,74 C 420,10 1180,10 1620,66 L1620,120 L0,120 Z" fill="#f4ecdf"></path></svg>
    <div class="panel">
      <div class="credtitle">Credentials &amp; Certifications</div>
      <div class="divider"><span class="ln"></span>
        <img src="{f(BRAND,'Medical','eternal-life-hospice-infinity-metallic.png')}" alt="">
        <span class="ln r"></span></div>
      <div class="logos">
        <div class="logo cms"><div class="art"><img src="{f(BRAND,'credential-logos','cms-centers-for-medicare-medicaid-services.png')}" alt="CMS"></div><span class="pill">Medicare-Certified</span></div>
        <div class="logo cdph"><div class="art"><img src="{f(IMG,'cred-cdph.png')}" alt="CDPH"></div><span class="pill">CDPH-Licensed</span></div>
        <div class="logo achc"><div class="art"><img src="{f(BRAND,'credential-logos','achc-accredited-gold-seal-metallic.png')}" alt="ACHC"></div><span class="pill">ACHC-Accredited</span></div>
      </div>
    </div>
  </div>
</div></body></html>
"""


def main():
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
        fh.write(HTML)
        html_path = fh.name
    raw = os.path.join(tempfile.gettempdir(), "welcome-raw.png")
    subprocess.run([
        "chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--hide-scrollbars", "--force-device-scale-factor=2",
        f"--window-size={CSS_W},{CSS_H}", "--virtual-time-budget=6000",
        f"--screenshot={raw}", f"file://{html_path}",
    ], check=True)
    im = Image.open(raw).convert("RGB").resize((OUT_W, OUT_H), Image.LANCZOS)
    im.save(OUT, "JPEG", quality=90, optimize=True, progressive=True)
    os.remove(html_path)
    print(f"Built {OUT} ({im.size[0]}x{im.size[1]}, {os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
