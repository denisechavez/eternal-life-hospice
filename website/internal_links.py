"""Curated link architecture shared by authors, generators, server and checks."""
import html
import json
import posixpath
import re
from datetime import datetime
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from zoneinfo import ZoneInfo
from analytics_assets import analytics_url

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / "elh-preview"
START = "<!-- INTERNAL_LINKS_START -->"
END = "<!-- INTERNAL_LINKS_END -->"
STYLE = '<link rel="stylesheet" href="/assets/internal-links.css?v=20261007-inline">'


def config():
    return json.loads((BASE / "content/internal-links.json").read_text())


def today():
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


class PageParser(HTMLParser):
    """Keep chrome and breadcrumbs separate from meaningful content links."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text, as_of=None):
        super().__init__(convert_charrefs=True)
        self.stack, self.links, self.ids = [], [], set()
        self.anchor = None
        self.canonical, self.noindex, self.refresh = "", False, False
        self.as_of = as_of
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = urlsplit(a.get("href", "")).path or "/"
        if tag == "meta":
            self.noindex |= a.get("name") == "robots" and "noindex" in a.get("content", "")
            self.refresh |= a.get("http-equiv", "").lower() == "refresh"
        chrome = any(x[1] for x in self.stack) or tag in {"header", "footer"} or a.get("id") in {"hdr", "site-footer"}
        breadcrumb = any(x[2] for x in self.stack) or "breadcrumb" in a.get("class", "")
        hidden = any(x[3] for x in self.stack) or bool(self.as_of and a.get("data-publish-date", "") > self.as_of)
        if tag == "a" and "href" in a and not hidden:
            self.links.append((a["href"], "chrome" if chrome else "breadcrumb" if breadcrumb else "content", a))
            self.anchor = a
            a["_text"] = ""
        if tag not in self.VOID:
            self.stack.append((tag, chrome, breadcrumb, hidden))

    def handle_endtag(self, tag):
        if tag == "a":
            self.anchor = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor["_text"] += data


def journal_records():
    records = {}
    for path in sorted((BASE / "content/30-day-journal").glob("*.json")):
        for item in json.loads(path.read_text()):
            records["/blog/" + item["slug"]] = item
    return records


def inventory(as_of=None):
    as_of = as_of or today()
    files = sorted(PUBLIC.rglob("*.html"))
    sources = [BASE / "content/internal-links.json", BASE / "content/30-day-journal-manifest.json"]
    sources += sorted((BASE / "content/30-day-journal").glob("*.json"))
    stamp = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files + sources)
    return _inventory(as_of, stamp)


@lru_cache(maxsize=4)
def _inventory(as_of, stamp):
    rules, records = config(), journal_records()
    manifest = json.loads((BASE / "content/30-day-journal-manifest.json").read_text())
    dates = {"/blog/" + a["slug"]: a["date"] for a in manifest["articles"]}
    pages = {}
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text()
        p = PageParser(text, as_of)
        route = p.canonical
        actual = "/" + path.relative_to(PUBLIC).as_posix()[:-5]
        if actual == "/index":
            actual = "/"
        if not route or (p.noindex and route not in rules["utility"]) or p.refresh or route != actual or route in rules["excluded"]:
            continue
        item = records.get(route, {})
        if item.get("publicationStatus") == "archived" or dates.get(route, "") > as_of:
            continue
        pages[route] = (path, text, p)
    return pages


def resolve(source, href):
    parsed = urlsplit(urljoin("https://eternallifehospice.com" + source, href))
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in {"eternallifehospice.com", "www.eternallifehospice.com"}:
        return None
    return posixpath.normpath(unquote(parsed.path)), unquote(parsed.fragment), parsed.query


def recommendations(route, as_of=None, pages=None, with_topics=False):
    rules, pages, records = config(), pages if pages is not None else inventory(as_of), journal_records()
    topics = rules["pages"].get(route)
    if route.startswith("/hospice-") and topics is None:
        topics = ["local", "care", "starting"]
    owner = None
    if route.startswith("/blog/"):
        item = records.get(route, {})
        key = rules["journalCategories"].get(item.get("category"), "family")
        owner = rules["journalOwners"].get(route.split("/")[-1], rules["topics"][key][0])
        topics = [key, "journal", "family"]
    candidates = ([ [owner, "Explore " + html.unescape(re.sub("<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", pages[owner][1], re.S).group(1))), key] ]
                  if owner in pages else [])
    candidates += [rules["topics"][key] + [key] for key in (topics or [])]
    candidates += [link + ["support"] for link in rules["supportLinks"].get(route, [])]
    # Topic owners may recommend one published supporting Journal story.
    if route in {v[0] for v in rules["topics"].values()}:
        for dest in sorted(records, key=lambda d: (records[d]["date"], d), reverse=True):
            item = records[dest]
            key = rules["journalCategories"].get(item.get("category"), "family")
            topic_owner = rules["journalOwners"].get(item["slug"], rules["topics"][key][0])
            if dest in pages and topic_owner == route:
                candidates.append([dest, item["title"], "journal"])
                break
    result, seen = [], {route}
    for dest, anchor, topic in candidates:
        target = urlsplit(dest).path
        if target not in pages or target in seen:
            continue
        seen.add(target)
        result.append((dest, anchor, topic) if with_topics else (dest, anchor))
    return result[:5]


def render_links(text, route, as_of=None, pages=None):
    if route == "/":
        # Render targets before the browser resolves an incoming fragment.
        # Late JavaScript-created IDs can trigger another native anchor jump.
        text = re.sub(
            r'(<div class="mod-card[^"]*"\s+)(data-mod="([a-z]+)")',
            lambda match: match[1] + 'id="therapy-' + match[3] + '" ' + match[2],
            text,
        )
    links = recommendations(route, as_of, pages, with_topics=True)
    block = ""
    if links:
        block = '<section class="elh-related" aria-labelledby="elh-related-title"><h2 id="elh-related-title">Continue exploring</h2><ul>'
        # Fixed editorial metadata only: no labels, queries or visitor input.
        block += "".join(
            f'<li><a href="{html.escape(dest, quote=True)}"'
            f' data-reading-source="{html.escape(route, quote=True)}"'
            f' data-reading-destination="{html.escape(urlsplit(dest).path, quote=True)}"'
            f' data-reading-topic="{html.escape(topic, quote=True)}">'
            f'{html.escape(anchor)}</a></li>'
            for dest, anchor, topic in links)
        block += "</ul></section>"
    replacement = START + "\n" + block + "\n" + END
    if START in text:
        text = re.sub(re.escape(START) + r"[\s\S]*?" + re.escape(END), lambda _: replacement, text)
    elif links:
        marker = "</main>" if "</main>" in text else "</body>"
        text = text.replace(marker, replacement + "\n" + marker, 1)
    if links:
        if re.search(r'<link\b[^>]*href="/assets/internal-links\.css[^"]*"[^>]*>', text):
            text = re.sub(r'<link\b[^>]*href="/assets/internal-links\.css[^"]*"[^>]*>', STYLE, text)
        elif STYLE not in text:
            text = text.replace("</head>", STYLE + "\n</head>", 1)
    from inline_links import apply_inline_links
    text = apply_inline_links(canonical_links(text, route), route, pages)
    # Refresh the shared tracker without reusing an immutable URL after changes.
    text = re.sub(r'(<script\b[^>]*\bsrc=)(["\'])([^"\']*assets/analytics\.js)(?:\?[^"\']*)?\2',
                  lambda m: m[1] + m[2] + m[3] + "?" + analytics_url().split("?", 1)[1] + m[2], text)
    return text


def canonical_links(text, route):
    """Normalize anchor destinations only; never replace keywords or prose."""
    from devserver import LEGACY_PAGE_REDIRECTS
    def anchor(match):
        tag = match.group(0)
        attr = re.search(r'\bhref=(["\'])(.*?)\1', tag)
        if not attr:
            return tag
        href = html.unescape(attr[2])
        target = resolve(route, href)
        if target is None or href.startswith("#"):
            return tag
        dest, fragment, query = target
        if dest.endswith(".html"):
            dest = dest[:-5]
        if dest == "/index":
            dest = "/"
        dest = LEGACY_PAGE_REDIRECTS.get(dest, dest)
        if dest == "/card-aleksandra-dubina":
            dest = "/about/aleksandra-dubina"
        if dest == "/refer" and not fragment:
            fragment = "referral-form"
        label = re.sub("<[^>]*>", "", tag + text[match.end():text.find("</a>", match.end())])
        if "lead=physician" in query:
            dest, query, fragment = "/refer", "", "referral-form"
        if "Request Care" in html.unescape(label):
            dest, query, fragment = "/", "lead=family", "leadcap"
        value = dest + ("?" + query if query else "") + ("#" + fragment if fragment else "")
        return tag[:attr.start(2)] + html.escape(value, quote=True) + tag[attr.end(2):]
    return re.sub(r"<a\b[^>]*>", anchor, text)


def refresh(as_of=None):
    """Refresh curated slots, without changing authored prose or existing groups."""
    pages = inventory(as_of)
    # Also normalize staged article files, but never select future recommendations.
    staged = inventory("9999-12-31")
    for route, (path, text, _) in staged.items():
        updated = render_links(text, route, as_of, pages)
        if updated != text:
            path.write_text(updated)

