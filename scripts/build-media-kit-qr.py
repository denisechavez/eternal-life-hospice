#!/usr/bin/env python3
"""Build the Eternal Life Hospice MEDIA-KIT QR code.

Encodes https://eternallifehospice.com/media-kit at error-correction level H so the
centered ELH infinity logo badge can sit in the middle without breaking the scan.
Reuses the exact badge/glyph composition of scripts/build-refer-qr.py.

Outputs:
  - website/elh-preview/assets/qr-media-kit.png        plum-on-WHITE (print / light tiles)
  - website/elh-preview/assets/img/qr-media-kit-cream.png  plum-on-CREAM (dark surfaces)

Run: python3 scripts/build-media-kit-qr.py
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import qrcode
from qrcode.constants import ERROR_CORRECT_H

URL = "https://eternallifehospice.com/media-kit"
DEEP_PLUM = (60, 28, 59); PLUM = (91, 46, 89)
CREAM = (245, 240, 235); WHITE = (255, 255, 255)
ROOT = "website/elh-preview"
GLYPH_SRC = f"{ROOT}/assets/img/qr-cream.png"


def extract_infinity_glyph():
    a = np.array(Image.open(GLYPH_SRC).convert("RGB"))
    h, w, _ = a.shape; cx, cy = w // 2, h // 2; box = 110
    sub = a[cy - box:cy + box, cx - box:cx + box].astype(int)
    mask = sub.sum(2) < 560
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


def make_qr(size, module_color, bg_color, badge_fill, outline):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=4)
    qr.add_data(URL); qr.make(fit=True)
    img = qr.make_image(fill_color=module_color, back_color=bg_color).convert("RGB")
    img = img.resize((size, size), Image.NEAREST)
    badge = int(size * 0.30); clear = int(badge * 1.06); cx = cy = size // 2
    ImageDraw.Draw(img).rectangle([cx - clear // 2, cy - clear // 2, cx + clear // 2, cy + clear // 2], fill=bg_color)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    rad = int(badge * 0.22)
    bx0, by0 = cx - badge // 2, cy - badge // 2; bx1, by1 = cx + badge // 2, cy + badge // 2
    sd.rounded_rectangle([bx0, by0 + int(badge * 0.04), bx1, by1 + int(badge * 0.04)], radius=rad, fill=(40, 24, 56, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(badge * 0.05)))
    img = Image.alpha_composite(img.convert("RGBA"), shadow)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad, fill=badge_fill + (255,))
    if outline:
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad, outline=PLUM + (90,), width=max(2, size // 700))
    glyph = extract_infinity_glyph()
    gw = int(badge * 0.66); gh = int(gw * glyph.height / glyph.width)
    glyph = glyph.resize((gw, gh), Image.LANCZOS)
    img.alpha_composite(glyph, (cx - gw // 2, cy - gh // 2))
    return img.convert("RGB")


def verify(path):
    import cv2
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(path))
    ok = data == URL
    print(f"  decode {path} -> {data!r} {'OK' if ok else 'FAIL'}")
    return ok


def main():
    wp = f"{ROOT}/assets/qr-media-kit.png"; cp = f"{ROOT}/assets/img/qr-media-kit-cream.png"
    make_qr(1480, DEEP_PLUM, WHITE, WHITE, True).save(wp)
    make_qr(1024, PLUM, CREAM, (250, 247, 243), False).save(cp)
    print(f"wrote {wp}\nwrote {cp}")
    sys.exit(0 if (verify(wp) and verify(cp)) else 1)


if __name__ == "__main__":
    main()
