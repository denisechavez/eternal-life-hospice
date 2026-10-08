#!/usr/bin/env python3
"""Build private 101-term coverage/review assets without changing public articles."""
import base64
import csv
import hashlib
import html
import io
import json
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "exports/site-audits/seo-keyword-stage-one-2026-10-08"
OUTPUT = ROOT / "exports/site-audits/seo-keyword-101-2026-10-08"
CONTENT = ROOT / "website/content"
PUBLIC = ROOT / "website/elh-preview"
NEW = [
    (97, "Hospice Thousand Oaks CA", "Hospice selection and evaluation"),
    (98, "Hospice Care Services Thousand Oaks CA", "Interdisciplinary services and care-plan boundaries"),
    (99, "Hospice Agency Thousand Oaks CA", "Provider selection and address-level availability"),
    (100, "Hospice Nursing Services Thousand Oaks CA", "Nursing assessment, visit planning and 24/7 on-call support"),
    (101, "Home Hospice Care Thousand Oaks CA", "Care at home, caregiver responsibilities and visit boundaries"),
]
CYCLES = [
    ("C1", "2026-10-08", "2026-11-06"),
    ("C2", "2026-11-07", "2026-12-06"),
    ("C3", "2026-12-07", "2026-12-31"),
]


def read_csv(name):
    with (BASELINE / name).open(newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "main":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def main_text(source):
    parser = MainText()
    parser.feed(source)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).casefold()


def inline(text):
    # Drafts accept only local, existing destinations.
    result, pos = [], 0
    for match in re.finditer(r"\[([^\]]+)\]\((/[^)\s]+)\)", text):
        result.append(html.escape(text[pos:match.start()]))
        target = match[2]
        assert not target.startswith("//")
        assert (PUBLIC / (target.lstrip("/") + ".html")).is_file(), target
        result.append(f'<a class="elh-inline-link" href="{html.escape(target)}">{html.escape(match[1])}</a>')
        pos = match.end()
    return "".join(result) + html.escape(text[pos:])


