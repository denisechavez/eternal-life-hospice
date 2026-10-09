"""Pure helpers for private Journal SEO audits; never alter public files."""
import hashlib
import html
import itertools
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain(source):
    parser = Text()
    parser.feed(source)
    return " ".join(" ".join(parser.parts).split())


def article(source):
    return re.search(r"<article\b[^>]*>(.*?)</article>", source, re.S)[1]


def main(source):
    return re.search(r"<main\b[^>]*>(.*?)</main>", source, re.S)[1]


def core(source):
    body = article(source)
    body = re.sub(r"<aside\b[^>]*>.*?</aside>", "", body, flags=re.S)
    body = re.sub(r'<div class="blog-byline">.*?</div>', "", body, flags=re.S)
    body = re.sub(r'<a class="backlink".*?</a>', "", body, flags=re.S)
    return plain(body)


def words(source):
    return len(re.findall(r"\b[\w’'-]+\b", core(source)))


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def heading(source):
    return plain(re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.S)[1])


def hero(source):
    main = source.split("<main", 1)[1]
    return re.search(r"background-image:url\(['\"]?([^'\"\)]+)", main)[1].replace("../", "/")


def attrs(source):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', source))


ANCHOR = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S)


def content_links(source):
    return [(attrs(match[1])["href"], plain(match[2]))
            for match in ANCHOR.finditer(main(source))
            if "elh-inline-link" in attrs(match[1]).get("class", "").split()
            and urlsplit(attrs(match[1]).get("href", "")).netloc == ""]


def inline(value):
    result, cursor = [], 0
    for match in re.finditer(r"\[([^\]]+)\]\((/[^)\s]+)\)", value):
        assert not match[2].startswith("//")
        result += [html.escape(value[cursor:match.start()]),
                   f'<a class="elh-inline-link" href="{html.escape(match[2])}">{html.escape(match[1])}</a>']
        cursor = match.end()
    return "".join(result) + html.escape(value[cursor:])


def insert(source, sections):
    if not sections:
        return source
    start = source.index("<article")
    headings = list(re.finditer(r"<h2\b", source[start:source.index("</article>")]))
    assert len(headings) > 1
    point = start + headings[1].start()
    addition = "".join("<h2>" + html.escape(s["heading"]) + "</h2>\n" +
                       "".join("<p>" + inline(p) + "</p>\n" for p in s["paragraphs"]) for s in sections)
    return source[:point] + addition + source[point:]


def update_metadata(source, title=None, description=None, update_hero=True):
    if title:
        source = re.sub(r"<title>.*?</title>", "<title>" + html.escape(title) + "</title>", source, flags=re.S)
        source = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*',
                        lambda m: m[1] + html.escape(title, quote=True), source)
    if description:
        source = re.sub(r'(<meta (?:property|name)="(?:description|og:description|twitter:description)" content=")[^"]*',
                        lambda m: m[1] + html.escape(description, quote=True), source)
        if update_hero:
            source = re.sub(r'(<h1\b[^>]*>.*?</h1>\s*<p>).*?(</p>)',
                            lambda m: m[1] + html.escape(description) + m[2], source, count=1, flags=re.S)
        def schema(match):
            value = json.loads(match[2])
            def visit(node):
                if isinstance(node, list):
                    for item in node:
                        visit(item)
                elif isinstance(node, dict):
                    types = node.get("@type", [])
                    types = [types] if isinstance(types, str) else types
                    if any(t in types for t in ("Article", "BlogPosting")):
                        node["description"] = description
                    if "@graph" in node:
                        visit(node["@graph"])
            visit(value)
            return match[1] + json.dumps(value, ensure_ascii=False).replace("</", "<\\/") + match[3]
        source = re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',
                        schema, source, flags=re.S)
    return source


def prune_links(source, approved_targets, future_slugs):
    """Keep words, prefer contextual county/topic-owner links, cap at five."""
    original = main(source)
    log = []
    def eligible(match):
        attributes = attrs(match[1])
        if "elh-inline-link" not in attributes.get("class", "").split():
            return match[0]
        target = attributes.get("href", "")
        if target.split("?", 1)[0].split("#", 1)[0] in future_slugs:
            target = "/services"
            attributes["href"] = target
            attributes.pop("data-reading-destination", None)
            log.append("Future Journal target replaced by verified services overview")
        if target not in approved_targets:
            log.append("Unverified destination withheld: " + target)
            return match[2]
        attributes["data-reading-destination"] = target
        return "<a " + " ".join(f'{k}="{html.escape(v, quote=True)}"' for k, v in attributes.items()) + ">" + match[2] + "</a>"
    body = ANCHOR.sub(eligible, original)
    links = [(m, attrs(m[1])) for m in ANCHOR.finditer(body)
             if "elh-inline-link" in attrs(m[1]).get("class", "").split()]
    # Prefer a county hub and a related published article where appropriate.
    ranked = sorted(enumerate(links), key=lambda item: (
        0 if "ventura-and-los-angeles-county" in item[1][1].get("href", "") else
        1 if item[1][1].get("href", "").startswith("/blog/") else 2, item[0]))
    keep, destinations = set(), set()
    for index, (match, attribute) in ranked:
        target = attribute["href"]
        if len(keep) < 5 and target not in destinations:
            keep.add(match.start())
            destinations.add(target)
    # A short legacy story can legitimately refer twice to the same resource
    # from different passages. Preserve two contextual links, not new filler.
    for _, (match, _) in ranked:
        if len(keep) < 2:
            keep.add(match.start())
    def limited(match):
        if "elh-inline-link" in attrs(match[1]).get("class", "").split() and match.start() not in keep:
            log.append("Excess/repeated link unwrapped; wording preserved")
            return match[2]
        return match[0]
    body = ANCHOR.sub(limited, body)
    return source.replace(original, body, 1), log


def similarity_pairs(documents, threshold=.35):
    shingles = {}
    for slug, source in documents.items():
        tokens = re.findall(r"\w+", core(source).casefold())
        shingles[slug] = set(tuple(tokens[i:i+5]) for i in range(len(tokens)-4))
    pairs = []
    for a, b in itertools.combinations(shingles, 2):
        score = len(shingles[a] & shingles[b]) / len(shingles[a] | shingles[b])
        if score >= threshold:
            pairs.append({"a": a, "b": b, "fiveWordJaccard": round(score, 4),
                          "status": "Human comparison required; not a plagiarism verdict"})
    return pairs
