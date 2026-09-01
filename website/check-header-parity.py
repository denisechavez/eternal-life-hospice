#!/usr/bin/env python3
"""
ELH Header Parity Audit
Header consistency checks for the published site.
Scans every HTML page in elh-preview and classifies its header against
the canonical homepage implementation.

Usage:
    python3 website/check-header-parity.py

Exit code 0 = all standard pages pass.  Non-zero = failures found.
"""

import os, re, sys
from html.parser import HTMLParser

ROOT = os.path.join(os.path.dirname(__file__), "elh-preview")

# ── Approved six-item navigation labels ────────────────────────────────────
NAV_LABELS = [
    "Hospice Care", "Services", "Resources",
    "Service Areas", "About", "Request Care",
]
NAV_FINGERPRINT = tuple(NAV_LABELS)

# ── Pages that intentionally omit the standard header ─────────────────────
INTENTIONAL_EXCEPTIONS = {
    # Digital contact / vCard pages — minimal by design
    "card-aleksandra-dubina.html": "digital contact card — no nav intentional",
    "card-denise-chavez.html":     "digital contact card — no nav intentional",
    # Referral tool — stripped header (logo + phone only), no full nav
    "referral-card.html":          "referral tool — stripped header intentional",
    # Full-page interactive booklet — own toolbar with Back to site
    "family-guide.html":           "flipbook UI — own toolbar, no standard nav",
    "media-kit.html":              "flipbook UI — own toolbar, no standard nav",
    # Redirect stubs — noindex, meta-refresh, no UI needed
    "blog/index.html":             "redirect stub → /blog.html",
    # Care Brief issue pages — clean reader layouts without standard site chrome
    "care-brief/issue-1.html":     "reader view — clean issue layout intentionally",
    # Homepage — IS the canonical; uses inline JS not header.js file
    # Internal / utility pages not in public nav
    "assets/img/amethyst-tmp/gallery.html": "internal asset gallery",
    # Social graphics — not public pages
    "assets/social/index.html":             "social graphic — not a public page",
    "assets/social/amethyst-duotone.html":  "social graphic",
    "assets/social/bowl-wash.html":         "social graphic",
    "assets/social/elh-social-brand-brief.html": "social graphic",
    "assets/social/eye-split.html":         "social graphic",
    "assets/social/mosaic-m1.html":         "social graphic",
    "assets/social/mosaic-m3.html":         "social graphic",
    "assets/social/mosaic-m5.html":         "social graphic",
    "assets/social/mosaic-m7.html":         "social graphic",
    "assets/social/mosaic-m9.html":         "social graphic",
    "assets/social/mosaic-pinterest.html":  "social graphic",
    "assets/social/pen-graphic-pop.html":   "social graphic",
    "assets/social/stillness-card.html":    "social graphic",
}

# ── Canonical checks ───────────────────────────────────────────────────────
REQUIRED = {
    "header_id":   ('id="hdr"',          "header element uses id=hdr"),
    "menu_btn":    ('class="menu-btn"',   "hamburger button present"),
    "search_btn":  ('class="search-btn"', "search button present"),
    "request_care":('Request Care', "Request Care navigation present"),
    "referral_link":('Physicians &amp; Referrals', "Physicians & Referrals utility link present"),
    "accessibility":('class="foot-access"', "footer accessibility control present"),
    "logo_cream":  ('elh-logo-h2-cream',  "cream logo present"),
    "header_css":  ('header-nav.css?v=20260901q', "current header navigation stylesheet included"),
    "header_js":   ('header.js?v=20260901c', "current header.js included"),
    "no_stale_url":('/aleksandradubina',  "stale /aleksandradubina URL"),  # must NOT appear
}

