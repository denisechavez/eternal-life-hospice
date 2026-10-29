"""Narrow workspace-only fallback for reviewed export downloads."""
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "ELH-Google-PPC-Three-Thank-You-Options.pdf": (
        "google-ppc-three-options/ELH-Google-PPC-Three-Thank-You-Options.pdf",
        "application/pdf",
    ),
    "ELH-Google-PPC-Three-Thank-You-Options-Handoff.zip": (
        "google-ppc-three-options/ELH-Google-PPC-Three-Thank-You-Options-Handoff.zip",
        "application/zip",
    ),
    "Eternal-Manual-Social-October-27-31-2026.zip": (
        "Eternal-Manual-Social-October-27-31-2026.zip", "application/zip"
    ),
    "ELH-Handbook-Concepts-7-8-9.zip": (
        "patient-guide/ELH-Handbook-Concepts-7-8-9.zip", "application/zip"
    ),
    "7-ELH-Handbook-Concept-Garden.pdf": (
        "patient-guide/7. ELH-Handbook-Concept-Garden.pdf", "application/pdf"
    ),
    "8-ELH-Handbook-Concept-Held-Together.pdf": (
        "patient-guide/8. ELH-Handbook-Concept-Held-Together.pdf", "application/pdf"
    ),
    "9-ELH-Handbook-Concept-Botanical.pdf": (
        "patient-guide/9. ELH-Handbook-Concept-Botanical.pdf", "application/pdf"
    ),
    "october-23-gbp.jpg": (
        "social-2026-10-23/2026-10-23-gbp.jpg", "image/jpeg"
    ),
    "october-26-30-review.pdf": (
        "social-2026-10-26/review.pdf", "application/pdf"
    ),
    "october-26-30-social.zip": (
        "eternal-social-october-26-2026.zip", "application/zip"
    ),
}


def serve(handler):
    path = urlsplit(handler.path).path
    prefix = "/__social-downloads/"
    if not path.startswith(prefix):
        return False
    name = path[len(prefix):]
    # Exports must not become publicly available on a published deployment.
    if os.environ.get("REPLIT_DEPLOYMENT") == "1" or name not in FILES:
        handler.send_error(404)
        return True
    relative, media_type = FILES[name]
    file = ROOT / "generated-artifacts" / relative
    try:
        stream = file.open("rb")
    except FileNotFoundError:
        handler.send_error(404)
        return True
    with stream:
        handler.send_response(200)
        handler.send_header("Content-Type", media_type)
        handler.send_header("Content-Length", str(os.fstat(stream.fileno()).st_size))
        handler.send_header("Content-Disposition", f'attachment; filename="{name}"')
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Robots-Tag", "noindex, nofollow")
        handler.end_headers()
        if handler.command != "HEAD":
            shutil.copyfileobj(stream, handler.wfile)
    return True
