"""Promote only the owner-approved service suite; never run as an automatic build."""
import html
import re
import shutil
from datetime import date
from pathlib import Path

import service_preview

BASE = Path(__file__).resolve().parent
SITE = BASE / "elh-preview"
ORIGIN = "https://eternallifehospice.com"


def prepare():
    assets = SITE / service_preview.PUBLIC_ASSET_PREFIX.lstrip("/")
    images = BASE.parent / "generated-artifacts/service-community-preview"
    # Validate the complete reviewed bundle before writing public files.
    sources = {
        name: service_preview.PREVIEWS / name
        for name in service_preview.PRESENTATION_ASSETS
    }
    sources["catalog.json"] = service_preview.PREVIEWS / "catalog.json"
    sources.update({name: images / name for name in service_preview.IMAGE_NAMES})
    documents = {"/services": service_preview.PREVIEWS / "services-directory.html"}
    documents.update({
        "/services/" + slug: service_preview.PREVIEWS / (slug + ".html")
        for slug in service_preview.SLUGS
    })
    for source in [*sources.values(), *documents.values()]:
        if not source.is_file():
            raise FileNotFoundError("Approved service asset missing: " + str(source))
    homepage = (SITE / "index.html").read_text()
    shared_chrome = {
        tag: re.search(rf"<{tag}\b.*?</{tag}>", homepage, re.S)[0]
        for tag in ("header", "footer")
    }
    shared_meta = dict(re.findall(
        r'<meta property="(og:image[^"]*)" content="([^"]*)"', homepage))
    assets.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        if name == "catalog.json":
            (assets / name).write_text(source.read_text().replace(
                service_preview.ASSET_PREFIX, service_preview.PUBLIC_ASSET_PREFIX))
        else:
            shutil.copyfile(source, assets / name)
    for route, source in documents.items():
        document = source.read_text()
        for tag, markup in shared_chrome.items():
            document = re.sub(rf"<{tag}\b.*?</{tag}>", lambda _: markup,
                              document, count=1, flags=re.S)
        document = document.replace("header.js?v=20260920",
                                    "header.js?v=20260901d")
        document = document.replace(service_preview.ASSET_PREFIX,
                                    service_preview.PUBLIC_ASSET_PREFIX)
        document = re.sub(
            r'<meta name="robots" content="[^"]*">',
            '<meta name="robots" content="index,follow">', document)
        # Canonicals are explicit and stable; do not copy preview-only addresses.
        document = re.sub(r'<link rel="canonical"[^>]*>\s*', '', document)
        canonical = html.escape(ORIGIN + route, quote=True)
        title = html.unescape(re.search(r"<title>(.*?)</title>", document, re.S)[1])
        description = html.unescape(re.search(
            r'<meta name="description" content="([^"]*)"', document)[1])
        metadata = {
            "og:title": title, "og:description": description,
            "og:url": ORIGIN + route, "og:type": "website",
            "og:site_name": "Eternal Life Hospice",
            **{name: html.unescape(shared_meta[name]) for name in (
                "og:image", "og:image:width", "og:image:height", "og:image:alt")},
            "twitter:card": "summary_large_image", "twitter:title": title,
            "twitter:description": description,
            "twitter:image": html.unescape(shared_meta["og:image"]),
        }
        social = "\n".join(
            f'<meta {"property" if name.startswith("og:") else "name"}="{name}" '
            f'content="{html.escape(value, quote=True)}">'
            for name, value in metadata.items())
        document = document.replace("</head>",
                                    f'<link rel="canonical" href="{canonical}">\n'
                                    + social + "\n</head>", 1)
        target = SITE / (route.lstrip("/") + ".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
    sitemap = SITE / "sitemap.xml"
    xml = sitemap.read_text()
    for route in documents:
        if f"<loc>{ORIGIN}{route}</loc>" not in xml:
            entry = (f"  <url><loc>{ORIGIN}{route}</loc><lastmod>{date.today().isoformat()}"
                     "</lastmod><priority>0.7</priority></url>\n")
            xml = xml.replace("</urlset>", entry + "</urlset>")
    sitemap.write_text(xml)
    print(f"Prepared {len(documents)} approved service pages and {len(sources)} assets.")


if __name__ == "__main__":
    prepare()
