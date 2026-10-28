"""Website-only primary phone projection; never applied to acknowledgment mail."""
import re

MAIN_DISPLAY = "805.409.9262"
MAIN_TEL = "18054099262"
PUBLIC_API_ROUTES = {"/api/chat", "/api/coverage", "/api/form-submit"}
OLD_PUBLIC_PHONE = re.compile(
    r"(?<!\d)(\+?1[ .-]?)?(\(?805\)?)([ .-]?)(953[ .-]?7273|410[ .-]?1151)(?!\d)"
)


def public_text(text):
    """Unify all website company contacts, including office and referral labels."""
    def replace(match):
        _, middle, last = MAIN_DISPLAY.split(".")
        separator = re.sub(r"\d", "", match.group(4))
        return ((match.group(1) or "") + match.group(2)
                + match.group(3) + middle + separator + last)
    return OLD_PUBLIC_PHONE.sub(replace, text)


def public_html(document, route=None):
    """Unify every company call point, including footers and employee cards.

    Runtime projection also covers approved Journal snapshots without changing
    their signed source documents.
    """
    return public_text(document)


def public_payload(value):
    """Apply only at public API boundaries, never to stored or emailed letters."""
    if isinstance(value, str):
        return public_text(value)
    if isinstance(value, list):
        return [public_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: public_payload(item) for key, item in value.items()}
    return value