def channels():
    """Unique recurring draft treatments, not scheduled/sendable campaigns."""
    angles = [
        ("C1", "2026-10-08", "Start with the first conversation", [
            "Hospice in Thousand Oaks: Start With the Household, Not a Checklist",
            "Hospice Care Services in Thousand Oaks: Ask Who Does What",
            "Choosing a Hospice Agency in Thousand Oaks: Five First-Call Questions",
            "Hospice Nursing Services in Thousand Oaks: What Happens During a Visit?",
            "Home Hospice Care in Thousand Oaks: Who Is There Between Visits?",
        ]),
        ("C2", "2026-11-07", "Plan visits around the person", [
            "Thousand Oaks Hospice Questions Before Holiday Visitors Arrive",
            "Thousand Oaks Hospice Care Services: Protect Quiet Time",
            "Talk With Your Thousand Oaks Hospice Agency Before Travel Plans Change",
            "Thousand Oaks Hospice Nursing: Bring One Clear Question List",
            "Home Hospice in Thousand Oaks: Visitors Are Not a Caregiving Plan",
        ]),
        ("C3", "2026-12-07", "Review changing needs", [
            "Hospice in Thousand Oaks: Questions to Carry Into a New Year",
            "Reviewing Hospice Care Services in Thousand Oaks as Needs Change",
            "Thousand Oaks Hospice Agency Questions When the Main Caregiver Changes",
            "Hospice Nursing in Thousand Oaks: When to Ask About Visit Changes",
            "Thousand Oaks Home Hospice Care: Review the Hours Between Visits",
        ]),
    ]
    explanations = [
        "Share the person’s wishes, home address and household needs on the first call. A conversation can clarify options; it is not automatic admission or an eligibility decision.",
        "Ask about the clinical team, practical support and how the individualized plan is reviewed. Optional sound bathing and a death doula do not replace nursing care; request details about consent, availability and any arrangements.",
        "Ask who coordinates care, how availability is confirmed for the actual address and whom to call after hours. A city name alone does not confirm admission or capacity.",
        "Ask what the nurse will assess, what caregivers will be taught and how visits can change with assessed needs. 24/7 on-call support is not continuous bedside nursing or a guaranteed immediate visit.",
        "Routine home hospice works alongside the household’s caregiving plan. Identify who is present between visits and keep the team’s individualized clinical and emergency instructions accessible.",
    ]
    social, pins, videos = [], [], []
    for cycle, start, theme, titles in angles:
        for i, title in enumerate(titles):
            term = NEW[i]
            shared = {"cycle": cycle, "keywordIds": [term[0]], "keywordPhrase": term[1],
                      "status": "Draft — not approved, posted or scheduled"}
            social.append({**shared, "title": title,
                           "copy": f"{theme}. {explanations[i]} Personalized support begins with listening, not a standard script.",
                           "link": "https://eternallifehospice.com/services"})
            pins.append({**shared, "title": title, "description": f"A practical question guide for families in Thousand Oaks, California. {explanations[i]}",
                         "destination": "https://eternallifehospice.com/family-guide",
                         "imageNote": "Use an existing licensed, approved photograph; no new image or change to original photography."})
            videos.append({**shared, "title": title, "description": explanations[i] + " Learn more: https://eternallifehospice.com/services",
                           "spokenScript": f"{title} {explanations[i]} Start with the person’s wishes. Ask the hospice team how the plan fits your household."})
    emails = []
    first = date(2026, 10, 12)
    for week in range(12):
        proposed = first + timedelta(days=7 * week)
        cycle = next(c for c, start, end in CYCLES if start <= proposed.isoformat() <= end)
        title = angles[int(cycle[-1]) - 1][3][week % 5]
        # Each draft has a different prompt and practical action; no recipient,
        # list, campaign ID, send time or delivery request is created here.
        prompt = [
            "Write down the two questions you want answered before an evaluation.",
            "Choose the person who can keep the family’s question list current.",
            "Check that the after-hours number is easy for caregivers to find.",
            "Ask how changes in comfort or symptoms should be described to the nurse.",
            "Review who can stay with the person between scheduled visits.",
            "Agree on how visitors can respect the person’s privacy and preferences.",
            "Ask whether caregiver teaching needs to be refreshed before a busy week.",
            "Make sure an approved family contact knows where the care instructions are.",
            "Tell the team if household routines or caregiver availability have changed.",
            "Ask what nursing observations should be shared at the next visit.",
            "Review the care plan’s emergency instructions with the household.",
            "Bring your updated questions to the team without assuming benefits change on January 1.",
        ][week]
        copy = f"{explanations[week % 5]} {prompt} For families seeking hospice nursing services or home hospice care in Thousand Oaks, California, the goal is a plan that reflects the person’s wishes and the household’s real circumstances. Personalization starts on the first call; clinical arrangements and eligibility require individual review."
        raw = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#f5f0eb;font-family:Arial,sans-serif;color:#381b37"><table role="presentation" style="max-width:600px;width:100%;margin:auto;background:#fff"><tr><td style="background:#381b37;color:#c9b07e;padding:24px">ETERNAL LIFE HOSPICE · WEEKLY DRAFT</td></tr><tr><td style="padding:28px"><h1 style="font-size:25px">{html.escape(title)}</h1><p style="line-height:1.7">{html.escape(copy)}</p><p><a href="https://eternallifehospice.com/services">Explore hospice services</a> · <a href="https://eternallifehospice.com/family-guide">Open the Family Guide</a></p><p style="font-size:12px">Draft for Studio review only. This is not a queued or scheduled campaign. Services depend on the individual care plan and eligibility.</p><p><a href="{{{{ unsubscribe }}}}">Unsubscribe</a></p></td></tr></table></body></html>"""
        emails.append({"html": raw, "plainText": title + "\n\n" + copy + "\n\nhttps://eternallifehospice.com/services\nUnsubscribe: {{ unsubscribe }}",
                       "subject": title, "preheader": prompt, "sendDate": proposed.isoformat(),
                       "dateMeaning": "Proposed editorial week only; not a send schedule",
                       "framework": "journal-draft", "keywordIds": [100, 101, NEW[week % 5][0]],
                       "seoRevision": hashlib.sha256(raw.encode()).hexdigest()[:12]})
    return {"social": social, "pinterest": pins, "shortVideo": videos, "weeklyEmail": emails}


