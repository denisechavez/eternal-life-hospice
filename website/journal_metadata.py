"""Read-only checks for article-level Journal search and social summaries."""
import html
import json
import unicodedata
from html.parser import HTMLParser


DESCRIPTION_FIELDS = ("description", "og:description", "twitter:description")


def normalized_copy(value):
    """Ignore HTML entities, Unicode presentation forms and whitespace only."""
    return " ".join(unicodedata.normalize("NFKC", html.unescape(value)).split())


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.descriptions = {field: [] for field in DESCRIPTION_FIELDS}
        self.schemas = []
        self.script_parts = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag == "meta":
            field = attrs.get("name", attrs.get("property", "")).lower()
            if field in self.descriptions:
                self.descriptions[field].append(attrs.get("content", ""))
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.script_parts = []

    def handle_data(self, data):
        if self.script_parts is not None:
            self.script_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script_parts is not None:
            self.schemas.append("".join(self.script_parts))
            self.script_parts = None
        if tag == "head":
            self.in_head = False


def blog_postings(value):
    """Support standalone nodes, arrays and @graph without checking Blog cards."""
    if isinstance(value, list):
        for node in value:
            yield from blog_postings(node)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if isinstance(types, list) and "BlogPosting" in types:
            yield value
        if "@graph" in value:
            yield from blog_postings(value["@graph"])


def article_metadata_issues(path, title, description):
    """Return actionable diagnostics; never write or compare SEO/social titles."""
    parser = MetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    issues = []

    def report(field, message):
        issues.append(f"{path}: {field}: {message}")

    def compare(field, value, expected):
        if not isinstance(value, str) or not normalized_copy(value):
            report(field, "missing or empty text")
        elif normalized_copy(value) != normalized_copy(expected):
            report(field, f"differs from visible hero copy; metadata={value!r}; hero={expected!r}")

    for field, values in parser.descriptions.items():
        if len(values) != 1:
            report(field, f"expected one meta tag, found {len(values)}")
        else:
            compare(field, values[0], description)

    postings = []
    for index, text in enumerate(parser.schemas, 1):
        try:
            postings.extend(blog_postings(json.loads(text)))
        except (ValueError, RecursionError):
            report(f"JSON-LD block {index}", "invalid JSON; cannot verify structured metadata")
    if parser.script_parts is not None:
        report("JSON-LD", "unterminated script; cannot verify structured metadata")
    if len(postings) != 1:
        report("BlogPosting", f"expected one article-level node, found {len(postings)}")
    for index, posting in enumerate(postings, 1):
        for field, expected in (("headline", title), ("description", description)):
            compare(f"BlogPosting[{index}].{field}", posting.get(field), expected)
    return issues