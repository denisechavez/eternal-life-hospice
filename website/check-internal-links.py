#!/usr/bin/env python3
"""Route-aware internal-link guard and reproducible graph report."""
import argparse
from collections import deque
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from internal_links import PageParser, config, inventory, render_links, resolve, today
from devserver import LEGACY_PAGE_REDIRECTS


def audit(pages, as_of):
    errors, incoming, graphs = [], {r: set() for r in pages}, {"content": {}, "chrome": {}, "all": {}}
    chrome_incoming = {r: set() for r in pages}
    rules = config()
    for source, (_, text, parser) in pages.items():
        edges, chrome_edges, all_edges = set(), set(), set()
        for href, kind, attrs in parser.links:
            label = " ".join(attrs.get("_text", "").lower().split())
            if "request care" in label and not href.startswith("tel:") and href != "/?lead=family#leadcap":
                errors.append(f"{source}: Request Care must open the family intake form: {href}")
            if label in {"refer a patient", "refer a patient →", "send a referral", "physicians & referrals", "send a patient referral"} and href != "/refer#referral-form":
                errors.append(f"{source}: provider action must open the referral form: {href}")
            target = resolve(source, href)
            if target is None:
                continue
            dest, fragment, query = target
            if href == "#" and attrs.get("onclick"):
                continue  # Explicit action control, not discovery.
            if dest in rules["excluded"] or dest.startswith(("/canvas-hub", "/__reviews-mockup", "/assets/social")):
                errors.append(f"{source}: prohibited target {href}")
                continue
            if dest in LEGACY_PAGE_REDIRECTS:
                errors.append(f"{source}: redirecting link {href}")
                continue
            if dest not in pages:
                asset = Path(__file__).parent / "elh-preview" / dest.lstrip("/")
                if asset.is_file() and asset.suffix.lower() not in {".html", ".md", ".py"}:
                    continue
                errors.append(f"{source}: broken or unpublished target {href}")
                continue
            if fragment and fragment not in pages[dest][2].ids:
                errors.append(f"{source}: missing fragment {href}")
            if kind == "content" and (urlsplit(href).netloc or (urlsplit(href).path and not href.startswith("/"))):
                errors.append(f"{source}: noncanonical content link {href}")
            if kind == "content" and urlsplit(href).path not in {"", dest}:
                errors.append(f"{source}: noncanonical content link {href}")
            if dest != source:
                all_edges.add(dest)
                if kind == "content":
                    edges.add(dest)
                    incoming[dest].add(source)
                elif kind == "chrome":
                    chrome_edges.add(dest)
                    chrome_incoming[dest].add(source)
        graphs["content"][source] = sorted(edges)
        graphs["chrome"][source] = sorted(chrome_edges)
        graphs["all"][source] = sorted(all_edges)
        block = text.split("<!-- INTERNAL_LINKS_START -->")[-1].split("<!-- INTERNAL_LINKS_END -->")[0] if "<!-- INTERNAL_LINKS_START -->" in text else ""
        related = [resolve(source, href)[0] for href, _, _ in PageParser(block).links if resolve(source, href)]
        if len(related) != len(set(related)):
            errors.append(f"{source}: duplicate related destination")
    for route in pages:
        if not incoming[route] and route not in rules["incomingExceptions"]:
            errors.append(f"{route}: no incoming main-content link")
    depths = {}
    for kind, graph in graphs.items():
        found = {"/": 0}
        queue = deque(["/"])
        while queue:
            source = queue.popleft()
            for dest in graph.get(source, []):
                if dest not in found:
                    found[dest] = found[source] + 1
                    queue.append(dest)
        depths[kind] = found
    return {
        "date": as_of, "routes": sorted(pages), "errors": sorted(set(errors)),
        "summary": {"pages": len(pages), "content_edges": sum(map(len, graphs["content"].values())),
                    "chrome_edges": sum(map(len, graphs["chrome"].values())),
                    "all_edges": sum(map(len, graphs["all"].values())),
                    "content_orphans": sum(not v for k, v in incoming.items() if k not in rules["incomingExceptions"]),
                    "content_reachable": len(depths["content"]),
                    "all_reachable": len(depths["all"]),
                    "max_content_depth": max(depths["content"].values(), default=0)},
        "pages": {r: {"incoming_content": sorted(incoming[r]),
                      "incoming_chrome": sorted(chrome_incoming[r]),
                      "content_depth": depths["content"].get(r), "all_depth": depths["all"].get(r),
                      "exception": rules["incomingExceptions"].get(r)} for r in pages},
        "graphs": graphs,
    }


