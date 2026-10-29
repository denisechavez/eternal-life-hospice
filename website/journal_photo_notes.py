"""Apply the owner's no-visible-photo-notes presentation to release snapshots."""
import re

PHOTO_NOTE = re.compile(r'<p class="journal-photo-credit">.*?</p>\n?', re.DOTALL)


def public_html(document):
    """Remove visible credit blocks without changing photographs or stored sources."""
    return PHOTO_NOTE.sub("", document)
