"""Apply the owner's no-visible-photo-notes presentation to release snapshots."""
import re
from html.parser import HTMLParser


class _PhotoNotes(HTMLParser):
    """Locate explicit credit paragraphs without reserializing the document."""

    def __init__(self, document):
        super().__init__(convert_charrefs=False)
        self.document = document
        # HTMLParser counts lines on LF only; keep offsets in the original text.
        self.lines = [0] + [match.end() for match in re.finditer("\n", document)]
        self.start = None
        self.spans = []

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            # A new paragraph implicitly ends an unclosed old one. Do not let
            # malformed legacy markup consume the following article paragraph.
            self.start = None
            classes = [value or "" for name, value in attrs if name == "class"]
            if len(classes) == 1 and "journal-photo-credit" in re.split(
                    r"[ \t\n\r\f]+", classes[0]):
                self.start = self.source_offset()

    def handle_startendtag(self, tag, attrs):
        # A self-closing paragraph has no credit body to remove.
        if tag == "p":
            self.start = None

    def handle_endtag(self, tag):
        if tag == "p" and self.start is not None:
            end = self.document.index(">", self.source_offset()) + 1
            # Retain the historical removal of one following line break.
            if self.document.startswith("\r\n", end):
                end += 2
            elif self.document.startswith("\n", end):
                end += 1
            self.spans.append((self.start, end))
            self.start = None


def public_html(document):
    """Remove only closed p elements with the exact journal-photo-credit class.

    Attribute quotes, order, additional classes and HTML whitespace may vary.
    Comments, script/style data, similar class names and unclosed paragraphs are
    not credit blocks. Preserve all bytes outside recognized blocks, including
    image/source metadata; this presentation rule does not waive source licenses.
    """
    parser = _PhotoNotes(document)
    parser.feed(document)
    parser.close()
    parts = []
    previous = 0
    for start, end in parser.spans:
        parts.append(document[previous:start])
        previous = end
    parts.append(document[previous:])
    return "".join(parts)