class HeaderStructureParser(HTMLParser):
    """Extract the canonical header structure from actual HTML elements."""

    VOID_TAGS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    })

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.header_count = 0
        self.in_header = False
        self.header_depth = None
        self.nav_attrs = []
        self.menu_attrs = []
        self.full_logo_count = 0
        self.wordmark_count = 0
        self.nav_parent_labels = []
        self.nav_parent_attrs = []
        self.nav_sub_count = 0
        self.nav_group_count = 0
        self._parent_text = None

    @staticmethod
    def _attrs(attrs):
        return {str(k).lower(): (v or "") for k, v in attrs}

    @staticmethod
    def _classes(attrs):
        return set(attrs.get("class", "").split())

    def handle_starttag(self, tag, attrs):
        attr = self._attrs(attrs)
        classes = self._classes(attr)
        if tag not in self.VOID_TAGS:
            self.stack.append((tag, classes))

        if tag == "header" and attr.get("id") == "hdr":
            self.header_count += 1
            self.in_header = True
            self.header_depth = len(self.stack)
            return
        if not self.in_header:
            return

        if tag == "nav":
            self.nav_attrs.append(attr)
        if tag == "button" and "menu-btn" in classes:
            self.menu_attrs.append(attr)
        if "hdr-wordmark" in classes:
            self.wordmark_count += 1
        if tag == "img" and any("hdr-logo" in ancestor for _, ancestor in self.stack):
            if "elh-logo-h2-" in attr.get("src", ""):
                self.full_logo_count += 1
        if "nav-group" in classes:
            self.nav_group_count += 1
        if "nav-sub" in classes:
            self.nav_sub_count += 1
        if tag == "a" and "nav-parent" in classes:
            self.nav_parent_attrs.append(attr)
            self._parent_text = []

    def handle_data(self, data):
        if self._parent_text is not None:
            self._parent_text.append(data)

    def handle_endtag(self, tag):
        if self.in_header and tag == "a" and self._parent_text is not None:
            label = " ".join("".join(self._parent_text).split())
            self.nav_parent_labels.append(label)
            self._parent_text = None

        if self.in_header and tag == "header" and self.header_depth == len(self.stack):
            self.in_header = False
            self.header_depth = None
        if self.stack:
            self.stack.pop()


def structural_header_failures(html):
    """Return canonical header structure/accessibility failures for one page."""
    parser = HeaderStructureParser()
    try:
        parser.feed(html)
    except Exception as exc:
        return [f"INVALID HEADER MARKUP: parser error: {exc}"]

    errors = []
    if parser.header_count != 1:
        errors.append(f"STRUCTURE: expected 1 #hdr header, found {parser.header_count}")
    if len(parser.nav_attrs) != 1:
        errors.append(f"STRUCTURE: expected 1 header nav, found {len(parser.nav_attrs)}")
    elif parser.nav_attrs[0].get("aria-label", "").strip().lower() != "main navigation":
        errors.append('ACCESSIBILITY: header nav must have aria-label="Main navigation"')

    if len(parser.menu_attrs) != 1:
        errors.append(f"STRUCTURE: expected 1 .menu-btn button, found {len(parser.menu_attrs)}")
    else:
        menu = parser.menu_attrs[0]
        if menu.get("aria-label", "").strip().lower() != "menu":
            errors.append('ACCESSIBILITY: .menu-btn must have aria-label="Menu"')
        if menu.get("aria-expanded") != "false":
            errors.append('ACCESSIBILITY: .menu-btn must start with aria-expanded="false"')

    if parser.full_logo_count and parser.wordmark_count:
        errors.append(
            "DUPLICATE WORDMARK: full horizontal elh-logo-h2 image is paired "
            "with .hdr-wordmark markup"
        )

    if tuple(parser.nav_parent_labels) != NAV_FINGERPRINT:
        actual = " > ".join(parser.nav_parent_labels) or "(none)"
        expected = " > ".join(NAV_FINGERPRINT)
        errors.append(f"NAV ORDER: expected [{expected}], found [{actual}]")

    expected_groups = len(NAV_FINGERPRINT)
    if parser.nav_group_count != expected_groups or parser.nav_sub_count != expected_groups:
        errors.append(
            "SUBMENU STRUCTURE: expected "
            f"{expected_groups} nav groups and submenus, found "
            f"{parser.nav_group_count} groups and {parser.nav_sub_count} submenus"
        )
    if len(parser.nav_parent_attrs) == expected_groups:
        missing_hrefs = [
            parser.nav_parent_labels[index]
            for index, attrs in enumerate(parser.nav_parent_attrs)
            if not attrs.get("href")
        ]
        if missing_hrefs:
            errors.append(
                "ACCESSIBILITY: submenu controls must remain keyboard-reachable "
                f"links; missing href: {', '.join(missing_hrefs)}"
            )
    return errors


