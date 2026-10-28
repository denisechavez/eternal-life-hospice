"""Shared contact ordering for generated pages and frozen public HTML."""
import re
from website_phone import public_text

FOOTER = re.compile(r'<footer\b[^>]*\bid="site-footer"[^>]*>.*?</footer>', re.S)
PHONE = re.compile(
    r'<a class="fc-line(?: no-swap| fc-direct)*" href="tel:1805(?:9537273|4099262)">.*?</a>',
    re.S,
)
STYLESHEET = '<link rel="stylesheet" href="/assets/footer-contact.css?v=20261023-nowrap">'


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
        phones = list(PHONE.finditer(footer))
        if not phones:
            return footer
        primary = next((phone for phone in phones if "fc-direct" in phone.group()), phones[0])
        link = re.sub(r'class="fc-line[^"]*"', 'class="fc-line fc-direct no-swap"', primary.group(), count=1)
        link = re.sub(r'<span>805\.409\.9262(?: · Main)?</span>',
                      '<span>805.409.9262 · Main</span>', link)
        # Do not list the same company number twice after unifying office/Main.
        return PHONE.sub(lambda phone: link if phone.start() == primary.start() else "", footer)
    document = FOOTER.sub(update, document)
    if "</head>" in document and STYLESHEET not in document:
        document = document.replace("</head>", STYLESHEET + "\n</head>", 1)
    return document
