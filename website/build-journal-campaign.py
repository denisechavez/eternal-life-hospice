#!/usr/bin/env python3
"""Build scheduled Eternal Journal stories.

The original 30-day batches remain fixed. New stories belong in additional-*.json
arrays in the same directory. Existing article HTML is never regenerated; edit
those pages directly if their published copy needs changing. Publication is
enforced at request time by devserver.py.
"""
from __future__ import annotations

import html
import argparse
import json
import re
import subprocess
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
CONTENT = ROOT / "content" / "30-day-journal"
OUT = PUBLIC / "blog"
MANIFEST = ROOT / "content" / "30-day-journal-manifest.json"
BASE_URL = "https://eternallifehospice.com/blog/"
LEGACY_POSTS = [
    {"title": "Rest, Renewal and the Work of Caring", "slug": "the-caregiver-who-needs-care",
     "description": "Nurses, social workers, chaplains, family members at the bedside — everyone who gives needs renewal. Why it matters and what it actually looks like.",
     "date": "2026-08-13", "category": "Family & Professional Care", "readMinutes": 6,
     "heroImage": "/assets/img/comfort-therapies-hero.jpg"},
    {"title": "Sound Baths: Ancient Origins, Present Comfort", "slug": "sound-baths-ancient-comfort-for-body-and-spirit",
     "description": "Where sound baths come from and the tranquility they can bring — sustained tones from singing bowls and gongs, offered gently for comfort of body and spirit.",
     "date": "2026-07-08", "category": "Integrative Comfort", "readMinutes": 5, "heroImage": "/assets/img/sound-bath-hero.jpg"},
    {"title": "The Quiet Work of Hospice Volunteers", "slug": "the-quiet-work-of-hospice-volunteers",
     "description": "What hospice volunteers actually do, why every Medicare-certified hospice relies on them, and how to become one.",
     "date": "2026-07-03", "category": "Community", "readMinutes": 4, "heroImage": "/assets/img/volunteer.jpg"},
    {"title": "Talking with Children When a Loved One Is Seriously Ill", "slug": "talking-with-children-when-a-loved-one-is-seriously-ill",
     "description": "How to talk with children when a loved one is seriously ill or dying: plain words, honest answers, and how hospice social workers can help.",
     "date": "2026-06-17", "category": "Family Support", "readMinutes": 6, "heroImage": "/assets/img/talking-with-children.jpg"},
    {"title": "Music at the Bedside: How Sound Brings Comfort", "slug": "music-at-the-bedside",
     "description": "How music is used at the bedside in hospice for comfort and connection, and the compassionate boundaries around it.",
     "date": "2026-05-27", "category": "Integrative Comfort", "readMinutes": 5, "heroImage": "/assets/img/music-therapy.jpg"},
    {"title": "Five Hospice Myths That Cause Families to Wait Too Long", "slug": "five-hospice-myths-that-cause-families-to-wait",
     "description": "Five common hospice myths that cause families to wait too long, and the reassuring facts behind each.",
     "date": "2026-05-06", "category": "Understanding Hospice", "readMinutes": 6, "heroImage": "/assets/img/when-is-it-time.jpg"},
]


