"""Discovery copy comes from the released document, never a pending source."""
import html
import json
import re
from datetime import date
from urllib.parse import urlsplit
from journal_metadata import MetadataParser, blog_postings


def plain(text):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", text)).split())


def summary(row):
    document = row["html"]
    heading = re.search(r"<h1\b[^>]*>([\s\S]*?)</h1>", document)
    hero = re.search(r'<section\b[^>]*class=["\'][^"\']*\bhero\b[^"\']*["\'][^>]*>([\s\S]*?)</section>', document)
    paragraph = re.search(r"<p\b[^>]*>([\s\S]*?)</p>", hero[1]) if hero else None
    parser = MetadataParser()
    parser.feed(document)
    postings = []
    for source in parser.schemas:
        try:
            postings.extend(blog_postings(json.loads(source)))
        except ValueError:
            continue
    posting = postings[0] if postings else {}
    image = posting.get("image", "")
    if isinstance(image, dict):
        image = image.get("url", "")
    if isinstance(image, list):
        image = image[0] if image else ""
    if not image:
        images = re.findall(r"url\([\"']?([^)'\"\s]+)", document)
        image = next((x for x in images if "/api/journal-photo/" in x or re.search(r"\.(?:jpg|png|webp|jpeg)(?:\?|$)", x)), "")
    if image and urlsplit(image).netloc == "eternallifehospice.com":
        image = urlsplit(image).path
    return {"title": plain(heading[1]) if heading else posting.get("headline", ""),
            "desc": plain(paragraph[1]) if paragraph else posting.get("description", ""),
            "image": image, "date": row["date"]}


def card(markup, row):
    info = summary(row)
    if not info["title"]:
        return markup
    markup = re.sub(r'\bdata-featured="([^"]*)"',
                    lambda m: 'data-featured="' + html.escape(card(html.unescape(m[1]), row), quote=True) + '"',
                    markup)
    markup = re.sub(r'(<h[23]\b[^>]*>(?:<a\b[^>]*>)?)[\s\S]*?((?:</a>)?</h[23]>)',
                    lambda m: m[1] + html.escape(info["title"]) + m[2], markup)
    markup = re.sub(r'(<p(?:\s+class="rc-ex")?>)[\s\S]*?(</p>)',
                    lambda m: m[1] + html.escape(info["desc"]) + m[2], markup)
    if info["image"]:
        markup = re.sub(r"background-image:url\([^)]*\)",
                        lambda _: "background-image:url('" + html.escape(info["image"], quote=True) + "')", markup)
    markup = re.sub(r'((?:data-publish-date|datetime)=")[^"]+(")', lambda m: m[1]+info["date"]+m[2], markup)
    markup = re.sub(r'(<time\b[^>]*>)[\s\S]*?(</time>)',
                    lambda m:m[1]+date.fromisoformat(info["date"]).strftime("%B %-d, %Y")+m[2], markup)
    # aria-label is visible/accessibility discovery copy too.
    markup = re.sub(r'aria-label="[^"]*"', lambda _:'aria-label="'+html.escape(info["title"], quote=True)+'"', markup)
    return markup


def archive(text, released):
    def replace(match):
        slug = re.search(r'href="/?blog/([^"#?]+)', match[0])
        return card(match[0], released[slug[1]]) if slug and slug[1] in released else match[0]
    text = re.sub(r'<a class="rc"[^>]*>[\s\S]*?</a>', replace, text)
    return re.sub(r'<div class="blog-featured"[^>]*>[\s\S]*?</div>\s*</div>', replace, text)
