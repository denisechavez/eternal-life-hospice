"""Current public Journal label, without rewriting signed article documents."""
import re

DISPLAY_NAME = "The Eternal Journal/Blog"
PUBLICATION_NAME = re.compile(r"\b(?:The )?Eternal Journal(?:/Blog)?\b")
JOURNAL_LINK = re.compile(
    r"""(<a\b[^>]*\bhref=["'](?:\.\./|/)?blog(?:\.html)?/?["'][^>]*>)"""
    r"(?:Journal|Blog)(</a>)"
)


def public_html(document):
    """Refresh publication labels and metadata, keeping URLs and articles intact."""
    document = PUBLICATION_NAME.sub(DISPLAY_NAME, document)
    document = JOURNAL_LINK.sub(
        lambda match: match[1] + DISPLAY_NAME + match[2], document)
    return document.replace(
        '<div class="kicker">Journal &middot;',
        f'<div class="kicker">{DISPLAY_NAME} &middot;',
    )
