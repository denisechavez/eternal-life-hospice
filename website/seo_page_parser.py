"""Small, dependency-free HTML reader for the advisory SEO report."""
import json
from html.parser import HTMLParser


def clean(value):
    return " ".join(value.split())

def has_type(node, name):
    types = node.get("@type", [])
    types = [types] if isinstance(types, str) else types
    return isinstance(types, list) and any(
        isinstance(value, str) and value.rstrip("/").split("/")[-1].split(":")[-1] == name
        for value in types)


def schema_records(value, context=None):
    if isinstance(value, list):
        for item in value:
            yield from schema_records(item, context)
    elif isinstance(value, dict):
        context = value.get("@context", context)
        yield value, context
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from schema_records(item, context)


def schema_nodes(value):
    for node, _ in schema_records(value):
        yield node


class Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, document):
        super().__init__(convert_charrefs=True)
        self.frames = []
        self.titles, self.headings, self.descriptions = [], [], []
        self.links, self.images, self.breadcrumbs = [], [], []
        self.schemas, self.schema_errors, self.ids = [], [], set()
        self.schema_contexts = {}
        self.canonical, self.refresh = "", ""
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") or (tag == "a" and attrs.get("name")):
            self.ids.add(attrs.get("id") or attrs["name"])
        if tag == "meta":
            if attrs.get("name", "").lower() == "description":
                self.descriptions.append(attrs.get("content", ""))
            if attrs.get("http-equiv", "").lower() == "refresh":
                self.refresh = attrs.get("content", "")
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "")
        if tag == "img" or (tag == "input" and attrs.get("type") == "image"):
            self.images.append(attrs)
        if tag in self.VOID:
            return
        parent_crumb = next((f for f in self.frames if f["crumb"]), None)
        own_crumb = not parent_crumb and (
            "breadcrumb" in attrs.get("class", "").lower()
            or "breadcrumb" in attrs.get("aria-label", "").lower())
        self.frames.append({
            "tag": tag, "attrs": attrs, "text": [], "crumb": bool(own_crumb),
            "parent_crumb": parent_crumb, "items": [], "anchors": [],
            "menu": any(f["tag"] == "header" for f in self.frames),
        })

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_data(self, text):
        for frame in self.frames:
            if frame["tag"] in {"title", "h1", "a", "li", "span", "script"} or frame["crumb"]:
                frame["text"].append(text)

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.frames) - 1, -1, -1)
                      if self.frames[i]["tag"] == tag), None)
        if index is None:
            return
        frame = self.frames[index]
        text, attrs = clean("".join(frame["text"])), frame["attrs"]
        crumb = frame["parent_crumb"]
        if tag == "title":
            self.titles.append(text)
        elif tag == "h1":
            self.headings.append(text)
        elif tag == "a" and "href" in attrs:
            link = {"href": attrs["href"], "label": text, "menu": frame["menu"],
                    "breadcrumb": bool(crumb), "attrs": attrs}
            self.links.append(link)
            for ancestor in self.frames[:index]:
                ancestor["anchors"].append(link)
        elif tag == "li" and crumb:
            crumb["items"].append({"label": text, "links": frame["anchors"]})
        elif tag == "span" and crumb and attrs.get("aria-current") == "page":
            crumb["current"] = text
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            try:
                for node, context in schema_records(json.loads("".join(frame["text"]))):
                    self.schemas.append(node)
                    self.schema_contexts[id(node)] = context
            except (ValueError, TypeError) as error:
                self.schema_errors.append(str(error))
        if frame["crumb"]:
            items = frame["items"]
            if not items:
                items = [{"label": link["label"], "links": [link]}
                         for link in frame["anchors"]]
                if frame.get("current"):
                    items.append({"label": frame["current"], "links": []})
            self.breadcrumbs.append(items)
        del self.frames[index:]

    @property
    def breadcrumb_schemas(self):
        return [node for node in self.schemas if has_type(node, "BreadcrumbList")]