# ── Sentinel self-test ─────────────────────────────────────────────────────
# Verifies the guard correctly detects a page missing required header elements.
# If the token-matching logic were broken so it always reported "pass", this
# exits 1 instead of silently passing the deploy.
_st_html = "<html><head></head><body><p>No ELH header present</p></body></html>"
_st_found_failures = False
for _st_key, (_st_token, _st_label) in REQUIRED.items():
    if _st_key == "no_stale_url":
        continue  # negative check — skip for self-test
    if _st_token not in _st_html:
        _st_found_failures = True
        break
if not _st_found_failures:
    print("❌  SELF-TEST FAILED: guard did not detect a page missing required header elements")
    sys.exit(1)

_st_duplicate = """<header id="hdr"><a class="hdr-logo">
<img src="assets/img/elh-logo-h2-cream.webp"><span class="hdr-wordmark">Eternal</span>
</a><nav aria-label="Main navigation"></nav>
<button class="menu-btn" aria-label="Menu" aria-expanded="false"></button></header>"""
if not any("DUPLICATE WORDMARK" in failure for failure in structural_header_failures(_st_duplicate)):
    print("❌  SELF-TEST FAILED: guard did not detect a duplicate full-logo wordmark")
    sys.exit(1)

_st_bad_order = """<header id="hdr"><nav aria-label="Main navigation">
<div class="nav-group"><a class="nav-parent" href="/">Services</a><div class="nav-sub"></div></div>
</nav><button class="menu-btn" aria-label="Menu" aria-expanded="false"></button></header>"""
if not any("NAV ORDER" in failure for failure in structural_header_failures(_st_bad_order)):
    print("❌  SELF-TEST FAILED: guard did not detect a changed nav label/order fingerprint")
    sys.exit(1)
print("SENTINEL: check-header-parity.py self-test OK")

results = {"pass": [], "fail": [], "exception": []}
failures = []
stale_exceptions = []      # exception keys whose file is missing from disk
redundant_exceptions = []  # exception keys whose file now passes all parity checks
broken_redirects = []      # redirect stubs that no longer contain a redirect to their documented target
missing_redirect_targets = []  # redirect stubs whose target file does not exist under elh-preview/

for dirpath, dirs, files in os.walk(ROOT):
    dirs.sort()
    for fn in sorted(files):
        if not fn.endswith(".html"):
            continue
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        rel = rel.replace("\\", "/")

        if rel in INTENTIONAL_EXCEPTIONS:
            results["exception"].append((rel, INTENTIONAL_EXCEPTIONS[rel]))
            continue

        html = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
        page_fails = []

        # Standard presence checks
        for key, (token, label) in REQUIRED.items():
            if key == "no_stale_url":
                if token in html:
                    page_fails.append(f"STALE URL: {token} found")
            else:
                if token not in html:
                    page_fails.append(f"MISSING: {label}")

        # All six nav labels must appear
        for label in NAV_LABELS:
            if label not in html:
                page_fails.append(f"MISSING NAV: {label}")
        page_fails.extend(structural_header_failures(html))

        if "elh.css?v=20260813" in html or "header.js?v=20260813" in html:
            page_fails.append("STALE HEADER ASSET: pre-phone-fix cache version found")

        if page_fails:
            results["fail"].append(rel)
            failures.append((rel, page_fails))
        else:
            results["pass"].append(rel)

# ── Staleness scan: verify every exception entry is still valid ────────────
import re as _re
from html.parser import HTMLParser as _HTMLParser

def _extract_redirect_target(reason: str):
    """Return the target path from a 'redirect stub → /foo.html' reason, or None."""
    m = _re.search(r"redirect stub\s*→\s*(\S+)", reason)
    return m.group(1) if m else None

def _js_string_mask(code: str):
    """Return a list of bools: True where *code* is inside a JS string literal.

    Handles single-quoted, double-quoted, and template-literal strings with
    backslash escapes.  The opening/closing quote characters are marked False
    (they are punctuation, not string content).
    """
    mask = [False] * len(code)
    i = 0
    while i < len(code):
        if code[i] in ('"', "'", '`'):
            quote = code[i]
            i += 1                    # skip opening quote (stays False)
            while i < len(code):
                if code[i] == '\\':
                    mask[i] = True    # backslash
                    i += 1
                    if i < len(code):
                        mask[i] = True  # escaped char
                        i += 1
                    continue
                if code[i] == quote:
                    i += 1            # skip closing quote (stays False)
                    break
                mask[i] = True        # ordinary string content
                i += 1
        else:
            i += 1
    return mask

