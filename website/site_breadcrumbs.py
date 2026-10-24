"""Shared content-area breadcrumbs; never rewrite reviewed article content."""
import html
import json
import re
from html.parser import HTMLParser

from seo_page_parser import Page, has_type, schema_nodes

ORIGIN = "https://eternallifehospice.com"
AREA_HUB = "/hospice-ventura-and-los-angeles-county-ca"
STYLE = '<link rel="stylesheet" href="/assets/content-breadcrumbs.css?v=20261024">'


def expected_path(route, heading):
    if route == "/":
        return []
    parents = [("Home", "/")]
    if route.startswith("/services/"):
        parents.append(("Services", "/services"))
    elif route.startswith("/resources/") or route in {"/blog", "/care-brief", "/family-guide", "/media-kit"}:
        parents.append(("Resources", "/resources"))
    elif route.startswith("/blog/"):
        parents.extend([("Resources", "/resources"), ("The Eternal Journal", "/blog")])
    elif route.startswith("/care-brief/"):
        parents.extend([("Resources", "/resources"), ("The Eternal Care Brief", "/care-brief")])
    elif route == "/sound-bath":
        parents.append(("Services", "/services"))
    elif route.startswith("/hospice-") and route.endswith("-ca") and route != AREA_HUB:
        parents.append(("Service Areas", AREA_HUB))
    return parents + [(heading, route)]


class HeroEnd(HTMLParser):
    """Find the end of the hero without matching nested section closing tags."""
    def __init__(self, document):
        super().__init__()
        self.document, self.insertion_offset, self.depth, self.active = document, None, 0, False
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer("\n", document))
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag != "section":
            return
        if self.active:
            self.depth += 1
        elif any("hero" in value.split() or any(
                word.startswith("hero--") for word in value.split())
                for name, value in attrs if name == "class"):
            if self.insertion_offset is None:
                self.active, self.depth = True, 1

    def handle_endtag(self, tag):
        if tag == "section" and self.active:
            self.depth -= 1
            if not self.depth:
                line, column = self.getpos()
                self.insertion_offset = self.lines[line - 1] + column + len("</section>")
                self.active = False


def decorate(document, route):
    eligible = (route.startswith(("/blog/", "/resources/"))
                or (route.startswith("/hospice-") and route.endswith("-ca")))
    if not eligible:
        return document
    parsed = Page(document)
    if parsed.breadcrumbs or len(parsed.headings) != 1:
        return document
    trail = expected_path(route, parsed.headings[0])
    items = "".join(
        '<li>' + (f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
                  if index < len(trail) - 1 else
                  f'<span aria-current="page">{html.escape(label)}</span>') + "</li>"
        for index, (label, url) in enumerate(trail))
    markup = '<nav class="content-breadcrumbs" aria-label="Breadcrumb"><ol>' + items + "</ol></nav>"
    offset = HeroEnd(document).insertion_offset
    if offset is None:
        main = re.search(r"<main\b[^>]*>", document)
        if not main:
            return document
        offset = main.end()
    document = document[:offset] + markup + document[offset:]
    # New breadcrumbs must agree with their own structured data. Preserve every
    # other schema object, including BlogPosting and its approved dates.
    def remove_breadcrumb(match):
        try:
            value = json.loads(match[1])
        except ValueError:
            return match[0]
        if not any(has_type(node, "BreadcrumbList") for node in schema_nodes(value)):
            return match[0]
        def prune(node):
            if isinstance(node, list):
                return [prune(item) for item in node if not (
                    isinstance(item, dict) and has_type(item, "BreadcrumbList"))]
            if isinstance(node, dict):
                if has_type(node, "BreadcrumbList"):
                    return None
                return {key: prune(item) for key, item in node.items()}
            return node
        value = prune(value)
        return ('<script type="application/ld+json">' + json.dumps(value) + "</script>"
                if value else "")
    document = re.sub(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        remove_breadcrumb, document, flags=re.S | re.I)
    schema_id = (parsed.breadcrumb_schemas[0].get("@id")
                 if len(parsed.breadcrumb_schemas) == 1 else None)
    schema = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "@id": schema_id or ORIGIN + route + "#breadcrumb",
              "itemListElement": [
                  {"@type": "ListItem", "position": index + 1,
                   "name": label, "item": ORIGIN + url}
                  for index, (label, url) in enumerate(trail)]}
    metadata = '<script type="application/ld+json">' + json.dumps(
        schema, ensure_ascii=True).replace("<", "\\u003c") + "</script>"
    return document.replace("</head>", STYLE + metadata + "</head>", 1)
