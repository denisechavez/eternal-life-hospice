"""Shared contact ordering for generated pages and frozen public HTML."""
import re

FOOTER = re.compile(r'<footer\b[^>]*\bid="site-footer"[^>]*>.*?</footer>', re.S)
PHONE = re.compile(
    r'<a class="fc-line(?: no-swap| fc-direct)" href="tel:1805(?:9537273|4099262)">.*?</a>',
    re.S,
)
STYLESHEET = '<link rel="stylesheet" href="/assets/footer-contact.css?v=20261023-nowrap">'


def update_main_number(document):
    """Refresh the website's main listing without touching other phone CTAs."""
    return FOOTER.sub(
        lambda match: match.group().replace(
            "tel:18054101151", "tel:18054099262"
        ).replace("805.410.1151", "805.409.9262"),
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
        if len(phones) != 2:
            return footer
        tracking = next((p.group() for p in phones if 'tel:18054099262' in p.group()), None)
        landline = next((p.group() for p in phones if 'tel:18059537273' in p.group()), None)
        if not tracking or not landline:
            return footer
        tracking = re.sub(r'<span>805\.409\.9262(?: · Main)?</span>',
                          '<span>805.409.9262 · Main</span>', tracking)
        replacements = iter((tracking, landline))
        return PHONE.sub(lambda _: next(replacements), footer)
    document = FOOTER.sub(update, document)
    if "</head>" in document and STYLESHEET not in document:
        document = document.replace("</head>", STYLESHEET + "\n</head>", 1)
    return document
