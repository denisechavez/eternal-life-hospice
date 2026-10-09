#!/usr/bin/env python3
"""Verify private review coverage, source safety and complete article documents."""
import csv
import html
import json
import re
from pathlib import Path
from datetime import timedelta, date
from journal_seo_review_tools import content_links, core, heading, hero, sha

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT/"website/content"
PUBLIC = ROOT/"website/elh-preview"
OUTPUT = ROOT/"exports/site-audits/journal-seo-optimization"
audit = json.loads((OUTPUT/"quality-audit.json").read_text())
review = json.loads((CONTENT/"seo-journal-review.json").read_text())
master = json.loads((CONTENT/"seo-keyword-master.json").read_text())
originals = {slug:(PUBLIC/"blog"/(slug+".html")).read_text() for slug in audit["publicArticleHashes"]}
documents = {slug:review["articles"].get(slug, {}).get("reviewHtml", source) for slug,source in originals.items()}


def schemas(source):
    result = []
    for text in re.findall(r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',source,re.S):
        def visit(value):
            if isinstance(value,list):
                for item in value:
                    visit(item)
            elif isinstance(value,dict):
                if any(k in value.get("@type", []) for k in ("Article","BlogPosting")):
                    result.append(value)
                if "@graph" in value:
                    visit(value["@graph"])
        visit(json.loads(text))
    return result


def meta(source, field):
    match = re.search(r'<meta (?:name|property)="'+field+r'" content="([^"]*)"',source)
    assert match, field
    return html.unescape(match[1])


assert len(documents) == 107 and set(review["articles"]) <= set(originals)
assert len(master["keywords"]) == 101
assert [k["id"] for k in master["keywords"]] == list(range(1,102))
assert not audit["beforeSimilarityPairs"] and not audit["afterSimilarityPairs"]
titles, descriptions = set(), set()
for slug, document in documents.items():
    original = originals[slug]
    assert sha(original) == audit["publicArticleHashes"][slug], slug
    assert heading(document) == heading(original), slug
    assert hero(document) == hero(original), slug
    assert len(re.findall(r"<h1\b",document)) == 1
    assert re.search(r'<link rel="canonical"[^>]*>',document)[0] == re.search(r'<link rel="canonical"[^>]*>',original)[0]
    before, after = schemas(original), schemas(document)
    assert len(before) == len(after) == 1, slug
    # Description can change, but identity, dates, author, publisher and image cannot.
    assert {k:v for k,v in before[0].items() if k != "description"} == {
        k:v for k,v in after[0].items() if k != "description"}, slug
    assert meta(document,"description") == meta(document,"og:description") == meta(document,"twitter:description")
    assert meta(document,"description") == after[0]["description"]
    title = html.unescape(re.search(r"<title>(.*?)</title>",document,re.S)[1])
    description = meta(document,"description")
    assert title not in titles and description not in descriptions, slug
    titles.add(title)
    descriptions.add(description)
    assert 2 <= len(content_links(document)) <= 5, slug
    for target, anchor in content_links(document):
        check = audit["checkedLinks"][target]
        assert check["status"] == 200 and check["main"] and check["fragmentOK"], (slug,target)
        assert anchor.strip() and anchor.casefold() not in ("click here","read more","learn more")
        if target.startswith("/blog/"):
            destination = target.removeprefix("/blog/")
            assert schemas(originals[destination])[0]["datePublished"][:10] <= audit["asOf"]
    draft = review["articles"].get(slug)
    if draft:
        assert draft["revision"] == sha(document)[:12]
        for section in draft["sections"]:
            assert document.count("<h2>"+html.escape(section["heading"])+"</h2>") == 1, (slug,section["heading"])
    # Original body words remain in order; link unwrapping never removes prose.
    remaining = iter(core(document).split())
    assert all(any(word == candidate for candidate in remaining) for word in core(original).split()), slug

for relative, digest in audit["preservedHistoryHashes"].items():
    assert sha((ROOT/relative).read_bytes()) == digest, relative
assert len(review["weeklyEmail"]) == 12
old = json.loads((CONTENT/"seo-private-review.json").read_text())
assert [e["sendDate"] for e in review["weeklyEmail"]] == [e["sendDate"] for e in old["weeklyEmail"]]
assert len({e["subject"] for e in review["weeklyEmail"]}) == 12
for email in review["weeklyEmail"]:
    assert email["seoRevision"] == sha(email["html"])[:12]
    assert html.escape(email["subject"]) in email["html"]
    assert "{{ unsubscribe }}" in email["html"] and "{{ unsubscribe }}" in email["plainText"]
    assert email["journalSlug"] in documents
    assert email["journalTitle"] == heading(documents[email["journalSlug"]])
    if schemas(originals[email["journalSlug"]])[0]["datePublished"][:10] > audit["asOf"]:
        assert not re.search(r'href="https://eternallifehospice.com/blog/', email["html"]), "Future companion must not be linked"
    assert email["status"].startswith("Draft")
    assert email["plainText"].split("\n\n")[1] in html.unescape(email["html"])
assert len(list(csv.DictReader((OUTPUT/"keyword-coverage-101-optimized.csv").open()))) == 303
rolling = list(csv.DictReader((OUTPUT/"rolling-keyword-coverage-101.csv").open()))
assert len(rolling) == 56
for r in rolling:
    assert date.fromisoformat(r["Window end"]) - date.fromisoformat(r["Window start"]) == timedelta(days=29)
print("PASS: all 107 full documents; 2–5 verified contextual links; 101 IDs; 303 coverage rows; 56 rolling windows; 12 aligned drafts; public/history/paused sources unchanged.")
