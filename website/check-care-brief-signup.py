#!/usr/bin/env python3
"""Read-only guard for the Care Brief signup label; never sends a signup."""
from html.parser import HTMLParser
from pathlib import Path
import sys


PAGE = Path(__file__).resolve().parent / "elh-preview" / "care-brief.html"
FORM_NAME = "elh-care-brief-signup"
APPROVED_LABEL = "Sign up today →"


class SignupParser(HTMLParser):
    """Collect text only from submit buttons in the named signup form."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_signup = False
        self.form_count = 0
        self.buttons = []
        self.current_button = None
        self.suppressed = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.in_signup = attrs.get("name") == FORM_NAME
            if self.in_signup:
                self.form_count += 1
        if self.in_signup and tag == "button":
            if (attrs.get("type") or "submit").lower() == "submit":
                self.current_button = []
                self.buttons.append(self.current_button)
        if self.current_button is not None:
            hidden = (
                tag in ("script", "style", "template")
                or "hidden" in attrs
                or attrs.get("aria-hidden", "").lower() == "true"
            )
            if hidden or self.suppressed:
                if tag not in ("area", "base", "br", "col", "embed", "hr", "img",
                               "input", "link", "meta", "param", "source", "track", "wbr"):
                    self.suppressed.append(tag)
        if tag == "br" and self.current_button is not None and not self.suppressed:
            self.current_button.append(" ")

    def handle_endtag(self, tag):
        if self.suppressed and tag == self.suppressed[-1]:
            self.suppressed.pop()
        if tag == "button":
            self.current_button = None
            self.suppressed.clear()
        if tag == "form":
            self.in_signup = False

    def handle_data(self, data):
        if self.current_button is not None and not self.suppressed:
            self.current_button.append(data)


def check_label(html):
    parser = SignupParser()
    parser.feed(html)
    parser.close()
    if parser.form_count != 1:
        return [f"expected one signup form, found {parser.form_count}"]
    if len(parser.buttons) != 1:
        return [f"expected one signup submit button, found {len(parser.buttons)}"]
    # Decode entities once via HTMLParser, just as the browser does. A second
    # unescape would incorrectly accept visible literal text such as &#8594;.
    label = " ".join("".join(parser.buttons[0]).split())
    if label != APPROVED_LABEL:
        return [f"signup submit label must be {APPROVED_LABEL!r}; found {label!r}"]
    return []


def self_test():
    def fixture(label, button_type="submit"):
        return (
            f'<form name="{FORM_NAME}"><button type="{button_type}">'
            f'{label}</button></form>'
            '<section id="share"><button>Share the Eternal Care Brief</button></section>'
        )

    good = [
        fixture(APPROVED_LABEL),
        fixture("Sign up today &#8594;"),
        fixture("Sign up today &#x2192;"),
        fixture("Sign up today &rarr;"),
        fixture("\n Sign up <span>today</span>  → \n"),
        fixture('Sign up today →<span hidden>not visible</span>'),
    ]
    bad = [
        fixture("Sign up today Sign up today →"),
        fixture("Sign up today → Sign up today →"),
        fixture("Sign up today &amp;#8594;"),
        fixture("Sign up today &amp;rarr;"),
        fixture("Sign up today &amp;#x2192;"),
        fixture("Sign up today 8594;"),
        fixture("Sign up today"),
        fixture("Subscribe →"),
        fixture(APPROVED_LABEL, "button"),
        fixture('<span hidden>Sign up today →</span>'),
        fixture("Share the Eternal Care Brief"),
        fixture(APPROVED_LABEL).replace(FORM_NAME, "another-form"),
        fixture(APPROVED_LABEL).replace("</button>", "</button><button>Extra</button>", 1),
        fixture(APPROVED_LABEL) + fixture(APPROVED_LABEL),
        "<section>Sign up today →</section>",
    ]
    for html in good:
        if check_label(html):
            raise AssertionError(f"rejected approved label: {html!r}")
    for html in bad:
        if not check_label(html):
            raise AssertionError(f"accepted damaged/missing/ambiguous label: {html!r}")
    # Sharing content is deliberately outside this guard's scope.
    if check_label(fixture(APPROVED_LABEL).replace(
            "Share the Eternal Care Brief", "Sign up today &amp;#8594; repeated")):
        raise AssertionError("unrelated sharing content affected the signup check")
    print("SENTINEL: check-care-brief-signup.py self-test OK")


def main():
    self_test()
    try:
        errors = check_label(PAGE.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        errors = [str(exc)]
    if errors:
        print(f"Care Brief signup label check FAILED ({PAGE}):", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"Care Brief signup label OK: {APPROVED_LABEL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
