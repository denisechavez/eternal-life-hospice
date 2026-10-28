"""Website-only primary phone projection; never applied to acknowledgment mail."""
import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("website-contact.json")
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
MAIN = CONFIG["main"]
ALIASES = set(CONFIG["previousWebsiteNumbers"]) | {MAIN}
if any(not re.fullmatch(r"[2-9]\d{9}", number) for number in ALIASES):
    raise ValueError("Website phone settings must contain ten-digit US numbers")
MAIN_DISPLAY = f"{MAIN[:3]}.{MAIN[3:6]}.{MAIN[6:]}"
MAIN_TEL = "1" + MAIN
PUBLIC_API_ROUTES = {"/api/chat", "/api/coverage", "/api/form-submit", "/api/form-security"}
PHONE_PATTERN = (
    r"(?<!\d)(\+?1[ .-]?)?(\(?\d{3}\)?)([ .-]?)(\d{3})([ .-]?)(\d{4})(?!\d)"
)
# Retained for callers that check for retired website numbers.
OLD_PUBLIC_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[ .-]?)?(?:" + "|".join(
        rf"\(?{number[:3]}\)?[ .-]?{number[3:6]}[ .-]?{number[6:]}"
        for number in sorted(ALIASES - {MAIN})
    ) + r")(?!\d)"
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
        country, area, first, middle, second, last = match.groups()
        if re.sub(r"\D", "", area) + middle + last not in ALIASES:
            return match.group()
        return ((country or "") + re.sub(r"\d{3}", MAIN[:3], area)
                + first + MAIN[3:6] + second + MAIN[6:])
    text = text.replace("__ELH_MAIN_DISPLAY__", MAIN_DISPLAY).replace("__ELH_MAIN_TEL__", MAIN_TEL)
    return re.sub(PHONE_PATTERN, replace, text)


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
