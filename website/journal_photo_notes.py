"""Apply approved photo-note presentation without rewriting release snapshots."""
import html
import re

PHOTO_NOTE = re.compile(r'<p class="journal-photo-credit">.*?</p>\n?', re.DOTALL)
OPTIONAL_LICENSES = {
    "https://www.pexels.com/license",
    "https://creativecommons.org/publicdomain/mark/1.0",
    "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
}


def public_html(document):
    """Remove optional stock notes; retain required license and modification credit."""
    def clean(match):
        note = match.group()
        links = re.findall(r"""href=["']([^"']+)["']""", note)
        if any(html.unescape(link).rstrip("/") in OPTIONAL_LICENSES for link in links):
            return ""
        return note.replace("Illustrative photograph:", "Photo:").replace(
            " The photograph does not depict an Eternal patient or service encounter.", "")
    return PHOTO_NOTE.sub(clean, document)
