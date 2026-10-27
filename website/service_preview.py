"""Approved service navigation and workspace-only draft rendering."""
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
PREVIEWS = BASE / "previews"
ASSET_PREFIX = "/__service-preview-assets/"
PUBLIC_ASSET_PREFIX = "/assets/service-pages/"
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
    ("Getting Started", ("hospice-evaluation",)),
    ("Where We Provide Care", SLUGS[:4]),
    ("Care for Specific Conditions", SLUGS[4:8]),
    ("Comfort & Support", (
        ("/resources/pain-symptom-management", "Pain & Symptom Management"),
        ("/resources/comfort-therapies", "Integrative & Whole-Person Care"),
        ("/sound-bath", "Sound Bath"),
        "bereavement-support",
    )),
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
    source = (PREVIEWS / "catalog.json" if enabled() else
              BASE / "elh-preview" / PUBLIC_ASSET_PREFIX.lstrip("/") / "catalog.json")
    records = json.loads(source.read_text())
    if len(records) != len(SLUGS) or {r["slug"] for r in records} != set(SLUGS):
        raise ValueError("Service preview catalog must contain exactly ten approved pages")
    return {record["slug"]: record for record in records}

def directory_issues(document):
    """Validate the approved directory instead of the retired hero card counts."""
    main = re.search(r"<main\b.*?</main>", document, re.S)
    if not main:
        return ["services-directory-missing-main"]
    headings = [
        html.unescape(text)
        for text in re.findall(
            r'<section class="directory-group[^"]*"><h2>(.*?)</h2>', main[0], re.S)
    ]
    links = re.findall(
        r'<article class="directory-item">\s*<a href="([^"]+)">', main[0], re.S)
    expected_links = [
        item[0] if isinstance(item, tuple) else "/services/" + item
        for _, items in GROUPS for item in items
    ]
    issues = []
    if headings != [name for name, _ in GROUPS]:
        issues.append("services-directory-groups: expected the four approved groups in order")
    if sorted(links) != sorted(expected_links):
        issues.append("services-directory-links: expected each of the 13 approved services exactly once")
    return issues


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
    """Apply approved navigation without rewriting signed article sources."""
    asset_prefix = ASSET_PREFIX if enabled() else PUBLIC_ASSET_PREFIX
    changed = False

    def header(match):
        nonlocal changed
        source = match.group()
        # Refresh shared navigation in old/frozen pages at response time too.
        # Do not rewrite Journal approval snapshots for a chrome-only change.
        insurance_link = (
            '<a href="/resources/medicare-hospice-benefit#insurance">'
            'Insurance &amp; Coverage</a>'
        )
        resources = (
            r'(<div\b[^>]*\bdata-section="resources"[^>]*>\s*'
            r'<a\b[^>]*>.*?</a>\s*<div class="nav-sub">)(.*?)(</div>)'
        )
        source = re.sub(
            resources,
            lambda m: m.group(1) +
            ("" if insurance_link in m.group(2) else insurance_link) +
            m.group(2) + m.group(3),
            source, count=1, flags=re.S,
        )
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
        stylesheet = asset_prefix + "navigation.css"
        script = asset_prefix + "navigation.js"
        if stylesheet not in document:
            document = document.replace(
                "</head>", f'<link rel="stylesheet" href="{stylesheet}">\n</head>', 1)
        if script not in document:
            document = document.replace(
                "</body>", f'<script src="{script}" defer></script>\n</body>', 1)
        if route.rstrip("/").removesuffix(".html") in {
            "/services", *("/services/" + slug for slug in SLUGS)
        }:
            edge_styles = asset_prefix + "service-hero-edge.css"
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
        # Approved pages are now ordinary public HTML. Never expose draft assets.
        if not is_asset:
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
