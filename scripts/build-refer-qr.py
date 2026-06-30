#!/usr/bin/env python3
"""
Build the Eternal Life Hospice REFERRAL-page QR codes.

Encodes https://eternallifehospice.com/refer (the one-page partner referral form)
at error-correction level H so the centered ELH infinity logo badge can sit in the
middle without breaking the scan.

Outputs two reusable masters (siblings of the existing homepage QRs):
  - website/elh-preview/assets/qr-refer.png        plum-on-WHITE  (for print on light/white tiles; matches qr-eternallifehospice.png placement)
  - website/elh-preview/assets/img/qr-refer-cream.png  plum-on-CREAM (light-backed variant for dark surfaces; matches qr-cream.png approach)

The infinity glyph is lifted from the existing footer QR (assets/img/qr-cream.png)
so the mark + metallic gradient stay byte-faithful to the brand.

Run:  python3 scripts/build-refer-qr.py
Verify is built in (re-decodes each PNG with OpenCV before finishing).
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import qrcode
from qrcode.constants import ERROR_CORRECT_H

REFER_URL = "https://eternallifehospice.com/refer"

DEEP_PLUM = (60, 28, 59)    # #3C1C3B  – module color matching qr-eternallifehospice.png (white master)
PLUM      = (91, 46, 89)    # #5B2E59  – module color matching qr-cream.png (cream master)
CREAM     = (245, 240, 235) # #F5F0EB
WHITE     = (255, 255, 255)

ROOT = "website/elh-preview"
GLYPH_SRC = f"{ROOT}/assets/img/qr-cream.png"


def extract_infinity_glyph():
    """Lift the plum infinity mark (with its gradient) from the footer QR center."""
    a = np.array(Image.open(GLYPH_SRC).convert("RGB"))
    h, w, _ = a.shape
    cx, cy = w // 2, h // 2
    box = 110
    sub = a[cy - box:cy + box, cx - box:cx + box].astype(int)
    lum = sub.sum(2)
    mask = lum < 560
    ys, xs = np.where(mask)
    x0, x1 = cx - box + xs.min(), cx - box + xs.max()
    y0, y1 = cy - box + ys.min(), cy - box + ys.max()
    pad = 10
    crop = a[y0 - pad:y1 + pad + 1, x0 - pad:x1 + pad + 1].astype(float)
    glum = crop.sum(2)
    alpha = np.clip((720 - glum) / (720 - 520), 0, 1)
    rgba = np.zeros((crop.shape[0], crop.shape[1], 4), dtype=np.uint8)
    rgba[..., :3] = crop.astype(np.uint8)
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def make_qr(size, module_color, bg_color, badge_fill, draw_badge_outline):
    """Render the /refer QR at `size` px with a centered infinity logo badge."""
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=4)
    qr.add_data(REFER_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color=module_color, back_color=bg_color).convert("RGB")
    img = img.resize((size, size), Image.NEAREST)

    # Clear a quiet center square so the badge reads cleanly (level H absorbs the loss).
    badge = int(size * 0.30)
    clear = int(badge * 1.06)
    cx = cy = size // 2
    draw = ImageDraw.Draw(img)
    draw.rectangle([cx - clear // 2, cy - clear // 2, cx + clear // 2, cy + clear // 2], fill=bg_color)

    # Soft drop shadow + rounded badge tile.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    rad = int(badge * 0.22)
    bx0, by0 = cx - badge // 2, cy - badge // 2
    bx1, by1 = cx + badge // 2, cy + badge // 2
    sd.rounded_rectangle([bx0, by0 + int(badge * 0.04), bx1, by1 + int(badge * 0.04)],
                         radius=rad, fill=(40, 24, 56, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(badge * 0.05)))
    img = Image.alpha_composite(img.convert("RGBA"), shadow)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad, fill=badge_fill + (255,))
    if draw_badge_outline:
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad,
                               outline=PLUM + (90,), width=max(2, size // 700))

    # Place the infinity glyph centered inside the badge.
    glyph = extract_infinity_glyph()
    gw = int(badge * 0.66)
    gh = int(gw * glyph.height / glyph.width)
    glyph = glyph.resize((gw, gh), Image.LANCZOS)
    img.alpha_composite(glyph, (cx - gw // 2, cy - gh // 2))
    return img.convert("RGB")


def verify(path):
    import cv2
    arr = cv2.imread(path)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    ok = data == REFER_URL
    print(f"  decode {path} -> {data!r} {'OK' if ok else 'FAIL'}")
    return ok


def main():
    white_path = f"{ROOT}/assets/qr-refer.png"
    cream_path = f"{ROOT}/assets/img/qr-refer-cream.png"

    make_qr(1480, DEEP_PLUM, WHITE, WHITE, draw_badge_outline=True).save(white_path)
    make_qr(1024, PLUM, CREAM, (250, 247, 243), draw_badge_outline=False).save(cream_path)
    print(f"wrote {white_path}\nwrote {cream_path}")

    ok = verify(white_path) and verify(cream_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