def load_articles():
    articles = []
    for path in sorted(CONTENT.glob("batch-*.json")):
        value = json.loads(path.read_text())
        if not isinstance(value, list):
            raise ValueError(f"{path} must contain an array")
        articles.extend(value)
    if len(articles) != 30:
        raise ValueError(f"Expected 30 original articles, found {len(articles)}")
    for index, article in enumerate(articles):
        if not isinstance(article, dict) or not isinstance(article.get("date"), str) or \
                date.fromisoformat(article["date"]) != date(2026, 9, 21) + timedelta(days=index):
            raise ValueError("Original publication dates must be consecutive 2026-09-21 through 2026-10-20")
    for path in sorted(CONTENT.glob("additional-*.json")):
        value = json.loads(path.read_text())
        if not isinstance(value, list):
            raise ValueError(f"{path} must contain an array")
        articles.extend(value)
    seen_slugs, seen_dates = set(), set()
    required = {"date", "slug", "title", "seoTitle", "description", "category",
                "readMinutes", "heroImage", "lede", "sections", "ctaHeading", "ctaCopy"}
    for index, article in enumerate(articles):
        if not isinstance(article, dict) or not required <= article.keys():
            raise ValueError(f"Article {index + 1} is missing required fields")
        published = date.fromisoformat(article["date"])
        if index >= 30 and published <= date(2026, 10, 20):
            raise ValueError("Additional publication dates must be after 2026-10-20")
        if article["slug"] in seen_slugs or article["date"] in seen_dates:
            raise ValueError("Slugs and publication dates must be unique")
        if article["slug"] in {a["slug"] for a in LEGACY_POSTS} or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", article["slug"]):
            raise ValueError(f"Invalid slug: {article['slug']}")
        if not article["sections"] or any(
            not s.get("heading") or not s.get("paragraphs") for s in article["sections"]
        ):
            raise ValueError(f"Invalid sections: {article['slug']}")
        seen_slugs.add(article["slug"]); seen_dates.add(article["date"])
    public_posts = [a for a in articles if a.get("publicationStatus") != "archived"] + LEGACY_POSTS
    images = [a["heroImage"] for a in public_posts]
    if len(images) != len(set(images)):
        repeated = sorted({image for image in images if images.count(image) > 1})
        raise ValueError(f"Journal posts must have distinct images: {', '.join(repeated)}")
    for article in public_posts:
        image = article["heroImage"]
        if not image.startswith("/assets/img/") or not (PUBLIC / image.lstrip("/")).is_file():
            raise ValueError(f"Journal image missing or outside image assets: {article['slug']}: {image}")
    return sorted(articles, key=lambda article: article["date"])


def esc(value):
    return html.escape(str(value), quote=True)


