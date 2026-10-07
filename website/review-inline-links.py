#!/usr/bin/env python3
"""Editorial workbench: propose exact-passage annotations and export review sheets.

Only an explicitly written map is used by the site. Inspect the proposal report
before applying it; new or changed paragraphs never get automatic keyword links.
"""
import argparse
import csv
import html
import json
import re
from pathlib import Path

from inline_links import MAP, ProseParser, destination, link_budget
from internal_links import BASE, inventory, today

# Topic-owner vocabulary, used only to prepare a reviewed editorial proposal.
TOPICS = [
    ("/resources/medicare-hospice-benefit", ["Medicare hospice benefit", "Medicare Hospice Benefit",
      "Medicare coverage", "hospice coverage", "what it covers", "covered hospice services"]),
    ("/resources/how-to-choose-a-hospice", ["how to choose a provider", "choosing a hospice",
      "choose a hospice", "hospice provider"]),
    ("/sound-bath", ["sound bathing", "sound baths", "sound bath", "Sound bath", "Sound Bath"]),
    ("/resources/pain-symptom-management", ["pain and symptom management", "symptom management",
      "pain management", "comfort medications", "managing symptoms"]),
    ("/resources/comfort-therapies", ["integrative comfort therapies", "integrative therapies",
      "integrative wellness", "whole-person care", "whole-person approach", "comfort therapies",
      "end-of-life doula", "death doula", "doula support", "music therapy"]),
    ("/resources/first-48-hours", ["first 48 hours", "first hospice visit", "starting hospice",
      "start hospice", "first visit", "care plan", "plan of care"]),
    ("/services", ["skilled medical care", "clinical services", "hospice team",
      "nursing care", "clinical team", "coordinated care", "care team"]),
    ("/hospice-care", ["hospice care", "hospice eligibility", "hospice evaluation",
      "hospice assessment", "hospice support"]),
    ("/family-guide", ["Family Guide", "family guide"]),
    ("/resources", ["caregiver support", "family caregivers", "grief support",
      "bereavement support", "guidance for families"]),
    ("/hospice-ventura-and-los-angeles-county-ca", ["Ventura and Los Angeles Counties",
      "Ventura and Los Angeles counties", "Ventura County and Los Angeles County",
      "Ventura and Los Angeles County", "service area"]),
    ("/resources/volunteer", ["hospice volunteers", "volunteer support",
      "volunteer companionship", "volunteer program"]),
    ("/about/aleksandra-dubina", ["Aleksandra Dubina", "our founder"]),
    ("/refer#referral-form", ["send a referral", "patient referral", "referral process"]),
]
UTILITY = {"/privacy-policy", "/terms", "/sitemap", "/referral-card"}
# Passage choices for short/editorial pages whose relevant language is not a
# service keyword. These connect concepts without adding claims or new copy.
PASSAGES = {
    "/blog": [("guidance", "/resources"),
              ("families walking the hospice road", "/family-guide")],
    "/": [("hospice care", "/hospice-care"),
          ("Advanced symptom management", "/resources/pain-symptom-management"),
          ("end-of-life doula support", "/resources/comfort-therapies"),
          ("sound bath sessions", "/sound-bath")],
    "/resources": [("step-by-step hospice guidance", "/hospice-care")],
    "/resources/first-48-hours": [("begin hospice", "/hospice-care"),
                                 ("Medications tied to comfort", "/resources/pain-symptom-management")],
    "/resources/back-to-the-earth": [("real comfort", "/resources/comfort-therapies"),
                                     ("Care that honors life", "/hospice-care")],
    "/resources/when-is-it-time": [("Choosing hospice", "/resources/how-to-choose-a-hospice"),
                                   ("Eligibility is reviewed", "/hospice-care")],
    "/resources/the-circle-around-you": [("trained volunteers", "/resources/volunteer")],
    "/resources/volunteer": [("hospice volunteers", "/volunteer"),
                             ("a tired caregiver", "/family-guide")],
    "/volunteer": [("hospice care", "/hospice-care"),
                    ("Volunteers", "/resources/volunteer")],
    "/sound-bath": [("rest, comfort and quiet presence", "/resources/comfort-therapies"),
                    ("wherever home is", "/hospice-care")],
    "/blog/music-at-the-bedside": [("other gentle comforts woven into care", "/resources/comfort-therapies"),
                                   ("the natural world", "/resources/back-to-the-earth")],
    "/blog/talking-with-children-when-a-loved-one-is-seriously-ill": [
        ("Guidance for one of the hardest conversations a family faces", "/family-guide"),
        ("help them grieve", "/resources/the-circle-around-you")],
    "/hospice-ventura-and-los-angeles-county-ca": [
        ("same core benefit", "/resources/medicare-hospice-benefit")],
    "/media-kit": [("Integrative modalities", "/resources/comfort-therapies")],
    "/blog/hospice-care-in-moorpark-what-to-know": [
        ("Medicare’s hospice benefit", "/resources/medicare-hospice-benefit"),
        ("the first call", "/resources/first-48-hours"),
        ("Moorpark families", "/hospice-moorpark-ca")],
}