def self_test():
    def fixture(route, text):
        return (None, text, PageParser(text))
    pages = {
        "/": fixture("/", '<main><a href="/resources?x=1#answer">Read answers</a><a href="#leadcap">Care</a><div id="leadcap"></div></main>'),
        "/resources": fixture("/resources", '<main id="answer"><a href="/">Home</a></main>')
    }
    assert not audit(pages, "2026-10-07")["errors"]
    assert resolve("/resources/article", "../resources?q=1#answer") == ("/resources", "answer", "q=1")
    runtime_home = render_links(
        '<main><div class="mod-card" data-mod="music"></div></main>',
        "/", "2026-10-07", pages=pages)
    assert "therapy-music" in PageParser(runtime_home).ids
    for href, expected in [("/missing", "broken"), ("/resources#gone", "fragment"),
                           ("/insurance", "redirecting"), ("/card-denise-chavez", "prohibited"),
                           ("/resources.html", "broken"), ("/__reviews-mockup/", "prohibited")]:
        bad = dict(pages)
        bad["/"] = fixture("/", f'<main><a href="{href}">Bad</a></main>')
        assert any(expected in e for e in audit(bad, "2026-10-07")["errors"]), href
    bad = dict(pages)
    bad["/"] = fixture("/", '<footer><a href="/resources">Resources</a></footer>')
    assert any("no incoming" in e for e in audit(bad, "2026-10-07")["errors"])
    from internal_links import journal_records, recommendations
    for route, record in journal_records().items():
        if record.get("publicationStatus") == "archived":
            assert route not in inventory("2027-01-01")
    # A staged article becomes eligible on its own local publication date.
    route = "/blog/does-medicare-cover-hospice-care"
    assert route not in inventory("2026-09-24")
    assert route in inventory("2026-09-25")
    before = recommendations("/resources/medicare-hospice-benefit", "2026-09-24")
    after = recommendations("/resources/medicare-hospice-benefit", "2026-09-25")
    assert route not in [x[0] for x in before]
    assert route in [x[0] for x in after]
    cached = render_links('<head></head><main></main>', "/resources/medicare-hospice-benefit", "2026-09-25")
    assert route not in render_links(cached, "/resources/medicare-hospice-benefit", "2026-09-24")
    conversion = dict(pages)
    conversion["/"] = fixture("/", '<a href="/resources">Request Care</a>')
    assert any("family intake" in e for e in audit(conversion, "2026-10-07")["errors"])
    legacy = render_links('<head></head><main></main>', "/resources", "2026-09-20")
    for dest, _ in recommendations("/resources", "2026-09-20"):
        assert dest in inventory("2026-09-20")
    assert "can-a-family-request-a-hospice-evaluation" not in legacy
    print("SENTINEL: check-internal-links.py self-test OK")


def map_issues():
    """A typo in curation must fail, not disappear during eligibility filtering."""
    rules, all_pages, errors = config(), inventory("9999-12-31"), []
    destinations = [value[0] for value in rules["topics"].values()]
    destinations += list(rules["journalOwners"].values())
    destinations += [value[0] for values in rules["supportLinks"].values() for value in values]
    for href in destinations:
        resolved = resolve("/", href)
        if resolved is None or resolved[0] not in all_pages:
            errors.append(f"Curated map: missing or prohibited destination {href}")
        elif resolved[1] and resolved[1] not in all_pages[resolved[0]][2].ids:
            errors.append(f"Curated map: missing fragment {href}")
    for route, topics in rules["pages"].items():
        if route not in all_pages:
            errors.append(f"Curated map: missing source page {route}")
        for topic in topics:
            if topic not in rules["topics"]:
                errors.append(f"Curated map: unknown topic {topic} on {route}")
    return errors


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--date", default=today())
    cli.add_argument("--report")
    cli.add_argument("--baseline", action="store_true")
    cli.add_argument("--baseline-from-git", action="store_true",
                     help="Read tracked pre-rollout HTML from HEAD for the same eligible corpus")
    args = cli.parse_args()
    if not args.baseline:
        self_test()
    pages = inventory(args.date)
    if args.baseline_from_git:
        import subprocess
        pages = {r: (p, original, PageParser(original, args.date))
                 for r, (p, _, _) in pages.items()
                 for original in [subprocess.check_output(["git", "show", "HEAD:" + str(p.relative_to(Path.cwd()))], text=True)]}
    # Keep source anchors checked; only refresh the dated curated slot.
    if not args.baseline:
        from internal_links import START, END, recommendations
        import re
        def dated(text, route):
            rendered = render_links(text, route, args.date)
            block = rendered.split(START)[-1].split(END)[0]
            return re.sub(re.escape(START) + r"[\s\S]*?" + re.escape(END), lambda _: START + block + END, text)
        def checked_parser(text, route):
            parser = PageParser(dated(text, route), args.date)
            # Incoming anchors may target IDs added by the existing server
            # renderer. Retain authored link checks, but validate real targets.
            parser.ids.update(PageParser(render_links(
                text, route, args.date), args.date).ids)
            return parser
        pages = {r: (p, dated(t, r), checked_parser(t, r))
                 for r, (p, t, _) in pages.items()}
    result = audit(pages, args.date)
    if not args.baseline:
        result["errors"].extend(map_issues())
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    for error in result["errors"]:
        print(error)
    sys.exit(0 if args.baseline or not result["errors"] else 1)
