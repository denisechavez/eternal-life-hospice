#!/usr/bin/env python3
"""Reproducible city-page text audit; no network requests or site writes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
SHINGLE_SIZE = 8


class VisibleText(HTMLParser):
    """Main excludes shared chrome; full includes visible navigation/footer text."""
    def __init__(self, main_only):
        super().__init__(convert_charrefs=True)
        self.main_only = main_only
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        excluded = tag in {"head", "script", "style", "noscript"}
        if self.main_only:
            excluded |= tag in {"nav", "header", "footer", "button"}
            excluded |= bool(set(attrs.get("class", "").split()) &
                             {"hero-btns", "btns", "creds"})
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, excluded))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if any(excluded for _, excluded in self.stack):
            return
        if self.main_only and not any(tag == "main" for tag, _ in self.stack):
            return
        self.parts.append(text)


def tokens(markup, main_only, name_pattern):
    parser = VisibleText(main_only)
    parser.feed(markup)
    text = " ".join(parser.parts).lower()
    # Prevent city-name swaps from artificially making a template look unique.
    text = name_pattern.sub(" city ", text)
    return re.findall(r"\w+(?:['’]\w+)?", text)


def shingles(words):
    return [tuple(words[i:i + SHINGLE_SIZE])
            for i in range(max(0, len(words) - SHINGLE_SIZE + 1))]


def summarize(pages):
    passage_sets = {slug: set(shingles(words)) for slug, words in pages.items()}
    counts = Counter(p for passages in passage_sets.values() for p in passages)
    per_page = {}
    for slug, words in pages.items():
        covered = set()
        for index, passage in enumerate(shingles(words)):
            if counts[passage] > 1:
                covered.update(range(index, index + SHINGLE_SIZE))
        per_page[slug] = {
            "words": len(words), "repeated_words": len(covered),
            "redundancy_percent": round(100 * len(covered) / max(1, len(words)), 2)
        }
    scores = []
    for left, right in itertools.combinations(sorted(passage_sets), 2):
        a, b = passage_sets[left], passage_sets[right]
        scores.append((len(a & b) / max(1, len(a | b)), left, right))
    words = sum(p["words"] for p in per_page.values())
    repeated = sum(p["repeated_words"] for p in per_page.values())
    return {
        "word_weighted_redundancy_percent": round(100 * repeated / max(1, words), 2),
        "average_pairwise_jaccard_percent": round(
            100 * sum(s[0] for s in scores) / max(1, len(scores)), 2),
        "worst_pairs": [{"jaccard_percent": round(score * 100, 2),
                         "left": left, "right": right}
                        for score, left, right in sorted(scores, reverse=True)[:10]],
        "total_words": words, "total_repeated_words": repeated,
        "per_page": per_page
    }


def audit():
    cities = json.loads((ROOT / "city-data.json").read_text())
    cities = [c for c in cities if c.get("publishStatus") == "published"]
    names = sorted({c["city"].lower() for c in cities}, key=len, reverse=True)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in names) +
                         r")(?!\w)", re.I)
    corpus = {c["slug"]: (PUBLIC / f"hospice-{c['slug']}-ca.html").read_text()
              for c in cities}
    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_count": len(corpus),
        "scope": "All published local landing pages in city-data.json; county hub excluded",
        "method": {
            "phrase_length_words": SHINGLE_SIZE,
            "city_names_normalized": True,
            "primary": "Percent of main-content word positions belonging to an exact "
                       "eight-word phrase also present on at least one OTHER local page. "
                       "Word-weighted across the fixed corpus; overlapping matches "
                       "count each word once. Excludes navigation, footer, scripts, "
                       "styles, shared credential labels and CTA button text.",
            "secondary": "Same repeated-word measure on all visible page text, "
                         "including navigation and footer.",
            "pairwise": "Eight-word set Jaccard intersection/union across every pair",
            "caveat": "Local text-overlap audit, not a Siteliner score, plagiarism score "
                      "or a Google ranking/quality measurement."
        },
        "main_content": summarize({s: tokens(p, True, pattern) for s, p in corpus.items()}),
        "full_visible_page": summarize({s: tokens(p, False, pattern) for s, p in corpus.items()})
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("page_count", "scope")}, indent=2))
    for scope in ("main_content", "full_visible_page"):
        print(scope, result[scope]["word_weighted_redundancy_percent"],
              "% repeated-word coverage;",
              result[scope]["average_pairwise_jaccard_percent"], "% average Jaccard")


if __name__ == "__main__":
    main()