def propose():
    allpages, eligible = inventory("9999-12-31"), inventory()
    pages, rows, summary = {}, [], []
    for route, (_, text, _) in sorted(allpages.items()):
        if route in UTILITY:
            continue
        parser = ProseParser(text, route)
        count = sum(len(b["links"]) for b in parser.blocks)
        words = sum(len(b["text"].split()) for b in parser.blocks)
        # Relevance is more important than hitting a quota. Existing adequate links stay.
        target_count = 2 if words < 500 else 4 if words < 1000 else 5
        target_count = max(target_count, min(count, 7))
        annotations = []
        seen = {a["target"] for b in parser.blocks for a in b["links"]}
        used_blocks = set()
        candidates = []
        for href, phrases in TOPICS:
            target = destination(route, href)
            if target not in eligible or target in seen:
                continue
            for block_index, block in enumerate(parser.blocks):
                for phrase_index, phrase in enumerate(phrases):
                    for node in block["nodes"]:
                        match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                                          node["raw"], re.I)
                        if match:
                            candidates.append((block_index, phrase_index, href, match.group(),
                                               block["signature"], block["text"]))
                            break
                    else:
                        continue
                    break
        # Spread links through the copy, with one per paragraph whenever possible.
        for spread in [True, False]:
            for block_index, rank, href, phrase, key, paragraph in sorted(candidates):
                target = destination(route, href)
                if count + len(annotations) >= target_count:
                    break
                if target in seen or (spread and key in used_blocks):
                    continue
                annotation = {"paragraph": key, "phrase": phrase, "href": href,
                              "context": paragraph}
                annotations.append(annotation)
                rows.append([route, words, count, phrase, href, paragraph])
                seen.add(target)
                used_blocks.add(key)
        # The approved example links these two phrases in the Hospice Care introduction.
        if route == "/hospice-care":
            intro = next(b for b in parser.blocks if b["text"].startswith("Clear answers on when hospice begins"))
            annotations = [{"paragraph": intro["signature"], "phrase": phrase, "href": href,
                            "context": intro["text"]} for phrase, href in [
                ("what it covers", "/resources/medicare-hospice-benefit"),
                ("how to choose a provider", "/resources/how-to-choose-a-hospice")]]
            rows = [r for r in rows if r[0] != route]
            rows += [[route, words, count, a["phrase"], a["href"], a["context"]] for a in annotations]
        if route in PASSAGES and (count < 2 or route == "/"):
            if route in {"/", "/blog", "/volunteer", "/resources/volunteer"}:
                annotations = []
                seen = {a["target"] for b in parser.blocks for a in b["links"]}
                rows = [r for r in rows if r[0] != route]
            for phrase, href in PASSAGES[route]:
                if destination(route, href) in seen or count + len(annotations) >= 7:
                    continue
                block = next((b for b in parser.blocks
                              if any(phrase in node["raw"] for node in b["nodes"])), None)
                if block is None:
                    raise ValueError(f"Reviewed phrase changed: {route}: {phrase}")
                annotations.append({"paragraph": block["signature"], "phrase": phrase,
                                    "href": href, "context": block["text"]})
                rows.append([route, words, count, phrase, href, block["text"]])
                seen.add(destination(route, href))
        if annotations:
            pages[route] = annotations
        summary.append([route, words, count, len(annotations),
                        min(count, link_budget(route, words)) + len(annotations),
                        "current" if route in eligible else "scheduled"])
    return {"description": "Reviewed exact-passage contextual links; never blanket keyword replacement.",
            "pages": pages}, rows, summary


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--propose", action="store_true")
    cli.add_argument("--write-map", action="store_true")
    args = cli.parse_args()
    root = BASE / "reports" / "inline-links"
    root.mkdir(parents=True, exist_ok=True)
    if args.propose or args.write_map:
        data, rows, summary = propose()
        (root / "proposal.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        for name, header, values in [
            ("proposal.csv", ["Page", "Copy words", "Existing inline links", "Anchor phrase", "Destination", "Existing paragraph"], rows),
            ("coverage.csv", ["Page", "Copy words", "Before", "Proposed additions", "After", "Publication"], summary)]:
            with (root / name).open("w", newline="") as f:
                writer = csv.writer(f); writer.writerow(header); writer.writerows(values)
        if args.write_map:
            if MAP.exists():
                raise SystemExit("Do not overwrite the reviewed map. Inspect proposals and edit the existing map explicitly.")
            MAP.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"Proposed {len(rows)} inline links across {len(data['pages'])} pages.")
        print("Pages with fewer than two:")
        for row in summary:
            if row[4] < 2:
                print(row)


if __name__ == "__main__":
    main()
