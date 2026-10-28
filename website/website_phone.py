"""Website-only primary phone projection; never applied to acknowledgment mail."""
import re

from footer_contact import FOOTER

MAIN_DISPLAY = "805.409.9262"
MAIN_TEL = "18054099262"
PUBLIC_API_ROUTES = {"/api/chat", "/api/coverage", "/api/form-submit"}
EMPLOYEE_CARD_ROUTES = {"/card-aleksandra-dubina", "/card-denise-chavez"}
OLD_PUBLIC_PHONE = re.compile(
    r"(?<!\d)(\+?1[ .-]?)?(\(?805\)?)([ .-]?)953([ .-]?)7273(?!\d)"
)
OFFICE_PREFIX = re.compile(r"\boffice\b[^<>]{0,35}$", re.I)
PROTECTED_BLOCKS = re.compile(
    FOOTER.pattern + r"|<a\b[^>]*>.*?</a>|<p\b[^>]*>.*?</p>",
    re.S | re.I,
)


def public_text(text):
    """Refresh general contact references; retain explicitly labeled office text."""
    def replace(match):
        prefix = text[max(0, match.start() - 50):match.start()]
        if OFFICE_PREFIX.search(prefix):
            return match.group()
        _, middle, last = MAIN_DISPLAY.split(".")
        return ((match.group(1) or "") + match.group(2)
                + match.group(3) + middle + match.group(4) + last)
    return OLD_PUBLIC_PHONE.sub(replace, text)


def public_html(document, route=None):
    """Preserve the footer landline and Office links, updating other call points.

    Runtime projection also covers approved Journal snapshots without changing
    their signed source documents.
    """
    if route in EMPLOYEE_CARD_ROUTES:
        return document
    chunks = []
    cursor = 0
    for match in PROTECTED_BLOCKS.finditer(document):
        chunks.append(public_text(document[cursor:match.start()]))
        block = match.group()
        label = re.sub(r"<[^>]*>", "", block)
        if FOOTER.fullmatch(block) or re.search(r"\boffice\b", label, re.I):
            chunks.append(block)
        else:
            chunks.append(public_text(block))
        cursor = match.end()
    chunks.append(public_text(document[cursor:]))
    return "".join(chunks)


def public_payload(value):
    """Apply only at public API boundaries, never to stored or emailed letters."""
    if isinstance(value, str):
        return public_text(value)
    if isinstance(value, list):
        return [public_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: item if re.search(r"office|referral", key, re.I)
                else public_payload(item) for key, item in value.items()}
    return value
