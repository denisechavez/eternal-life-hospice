"""Read-only SEO audit of canonical site sources and shared rendered chrome."""
import ast
from collections import defaultdict
from datetime import datetime
import html
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urljoin, urlsplit
from zoneinfo import ZoneInfo

import internal_links
import service_preview
import site_breadcrumbs
import footer_contact
import recruitment_policy
from seo_page_parser import Page, clean, has_type

BASE = Path(__file__).resolve().parent
SITE = BASE / "elh-preview"
ORIGIN = site_breadcrumbs.ORIGIN
HOSTS = {"eternallifehospice.com", "www.eternallifehospice.com"}


def local_target(source, href):
    value = urlsplit(urljoin(ORIGIN + source, html.unescape(href)))
    if value.scheme not in {"https", "http"} or value.hostname not in HOSTS:
        return None
    path = posixpath.normpath(unquote(value.path) or "/")
    if value.path.endswith("/") and path != "/":
        path += "/"
    return path, unquote(value.fragment)


def canonical_route(path):
    path = path.removesuffix(".html")
    if path.endswith("/index"):
        path = path[:-6]
    return path.rstrip("/") or "/"


def routing_value(name):
    # Read literal routing configuration without starting APIs or touching data.
    tree = ast.parse((BASE / "devserver.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"The site's routing configuration {name} could not be read.")


def redirect_rules():
    return routing_value("LEGACY_PAGE_REDIRECTS")


def read_pages(site=SITE):
    pages, redirects = {}, redirect_rules()
    canonical_html_routes = routing_value("CANONICAL_HTML_ROUTES")
    archived = {route for route, item in internal_links.journal_records().items()
                if item.get("publicationStatus") == "archived"}
    for file in sorted(site.rglob("*.html")):
        relative = file.relative_to(site)
        if "assets" in relative.parts or any(part.startswith(("_", ".")) for part in relative.parts):
            continue
        text = file.read_text(encoding="utf-8")
        parsed = Page(text)
        file_route = "/" + relative.as_posix().removesuffix(".html")
        route = canonical_route(file_route)
        # Match the server's explicit hub routing, not filesystem sort order.
        # A historical directory index can otherwise hide the real page's IDs.
        if (relative.name == "index.html" and route in canonical_html_routes
                and (site / (route.lstrip("/") + ".html")).is_file()):
            continue
        if parsed.refresh:
            target = re.search(r"url\s*=\s*['\"]?([^'\"]+)", parsed.refresh, re.I)
            if target:
                redirects[file_route] = target[1].strip()
                redirects[file_route + ".html"] = target[1].strip()
            continue
        if route in archived or recruitment_policy.withdrawn(route):
            continue
        # Directory index stubs are not separate pages.
        if route in pages:
            continue
        pages[route] = {"file": file, "source": text, "page": parsed}
    for route in ("/blog/", "/services/"):
        redirects[route] = route.rstrip("/")
    return pages, redirects


def schema_url(item):
    value = item.get("item")
    if isinstance(value, dict):
        return value.get("@id") or value.get("url")
    return value

def schema_context_valid(value):
    if isinstance(value, str):
        return value.rstrip("/") in {"https://schema.org", "http://schema.org"}
    if isinstance(value, list):
        return any(schema_context_valid(item) for item in value)
    if isinstance(value, dict):
        return any(schema_context_valid(item) for item in value.values())
    return False


def audit(pages, redirects, site=SITE):
    issues = []
    def problem(route, check, detail, fix):
        row = {"url": ORIGIN + route, "check": check, "problem": detail, "fix": fix}
        if row not in issues:
            issues.append(row)

    menus = defaultdict(set)
    for route, record in pages.items():
        for link in record["page"].links:
            target = local_target(route, link["href"])
            if link["menu"] and target and link["label"]:
                menus[canonical_route(target[0])].add(link["label"])

    for field, label in (("titles", "title tag"), ("descriptions", "meta description")):
        duplicate = defaultdict(list)
        for route, record in pages.items():
            values = getattr(record["page"], field)
            if len(values) != 1 or not clean(values[0]):
                problem(route, "Page identity", f"The page needs exactly one nonempty {label}; found {len(values)}.",
                        f"Add one unique {label} that describes this page.")
            else:
                duplicate[clean(values[0]).casefold()].append(route)
        for routes in duplicate.values():
            if len(routes) > 1:
                for route in routes:
                    others = ", ".join(ORIGIN + other for other in routes if other != route)
                    problem(route, "Duplicate page identity", f"The {label} is also used on {others}.",
                            f"Write a distinct {label} for each of these pages.")

    for route, record in pages.items():
        page = record["page"]
        if len(page.headings) != 1 or not page.headings[0]:
            problem(route, "Main heading", f"Expected one nonempty H1; found {len(page.headings)}.",
                    "Keep one clear H1 and change secondary headings to H2 or H3.")
        for image in page.images:
            if not image.get("alt", "").strip():
                decorative = image.get("alt") == "" and (
                    image.get("role") in {"presentation", "none"} or image.get("aria-hidden") == "true")
                if not decorative:
                    problem(route, "Image description", f"Image {image.get('src', '(image source missing)')} has no descriptive alt text.",
                            "Add a concise description. For a truly decorative image, use alt=\"\" and explicitly mark it decorative.")
        for link in page.links:
            target = local_target(route, link["href"])
            if target is None:
                continue
            path, fragment = target
            kind = "Breadcrumb link" if link["breadcrumb"] else "Internal link"
            if path in redirects:
                problem(route, kind, f"{link['href']} redirects to {redirects[path]}.",
                        f"Link directly to {urljoin(ORIGIN + route, redirects[path])}.")
                continue
            destination = canonical_route(path)
            if destination in pages:
                if fragment and fragment not in pages[destination]["page"].ids:
                    problem(route, kind, f"{link['href']} points to a section that does not exist.",
                            f"Correct #{fragment} or add that section ID on {ORIGIN + destination}.")
                continue
            file = (site / path.lstrip("/")).resolve()
            if not file.is_relative_to(site.resolve()) or not file.is_file():
                problem(route, kind, f"{link['href']} has no matching public page or file.",
                        "Replace it with the correct existing destination or remove the link.")
        if route == "/":
            continue
        if not page.breadcrumbs:
            problem(route, "Breadcrumb", "No HTML breadcrumb is present.",
                    "Add an accessible breadcrumb with linked ancestors and the current H1 as plain text. Structured data alone does not provide navigation.")
        elif len(page.breadcrumbs) != 1:
            problem(route, "Breadcrumb", f"Found {len(page.breadcrumbs)} breadcrumb trails.",
                    "Keep one unambiguous breadcrumb trail.")
        heading = page.headings[0] if len(page.headings) == 1 else "(page H1)"
        if menus[route] and heading not in menus[route]:
            problem(route, "Menu label", f"The H1 “{heading}” differs from the menu: "
                    + ", ".join(sorted(menus[route])) + ".",
                    "Agree on one approved label for the H1, menu and breadcrumb.")
        expected = site_breadcrumbs.expected_path(route, heading)
        for trail in page.breadcrumbs:
            if not trail:
                problem(route, "Breadcrumb", "The breadcrumb contains no readable items.",
                        "Use an ordered list of ancestors and a plain-text current page.")
                continue
            if trail[-1]["links"]:
                problem(route, "Breadcrumb current page", "The last breadcrumb item is a link.",
                        "Replace the final link with plain text and aria-current=\"page\".")
            if trail[-1]["label"] != heading:
                problem(route, "Breadcrumb label", f"The final label “{trail[-1]['label']}” does not exactly match the H1 “{heading}”.",
                        "Use the exact approved H1 text for the final breadcrumb label.")
            actual_paths = [canonical_route(local_target(route, item["links"][0]["href"])[0])
                            if item["links"] and local_target(route, item["links"][0]["href"])
                            else route for item in trail]
            if actual_paths != [url for _, url in expected]:
                problem(route, "Breadcrumb path", "The trail does not follow the site's page hierarchy.",
                        "Use: " + " → ".join(label for label, _ in expected) + ".")
            for index, (item, destination) in enumerate(zip(trail, actual_paths)):
                if destination == "/":
                    continue
                parent = pages.get(destination)
                if (index < len(trail) - 1 and parent and len(parent["page"].headings) == 1
                        and item["label"] != parent["page"].headings[0]):
                    problem(route, "Breadcrumb label", f"“{item['label']}” differs from the H1 “{parent['page'].headings[0]}” at {ORIGIN + destination}.",
                            "Agree on one label and use it consistently in that page's H1, navigation and breadcrumbs.")
                if menus[destination] and item["label"] not in menus[destination]:
                    problem(route, "Menu label", f"Breadcrumb “{item['label']}” differs from the menu: " + ", ".join(sorted(menus[destination])) + ".",
                            "Use the same approved wording in the menu, H1 and breadcrumb; do not shorten only one of them.")
        schemas = page.breadcrumb_schemas
        if len(schemas) != 1:
            problem(route, "Breadcrumb structured data", f"Expected one BreadcrumbList; found {len(schemas)}.",
                    "Add or keep one JSON-LD BreadcrumbList that matches the visible trail.")
        for error in page.schema_errors:
            problem(route, "Structured data", "A JSON-LD script is not valid JSON: " + error,
                    "Correct the JSON syntax without changing approved article metadata.")
        for schema in schemas:
            if not schema_context_valid(page.schema_contexts.get(id(schema))):
                problem(route, "Breadcrumb structured data", "The JSON-LD is missing a Schema.org context.",
                        'Add "@context": "https://schema.org" to the JSON-LD script or its enclosing graph.')
            items = schema.get("itemListElement")
            if not isinstance(items, list) or len(items) < 2:
                problem(route, "Breadcrumb structured data", "BreadcrumbList needs at least Home and the current page.",
                        "Provide an ordered itemListElement array.")
                continue
            names, paths, valid = [], [], True
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    valid = False
                    continue
                name, url = item.get("name"), schema_url(item)
                target = local_target(route, url) if isinstance(url, str) else None
                valid &= (has_type(item, "ListItem")
                          and type(item.get("position")) is int and item["position"] == index + 1
                          and isinstance(name, str) and bool(name.strip()))
                if index < len(items) - 1 and not target:
                    valid = False
                if url and (not target or not urlsplit(url).scheme):
                    valid = False
                names.append(name)
                paths.append(canonical_route(target[0]) if target else route)
                if target and (target[0] in redirects or canonical_route(target[0]) not in pages):
                    problem(route, "Breadcrumb structured data", f"Structured breadcrumb destination {url} is broken or redirected.",
                            "Use the final, existing canonical page URL.")
            if not valid:
                problem(route, "Breadcrumb structured data", "BreadcrumbList has invalid types, names, positions or item URLs.",
                        "Use named ListItem objects, integer positions starting at 1 and absolute canonical ancestor URLs.")
            if names != [label for label, _ in expected] or paths != [url for _, url in expected]:
                problem(route, "Breadcrumb structured data", "Structured breadcrumb labels or destinations do not match the expected page hierarchy.",
                        "Match the HTML trail: " + " → ".join(label for label, _ in expected) + ".")
            if page.breadcrumbs and names != [item["label"] for item in page.breadcrumbs[0]]:
                problem(route, "Breadcrumb structured data", "The JSON-LD labels differ from the HTML breadcrumb.",
                        "Make the structured and visible breadcrumb labels identical.")
    return issues


def run(site=SITE):
    pages, redirects = read_pages(site)
    context = internal_links.inventory()
    for route, record in pages.items():
        text = internal_links.render_links(record["source"], route, pages=context)
        text = footer_contact.public_html(recruitment_policy.public_html(text))
        text = site_breadcrumbs.decorate(text, route)
        text = service_preview.decorate(text, route)
        record["page"] = Page(text)
    issues = audit(pages, redirects, site)
    return {"generated_at": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            "pages_checked": len(pages), "issues": issues}


def plain_report(result):
    counts = defaultdict(int)
    grouped = defaultdict(list)
    for issue in result["issues"]:
        counts[issue["check"]] += 1
        grouped[issue["url"]].append(issue)
    lines = ["ETERNAL LIFE HOSPICE — PRE-PUBLISH SEO REPORT",
             "Advisory only. No publishing is blocked and no site files are changed.",
             f"Created: {result['generated_at']}",
             f"Pages checked: {result['pages_checked']}",
             f"Problems: {len(result['issues'])} across {len(grouped)} pages.",
             "Scope: website HTML sources, including scheduled articles, with shared rendered navigation.",
             "Redirect stubs, archived articles, withdrawn recruitment pages and private asset galleries are excluded.",
             "Local destinations and section IDs are checked offline. External sites, sign-in and live Journal approvals are not verified.",
             "Empty alt text is accepted only for explicitly marked decorative images.", ""]
    lines += [f"{name}: {count}" for name, count in sorted(counts.items())]
    lines += ["",
              f"Title and description checks: {counts['Page identity'] + counts['Duplicate page identity']} problems.",
              f"One-H1 check: {counts['Main heading']} problems.",
              f"Image alt-text check: {counts['Image description']} problems.",
              "The full list below includes the page address and recommended fix for each finding.",
              "Repeated shared-menu or footer problems are listed on each affected page."]
    for url, issues in grouped.items():
        lines.extend(["", url])
        for issue in issues:
            lines.extend([f"- {issue['check']}: {issue['problem']}", f"  Fix: {issue['fix']}"])
    if not grouped:
        lines.append("No problems found in the checks above.")
    return "\n".join(lines) + "\n"
