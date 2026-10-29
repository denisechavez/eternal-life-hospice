"""Shared contact ordering for generated pages and frozen public HTML."""
import re
from website_phone import MAIN_DISPLAY, MAIN_TEL, public_text

FOOTER = re.compile(r'<footer\b[^>]*\bid="site-footer"[^>]*>.*?</footer>', re.S)
PHONE = re.compile(
    rf'<a class="fc-line(?: no-swap| fc-direct)*" href="tel:{MAIN_TEL}">.*?</a>', re.S,
)
STYLESHEET = '<link rel="stylesheet" href="/assets/footer-contact.css?v=20261023-nowrap">'
INSURANCE_HREF = "/resources/medicare-hospice-benefit#insurance"
INSURANCE_LINK = f'<a href="{INSURANCE_HREF}">Insurance &amp; Coverage</a>'


def update_main_number(document):
    """Refresh all company footer numbers without touching article source."""
    return FOOTER.sub(
        lambda match: public_text(match.group()),
        document,
    )


def public_html(document):
    """Update footer chrome only; leave article content and other CTAs intact."""
    document = update_main_number(document)
    if not FOOTER.search(document):
        return document
    def update(match):
        footer = match.group()
        # Apply at response time too, including immutable approved Journal pages.
        if f'href="{INSURANCE_HREF}"' not in footer:
            footer = re.sub(
                r"(<h2(?:\s[^>]*)?>Resources</h2>)",
                lambda heading: heading.group() + INSURANCE_LINK,
                footer, count=1,
            )
        phones = list(PHONE.finditer(footer))
        if not phones:
            return footer
        primary = next((phone for phone in phones if "fc-direct" in phone.group()), phones[0])
        link = re.sub(r'class="fc-line[^"]*"', 'class="fc-line fc-direct no-swap"', primary.group(), count=1)
        link = re.sub(rf'<span>{re.escape(MAIN_DISPLAY)}(?: · Main)?</span>',
                      f'<span>{MAIN_DISPLAY} · Main</span>', link)
        # Do not list the same company number twice after unifying office/Main.
        return PHONE.sub(lambda phone: link if phone.start() == primary.start() else "", footer)
    document = FOOTER.sub(update, document)
    if "</head>" in document and STYLESHEET not in document:
        document = document.replace("</head>", STYLESHEET + "\n</head>", 1)
    return document
