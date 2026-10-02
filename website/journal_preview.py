"""Render Resources picks from the generated Journal archive, not a second list."""
import html
import re
from datetime import date


def recent_journal_cards(archive, manifest, today, limit=3):
    """Select dated archive cards, with manifest dates authoritative for campaigns.

    The featured story is a separate archive layout, so convert it to a regular
    card as well. Never carry its encoded promotion payload into Resources.
    """
    candidates = []
    campaign_dates = {item["slug"]: item["date"] for item in manifest}
    for match in re.finditer(
        r'<a class="rc"[^>]*data-publish-date="([^"]+)"[^>]*'
        r'href="blog/([^"]+)"[^>]*>[\s\S]*?</a>', archive
    ):
        card = re.sub(r' data-featured="[^"]*"', "", match.group(0), count=1)
        candidates.append((match.group(2), match.group(1), card))

    featured = re.search(
        r'<div class="blog-featured" data-publish-date="([^"]+)">'
        r'<a class="bf-img" href="blog/([^"]+)" '
        r'style="background-image:url\(\'([^\']+)\'\)"[^>]*></a>'
        r'<div class="bf-body"><div class="bf-cat">Latest &middot; ([\s\S]*?)</div>'
        r'<h2><a[^>]*>([\s\S]*?)</a></h2><p>([\s\S]*?)</p>',
        archive,
    )
    if featured:
        published, slug, image, category, title, summary = featured.groups()
        card = (
            f'<a class="rc" data-publish-date="{published}" href="blog/{slug}">'
            f'<div class="rc-img" style="background-image:url(\'{html.escape(image, quote=True)}\')"></div>'
            f'<div class="rc-body"><div class="rc-tag">{category}</div>'
            f'<h3 class="rc-title">{title}</h3><p class="rc-ex">{summary}</p>'
            '<div class="rc-meta"></div><span class="rc-go">Read &#8594;</span></div></a>'
        )
        candidates.append((slug, published, card))

    visible = {}
    for slug, published, card in candidates:
        published = campaign_dates.get(slug, published)
        if published > today:
            continue
        # Reflect the authoritative date in the card itself, not just selection.
        label = date.fromisoformat(published).strftime("%B %-d, %Y")
        card = re.sub(r'data-publish-date="[^"]+"',
                      f'data-publish-date="{published}"', card, count=1)
        card = re.sub(
            r'<div class="rc-meta">[\s\S]*?</div>',
            f'<div class="rc-meta"><time datetime="{published}">{label}</time></div>',
            card, count=1,
        )
        visible[slug] = (published, card)
    if not visible:
        raise ValueError("No published Journal stories available")
    return "\n".join(card for _, card in
                     sorted(visible.values(), key=lambda item: item[0], reverse=True)[:limit])


def render_resources_journal(resources, archive, manifest, today):
    start = "<!-- JOURNAL_PICKS_START -->"
    end = "<!-- JOURNAL_PICKS_END -->"
    if resources.count(start) != 1 or resources.count(end) != 1:
        raise ValueError("Resources Journal slot unavailable")
    before, rest = resources.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + "\n" + recent_journal_cards(archive, manifest, today) + "\n" + end + after