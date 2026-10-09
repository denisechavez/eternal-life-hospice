#!/usr/bin/env python3
"""Prepare private Journal/email SEO revisions; never publish or alter public files."""
import argparse
import csv
import html
import io
import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from journal_seo_review_tools import (
    article, attrs, content_links, core, heading, hero, insert, plain,
    prune_links, sha, similarity_pairs, update_metadata, words,
)

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "website/elh-preview"
CONTENT = ROOT / "website/content"
HISTORY = ROOT / "exports/site-audits/seo-keyword-stage-one-2026-10-08"
THRYV = ROOT / "exports/site-audits/seo-keyword-101-2026-10-08"
OUTPUT = ROOT / "exports/site-audits/journal-seo-optimization"
DOMAIN = "https://eternallifehospice.com"
PRIMARY = {"Thousand Oaks", "Westlake Village", "Simi Valley", "Calabasas",
           "Camarillo", "Moorpark", "Newbury Park", "Oxnard", "Ventura", "Conejo Valley"}


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def save_csv(name, values, fields=None):
    fields = fields or list(values[0])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(values)
    (OUTPUT / name).write_text(stream.getvalue(), newline="")


def verify_url(target):
    try:
        request = urllib.request.Request(DOMAIN + target, headers={"User-Agent":"ELH-Editorial-Link-Check/1.0"})
        with urllib.request.urlopen(request, timeout=18) as response:
            source = response.read().decode()
            fragment = urlsplit(target).fragment
            fragment_ok = not fragment or bool(re.search(
                r'(?:id|name)=["\']' + re.escape(fragment) + r'["\']', source))
            return target, {"status": response.status, "final": response.url,
                            "main": "<main" in source, "fragmentOK": fragment_ok}
    except urllib.error.HTTPError as error:
        return target, {"status":error.code}
    except Exception as error:
        return target, {"status":"Unverified", "error":type(error).__name__}


