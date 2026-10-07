"""Apply reviewed, passage-specific links without rewriting website copy.

The editorial map records an exact paragraph and anchor phrase for each route.
There is deliberately no request-time keyword replacement or topic inference.
"""
import hashlib
import html
import json
import re
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

MAP = Path(__file__).with_name("content") / "inline-links.json"
MAX_LINKS = 7
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
EXCLUDED = {"related", "elh-related", "rgrid", "rc", "r-card", "resource-card",
            "journal-grid", "post-card", "blog-featured", "breadcrumb", "toc", "cta", "btns",
            "meta", "article-meta", "post-meta", "photo-credit", "image-credit"}


def plain(raw):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", raw))).strip()


def signature(text):
    return hashlib.sha256(text.encode()).hexdigest()


def destination(route, href):
    from internal_links import resolve
    result = resolve(route, href)
    if not result or result[0] == route:
        return None
    return result[0]


def link_budget(route, words):
    # Keep ordinary city copy selective; long specialist/Journal copy can retain
    # up to seven useful existing links rather than treating seven as a quota.
    if (route.startswith("/hospice-") and route.endswith("-ca")
            and route != "/hospice-ventura-and-los-angeles-county-ca"):
        return 3 if words < 500 else 4 if words < 1000 else 5 if words < 1600 else 7
    return MAX_LINKS


class ProseParser(HTMLParser):
    """Locate real paragraphs/list prose, excluding cards, chrome and buttons."""
    def __init__(self, text, route):
        super().__init__(convert_charrefs=True)
        self.source, self.route = text, route
        self.lines, total = [], 0
        for line in text.splitlines(keepends=True):
            self.lines.append(total)
            total += len(line)
        self.stack, self.blocks = [], []
        self.block, self.anchor = None, None
        self.feed(text)

    def position(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        excluded = (any(x[1] for x in self.stack) or
                    tag in {"header", "footer", "nav", "form", "script", "style"} or
                    bool(EXCLUDED.intersection(attrs.get("class", "").split())) or
                    attrs.get("id") in {"hdr", "site-footer", "cookieBanner", "cookiePrefs"})
        inside_main = any(x[0] == "main" for x in self.stack)
        inside_anchor = any(x[0] == "a" for x in self.stack)
        if tag in {"p", "li"} and inside_main and not excluded and not inside_anchor and self.block is None:
            self.block = {"tag": tag, "start": self.position(), "text": "",
                          "nodes": [], "links": [], "attrs": attrs}
        if tag == "a" and self.block:
            target = destination(self.route, attrs.get("href", ""))
            self.anchor = {"start": self.position(), "open": self.get_starttag_text(),
                           "href": attrs.get("href", ""), "target": target, "text": ""}
        if tag not in VOID:
            self.stack.append((tag, excluded))

    def handle_data(self, data):
        if not self.block:
            return
        self.block["text"] += data
        if self.anchor is not None:
            self.anchor["text"] += data
        elif not any(x[0] in {"a", "button", "script", "style"} for x in self.stack):
            start = self.position()
            end = self.source.find("<", start)
            if end < 0:
                end = len(self.source)
            self.block["nodes"].append({"start": start, "raw": self.source[start:end]})

    def handle_endtag(self, tag):
        end = self.position()
        if tag == "a" and self.anchor is not None:
            self.anchor["close"] = end
            if self.anchor["target"]:
                self.block["links"].append(self.anchor)
            self.anchor = None
        if self.block is not None and tag == self.block["tag"]:
            block = self.block
            block["end"] = end + len("</" + tag + ">")
            block["text"] = re.sub(r"\s+", " ", block["text"]).strip()
            # A list of linked city names or an entire linked card is not inline copy.
            local_directory = (
                block["text"].lower().startswith(("explore ", "see nearby "))
                and sum(a["target"].startswith("/hospice-") and a["target"].endswith("-ca")
                        for a in block["links"]) >= 2)
            if len(block["text"].split()) >= 8 and not local_directory:
                block["signature"] = signature(block["text"])
                self.blocks.append(block)
            self.block = None
            self.anchor = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


@lru_cache(maxsize=2)
def _read_map(stamp):
    return json.loads(MAP.read_text())["pages"]


def editorial_map():
    if not MAP.exists():
        return {}
    return _read_map((MAP.stat().st_mtime_ns, MAP.stat().st_size))


def reading_attributes(route, target):
    from internal_links import config
    topics = config()["topics"]
    topic = next((key for key, value in topics.items()
                  if urlsplit(value[0]).path == target), "support")
    return (f'data-reading-source="{html.escape(route, quote=True)}" '
            f'data-reading-destination="{html.escape(target, quote=True)}" '
            f'data-reading-topic="{topic}"')


def mark_anchor(tag, route, target):
    # Existing valid editorial links receive the same styling/tracking as additions.
    tag = re.sub(r'\sdata-reading-(?:source|destination|topic)="[^"]*"', "", tag)
    match = re.search(r'\bclass=(["\'])(.*?)\1', tag)
    if match:
        classes = match[2].split()
        if "elh-inline-link" not in classes:
            classes.append("elh-inline-link")
        tag = tag[:match.start(2)] + " ".join(classes) + tag[match.end(2):]
    else:
        tag = tag[:-1] + ' class="elh-inline-link">'
    return tag[:-1] + " " + reading_attributes(route, target) + ">"


def apply_inline_links(text, route, eligible=None):
    from internal_links import inventory
    eligible = eligible if eligible is not None else inventory()
    parser = ProseParser(text, route)
    edits, retained, seen = [], [], set()
    existing = [a for b in parser.blocks for a in b["links"]]
    limit = link_budget(route, sum(len(b["text"].split()) for b in parser.blocks))
    # Retain up to seven useful existing links, preferring distinct destinations.
    ordered = sorted(enumerate(existing), key=lambda pair: (
        any(a["target"] == pair[1]["target"] for a in existing[:pair[0]]), pair[0]))
    keep = {index for index, a in ordered[:limit]}
    for index, anchor in enumerate(existing):
        if index not in keep or anchor["target"] not in eligible:
            edits.append((anchor["start"], anchor["start"] + len(anchor["open"]), ""))
            edits.append((anchor["close"], anchor["close"] + len("</a>"), ""))
            continue
        edits.append((anchor["start"], anchor["start"] + len(anchor["open"]),
                      mark_anchor(anchor["open"], route, anchor["target"])))
        retained.append(anchor)
        seen.add(anchor["target"])

    for annotation in editorial_map().get(route, []):
        target = destination(route, annotation["href"])
        if target not in eligible or target in seen or len(retained) >= limit:
            continue
        block = next((b for b in parser.blocks if b["signature"] == annotation["paragraph"]), None)
        if block is None:
            continue  # Changed wording must receive a new editorial annotation.
        found = None
        for node in block["nodes"]:
            matches = list(re.finditer(r"(?<!\w)" + re.escape(annotation["phrase"]) + r"(?!\w)", node["raw"]))
            if matches:
                found = (node["start"] + matches[0].start(), matches[0].group())
                break
        if found:
            start, phrase = found
            tag = (f'<a href="{html.escape(annotation["href"], quote=True)}" '
                   f'class="elh-inline-link" {reading_attributes(route, target)}>{phrase}</a>')
            edits.append((start, start + len(phrase), tag))
            seen.add(target)
            retained.append(annotation)
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text
