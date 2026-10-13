"""Reversible public recruitment takedown; original source files remain intact."""
import html
import json
import posixpath
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

RECRUITMENT_PAUSED = True
WITHDRAWN_ROUTES = frozenset({
    "/careers", "/volunteer", "/resources/volunteer",
    "/blog/the-quiet-work-of-hospice-volunteers",
})


def withdrawn(value):
    if not RECRUITMENT_PAUSED:
        return False
    parsed = urlsplit(html.unescape(value))
    if parsed.netloc and parsed.hostname not in ("eternallifehospice.com", "www.eternallifehospice.com"):
        return False
    path = "/" + posixpath.normpath("/" + unquote(parsed.path).lstrip("/")).lstrip("/")
    path = path.rstrip("/")
    if path.endswith("/index.html"):
        path = path[:-11]
    if path.endswith(".html"):
        path = path[:-5]
    return path in WITHDRAWN_ROUTES


class _Elements(HTMLParser):
    """Locate element spans without reserializing or restyling the document."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer("\n", text))
        self.nodes = []
        self.stack = []
        self.feed(text)

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        node = {"tag": tag, "attrs": dict(attrs), "start": start,
                "open_end": start + len(self.get_starttag_text()),
                "end": start + len(self.get_starttag_text())}
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        end = self.text.find(">", self.source_offset()) + 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                for node in self.stack[i:]:
                    node["close_start"] = self.source_offset()
                    node["end"] = end
                del self.stack[i:]
                break


def public_html(text):
    if not RECRUITMENT_PAUSED:
        return text
    parsed = _Elements(text)
    edits = []
    for node in parsed.nodes:
        attrs = node["attrs"]
        classes = (attrs.get("class") or "").split()
        snippet = text[node["start"]:node["end"]]
        if node["tag"] == "section" and (
            attrs.get("id") == "join" or "vol" in classes
            or ("cta" in classes and re.search(r"give time|volunteer|careers", snippet, re.I))
        ):
            edits.append((node["start"], node["end"], ""))
        elif node["tag"] == "p" and "Here to join our team or volunteer?" in snippet:
            edits.append((node["start"], node["end"], ""))
        elif node["tag"] == "a" and withdrawn(attrs.get("href", "")):
            # Keep clinical prose readable, but remove recruitment cards/nav links.
            replacement = (text[node["open_end"]:node.get("close_start", node["end"])]
                           if "elh-inline-link" in classes else "")
            edits.append((node["start"], node["end"], replacement))
    # Ignore nested edits within a section/card already being removed.
    accepted = []
    for edit in sorted(edits, key=lambda item: (item[0], -item[1])):
        if not accepted or edit[0] >= accepted[-1][1]:
            accepted.append(edit)
    for start, end, replacement in reversed(accepted):
        text = text[:start] + replacement + text[end:]
    text = text.replace(", and how to volunteer.", ".")
    # Structured data must not advertise retired links either.
    def clean_value(value):
        if isinstance(value, dict):
            return {key: clean_value(item) for key, item in value.items()
                    if not (isinstance(item, str) and withdrawn(item))}
        if isinstance(value, list):
            return [clean_value(item) for item in value
                    if not (isinstance(item, dict) and any(
                        isinstance(v, str) and withdrawn(v)
                        for k, v in item.items() if k in ("url", "item", "@id")
                    ))]
        return value
    def clean_script(match):
        try:
            value = json.loads(match.group(2))
        except ValueError:
            return match.group(0)
        cleaned = clean_value(value)
        return (match.group(1) + json.dumps(cleaned, ensure_ascii=False) + match.group(3)
                if cleaned != value else match.group(0))
    return re.sub(r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)([\s\S]*?)(</script>)',
                  clean_script, text)


def public_discovery(text, kind):
    if not RECRUITMENT_PAUSED:
        return text
    if kind == "search":
        entries = [entry for entry in json.loads(text) if not withdrawn(entry.get("url", ""))]
        for entry in entries:
            if entry.get("url") == "/resources":
                entry["kw"] = re.sub(r"\bvolunteer\s*,?\s*", "", entry.get("kw", ""), flags=re.I)
        return json.dumps(entries, ensure_ascii=False)
    if kind == "sitemap":
        return re.sub(r"\s*<url>[\s\S]*?</url>", lambda match: "" if any(
            withdrawn(url) for url in re.findall(r"<loc>(.*?)</loc>", match.group(0))
        ) else match.group(0), text)
    return "\n".join(line for line in text.split("\n") if not any(
        withdrawn(url.rstrip(")")) for url in re.findall(r"https?://[^\s]+", line)
    ))