def build():
    fields, original_rows = read_csv("keyword-coverage-96.csv")
    _, inventory = read_csv("article-inventory.csv")
    assert len(original_rows) == 288
    assert len(inventory) == 107
    by_slug = {row["Slug"]: row for row in inventory}
    master = [
        {"id": int(row["Keyword ID"]), "phrase": row["Keyword phrase"],
         "source": "Google Ads — original audit", "intent": row["Intent"],
         "geography": row["Geographic target"],
         "priority": "Primary" if "thousand oaks" in row["Geographic target"].casefold() else "Existing strategy",
         "cycles": [{"cycle": r["Cycle"], "baselineCandidates": int(r["Topic/variation candidate count"]),
                     "confirmation": r["Meaningful coverage"]} for r in original_rows if r["Keyword ID"] == row["Keyword ID"]],
         "draftDates": []}
        for row in original_rows if row["Cycle"] == "C1"
    ]
    spec = json.loads((CONTENT / "seo-thryv-drafts.json").read_text())
    drafts, public_hashes = {}, {}
    for entry in spec["articles"]:
        original = (PUBLIC / "blog" / (entry["slug"] + ".html")).read_text()
        public_hashes[entry["slug"]] = hashlib.sha256(original.encode()).hexdigest()
        addition = "\n".join(
            f'<h2>{html.escape(section["heading"])}</h2>\n' +
            "\n".join(f"<p>{inline(p)}</p>" for p in section["paragraphs"])
            for section in entry["sections"]
        )
        # Preserve every original byte, photograph and date. The generated
        # reader document is private and not read by the public builder.
        assert original.count("</article>") == 1
        article_start, article_end = original.index("<article"), original.index("</article>")
        headings = list(re.finditer(r"<h2\b", original[article_start:article_end]))
        assert len(headings) >= 2
        # Put new paragraphs in the article's content flow, after the first
        # existing section—not in a footer, related-links block or disclosure.
        position = article_start + headings[1].start()
        draft_html = original[:position] + addition + "\n" + original[position:]
        link_count = len(re.findall(r'<a[^>]+class="elh-inline-link"', draft_html))
        assert 2 <= link_count <= 7, (entry["slug"], link_count)
        revision = hashlib.sha256(draft_html.encode()).hexdigest()[:12]
        drafts[entry["slug"]] = {**entry, "revision": revision, "reviewHtml": draft_html,
                                "date": by_slug[entry["slug"]]["Publication date"]}
    placements = sorted(d["date"] for d in drafts.values() if set(d["keywordIds"]) == set(range(97, 102)))
    assert placements == ["2026-10-24", "2026-11-15", "2026-12-04", "2026-12-27"]
    new_rows = []
    for keyword_id, phrase, intent in NEW:
        master.append({"id": keyword_id, "phrase": phrase, "source": "Thryv — user-supplied keyword",
                       "intent": intent, "geography": "Thousand Oaks, California", "priority": "Primary",
                       "draftDates": placements, "cycles": []})
        for cycle, start, end in CYCLES:
            window = [r for r in inventory if start <= r["Publication date"] <= end]
            exact = [r for r in window if phrase.casefold() in main_text((PUBLIC / "blog" / (r["Slug"] + ".html")).read_text())]
            cycle_drafts = [d for d in drafts.values() if start <= d["date"] <= end and keyword_id in d["keywordIds"]]
            row = dict.fromkeys(fields, "")
            row.update({"Cycle": cycle, "Cycle start": start, "Cycle end": end,
                        "Keyword ID": keyword_id, "Keyword phrase": phrase, "Intent": intent,
                        "Geographic target": "Thousand Oaks, California", "Exact article count": len(exact),
                        "Exact locations": "Main content" if exact else "",
                        "Exact articles": "; ".join(r["Canonical URL"] for r in exact),
                        "Topic/variation candidate count": "", "Topic candidates": "",
                        "Meaningful coverage": "Public natural-coverage review pending; private draft prepared",
                        "Next proposed coverage date": min(d["date"] for d in cycle_drafts),
                        "Confirmed meaningful coverage count": "Unconfirmed",
                        "Last confirmed meaningful coverage date": "Unconfirmed",
                        "Draft article count": len(cycle_drafts),
                        "Draft articles": "; ".join(f'{d["date"]} {by_slug[d["slug"]]["Title"]}' for d in cycle_drafts),
                        "Draft status": "Private draft; not approved or published",
                        "Source": "Thryv keyword (not ranking data)"})
            new_rows.append(row)
            master[-1]["cycles"].append({"cycle": cycle, "baselineExactArticles": len(exact),
                                       "baselineCandidates": None, "draftArticles": len(cycle_drafts),
                                       "confirmation": "Private draft; meaningful coverage not approved"})
    all_fields = fields + ["Draft article count", "Draft articles", "Draft status", "Source"]
    current_rows = [{**dict.fromkeys(all_fields, ""), **row} for row in original_rows] + new_rows
    csv_data = csv_bytes(all_fields, current_rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "keyword-coverage-101.csv").write_bytes(csv_data)
    mapping_fields, mapping_rows = read_csv("three-cycle-proposed-mapping.csv")
    for row in new_rows:
        candidates = sorted(
            (d for d in drafts.values() if row["Cycle start"] <= d["date"] <= row["Cycle end"]
             and row["Keyword ID"] in d["keywordIds"]), key=lambda d: d["date"])
        chosen = candidates[0]
        mapping = dict.fromkeys(mapping_fields, "")
        mapping.update({"Cycle": row["Cycle"], "Keyword ID": row["Keyword ID"],
                        "Keyword phrase": row["Keyword phrase"], "Intent": row["Intent"],
                        "Geographic target": row["Geographic target"],
                        "Designation": "Secondary intent support; preserve existing educational purpose",
                        "Existing date": chosen["date"],
                        "Existing article": by_slug[chosen["slug"]]["Title"],
                        "Existing URL": by_slug[chosen["slug"]]["Canonical URL"],
                        "Status": "Private draft prepared; not approved or scheduled",
                        "Meaningful coverage confirmed": "Not confirmed; complete Studio review required"})
        mapping_rows.append(mapping)
    (OUTPUT / "three-cycle-proposed-mapping-101.csv").write_bytes(csv_bytes(mapping_fields, mapping_rows))
    rolling = []
    for offset in range(56):
        start = date(2026, 10, 8) + timedelta(days=offset)
        end = start + timedelta(days=29)
        included = [d for d in placements if start.isoformat() <= d <= end.isoformat()]
        assert included, (start, end)
        rolling.append({"Window start": start.isoformat(), "Window end": end.isoformat(),
                        "New keyword IDs": "97–101", "Draft placements": "; ".join(included),
                        "Status": "Planned coverage only; approval and release required",
                        "Ranking improvement": "Not measured"})
    (OUTPUT / "rolling-new-terms.csv").write_bytes(csv_bytes(list(rolling[0]), rolling))
    history = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in BASELINE.iterdir() if p.is_file()}
    channel_drafts = channels()
    write_json(CONTENT / "seo-keyword-master.json", {"termCount": 101, "keywords": master,
               "baselineAudit": str(BASELINE.relative_to(ROOT)), "baselineHashes": history,
               "rankingStatus": "No dated Thryv ranking observations supplied; coverage is not ranking performance."})
    write_json(CONTENT / "seo-private-review.json", {"articles": drafts, **channel_drafts})
    write_json(OUTPUT / "provenance.json", {"originalAuditHashes": history, "publicArticleHashes": public_hashes,
               "status": "Private revisions only; public sources and release controls unchanged",
               "newKeywordIds": list(range(97, 102))})
    # Ranking observations belong in a different file and remain unavailable.
    ranking_fields = ["Keyword ID", "Keyword", "Observed date", "Rank", "Search engine/device/location", "Status"]
    ranking_path = OUTPUT / "thryv-ranking-observations.csv"
    if not ranking_path.exists():
        # Never overwrite later ranking imports when refreshing coverage.
        ranking_path.write_bytes(csv_bytes(ranking_fields, [
            {"Keyword ID": i, "Keyword": phrase, "Observed date": "", "Rank": "",
             "Search engine/device/location": "", "Status": "Awaiting dated Thryv data; no improvement claimed"}
            for i, phrase, _ in NEW]))
    esc = html.escape
    keyword_table = "".join(f"<tr><td>{k['id']}</td><td>{esc(k['phrase'])}</td><td>{esc(k['source'])}</td><td>{esc(k['intent'])}</td></tr>" for k in master)
    article_blocks = "".join(f"<section><h3>{esc(by_slug[slug]['Title'])} · {d['date']}</h3>" +
        "".join(f"<h4>{esc(s['heading'])}</h4>" + "".join(f"<p>{inline(p)}</p>" for p in s["paragraphs"]) for s in d["sections"]) +
        "</section>" for slug, d in drafts.items())
    channel_blocks = "".join("<h2>" + esc(name) + "</h2>" + "".join(
        "<section><h3>" + esc(item.get("title", item.get("subject", ""))) + "</h3><p>" +
        esc(item.get("copy", item.get("description", item.get("plainText", "")))) +
        "</p><small>" + esc(item.get("cycle", item.get("sendDate", ""))) + " · Draft, not scheduled</small></section>"
        for item in items) for name, items in channel_drafts.items())
    report = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>101-Term SEO Update — Private Draft Review</title><style>body{{font:16px/1.65 Arial,sans-serif;color:#381b37;background:#f5f0eb;margin:0}}main{{max-width:1100px;margin:auto;padding:38px}}section{{background:white;padding:24px;margin:20px 0;border-left:4px solid #c9b07e}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}a{{color:#533054}}h1,h2{{line-height:1.25}}.notice{{background:#eee2f2;padding:20px}}summary{{cursor:pointer;font-weight:bold}}</style></head><body><main><h1>101-Term SEO Master Update</h1><p class="notice">PRIVATE DRAFT REVIEW · No article, photograph, publication date, URL or publishing control changed. No content posted, campaign sent or deployment performed.</p><p>IDs 1–96 and the original audit remain intact. IDs 97–101 are Thryv-supplied search phrases; no ranking observations were supplied.</p><h2>Recurring coverage</h2><p>Five private article revisions focus on nursing assessments, individualized visits, the difference between 24/7 on-call support and continuous bedside care, household responsibilities and first-call personalization. Four Thousand Oaks placements—October 24, November 15, December 4 and December 27—span every one of the 56 full rolling windows and the final partial cycle, if these versions receive approval and are released. This is planned natural-intent coverage, not exact-phrase completion or verified publication.</p><p>The original 96-term gaps remain open. This update does not approve the broader Stage Two plan.</p><p><a download="keyword-coverage-101.csv" href="data:text/csv;base64,{base64.b64encode(csv_data).decode()}">Download the 303-row coverage tracker</a></p><details><summary>All 101 keyword IDs and sources</summary><table><tr><th>ID</th><th>Phrase</th><th>Source</th><th>Intent</th></tr>{keyword_table}</table></details><h2>Existing-article draft additions</h2>{article_blocks}{channel_blocks}<h2>Release and measurement boundaries</h2><p>Studio review is required. Workspace approval indicators are not an authoritative publisher. Existing date-based release controls have not been modified. The requested persistent approval enforcement, 6:30 a.m. release and failure alerts remain outstanding work. Thryv rankings must be imported as dated observations with query, location and device context in the separate ranking file; keyword inclusion does not demonstrate ranking improvement.</p></main></body></html>"""
    # Report-local links point to canonical public destinations, never file paths.
    report = re.sub(r'href="(/[^"]+)"', r'href="https://eternallifehospice.com\1"', report)
    (OUTPUT / "101-term-update-and-channel-drafts.html").write_text(report)
    assert len(master) == 101 and {k["id"] for k in master} == set(range(1, 102))
    assert len(current_rows) == 303
    for path, digest in history.items():
        assert hashlib.sha256((BASELINE / path).read_bytes()).hexdigest() == digest
    for slug, digest in public_hashes.items():
        assert hashlib.sha256((PUBLIC / "blog" / (slug + ".html")).read_bytes()).hexdigest() == digest
    print("101 IDs; 303 keyword-cycle rows; 56 planned rolling windows; original audit/public articles unchanged.")
    print("Private review: 5 articles, 15 social drafts, 15 Pins, 15 video drafts, 12 weekly email drafts.")


if __name__ == "__main__":
    build()