class PublishedSummaryParser(HTMLParser):
    """Read plain text from the hero only, never metadata or article body."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hero_depth = 0
        self.hero_count = 0
        self.field = None
        self.parts = []
        self.values = {"h1": [], "p": []}
        self.invalid = False

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            if self.hero_depth:
                self.hero_depth += 1
            elif "hero" in dict(attrs).get("class", "").split():
                self.hero_depth = 1
                self.hero_count += 1
        if self.hero_depth and tag in self.values:
            if self.field:
                self.invalid = True
            self.field = tag
            self.parts = []
        if self.field and tag == "br":
            self.parts.append(" ")
        if self.hero_depth and tag in {"script", "style"}:
            self.invalid = True

    def handle_data(self, data):
        if self.field:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.field == tag:
            self.values[tag].append(" ".join("".join(self.parts).split()))
            self.field = None
        if tag == "section" and self.hero_depth:
            if self.field:
                self.invalid = True
                self.field = None
            self.hero_depth -= 1


def published_summary(article):
    """Overlay visible copy without changing source JSON or article HTML.

    Missing or ambiguous hero copy is an error, not permission to fall back to
    possibly stale JSON. Dates, categories and images remain source-controlled.
    """
    path = OUT / f'{article["slug"]}.html'
    parser = PublishedSummaryParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    if parser.invalid or parser.hero_count != 1 or parser.hero_depth or parser.field or any(
        len(values) != 1 or not values[0] for values in parser.values.values()
    ):
        raise ValueError(f"Cannot sync Journal summary: {path} needs one hero with "
                         "one non-empty h1 and one non-empty summary paragraph")
    return dict(article, title=parser.values["h1"][0],
                description=parser.values["p"][0])


def render_body(article):
    bits = [
        f'<section class="hero hero--photo" style="background-image:url(\'..{esc(article["heroImage"])}\')">',
        f'<div class="kicker">Journal &middot; {esc(article["category"])}</div>',
        f'<h1>{esc(article["title"])}</h1><p>{esc(article["description"])}</p></section>',
        '<article class="article sec wrap">',
        '<a class="backlink" href="../blog">&#8592;&nbsp;All Journal Posts</a>',
        f'<div class="blog-byline">By <b>Eternal Life Hospice</b> &middot; '
        f'<time datetime="{article["date"]}">{date.fromisoformat(article["date"]).strftime("%B %-d, %Y")}</time> '
        f'&middot; {article["readMinutes"]} min read</div>',
        f'<p class="lede">{esc(article["lede"])}</p>',
    ]
    for section in article["sections"]:
        bits.append(f'<h2>{esc(section["heading"])}</h2>')
        bits.extend(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
    bits.append("</article>")
    return "\n".join(bits)


def render_post(article, template):
    title = esc(article["seoTitle"])
    description = esc(article["description"])
    canonical = BASE_URL + article["slug"]
    image = "https://eternallifehospice.com" + article["heroImage"]
    head = re.sub(r"<title>.*?</title>", f"<title>{title} | Eternal Life Hospice</title>", template, count=1)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', rf"\g<1>{description}\2", head, count=1)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*(")', rf"\g<1>{canonical}\2", head, count=1)
    for prop, value in (("og:title", title), ("og:description", description),
                        ("og:url", canonical), ("og:image", image),
                        ("twitter:title", title), ("twitter:description", description),
                        ("twitter:image", image)):
        head = re.sub(
            rf'(<meta property="{prop}" content=")[^"]*(")',
            rf"\g<1>{value}\2", head, count=1
        )
        head = re.sub(
            rf'(<meta name="{prop}" content=")[^"]*(")',
            rf"\g<1>{value}\2", head, count=1
        )
    # Image dimensions vary per article; the actual dimensions are set below.
    head = re.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">', '', head)
    head = re.sub(r'<section class="hero hero--photo"[\s\S]*?</article>', render_body(article), head, count=1)
    # Keep the established CTA/related/footer convention, but make CTA editorial.
    head = re.sub(r'<section class="cta">[\s\S]*?</section>', (
        f'<section class="cta"><h2>{esc(article["ctaHeading"])}</h2>'
        f'<p>{esc(article["ctaCopy"])}</p><div class="btns">'
        '<a class="btn-gold" href="../family-guide">Read the Family Guide &#8594;</a>'
        '<a class="btn-ghost" href="tel:18059537273">Call 805.953.7273</a></div></section>'
    ), head, count=1)
    ld = {"@context": "https://schema.org", "@type": "BlogPosting",
          "headline": article["title"], "description": article["description"],
          "url": canonical, "datePublished": article["date"], "dateModified": article["date"],
          "author": {"@type": "Organization", "name": "Eternal Life Hospice",
                     "@id": "https://eternallifehospice.com/#organization"},
          "publisher": {"@type": "Organization", "name": "Eternal Life Hospice",
                        "@id": "https://eternallifehospice.com/#organization"}, "image": image}
    # Replace the first (BlogPosting) JSON-LD object while retaining breadcrumb LD.
    head = re.sub(r'<script type="application/ld\+json">\{[\s\S]*?</script>',
                  '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>",
                  head, count=1)
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [
                      {"@type": "ListItem", "position": 1, "name": "Home",
                       "item": "https://eternallifehospice.com"},
                      {"@type": "ListItem", "position": 2, "name": "Journal",
                       "item": "https://eternallifehospice.com/blog"},
                      {"@type": "ListItem", "position": 3, "name": article["title"],
                       "item": canonical}]}
    def replace_breadcrumb(match):
        try:
            if json.loads(match.group(1)).get("@type") == "BreadcrumbList":
                return '<script type="application/ld+json">' + json.dumps(breadcrumb, ensure_ascii=False) + "</script>"
        except json.JSONDecodeError:
            pass
        return match.group(0)
    head = re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>',
                  replace_breadcrumb, head)
    head = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(")', rf"\g<1>{title} | Eternal Life Hospice\2", head, count=1)
    return head


def card(article, featured=False):
    image = article["heroImage"]
    if featured:
        return (f'<div class="blog-featured" data-publish-date="{article["date"]}">'
                f'<a class="bf-img" href="blog/{article["slug"]}" style="background-image:url(\'{image}\')" '
                f'aria-label="{esc(article["title"])}"></a><div class="bf-body">'
                f'<div class="bf-cat">Latest &middot; {esc(article["category"])}</div>'
                f'<h2><a href="blog/{article["slug"]}">{esc(article["title"])}</a></h2>'
                f'<p>{esc(article["description"])}</p><div class="rc-meta"><time datetime="{article["date"]}">'
                f'{date.fromisoformat(article["date"]).strftime("%B %-d, %Y")}</time><span class="dot">&middot;</span>'
                f'{article["readMinutes"]} min read</div><a class="bf-go" href="blog/{article["slug"]}">Read the post &#8594;</a>'
                '</div></div>')
    # The server promotes the newest *published* card as each scheduled date arrives.
    # Store its ready-to-render featured form alongside the archive card.
    featured_card = esc(card(article, True))
    return (f'<a class="rc" data-publish-date="{article["date"]}" href="blog/{article["slug"]}" '
            f'data-featured="{featured_card}">'
            f'<div class="rc-img" style="background-image:url({image})"></div><div class="rc-body">'
            f'<div class="rc-tag">{esc(article["category"])}</div><h3 class="rc-title">{esc(article["title"])}</h3>'
            f'<p class="rc-ex">{esc(article["description"])}</p><div class="rc-meta"><time datetime="{article["date"]}">'
            f'{date.fromisoformat(article["date"]).strftime("%B %-d, %Y")}</time><span class="dot">&middot;</span>'
            f'{article["readMinutes"]} min read</div><span class="rc-go">Read &#8594;</span></div></a>')


def write_archive(active_articles, all_articles):
    # Resolve every public page before writing anything; never trust stale JSON
    # once the article exists. This also covers legacy cards and featured payloads.
    active_articles = [published_summary(a) for a in active_articles]
    legacy_posts = [published_summary(a) for a in LEGACY_POSTS]
    archive = (PUBLIC / "blog.html").read_text()
    active_articles = sorted(active_articles, key=lambda article: article["date"])
    newest = active_articles[-1]
    archive, replaced = re.subn(
        r'<div class="blog-featured"[^>]*>[\s\S]*?</div>\s*</div>'
        r'|<a class="blog-featured"[^>]*>[\s\S]*?</a>',
        lambda _: card(newest, True), archive, count=1,
    )
    if replaced != 1:
        raise ValueError("Journal archive is missing its featured story")
    # Keep a grid card for the staged lead story too. If a newer post is added
    # later, the server can promote it and put the old lead back into the grid.
    # The chosen lead's duplicate card is removed from the served response.
    cards = "\n".join(card(a) for a in reversed(active_articles))
    cards += "\n" + "\n".join(card(a) for a in legacy_posts)
    archive, replaced = re.subn(
        r'<div class="rgrid">[\s\S]*?</div>\s*</section>',
        lambda _: f'<div class="rgrid">{cards}</div></section>', archive, count=1)
    if replaced != 1:
        raise ValueError("Journal archive is missing its story grid")
    # Add campaign BlogPosting records to the existing Blog JSON-LD.
    entries = [{"@type": "BlogPosting", "headline": a["title"], "url": BASE_URL + a["slug"],
                "datePublished": a["date"], "dateModified": a["date"], "description": a["description"],
                "author": {"@type": "Organization", "name": "Eternal Life Hospice"}}
                for a in active_articles + legacy_posts]
    blog_count = 0
    def merge_blog_schema(match):
        payload = json.loads(match.group(1))
        existing = payload.get("blogPost", [])
        source_urls = {BASE_URL + a["slug"] for a in all_articles}
        by_url = {item.get("url"): item for item in existing
                  if isinstance(item, dict) and item.get("url") not in source_urls}
        by_url.update({item["url"]: item for item in entries})
        payload["blogPost"] = list(by_url.values())
        return '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False).replace("<", r"\u003c") + "</script>"
    def merge_script(match):
        nonlocal blog_count
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return match.group(0)
        if payload.get("@type") != "Blog":
            return match.group(0)
        blog_count += 1
        return merge_blog_schema(match)
    archive = re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>',
                     merge_script, archive)
    if blog_count != 1:
        raise ValueError("Journal archive needs exactly one valid Blog schema")
    (PUBLIC / "blog.html").write_text(archive, encoding="utf-8")


def update_image_dimensions(articles):
    """Refresh only share-image dimensions; preserve all existing article copy."""
    for article in articles:
        path = OUT / f'{article["slug"]}.html'
        text = path.read_text(encoding="utf-8")
        head, separator, body = text.partition("</head>")
        match = re.search(
            r'<meta property="og:image" content="https://eternallifehospice\.com(/assets/img/[^"]+)">',
            head,
        )
        if not match or not separator:
            raise ValueError(f"Article is missing its share image or head: {path}")
        with Image.open(PUBLIC / match.group(1).lstrip("/")) as image:
            width, height = image.size
        head = re.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">', '', head)
        dimensions = (f'<meta property="og:image:width" content="{width}">'
                      f'<meta property="og:image:height" content="{height}">')
        head = head[:match.end()] + dimensions + head[match.end():]
        updated = head + separator + body
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def refresh_images(articles):
    """Update images without overwriting editorial edits in existing article pages."""
    active_articles = [a for a in articles if a.get("publicationStatus") != "archived"]
    updates = []
    for article in active_articles:
        path = OUT / f'{article["slug"]}.html'
        text = path.read_text(encoding="utf-8")
        head, separator, body = text.partition("</head>")
        if not separator:
            raise ValueError(f"Article is missing its head: {path}")
        head = re.sub(r'<meta property="og:image:(?:width|height)" content="[^"]*">', '', head)
        match = re.search(
            r'<section class="hero hero--photo" style="background-image:url\('
            r'["\']?\.\.(\/assets\/img\/[^\'")]+)', body,
        )
        if match is None:
            raise ValueError(f"Article is missing its hero image: {path}")
        old_image = match.group(1)
        if old_image != article["heroImage"]:
            old_url = "https://eternallifehospice.com" + old_image
            new_url = "https://eternallifehospice.com" + article["heroImage"]
            if old_url not in head:
                raise ValueError(f"Article is missing its share image: {path}")
            head = head.replace(old_url, new_url)
            old_hero = match.group(0)
            new_hero = old_hero.replace(old_image, article["heroImage"])
            body = body.replace(old_hero, new_hero, 1)
        updated = head + separator + body
        if updated != text:
            updates.append((path, updated))
    for path, text in updates:
        path.write_text(text, encoding="utf-8")
    update_image_dimensions(active_articles)
    write_archive(active_articles, articles)


def build(articles):
    active_articles = [article for article in articles
                       if article.get("publicationStatus") != "archived"]
    active_slugs = {article["slug"] for article in active_articles}
    template = next((p.read_text() for p in sorted(OUT.glob("*.html"))), None)
    if not template:
        raise FileNotFoundError("No existing Journal post template")
    OUT.mkdir(exist_ok=True)
    for article in articles:
        if article["slug"] not in active_slugs:
            stale_path = OUT / f'{article["slug"]}.html'
            if stale_path.exists():
                stale_path.unlink()
    for article in active_articles:
        path = OUT / f'{article["slug"]}.html'
        if not path.exists():
            path.write_text(render_post(article, template), encoding="utf-8")
    update_image_dimensions(active_articles)
    write_archive(active_articles, articles)

    active_articles.sort(key=lambda article: article["date"])
    manifest = {"timezone": "America/Los_Angeles", "start": active_articles[0]["date"],
                "end": active_articles[-1]["date"], "articles": [
                    {"slug": a["slug"], "date": a["date"], "url": "/blog/" + a["slug"]}
                    for a in active_articles]}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Sitemap entries are intentionally generated for the server-side filter.
    sitemap = PUBLIC / "sitemap.xml"
    xml = sitemap.read_text()
    for article in articles:
        xml = re.sub(
            rf'\s*<url>\s*<loc>https://eternallifehospice\.com/blog/{re.escape(article["slug"])}'
            r'</loc>[\s\S]*?</url>',
            "", xml,
        )
    additions = "".join(f'  <url><loc>{BASE_URL}{a["slug"]}</loc><lastmod>{a["date"]}</lastmod><priority>0.6</priority></url>\n' for a in active_articles)
    sitemap.write_text(xml.replace("</urlset>", additions + "</urlset>"), encoding="utf-8")
    subprocess.run(["node", str(PUBLIC / "assets" / "build-search-index.js")],
                   check=True, cwd=str(ROOT))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--images-only", action="store_true",
                        help="Update existing post images and archive cards without replacing article text")
    mode.add_argument("--archive-only", action="store_true",
                      help="Sync archive cards and Blog schema from visible article copy; do not modify articles")
    args = parser.parse_args()
    if args.archive_only:
        articles = load_articles()
        write_archive([a for a in articles if a.get("publicationStatus") != "archived"], articles)
        print("Synced Journal archive from article pages without modifying articles")
    elif args.images_only:
        refresh_images(load_articles())
        print("Updated Journal images without replacing article text")
    else:
        build(load_articles())
        print("Built scheduled Journal articles")