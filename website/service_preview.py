"""One explicitly requested service preview, never served in production."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
ROUTE = "/services/hospice-in-assisted-living-and-skilled-nursing"
LABEL = "Hospice in Assisted Living &amp; Skilled Nursing"
ASSET_PREFIX = "/__service-preview-assets/"


def enabled():
    return os.environ.get("REPLIT_DEPLOYMENT") != "1"


def decorate(document, route):
    """Only requested discovery links change; source pages stay untouched."""
    if not enabled():
        return document
    link = f'<a href="{ROUTE}">{LABEL}</a>'
    def header(match):
        return re.sub(
            r'(<a\b[^>]*href="/services"[^>]*>\s*All Services\s*</a>)',
            lambda item: item.group() + link,
            match.group(), count=1,
        )
    document = re.sub(r'<header\b[^>]*>.*?</header>', header, document,
                      count=1, flags=re.S)
    if route.rstrip("/") in ("/services", "/services.html"):
        card = (
            f'<a class="rc" href="{ROUTE}">'
            '<div class="rc-img" style="background-image:'
            f'url({ASSET_PREFIX}hero.webp)"></div>'
            f'<div class="rc-body"><h2 class="rc-title">{LABEL}</h2></div></a>'
        )
        document = document.replace('<div class="rgrid">',
                                    '<div class="rgrid">' + card, 1)
    return document


def serve(handler, chrome):
    path = urlsplit(handler.path).path
    is_page = path.rstrip("/") in (ROUTE, ROUTE + ".html")
    is_asset = path.startswith(ASSET_PREFIX)
    if not is_page and not is_asset:
        return False
    if not enabled():
        handler.send_error(404)
        return True
    if is_page:
        file = BASE / "previews/care-community.html"
        media_type = "text/html; charset=utf-8"
    else:
        name = path[len(ASSET_PREFIX):]
        if name not in ("hero.webp", "communication.webp"):
            handler.send_error(404)
            return True
        file = BASE.parent / "generated-artifacts/service-community-preview" / name
        media_type = "image/webp"
    try:
        body = file.read_bytes()
    except FileNotFoundError:
        handler.send_error(404)
        return True
    if is_page:
        body = chrome(body.decode()).encode()
    handler.send_response(200)
    handler.send_header("Content-Type", media_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Robots-Tag", "noindex, nofollow")
    handler.end_headers()
    if handler.command != "HEAD":
        handler.wfile.write(body)
    return True
