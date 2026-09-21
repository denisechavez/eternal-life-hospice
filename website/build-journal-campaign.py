#!/usr/bin/env python3
"""Build the 30-day Eternal Journal campaign.

The source JSON remains the editorial source of truth.  This command validates
all batches, renders the posts using the existing Journal chrome, and updates
the archive/SEO artifacts.  Publication is enforced at request time by
devserver.py, rather than by relying on a deploy happening each morning.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

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
        raise ValueError(f"Expected 30 articles, found {len(articles)}")
    seen_slugs, seen_dates = set(), set()
    expected = date(2026, 9, 21)
    required = {"date", "slug", "title", "seoTitle", "description", "category",
                "readMinutes", "heroImage", "lede", "sections", "ctaHeading", "ctaCopy"}
    for index, article in enumerate(articles):
        if not isinstance(article, dict) or not required <= article.keys():
            raise ValueError(f"Article {index + 1} is missing required fields")
        published = date.fromisoformat(article["date"])
        if published != expected + timedelta(days=index):
            raise ValueError("Publication dates must be consecutive 2026-09-21 through 2026-10-20")
        if article["slug"] in seen_slugs or article["date"] in seen_dates:
            raise ValueError("Slugs and publication dates must be unique")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", article["slug"]):
            raise ValueError(f"Invalid slug: {article['slug']}")
        if not article["sections"] or any(
            not s.get("heading") or not s.get("paragraphs") for s in article["sections"]
        ):
            raise ValueError(f"Invalid sections: {article['slug']}")
        seen_slugs.add(article["slug"]); seen_dates.add(article["date"])
    return articles


def esc(value):
    return html.escape(str(value), quote=True)


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
    return (f'<a class="rc" data-publish-date="{article["date"]}" href="blog/{article["slug"]}">'
            f'<div class="rc-img" style="background-image:url({image})"></div><div class="rc-body">'
            f'<div class="rc-tag">{esc(article["category"])}</div><h3 class="rc-title">{esc(article["title"])}</h3>'
            f'<p class="rc-ex">{esc(article["description"])}</p><div class="rc-meta"><time datetime="{article["date"]}">'
            f'{date.fromisoformat(article["date"]).strftime("%B %-d, %Y")}</time><span class="dot">&middot;</span>'
            f'{article["readMinutes"]} min read</div><span class="rc-go">Read &#8594;</span></div></a>')


def build(articles):
    template = next((p.read_text() for p in sorted(OUT.glob("*.html"))), None)
    if not template:
        raise FileNotFoundError("No existing Journal post template")
    OUT.mkdir(exist_ok=True)
    for article in articles:
        (OUT / f'{article["slug"]}.html').write_text(render_post(article, template), encoding="utf-8")

    archive = (PUBLIC / "blog.html").read_text()
    newest = articles[-1]
    archive = re.sub(r'<div class="blog-featured">[\s\S]*?</div>\s*</div>', card(newest, True), archive, count=1)
    cards = "\n".join(card(a) for a in reversed(articles[:-1]))
    cards += "\n" + "\n".join(card(a) for a in LEGACY_POSTS)
    archive = re.sub(r'<div class="rgrid">[\s\S]*?</div>\s*</section>', f'<div class="rgrid">{cards}</div></section>', archive, count=1)
    # Add campaign BlogPosting records to the existing Blog JSON-LD.
    entries = [{"@type": "BlogPosting", "headline": a["title"], "url": BASE_URL + a["slug"],
                "datePublished": a["date"], "dateModified": a["date"], "description": a["description"],
                "author": {"@type": "Organization", "name": "Eternal Life Hospice"}}
               for a in articles + LEGACY_POSTS]
    def merge_blog_schema(match):
        payload = json.loads(match.group(1))
        existing = payload.get("blogPost", [])
        by_url = {item.get("url"): item for item in existing if isinstance(item, dict)}
        by_url.update({item["url"]: item for item in entries})
        payload["blogPost"] = list(by_url.values())
        return '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False) + "</script>"
    def merge_script(match):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return match.group(0)
        if payload.get("@type") != "Blog":
            return match.group(0)
        return merge_blog_schema(match)
    archive = re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>',
                     merge_script, archive)
    (PUBLIC / "blog.html").write_text(archive, encoding="utf-8")

    manifest = {"timezone": "America/Los_Angeles", "start": articles[0]["date"],
                "end": articles[-1]["date"], "articles": [
                    {"slug": a["slug"], "date": a["date"], "url": "/blog/" + a["slug"]}
                    for a in articles]}
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
    additions = "".join(f'  <url><loc>{BASE_URL}{a["slug"]}</loc><lastmod>{a["date"]}</lastmod><priority>0.6</priority></url>\n' for a in articles)
    sitemap.write_text(xml.replace("</urlset>", additions + "</urlset>"), encoding="utf-8")
    subprocess.run(["node", str(PUBLIC / "assets" / "build-search-index.js")],
                   check=True, cwd=str(ROOT))


if __name__ == "__main__":
    build(load_articles())
    print("Built 30 Journal campaign articles")