_EXECUTABLE_JS_TYPES = frozenset({
    '', 'text/javascript', 'application/javascript',
    'text/ecmascript', 'application/ecmascript', 'module',
})

def _stub_still_redirects(html: str, target: str) -> bool:
    """Return True if the HTML contains a valid meta-refresh or JS redirect to exactly *target*.

    Uses html.parser so that:
    • <meta> tags inside <script> or HTML comments are never seen as real elements.
    • Only actual <script> element bodies are inspected for JS redirects.
    JS detection additionally:
    • Skips inert script types (JSON-LD, text/template, etc.).
    • Strips JS block and line comments before scanning.
    • Rejects matches that land inside a JS string literal (via a character mask).
    The documented target must match exactly — no prefix or substring acceptance.
    """
    found = [False]

    class _Parser(_HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self._in_script = False
            self._script_type = ''
            self._buf = []

        def handle_starttag(self, tag, attrs):
            a = {k.lower(): (v or '') for k, v in attrs}
            if tag == 'meta':
                if a.get('http-equiv', '').lower().strip() == 'refresh':
                    content = a.get('content', '')
                    m = _re.search(r';\s*url\s*=\s*(\S*)', content, _re.IGNORECASE)
                    if m and m.group(1).strip() == target:
                        found[0] = True
            elif tag == 'script':
                self._in_script = True
                self._script_type = a.get('type', '').strip().lower()
                self._buf = []

        def handle_data(self, data):
            if self._in_script:
                self._buf.append(data)

        def handle_endtag(self, tag):
            if tag == 'script':
                if self._in_script and self._script_type in _EXECUTABLE_JS_TYPES:
                    body = ''.join(self._buf)
                    # Strip JS block comments, then line comments
                    body = _re.sub(r'/\*.*?\*/', '', body, flags=_re.DOTALL)
                    body = _re.sub(r'//[^\n]*', '', body)
                    # Build a string-literal mask and reject matches inside strings
                    mask = _js_string_mask(body)
                    pat = _re.compile(
                        r'window\.location(?:\.href)?\s*=\s*["\']'
                        + _re.escape(target) + r'["\']',
                        _re.IGNORECASE,
                    )
                    for m in pat.finditer(body):
                        if not mask[m.start()]:   # match starts in code, not a string
                            found[0] = True
                self._in_script = False
                self._script_type = ''
                self._buf = []

        # html.parser calls handle_comment for <!-- … --> so those are never
        # seen as starttags — no extra stripping needed.

    parser = _Parser()
    try:
        parser.feed(html)
    except Exception:
        pass
    return found[0]

for exc_rel, exc_reason in INTENTIONAL_EXCEPTIONS.items():
    exc_path = os.path.join(ROOT, exc_rel.replace("/", os.sep))
    if not os.path.exists(exc_path):
        stale_exceptions.append((exc_rel, exc_reason))
        continue
    # File exists — check whether it now passes all parity checks
    html = open(exc_path, encoding="utf-8", errors="replace").read()
    page_fails = []
    for key, (token, label) in REQUIRED.items():
        if key == "no_stale_url":
            if token in html:
                page_fails.append(f"STALE URL: {token} found")
        else:
            if token not in html:
                page_fails.append(f"MISSING: {label}")
    for nav_label in NAV_LABELS:
        if nav_label not in html:
            page_fails.append(f"MISSING NAV: {nav_label}")
    if not page_fails:
        redundant_exceptions.append((exc_rel, exc_reason))
    # For redirect stubs: verify the file still contains a redirect to its target
    redirect_target = _extract_redirect_target(exc_reason)
    if redirect_target:
        if not _stub_still_redirects(html, redirect_target):
            broken_redirects.append((exc_rel, exc_reason, redirect_target))
        # Verify the target file actually exists under elh-preview/
        target_path = os.path.join(ROOT, redirect_target.lstrip('/'))
        if not os.path.exists(target_path):
            missing_redirect_targets.append((exc_rel, exc_reason, redirect_target))

# ── Report ─────────────────────────────────────────────────────────────────
total = len(results["pass"]) + len(results["fail"]) + len(results["exception"])
print(f"\nELH Header Parity Audit — {total} pages scanned")
print(f"  ✅  Pass:       {len(results['pass'])}")
print(f"  ❌  Fail:       {len(results['fail'])}")
print(f"  ⚠️   Exceptions: {len(results['exception'])}")
if stale_exceptions:
    print(f"  🚨  Stale exceptions (file missing):        {len(stale_exceptions)}")
if broken_redirects:
    print(f"  🚨  Broken redirect stubs (no redirect):    {len(broken_redirects)}")
if missing_redirect_targets:
    print(f"  🚨  Redirect stubs with missing target file: {len(missing_redirect_targets)}")
if redundant_exceptions:
    print(f"  🔔  Redundant exceptions (now passes):      {len(redundant_exceptions)}")
print()

if failures:
    print("── FAILURES ─────────────────────────────────────────────────────")
    for rel, errs in failures:
        print(f"\n  {rel}")
        for e in errs:
            print(f"    • {e}")
    print()

if stale_exceptions:
    print("── STALE EXCEPTIONS (file no longer exists on disk) ─────────────")
    for rel, reason in stale_exceptions:
        print(f"  🚨  {rel}")
        print(f"       was: {reason}")
    print()

if broken_redirects:
    print("── BROKEN REDIRECT STUBS (no redirect to documented target) ─────")
    for rel, reason, target in broken_redirects:
        print(f"  🚨  {rel}")
        print(f"       expected redirect to: {target}")
        print(f"       was: {reason}")
        print(f"       → add meta-refresh/JS redirect or remove from INTENTIONAL_EXCEPTIONS")
    print()

if missing_redirect_targets:
    print("── REDIRECT STUBS WITH MISSING TARGET FILE ──────────────────────")
    for rel, reason, target in missing_redirect_targets:
        print(f"  🚨  {rel}")
        print(f"       redirects to: {target}")
        print(f"       but {target} does not exist under elh-preview/")
        print(f"       → fix the target URL or create the missing page")
    print()

if redundant_exceptions:
    print("── REDUNDANT EXCEPTIONS (file now passes all parity checks) ─────")
    for rel, reason in redundant_exceptions:
        print(f"  🔔  {rel}")
        print(f"       was: {reason}")
        print(f"       → consider removing this entry from INTENTIONAL_EXCEPTIONS")
    print()

print("── INTENTIONAL EXCEPTIONS ───────────────────────────────────────────")
for rel, reason in results["exception"]:
    print(f"  ⚠️  {rel}")
    print(f"       {reason}")

# ── _redirects validation ──────────────────────────────────────────────────
# Parse elh-preview/_redirects and:
#   1. Detect self-loop rules (source resolves to the same path as destination)
#      for ALL local rules, including wildcard/placeholder rules such as
#      ``/foo/*  /foo/:splat  301``.
#   2. Verify that every plain (non-placeholder) local destination exists on disk.
#
# External URLs (http/https) are skipped entirely.
# Placeholder destinations (containing a colon, e.g. /:splat) are excluded
# from the existence check but are still inspected for self-loops.

REDIRECTS_FILE = os.path.join(ROOT, "_redirects")
broken_netlify_rules = []  # (line_no, line, dest) tuples
self_loop_rules = []       # (line_no, line) tuples — source == destination after normalisation
redirect_cycle_rules = []  # list of (cycle_nodes, cycle_rule_list) — multi-hop cycles (length ≥ 2)
_plain_redirect_graph = {}  # normalised_src -> [(normalised_dest, lineno, raw_line)]
_parsed_netlify_rules = set()

import re as _re2  # _re already imported above; alias to avoid shadowing

def _loop_normalize(p: str) -> str:
    """Normalise a Netlify path for self-loop comparison.

    Handles both plain paths and wildcard/placeholder paths:
      ``/foo/*``       → ``/foo``   (wildcard suffix removed)
      ``/foo/:splat``  → ``/foo``   (named-param segments removed)
      ``/refer/``      → ``/refer`` (trailing slash removed)
      ``/refer``       → ``/refer``

    Trailing ``.html`` is intentionally preserved: ``/foo → /foo.html`` is a
    legitimate path-form redirect (the file exists on disk), not a self-loop.
    """
    # Remove a trailing wildcard segment (/*  or  /*)
    p = _re2.sub(r"/\*$", "", p)
    # Remove named-parameter segments (/:param)
    p = _re2.sub(r"/:[^/]+", "", p)
    # Strip trailing slashes
    return p.rstrip("/")

def _netlify_dest_exists(dest: str) -> bool:
    """Return True if *dest* resolves to a file under elh-preview/.

    Mirrors Netlify's own resolution order:
      1. Exact path (file on disk)
      2. dest + '.html'
      3. dest.rstrip('/') + '/index.html'
    """
    bare = dest.rstrip("/")
    candidates = [
        bare,
        bare + ".html",
        bare + "/index.html",
    ]
    for candidate in candidates:
        if os.path.isfile(os.path.join(ROOT, candidate.lstrip("/"))):
            return True
    return False

if os.path.isfile(REDIRECTS_FILE):
    with open(REDIRECTS_FILE, encoding="utf-8", errors="replace") as _rf:
        for _lineno, _raw in enumerate(_rf, 1):
            _line = _raw.strip()
            # Skip blank lines and comments
            if not _line or _line.startswith("#"):
                continue
            _parts = _line.split()
            if len(_parts) < 2:
                continue
            _src, _dest = _parts[0], _parts[1]
            _status = _parts[2] if len(_parts) > 2 else ""
            _parsed_netlify_rules.add((_src, _dest, _status))
            # Skip rules whose source or destination is an external URL
            if _src.startswith(("http://", "https://")) or _dest.startswith(("http://", "https://")):
                continue
            # ── Self-loop check (runs for ALL local rules, including placeholders) ──
            # A plain 3xx rule that differs only by one trailing slash is
            # canonicalization, not a loop (for example /blog/ → /blog).
            _trailing_slash_redirect = (
                "*" not in _src
                and ":" not in _src
                and "*" not in _dest
                and ":" not in _dest
                and _src != _dest
                and _src.rstrip("/") == _dest.rstrip("/")
                and _status.startswith("3")
            )
            if (
                _loop_normalize(_src) == _loop_normalize(_dest)
                and not _trailing_slash_redirect
            ):
                self_loop_rules.append((_lineno, _line))
            # ── Existence check (plain destinations only — skip placeholders) ──
            # Placeholder destinations contain a colon (e.g. /:splat, /:id).
            if ":" in _dest:
                continue
            if not _netlify_dest_exists(_dest):
                broken_netlify_rules.append((_lineno, _line, _dest))
            # ── Collect plain (non-splat) rules for multi-hop cycle detection ──
            # Skip wildcard sources/destinations — they represent pattern rules, not
            # fixed paths, so they cannot form a deterministic redirect cycle.
            if "*" not in _src and "*" not in _dest:
                _n_src = _src.rstrip("/")
                _n_dest = _dest.rstrip("/")
                if _n_src not in _plain_redirect_graph:
                    _plain_redirect_graph[_n_src] = []
                _plain_redirect_graph[_n_src].append((_n_dest, _lineno, _line))

required_canonical_hub_rules = {
    ("/resources", "/resources.html", "200!"),
    ("/resources/", "/resources.html", "200!"),
    ("/blog", "/blog.html", "200!"),
    ("/blog/", "/blog", "301!"),
}
missing_canonical_hub_rules = sorted(
    required_canonical_hub_rules - _parsed_netlify_rules
)

# ── Multi-hop cycle detection ──────────────────────────────────────────────
# Walk the graph of plain local redirect rules with DFS; collect any cycle
# of length ≥ 2 hops (A→B→A counts as 2 hops / 3 nodes in the path list).
# Self-loops (length 1) are already reported above; they are excluded here
# (the graph only contains rules whose source != destination after rstrip).

def _find_redirect_cycles(graph):
    """Return a list of cycles found via DFS.

    Each cycle is represented as a list of path strings:
      [A, B, A]  for a two-hop loop
      [A, B, C, A]  for a three-hop loop
    The first and last element are the same node (the cycle entry point).
    Only cycles of total length ≥ 3 nodes (≥ 2 hops) are returned.
    """
    visited = set()
    in_stack = {}   # node -> index in current DFS stack
    stack = []
    cycles = []

    def _dfs(node):
        visited.add(node)
        in_stack[node] = len(stack)
        stack.append(node)
        for next_node, _, _ in graph.get(node, []):
            if next_node not in visited:
                _dfs(next_node)
            elif next_node in in_stack:
                # Back-edge found — extract the cycle from the stack
                start_idx = in_stack[next_node]
                cycle_nodes = stack[start_idx:] + [next_node]
                if len(cycle_nodes) >= 3:   # ≥ 2 hops
                    cycles.append(list(cycle_nodes))
        stack.pop()
        del in_stack[node]

    for _start in list(graph.keys()):
        if _start not in visited:
            _dfs(_start)
    return cycles

_detected_cycles = _find_redirect_cycles(_plain_redirect_graph)
for _cycle_nodes in _detected_cycles:
    # Resolve each edge in the cycle back to its (lineno, raw_line) tuple
    _cycle_rules = []
    for _ci in range(len(_cycle_nodes) - 1):
        _cn, _cn_next = _cycle_nodes[_ci], _cycle_nodes[_ci + 1]
        for _nd, _nl, _nline in _plain_redirect_graph.get(_cn, []):
            if _nd == _cn_next:
                _cycle_rules.append((_nl, _nline))
                break
    redirect_cycle_rules.append((_cycle_nodes, _cycle_rules))

if redirect_cycle_rules:
    print("── REDIRECT CYCLE DETECTED (rules loop — browsers will get too-many-redirects) ─")
    for _cycle_nodes, _cycle_rules in redirect_cycle_rules:
        _hops = len(_cycle_nodes) - 1
        _path_str = " → ".join(_cycle_nodes)
        print(f"  🚨  {_hops}-hop cycle: {_path_str}")
        for _nl, _nline in _cycle_rules:
            print(f"       Line {_nl}: {_nline}")
        print(f"       → remove or reorder these rules to break the loop")
    print()

if self_loop_rules:
    print("── SELF-LOOP REDIRECT RULES (source == destination) ─────────────")
    for lineno, line in self_loop_rules:
        print(f"  🚨  Line {lineno}: {line}")
        print(f"       source and destination resolve to the same path — browsers will loop forever")
        print(f"       → fix the destination or remove this rule")
    print()

if broken_netlify_rules:
    print("── BROKEN NETLIFY REDIRECT RULES (destination not found) ────────")
    for lineno, line, dest in broken_netlify_rules:
        print(f"  🚨  Line {lineno}: {line}")
        print(f"       destination '{dest}' does not exist under elh-preview/")
        print(f"       → fix the destination path or create the missing page")
    print()

if missing_canonical_hub_rules:
    print("── MISSING CANONICAL HUB REWRITE RULES ─────────────────────────")
    for source, destination, status in missing_canonical_hub_rules:
        print(f"  🚨  Missing: {source}  {destination}  {status}")
    print()

exit_code = 0
if failures:
    print(f"\n❌  {len(failures)} page(s) failed — fix before deploying.\n")
    exit_code = 1
if stale_exceptions:
    print(f"\n🚨  {len(stale_exceptions)} stale exception(s) — remove or update INTENTIONAL_EXCEPTIONS.\n")
    exit_code = 1
if broken_redirects:
    print(f"\n🚨  {len(broken_redirects)} redirect stub(s) no longer redirect — fix or reclassify.\n")
    exit_code = 1
if missing_redirect_targets:
    print(f"\n🚨  {len(missing_redirect_targets)} redirect stub(s) point to a file that does not exist — fix the target URL.\n")
    exit_code = 1
if self_loop_rules:
    print(f"\n🚨  {len(self_loop_rules)} _redirects rule(s) loop back to themselves — fix before deploying.\n")
    exit_code = 1
if redirect_cycle_rules:
    print(f"\n🚨  {len(redirect_cycle_rules)} _redirects cycle(s) detected — browsers will hit 'too many redirects' — fix before deploying.\n")
    exit_code = 1
if broken_netlify_rules:
    print(f"\n🚨  {len(broken_netlify_rules)} _redirects rule(s) point to a destination that does not exist — fix before deploying.\n")
    exit_code = 1
if missing_canonical_hub_rules:
    print(f"\n🚨  {len(missing_canonical_hub_rules)} canonical hub rewrite rule(s) missing — fix before deploying.\n")
    exit_code = 1
if not failures and not stale_exceptions and not broken_redirects and not missing_redirect_targets and not self_loop_rules and not redirect_cycle_rules and not broken_netlify_rules and not missing_canonical_hub_rules:
    print(f"\n✅  All standard pages pass header parity check.\n")
if redundant_exceptions:
    print(f"🔔  {len(redundant_exceptions)} exception(s) may be redundant — review INTENTIONAL_EXCEPTIONS.\n")
sys.exit(exit_code)
