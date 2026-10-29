"""Shared legacy HTML cases for photo-note presentation regressions."""

NOTE_VARIANTS = (
    '<p class="journal-photo-credit"><small>Old note</small></p>\n',
    "<p class='journal-photo-credit'><small>Old note</small></p>\n",
    '<p id="credit" class="muted journal-photo-credit compact">Old note</p>\n',
    "<p\n data-source='photo' class \t= \n' muted\tjournal-photo-credit\ncompact '>"
    "\n<small>Old note</small>\n</p \t>\n",
    '<P CLASS="journal-photo-credit muted">Old note</P>\r\n',
)

# These bytes must survive every cleanup path, not merely equivalent DOM output.
PRESERVED_HTML = (
    "<p>Illustrative photograph: explain this term.</p>\n"
    "<p class='journal-photo-credit-caption'>An ordinary caption.</p>\n"
    "<p class='not-journal-photo-credit'>Article text.</p>\n"
    "<p data-class='journal-photo-credit'>More article text.</p>\n"
    "<p data-example=\"class='journal-photo-credit'\">Attribute example.</p>\n"
    "<div class='journal-photo-credit'>Not a credit paragraph.</div>\n"
    "<!-- <p class='journal-photo-credit'>An HTML example.</p> -->\n"
    "<script type='application/ld+json'>"
    '{"image":"/assets/original.jpg","sourceUrl":"https://example.org/source",'
    '"example":"<p class=\'journal-photo-credit\'>Stored markup.</p>"}'
    "</script>\n"
    "<style>.example:after { content: '<p class=\"journal-photo-credit\">CSS</p>'; }</style>\n"
    "<img src='/assets/original.jpg' alt='Original photo' data-source='https://example.org/photo'>\n"
    "<p><a href='https://example.org/source'>Source outside the credit block</a></p>\n"
    "<p class='journal-photo-credit'>Unclosed note\n"
    "<p>Do not swallow the next ordinary paragraph.</p>\n"
)