def make_emails(previous, documents, public_records, checked, today):
    """Maintain the same 12 proposed weeks; change only their draft copy."""
    related = [
        "what-24-7-on-call-hospice-support-means",
        "grief-support-before-and-after-a-loss",
        "hospice-and-home-health-which-questions-clarify-the-difference",
        "camarillo-build-a-caregiving-plan-around-work-schedules",
        "sound-baths-music-and-silence-three-different-choices",
        "what-online-hospice-reviews-can-tell-youand-what-they-cannot",
        "camarillo-a-holiday-backup-plan-for-the-family-caregiver",
        "ventura-keep-care-instructions-clear-when-weather-changes-plans",
        "westlake-village-coordinate-hospice-questions-across-family-households",
        "hospice-visits-and-telephones-use-each-for-the-right-question",
        "the-winter-solstice-a-quiet-reflection-without-health-promises",
        "preparing-a-hospice-family-s-year-end-contact-and-document-check",
    ]
    subjects = [
        "Thousand Oaks nursing support: visits and calls are different",
        "Grief does not wait for a loss",
        "Hospice, home health and palliative care: ask what is covered",
        "Camarillo families: plan care around real work schedules",
        "Sound, music or quiet: comfort starts with permission",
        "Westlake Village reviews: check the agency, not just the stars",
        "Camarillo caregivers: prepare a holiday backup plan",
        "Ventura families: keep care instructions clear when plans change",
        "Westlake Village: one care plan, several family households",
        "Simi Valley and Newbury Park: use visits and calls differently",
        "A quiet winter reflection, without a health promise",
        "A year-end check of the contacts that matter",
    ]
    keyword_ids = [
        [18,23,24,97,98,99,100,101], [7,79,91], [22,35,85,89,90],
        [8,14,28,29], [7,79,81,82], [2,3,4,5,94,95,96],
        [14,28,29,91], [8,14,32], [72,76,78,91],
        [1,18,25,26,41,84], [79,81,82], [88,95],
    ]
    copy = [
        "For a Thousand Oaks household, hospice nursing services can include symptom assessment, caregiver teaching and coordination with the clinical team. Visit frequency reflects assessed needs. Ask who responds after hours and when an in-person assessment may be needed; 24/7 on-call support is not continuous bedside nursing. Personalization begins by listening to the household on the first call.",
        "Anticipatory grief can arrive alongside practical caregiving. There is no required way to feel, and families do not need to wait for a loss before asking about emotional support. This week’s Journal invites a conversation about support that respects the person and the family rather than imposing a timetable.",
        "Los Angeles County families comparing care at home should separate the service from the payer arrangement. Hospice election, home health and non-hospice palliative care are not interchangeable labels. Ask the clinician and health plan what is being proposed, who provides it and which costs may remain. Do not infer a separate Eternal palliative program from comfort-focused hospice language.",
        "A Camarillo caregiver’s workday matters to the household plan. Identify who can be present between visits, which tasks relatives can realistically take on and what teaching is needed. Professional visits and 24/7 on-call guidance do not replace an entire caregiving shift. Bring those practical details into the first conversation.",
        "A person may prefer a familiar song, an optional sound bath or no sound at all. Ask permission and respect the answer. Integrative comfort is nonclinical, does not replace licensed care and does not promise a medical outcome. Ask the team about availability and fit; Eternal covers its optional integrative offerings at no additional expense to families.",
        "A review search for Eternal Life Hospice in Westlake Village should be checked against the actual agency identity. Similar names can describe different businesses. Reviews can help you prepare communication questions, but do not prove one agency is best for every care plan. Ask how the provider explains nursing visits, address-level availability and after-hours support.",
        "Before holiday plans change, a Camarillo household can identify a backup helper, an authorized contact and the tasks each person can take on. A backup relative is not automatically a replacement for clinical care. Tell the hospice when caregiver availability changes and ask how the plan can be reviewed.",
        "For a Ventura household, a clear contact list and accessible care instructions can reduce confusion when weather changes plans. Follow local authorities’ directions and the person’s individualized clinical and emergency instructions. Ask how the team wants changes reported; a generic checklist is not a substitute for that plan.",
        "Westlake Village relatives may help from several households, but the person’s care remains anchored in one individual plan. For a parent with dementia, share familiar routines and observations with the authorized team. Agree on who receives updates and who is present between visits; more relatives do not create more authority to change prescribed care.",
        "A Simi Valley care address and a relative in Newbury Park can involve both nursing visits and telephone coordination. Use calls for authorized updates and questions, not as a substitute for a clinical assessment or hands-on help. Ask how visit needs are reviewed and how to reach on-call support without assuming round-the-clock bedside staffing.",
        "The winter solstice can be a reason for a quiet reflection, not a claim about treatment or recovery. A familiar song, a few words or silence can be enough if the person welcomes it. A death doula offers nonclinical support alongside the team; sound bathing and other comfort choices remain optional.",
        "Review the authorized contacts, document locations and questions the household wants to raise with the care team. A new calendar year does not automatically reset hospice eligibility or benefits. Personalization includes hearing changed preferences and practical needs, then asking the responsible clinicians and payer for individual guidance.",
    ]
    result = []
    for old, slug, subject, body, keywords in zip(previous, related, subjects, copy, keyword_ids):
        record = public_records[slug]
        assert record["Publication date"] <= old["sendDate"]
        target = "/blog/" + slug
        active = record["Publication date"] <= today and checked.get(target, {}).get("status") == 200
        link = DOMAIN + target if active else DOMAIN + "/services"
        label = "Read the Journal article" if active else "Explore hospice services"
        doc = old["html"]
        doc = re.sub(r"<h1\b[^>]*>.*?</h1>", lambda m: m[0].split(">",1)[0]+">"+html.escape(subject)+"</h1>", doc, count=1, flags=re.S)
        doc = re.sub(r'<p style="line-height:1\.7">.*?</p>',
                     '<p style="line-height:1.7">'+html.escape(body)+'</p>', doc, count=1, flags=re.S)
        doc = doc.replace('<p><a href="https://eternallifehospice.com/services">Explore hospice services</a>',
                          f'<p><a href="{link}">{label}</a>')
        # These are proposed editorial weeks, never an instruction to send.
        result.append({**old, "subject":subject, "preheader":subject,
                       "html":doc, "plainText":subject+"\n\n"+body+"\n\n"+link+"\nUnsubscribe: {{ unsubscribe }}",
                       "journalSlug":slug, "journalTitle":heading(documents[slug]),
                       "journalUrl":DOMAIN+target,
                       "journalLinkStatus":"Verified public" if active else "Held until Journal article is publicly available",
                       "dateMeaning":"Original proposed editorial week preserved; not a send schedule",
                       "seoRevision":sha(doc)[:12], "keywordIds":keywords,
                       "status":"Draft — fresh Studio approval required"})
    assert len(result) == 12 and [e["sendDate"] for e in result] == [e["sendDate"] for e in previous]
    return result


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    inventory = rows(HISTORY / "article-inventory.csv")
    records = {r["Slug"]:r for r in inventory}
    originals = {slug:(PUBLIC/"blog"/(slug+".html")).read_text() for slug in records}
    baseline_hashes = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [
        *HISTORY.glob("*"), *THRYV.glob("*"), CONTENT/"seo-private-review.json",
        CONTENT/"seo-thryv-drafts.json"]}
    # Audit the complete corpus BEFORE applying any editorial changes.
    before_pairs = similarity_pairs(originals)
    image_groups = {}
    for slug, source in originals.items():
        path = PUBLIC / hero(source).lstrip("/")
        image_groups.setdefault(sha(path.read_bytes()), []).append(slug)
    assert len(image_groups) == 107, "Duplicate image bytes: review before changing articles"
    before_titles = [plain(re.search(r"<title>(.*?)</title>", s, re.S)[1]) for s in originals.values()]
    assert len(set(before_titles)) == 107
    additions = load(CONTENT/"journal-seo-optimization.json")
    assert set(additions) <= set(records), "Authored additions must use existing slugs"
    seed = load(CONTENT/"seo-thryv-drafts.json")["articles"]
    sections, ids = {}, {}
    for item in seed:
        sections[item["slug"]] = item["sections"]
        ids[item["slug"]] = item["keywordIds"]
    for slug, item in additions.items():
        sections.setdefault(slug, []).append({"heading":item["heading"],"paragraphs":item["paragraphs"]})
        ids.setdefault(slug, []).extend(item["keywordIds"])
    proposed, harmonized = {}, set()
    for slug, original in originals.items():
        proposed[slug] = update_metadata(insert(original, sections.get(slug, [])),
            additions.get(slug, {}).get("seoTitle"), additions.get(slug, {}).get("description"))
        if not additions.get(slug, {}).get("description"):
            description = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', original)[1])
            variants = [html.unescape(v) for v in re.findall(
                r'<meta (?:name|property)="(?:description|og:description|twitter:description)" content="([^"]*)"', original)]
            schema_descriptions = re.findall(r'"description"\s*:\s*"([^"]*)"', original)
            if any(v != description for v in variants) or any(html.unescape(v) != description for v in schema_descriptions):
                proposed[slug] = update_metadata(proposed[slug], description=description, update_hero=False)
                harmonized.add(slug)
    future = {"/blog/"+slug for slug, r in records.items() if r["Publication date"] > today}
    targets = {target for source in proposed.values() for target, _ in content_links(source) if target not in future}
    targets.update("/blog/"+slug for slug in [
        "what-24-7-on-call-hospice-support-means", "grief-support-before-and-after-a-loss",
        "hospice-and-home-health-which-questions-clarify-the-difference",
        "camarillo-build-a-caregiving-plan-around-work-schedules",
        "sound-baths-music-and-silence-three-different-choices",
        "what-online-hospice-reviews-can-tell-youand-what-they-cannot",
        "camarillo-a-holiday-backup-plan-for-the-family-caregiver",
        "ventura-keep-care-instructions-clear-when-weather-changes-plans",
        "westlake-village-coordinate-hospice-questions-across-family-households",
        "hospice-visits-and-telephones-use-each-for-the-right-question",
        "the-winter-solstice-a-quiet-reflection-without-health-promises",
        "preparing-a-hospice-family-s-year-end-contact-and-document-check"] if "/blog/"+slug not in future)
    checked = dict(ThreadPoolExecutor(max_workers=8).map(verify_url, sorted(targets)))
    save(OUTPUT/"live-link-snapshot.json", {"asOf":today,"targets":checked})
    approved = {target for target, result in checked.items()
                if result.get("status") == 200 and result.get("main") and result.get("fragmentOK")}
    assert "/services" in approved, "Required services destination is not verified"
    revised, current, optimization, link_rows = {}, {}, [], []
    for slug, source in proposed.items():
        doc, adjustments = prune_links(source, approved, future)
        links = content_links(doc)
        assert 2 <= len(links) <= 5, (slug, links)
        assert all(target in approved and target not in future for target, _ in links)
        changed = doc != originals[slug]
        current[slug] = doc
        revision = sha(doc)[:12] if changed else ""
        if changed:
            revised[slug] = {"slug":slug, "sections":sections.get(slug, []),
                            "reviewHtml":doc, "revision":revision,
                            "description":additions.get(slug, {}).get("description", records[slug]["Meta description"]),
                            "keywordIds":sorted(set(ids.get(slug, []))), "date":records[slug]["Publication date"],
                            "qaStatus":"Mechanical checks passed; complete editorial Studio review required"}
        optimization.append({"Slug":slug,"Date":records[slug]["Publication date"],
            "Title":records[slug]["Title"],"Revision":revision or "Original retained",
            "Status":"Private revision; needs review" if changed else "Audited; unchanged",
            "Content additions":len(sections.get(slug, [])),
            "Metadata summaries":"Aligned to existing search description" if slug in harmonized else "Retained or locally strengthened",
            "Original core words":words(originals[slug]),"Revised core words":words(doc),
            "Internal links":len(links),"Hero image":hero(doc),
            "Keyword IDs strengthened":"; ".join(map(str, sorted(set(ids.get(slug, []))))),
            "Geographic references strengthened":"; ".join(city for city in sorted(PRIMARY) if city in " ".join(
                p for s in sections.get(slug, []) for p in s["paragraphs"])),
            "Link adjustments":"; ".join(adjustments)})
        link_rows.extend({"Source article":slug,"Target":target,"Anchor":anchor,
                          "Live status":200,"Checked on":today,"Future target":False} for target, anchor in links)
    assert not similarity_pairs(current), "High-overlap pair requires editorial review"
    for slug in current:
        assert heading(current[slug]) == heading(originals[slug])
        assert hero(current[slug]) == hero(originals[slug])
    previous = load(CONTENT/"seo-private-review.json")
    emails = make_emails(previous["weeklyEmail"], current, records, checked, today)
    save(CONTENT/"seo-journal-review.json", {"articles":revised,"weeklyEmail":emails,"auditDate":today})
    master = load(CONTENT/"seo-keyword-master.json")
    baseline = rows(THRYV/"keyword-coverage-101.csv")
    coverage = []
    gaps = []
    for row in baseline:
        k = int(row["Keyword ID"])
        explicit = [slug for slug in sections if k in ids.get(slug, [])
                    and row["Cycle start"] <= records[slug]["Publication date"] <= row["Cycle end"]]
        retained = [slug for slug, record in records.items()
                    if record["Title"] in row.get("Topic candidates", "")
                    and row["Cycle start"] <= record["Publication date"] <= row["Cycle end"]]
        candidates = sorted(set(explicit+retained), key=lambda slug:records[slug]["Publication date"])
        exact = [slug for slug in current if row["Cycle start"] <= records[slug]["Publication date"] <= row["Cycle end"]
                 and row["Keyword phrase"].casefold() in core(current[slug]).casefold()]
        updated = {**row,"Current draft candidate count":len(candidates),
            "Current draft candidates":"; ".join(records[s]["Publication date"]+" "+s for s in candidates),
            "Current draft exact count":len(exact),
            "Current draft confirmation":"Not confirmed; editorial review required",
            "Coverage gap":"No candidate; separate localized article/subsection approval needed" if not candidates else "",
            "Ranking impact":"Not measured"}
        coverage.append(updated)
        if not candidates:
            gaps.append({"Cycle":row["Cycle"],"Keyword ID":k,"Keyword":row["Keyword phrase"],
                         "Geography":row["Geographic target"],"Status":"Open; do not force into unrelated copy"})
        keyword = next(item for item in master["keywords"] if item["id"] == k)
        for cycle in keyword["cycles"]:
            if cycle["cycle"] == row["Cycle"]:
                cycle["confirmation"] = (str(len(candidates))+" draft candidates; approval/semantic review pending"
                                         if candidates else "Gap; separate approval needed")
        keyword["draftDates"] = sorted(set(keyword["draftDates"] + [records[s]["Publication date"] for s in candidates]))
        if keyword["geography"] in PRIMARY:
            keyword["priority"] = "Primary"
    save(CONTENT/"seo-keyword-master.json", master)
    after_titles = [plain(re.search(r"<title>(.*?)</title>", s, re.S)[1]) for s in current.values()]
    assert len(set(after_titles)) == 107
    save_csv("article-optimization-record.csv", optimization)
    save_csv("keyword-coverage-101-optimized.csv", coverage)
    rolling = []
    for offset in range(56):
        start = date(2026, 10, 8) + timedelta(days=offset)
        end = start + timedelta(days=29)
        identified = set()
        for row in coverage:
            placements = re.findall(r"\b2026-\d{2}-\d{2}\b", row["Current draft candidates"])
            if any(start.isoformat() <= day <= end.isoformat() for day in placements):
                identified.add(int(row["Keyword ID"]))
        rolling.append({"Window start":start.isoformat(),"Window end":end.isoformat(),
            "Keyword IDs with draft candidates":len(identified),
            "Uncovered keyword IDs":"; ".join(map(str, sorted(set(range(1,102))-identified))),
            "Status":"Candidate coverage only; semantic review and approved release required",
            "Ranking impact":"Not measured"})
    save_csv("rolling-keyword-coverage-101.csv", rolling)
    save_csv("remaining-keyword-gaps.csv", gaps)
    save_csv("contextual-link-audit.csv", link_rows)
    save_csv("weekly-email-journal-alignment.csv", [
        {"Proposed week":e["sendDate"],"Subject":e["subject"],"Journal article":e["journalSlug"],
         "Journal date":records[e["journalSlug"]]["Publication date"],"Article link":e["journalLinkStatus"],
         "Status":e["status"]} for e in emails])
    audit = {"asOf":today,"articleCount":107,"beforeSimilarityPairs":before_pairs,
        "afterSimilarityPairs":[],"method":"Five-word shingle Jaccard screen at 0.35, with distinct existing article purposes retained; not proof of semantic uniqueness.",
        "heroHashes":image_groups,"publicArticleHashes":{s:sha(d) for s,d in originals.items()},
        "preservedHistoryHashes":baseline_hashes,"checkedLinks":checked,
        "privateRevisionCount":len(revised),"contentAdditionCount":len(sections),
        "metadataHarmonizedCount":len(harmonized),
        "wordRange":[min(words(s) for s in current.values()),max(words(s) for s in current.values())],
        "pausedChannels":"Care Brief, social, Pinterest and video sources untouched",
        "clinicalSources":["https://www.medicare.gov/coverage/hospice-care",
                           "https://www.medicare.gov/care-compare/resources/hospice/levels-of-care",
                           "https://vcaaa.venturacounty.gov/for-older-adults/"],
        "remainingGaps":len(gaps),"publication":"No release, deployment or send authorized"}
    save(OUTPUT/"quality-audit.json", audit)
    # Original audit rows and all public article bytes remain unchanged.
    for relative, digest in baseline_hashes.items():
        assert sha((ROOT/relative).read_bytes()) == digest, relative
    for slug, digest in audit["publicArticleHashes"].items():
        assert sha((PUBLIC/"blog"/(slug+".html")).read_bytes()) == digest
    table = "".join("<tr>"+"".join("<td>"+html.escape(str(r[k]))+"</td>" for k in
        ["Date","Title","Status","Revised core words","Internal links","Keyword IDs strengthened"])+"</tr>" for r in optimization)
    gap_table = "".join("<tr>"+"".join("<td>"+html.escape(str(r[k]))+"</td>" for k in
        ["Cycle","Keyword ID","Keyword","Geography"])+"</tr>" for r in gaps)
    email_table = "".join("<tr><td>"+e["sendDate"]+"</td><td>"+html.escape(e["subject"])+
        "</td><td>"+html.escape(e["journalTitle"])+"</td><td>"+e["journalLinkStatus"]+"</td></tr>" for e in emails)
    report = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Eternal Journal — Private SEO Optimization Review</title><style>body{{font:16px/1.6 Arial;color:#381b37;background:#f5f0eb}}main{{max-width:1180px;margin:auto;padding:35px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:9px;border-bottom:1px solid #ddd;vertical-align:top;text-align:left}}section{{background:white;padding:22px;margin:20px 0}}h1,h2{{line-height:1.25}}.notice{{padding:20px;background:#eee2f2}}summary{{cursor:pointer}}</style></head><body><main><h1>Eternal Journal: private SEO optimization</h1><p class="notice">No public articles, dates, URLs, photographs, site architecture, Care Brief materials or paused channels were changed. Nothing published, deployed or sent.</p><section><h2>What changed</h2><p>Audited all 107 articles before editing. Prepared {len(revised)} private revisions, including targeted additions in {len(sections)} articles. All 107 review versions have 2–5 contextual links to verified public destinations. The 12 weekly email drafts retain their proposed weeks and now align with individual Journal articles.</p><p>Core-body length remains varied: {audit['wordRange'][0]}–{audit['wordRange'][1]} words. No content was padded to meet a fixed count.</p><p>All 107 hero files have distinct SHA-256 hashes and are unchanged. Existing decorative CSS hero backgrounds retain their original presentation; no photo was relabeled with an invented clinical scene or renamed. Exact title/description, structural metadata and link checks are assessed separately from editorial approval.</p></section><section><h2>Coverage, not rankings</h2><p>The 303-row tracker preserves original evidence and adds current draft candidate columns. Assignments and exact phrase counts do not prove meaningful coverage, publication or ranking gains. {len(gaps)} keyword-cycle combinations still need appropriate coverage. Do not fill these gaps with city-name substitution. Existing primary-market topics were strengthened; unserved secondary intents require separate approval and verified local detail.</p><details><summary>Remaining keyword/city gaps</summary><table><tr><th>Cycle</th><th>ID</th><th>Keyword</th><th>Geography</th></tr>{gap_table}</table></details></section><section><h2>107-article record</h2><table><tr><th>Date</th><th>Article</th><th>Status</th><th>Core words</th><th>Links</th><th>Strengthened IDs</th></tr>{table}</table></section><section><h2>12 weekly emails</h2><p>Later Journal destinations remain unlinked until verified publicly available. The current draft uses an active educational resource instead. These are proposed editorial weeks, not scheduled sends.</p><table><tr><th>Week</th><th>Subject</th><th>Related Journal</th><th>Link status</th></tr>{email_table}</table></section><section><h2>Review boundaries and additional content</h2><p>Review the complete revised articles in Eternal Studio. Word-shingle screening detects overlap, not semantic equivalence; human reviewers should confirm distinct purposes. A clinical diagnosis is not automatic eligibility. No standalone palliative program, city office, owned hospice facility, immediate admission or continuous bedside nursing was claimed.</p><p>Recommend separately scoped educational guides for remaining San Fernando Valley communities, coastal Los Angeles markets, Glendale/Pasadena and Long Beach only after operations confirms address-level scope and a distinct local family question. These are recommendations, not new articles or dates.</p><p>Persistent publisher approval, the requested 6:30 a.m. release and failure alerts remain existing limitations; this optimization did not alter them. Studio statuses remain browser-local. Thryv ranking history is separate and untouched.</p><p>Clinical fact-check sources: Medicare.gov hospice coverage and its four-level care explanation. Live internal link checks are a snapshot dated {today}; revalidate immediately before release. Image byte uniqueness does not certify dissimilar photographic composition; final imagery judgment remains part of Studio review.</p></section></main></body></html>"""
    (OUTPUT/"journal-seo-review-summary.html").write_text(report)
    print(f"PASS: 107 audited; {len(revised)} private revisions; {len(sections)} targeted additions; 12 aligned drafts; {len(gaps)} open keyword-cycle gaps. No public/paused content changed.")


if __name__ == "__main__":
    build()
