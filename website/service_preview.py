"""Approved service-page suite and navigation, available in workspace preview only."""
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
PREVIEWS = BASE / "previews"
ASSET_PREFIX = "/__service-preview-assets/"
ROUTE = "/services/hospice-in-assisted-living-and-skilled-nursing"
LABEL = "Hospice in Assisted Living &amp; Skilled Nursing"
SLUGS = (
    "in-home-hospice-care",
    "hospice-in-assisted-living-and-skilled-nursing",
    "levels-of-hospice-care",
    "24-7-nurse-access",
    "hospice-care-for-dementia",
    "hospice-care-for-advanced-cancer",
    "hospice-care-for-heart-failure",
    "respiratory-care",
    "bereavement-support",
    "hospice-evaluation",
)
GROUPS = (
    ("Where We Provide Care", SLUGS[:4]),
    ("Care for Specific Conditions", SLUGS[4:8]),
    ("Comfort & Support", (
        ("/resources/pain-symptom-management", "Pain & Symptom Management"),
        ("/resources/comfort-therapies", "Integrative & Whole-Person Care"),
        ("/sound-bath", "Sound Bath"),
        "bereavement-support",
    )),
    ("Getting Started", ("hospice-evaluation",)),
)
PRESENTATION_ASSETS = {
    "service-pages.css": "text/css; charset=utf-8",
    "service-hero-edge.css": "text/css; charset=utf-8",
    "navigation.css": "text/css; charset=utf-8",
    "navigation.js": "application/javascript; charset=utf-8",
}
IMAGE_NAMES = {"hero.webp", "communication.webp"} | {
    f"{slug}-{kind}.webp"
    for slug in SLUGS if slug != SLUGS[1]
    for kind in ("hero", "communication")
}


def enabled():
    return os.environ.get("REPLIT_DEPLOYMENT") != "1"


def catalog():
    records = json.loads((PREVIEWS / "catalog.json").read_text())
    if len(records) != len(SLUGS) or {r["slug"] for r in records} != set(SLUGS):
        raise ValueError("Service preview catalog must contain exactly ten approved pages")
    return {record["slug"]: record for record in records}


def menu_markup():
    pages = catalog()
    groups = []
    for number, (heading, items) in enumerate(GROUPS, 1):
        links = []
        for item in items:
            if isinstance(item, tuple):
                url, label = item
            else:
                url, label = "/services/" + item, pages[item]["title"]
            links.append(f'<a href="{html.escape(url, quote=True)}">'
                         f'{html.escape(label)}</a>')
        label = html.escape(heading)
        groups.append(
            '<div class="sp-menu-section">'
            f'<span class="sp-group-heading">{label}</span>'
            '<button class="sp-group-toggle" type="button" aria-expanded="false" '
            f'aria-controls="sp-menu-links-{number}">{label}</button>'
            f'<div class="sp-group-links" id="sp-menu-links-{number}">'
            + "".join(links) + '</div></div>'
        )
    # End-of-Life Care & Choices is intentionally held from this proposed menu
    # pending the counsel clearance specified in the owner's approved brief.
    return (
        '<div class="nav-sub sp-mega" id="sp-services-menu">'
        '<div class="sp-menu-grid">' + "".join(groups) + '</div>'
        '<div class="sp-menu-bottom">'
        '<a href="/services">View All Services →</a>'
        '<a href="tel:8059537273">24/7 Nurse Access · 805.953.7273</a>'
        '</div></div>'
    )


def decorate(document, route):
    """Change only preview Services navigation, never source or approved content."""
    if not enabled():
        return document
    changed = False

    def header(match):
        nonlocal changed
        source = match.group()
        if 'id="sp-services-menu"' in source:
            changed = True
            return source
        pattern = (
            r'(<div\b[^>]*\bdata-section="services"[^>]*>\s*'
            r'<a\b[^>]*>.*?</a>)'
            r'\s*<div class="nav-sub">.*?</div>'
        )
        updated, count = re.subn(pattern, lambda m: m.group(1) + menu_markup(),
                                 source, count=1, flags=re.S)
        changed = bool(count)
        return updated

    document = re.sub(r'<header\b[^>]*>.*?</header>', header, document,
                      count=1, flags=re.S)
    if changed:
        stylesheet = ASSET_PREFIX + "navigation.css"
        script = ASSET_PREFIX + "navigation.js"
        if stylesheet not in document:
            document = document.replace(
                "</head>", f'<link rel="stylesheet" href="{stylesheet}">\n</head>', 1)
        if script not in document:
            document = document.replace(
                "</body>", f'<script src="{script}" defer></script>\n</body>', 1)
        if route.rstrip("/").removesuffix(".html") in {
            "/services", *("/services/" + slug for slug in SLUGS)
        }:
            # Approved canvas treatment; keep this suite preview-only.
            edge_styles = ASSET_PREFIX + "service-hero-edge.css"
            if edge_styles not in document:
                document = document.replace(
                    "</head>", f'<link rel="stylesheet" href="{edge_styles}">\n</head>', 1)
            document = re.sub(
                r'(<div\b[^>]*\bdata-section="services"[^>]*>\s*'
                r'<a\b)(?![^>]*aria-current=)',
                r'\1 aria-current="page"', document, count=1,
            )
    return document


def serve(handler, chrome):
    path = urlsplit(handler.path).path
    route = path.rstrip("/").removesuffix(".html")
    is_directory = route == "/services"
    is_page = route in {"/services/" + slug for slug in SLUGS}
    is_asset = path.startswith(ASSET_PREFIX)
    if not is_directory and not is_page and not is_asset:
        return False
    if not enabled():
        # The existing public All Services page must continue to work unchanged.
        if is_directory:
            return False
        handler.send_error(404)
        return True
    if is_directory or is_page:
        filename = ("services-directory.html" if is_directory
                    else route.rsplit("/", 1)[1] + ".html")
        file = PREVIEWS / filename
        media_type = "text/html; charset=utf-8"
    else:
        name = path[len(ASSET_PREFIX):]
        if name in PRESENTATION_ASSETS:
            file = PREVIEWS / name
            media_type = PRESENTATION_ASSETS[name]
        elif name in IMAGE_NAMES:
            file = BASE.parent / "generated-artifacts/service-community-preview" / name
            media_type = "image/webp"
        else:
            handler.send_error(404)
            return True
    try:
        body = file.read_bytes()
    except FileNotFoundError:
        handler.send_error(404)
        return True
    if is_directory or is_page:
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
