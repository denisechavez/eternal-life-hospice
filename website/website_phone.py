"""Website-only primary phone projection; never applied to acknowledgment mail."""
import re

MAIN_DISPLAY = "805.409.9262"
MAIN_TEL = "18054099262"
PUBLIC_API_ROUTES = {"/api/chat", "/api/coverage", "/api/form-submit"}
OLD_PUBLIC_PHONE = re.compile(
    r"(?<!\d)(\+?1[ .-]?)?(\(?805\)?)([ .-]?)(953[ .-]?7273|410[ .-]?1151)(?!\d)"
)
# An anchor cannot swallow another anchor, and a plain paragraph cannot
# swallow anchors or sibling paragraphs. Never exempt a container of CTAs.
OFFICE_BLOCK = re.compile(
    r"<a\b[^>]*>(?:(?!</?a\b).)*?</a>"
    r"|<p\b[^>]*>(?:(?!</?(?:a|p)\b).)*?</p>",
    re.S | re.I,
)
OFFICE_LABEL = re.compile(r"\boffice\b", re.I)
OFFICE_KEYS = {"officephone", "office_phone", "office"}


def public_text(text):
    """Unify all website company contacts, including office and referral labels."""
    def replace(match):
        _, middle, last = MAIN_DISPLAY.split(".")
        separator = re.sub(r"\d", "", match.group(4))
        return ((match.group(1) or "") + match.group(2)
                + match.group(3) + middle + separator + last)
    return OLD_PUBLIC_PHONE.sub(replace, text)


def public_html(document, route=None):
    """Unify public call points while retaining explicitly labeled office contacts.

    Runtime projection also covers approved Journal snapshots without changing
    their signed source documents.
    """
    # Protect only office-labeled contact blocks, not an entire page or footer.
    # Plain public CTAs and structured-data telephone fields still use Main.
    parts = []
    end = 0
    for match in OFFICE_BLOCK.finditer(document):
        parts.append(public_text(document[end:match.start()]))
        block = match.group()
        label = re.sub(r"<[^>]+>", " ", block)
        parts.append(block if OFFICE_LABEL.search(label) else public_text(block))
        end = match.end()
    parts.append(public_text(document[end:]))
    return "".join(parts)


def public_payload(value):
    """Apply only at public API boundaries, never to stored or emailed letters."""
    if isinstance(value, str):
        return public_text(value)
    if isinstance(value, list):
        return [public_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: item if key.lower() in OFFICE_KEYS else public_payload(item)
                for key, item in value.items()}
    return value
