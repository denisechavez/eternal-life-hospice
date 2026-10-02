#!/usr/bin/env python3
"""Build an offline five-city editorial review from a captured before snapshot."""
import argparse
import hashlib
import html
import itertools
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
PILOTS = ("thousand-oaks", "westlake-village", "simi-valley", "calabasas", "ventura")
THEMES = {
    "thousand-oaks": "Conejo Valley planning and the distinction between hospice visits and daily caregiving.",
    "westlake-village": "City versus mailing-address boundaries, cross-county coverage and care where the patient lives.",
    "simi-valley": "Coordinating information from doctors across Ventura County and the San Fernando Valley.",
    "calabasas": "Practical home-evaluation preparation, access instructions and caregiver involvement.",
    "ventura": "Choosing the care setting before discharge and clarifying home versus facility responsibilities.",
}


def plain(markup):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def main_html(page):
    return re.search(r"<main\b[^>]*>(.*?)</main>", page, re.S).group(1)


def normalize_city_names(text, cities):
    for name in sorted((c["city"] for c in cities), key=len, reverse=True):
        text = re.sub(r"\b" + re.escape(name) + r"\b", "[city]", text, flags=re.I)
    return text.lower()


def shingles(text):
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())
    return {" ".join(words[i:i + 8]) for i in range(max(0, len(words) - 7))}


def pair_scores(texts, cities):
    sets = {s: shingles(normalize_city_names(t, cities)) for s, t in texts.items()}
    return {
        (left, right): len(sets[left] & sets[right]) / len(sets[left] | sets[right])
        for left, right in itertools.combinations(PILOTS, 2)
    }


def review_copy(page):
    body = main_html(page)
    body = re.sub(r"<(picture|svg|nav)\b[^>]*>.*?</\1>", "", body, flags=re.S)
    body = re.sub(r"<img\b[^>]*>", "", body)
    body = re.sub(r"\s(?:class|id|tabindex|aria-[\w-]+)=\"[^\"]*\"", "", body)
    body = re.sub(r"<details([^>]*)>", "<details open>", body)
    body = re.sub(
        r'href="([^"]+)"',
        lambda m: 'href="' + html.escape(urljoin("https://eternallifehospice.com/", m[1]), quote=True) + '"',
        body,
    )
    return body


def build_report(baseline_path, output):
    before = json.loads(baseline_path.read_text())
    cities = json.loads((ROOT / "city-data.json").read_text())
    by_slug = {c["slug"]: c for c in cities}
    before_by_slug = {c["slug"]: c for c in before["source"]}
    pages = {s: (PUBLIC / f"hospice-{s}-ca.html").read_text() for s in PILOTS}
    changed_pages = [
        p.name for p in PUBLIC.glob("hospice-*-ca.html")
        if hashlib.sha256(p.read_bytes()).hexdigest() != before["hashes"].get(p.name)
    ]
    expected = {f"hospice-{s}-ca.html" for s in PILOTS}
    if set(changed_pages) != expected:
        raise ValueError(f"Pilot scope mismatch: changed pages = {sorted(changed_pages)}")
    changed_records = [s for s, c in by_slug.items() if c != before_by_slug.get(s)]
    if set(changed_records) != set(PILOTS):
        raise ValueError(f"Pilot source scope mismatch: {changed_records}")
    before_texts = {s: before["main"][f"hospice-{s}-ca.html"] for s in PILOTS}
    after_texts = {s: plain(main_html(page)) for s, page in pages.items()}
    before_scores = pair_scores(before_texts, cities)
    after_scores = pair_scores(after_texts, cities)
    e = html.escape
    audit_rows = (
        ("Medicare coverage paragraph", "145 of 145", "Clinical rules retained; pilot explanations connect coverage to the family’s next decision."),
        ("General resource-link paragraph", "145 of 145", "Replace pilot lists with links that support each page’s practical guidance."),
        ("Generic services explanation", "144 of 145", "Explain verified services in the context of the pilot’s care-planning question."),
        ("Default hero introduction", "123 of 145", "Distinct pilot openings, not city-name substitutions."),
        ("Regional discharge-coordination introduction", "69 of 145", "Replace reusable claims with clear, conditional steps a family can take."),
        ("Care-setting introduction", "78 of 145", "Explain who does what in the actual care setting without inventing facilities."),
    )
    rows = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in audit_rows)
    comparisons = "".join(
        f"<tr><td>{e(by_slug[a]['city'])} / {e(by_slug[b]['city'])}</td>"
        f"<td>{score:.1%}</td><td>{after_scores[(a, b)]:.1%}</td></tr>"
        for (a, b), score in before_scores.items()
    )
    date = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    sections = []
    for slug in PILOTS:
        c, old = by_slug[slug], before_by_slug[slug]
        sections.append(
            f'<article id="{slug}"><h2>{e(c["city"])} — pilot review</h2>'
            f'<p class="note">{e(THEMES[slug])}</p>'
            f'<dl><dt>Previous title</dt><dd>{e(old["title"])}</dd>'
            f'<dt>New title</dt><dd>{e(c["title"])}</dd>'
            f'<dt>New search description</dt><dd>{e(c["searchMetaDescription"])}</dd>'
            f'<dt>Visible main-content word count</dt><dd>{len(before_texts[slug].split())} before → '
            f'{len(after_texts[slug].split())} after</dd></dl>'
            f'<div class="copy">{review_copy(pages[slug])}</div></article>'
        )
    links = " · ".join(f'<a href="#{s}">{e(by_slug[s]["city"])}</a>' for s in PILOTS)
    report = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eternal Life Hospice — City Content Audit and Five-Page Pilot</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;color:#302b31;background:#f5f1ec;font:16px/1.65 Arial,sans-serif}}
main{{max-width:1080px;margin:auto;padding:44px 24px}}h1,h2,h3{{font-family:Georgia,serif;line-height:1.22;color:#44203f}}
h1{{font-size:36px}}h2{{margin-top:36px;font-size:27px}}h3{{font-size:21px}}a{{color:#5b2e59;text-underline-offset:3px}}
.eyebrow{{text-transform:uppercase;letter-spacing:2px;font-size:12px;color:#67605f}}
.note{{padding:16px 20px;background:#ebe4ee;border-left:3px solid #5b2e59}}
table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:left;border-bottom:1px solid #ded6cd;padding:12px;vertical-align:top}}
th{{color:#44203f;background:#eee8e0}}.table-wrap{{overflow:auto}}article{{background:white;padding:24px 30px;margin:30px 0;border:1px solid #e0d6ca}}
dt{{font-weight:bold;margin-top:12px}}dd{{margin-left:0}}.copy{{border-top:1px solid #ddd;padding-top:10px}}
.copy section{{margin:24px 0}}.copy details{{margin:16px 0}}summary{{font-weight:bold;color:#44203f}}
@media(max-width:600px){{main{{padding:24px 16px}}h1{{font-size:28px}}article{{padding:18px}}}}
@media print{{body{{background:white}}main{{padding:0}}article{{break-before:page;border:0}}a{{color:inherit}}}}
</style></head><body><main>
<p class="eyebrow">Eternal Life Hospice · Editorial review · {date}</p>
<h1>City Content Audit &amp; Five-Page Pilot</h1>
<p class="note"><strong>Review only:</strong> five local pages have been rewritten in the workspace. No other city pages or county hub were changed. Approval is required before expanding the pilot. This report contains the complete revised main copy; its public-site links may still serve earlier copy until publishing.</p>
<nav><a href="#audit">Before-edit audit</a> · <a href="#comparison">Measured pilot comparison</a> · {links}</nav>
<section id="audit"><h2>Before-edit report</h2>
<p><strong>Inventory:</strong> 145 data-backed local landing pages, including the Conejo Valley regional page, plus one county coverage hub (146 matching HTML files). Neighborhoods and unincorporated communities are included; this is a published-page count, not a guarantee of clinical coverage at every address.</p>
<p><strong>Siteliner:</strong> the supplied public report shows 187 scanned pages, 173 duplicate-table results and 20% sitewide duplication. The sampled table shows Ventura at 2% and Thousand Oaks at 3%. This is not a 20% finding for every city and does not establish a Google penalty. The report’s scan date was not confirmed.</p>
<div class="table-wrap"><table><thead><tr><th>Observed main-content pattern</th><th>Before-edit frequency</th><th>Pilot treatment</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Frequency findings come from the workspace main-content paragraphs, not the header or footer, using exact-text grouping after city-name normalization. They are separate from Siteliner’s method. Shared link wording and some short clinical wording can legitimately recur.</p>
<h3>Proposed page template</h3>
<ol><li>Distinct city H1, search title, description and opening.</li><li>At-a-glance guidance and verified community context.</li><li>A practical beginning-hospice section written for that community.</li><li>Relevant services and responsibilities across care settings.</li><li>Accurate coverage explanation and useful resource links.</li><li>Local referral guidance and at least three locally framed FAQs.</li><li>Existing contact CTA, legal disclosures and footer.</li></ol>
<p><strong>Remain standardized:</strong> navigation, branding, phone number, credentials, compliance disclosures, clinical eligibility requirements, existing images and styling. <strong>Become city-specific:</strong> titles, headings, introductions, starting-care guidance, care-setting explanations, contextual service/resource links and FAQs.</p>
<p>The pilot removes unsupported superlatives, named-hospital coordination promises and proximity-based response guarantees from the rewritten prose. The existing shared credential strip is unchanged; its “Same-Day Admissions” wording is not a city-specific new guarantee and still warrants separate operational review.</p></section>
<section id="comparison"><h2>Measured pilot comparison</h2>
<p>Eight-word passage Jaccard overlap between the five pilots, with all location names normalized. Comparison covers visible text inside <code>&lt;main&gt;</code>, including headings, FAQs, CTA and the shared credential close, but excludes navigation, footer and scripts. It measures shared passage sets—not a Siteliner percentage or a prediction of rankings. Longer useful copy can also reduce the ratio.</p>
<div class="table-wrap"><table><thead><tr><th>Page pair</th><th>Before</th><th>After</th></tr></thead><tbody>{comparisons}</tbody></table></div>
<p>Scope check: exactly five generated pages and five source records changed. No pages were removed, redirected or marked noindex.</p></section>
<section><h2>Validation and existing limitation</h2>
<p>The five-page content checks pass: distinct search/opening copy, source-to-page parity, visible FAQ/schema parity, real internal service/resource links and no duplicated long pilot paragraphs. All 145 local pages pass the current generator parity and city-script/content-distinctiveness checks. The five pilots preserve their previous header, footer, scripts, stylesheet references, photos and canonical URLs.</p>
<p><strong>Existing limitation:</strong> the legacy translation-bar check expects a footer language bar and translate.js tag that were already absent in the baseline pages. It fails that check; this content-only pilot does not restore or redesign the footer. No claim is made that every historical test passes.</p></section>
{''.join(sections)}
<section><h2>Sources and review limits</h2>
<ul>
<li><a href="https://www.siteliner.com/eternallifehospice.com?siteliner=site-duplicate&amp;siteliner-sort=match_words&amp;siteliner-from=121">User-supplied Siteliner report</a>; audited workspace city source and generated pages, captured before editing.</li>
<li><a href="https://toaks.gov/about">City of Thousand Oaks — About</a>: Ventura County geography.</li>
<li><a href="https://www.wlv.org/116/City-History">City of Westlake Village — City History</a>: incorporated city/county distinction. Local government search excerpts were readable; the fetched page body was incomplete.</li>
<li><a href="https://www.simivalley.org/our-city/at-a-glance">City of Simi Valley — At a Glance</a>: southeast Ventura County and adjacent San Fernando Valley.</li>
<li><a href="https://www.cityofcalabasas.com/our-city/about-us">City of Calabasas — About</a> and existing local source data: Calabasas geography; no new demographics or facility claims added.</li>
<li><a href="https://www.cityofventura.ca.gov/1882/City-Hall">City of Ventura — City Hall</a>: county-seat context, supported by its official search excerpt and existing local source data; fetched body was incomplete.</li>
</ul><p>No new hospital affiliations, facilities, testimonials, addresses, statistics or delivery-time promises were introduced. A new Siteliner crawl after publishing is needed to measure changes using Siteliner’s own method. Do not expand to the remaining pages before the user approves these five.</p></section>
</main></body></html>"""
    if len(report.encode("utf-8")) > 5 * 1024 * 1024:
        raise ValueError("Report exceeds delivery size limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Report: {output} ({len(report.encode('utf-8')):,} bytes)")
    print("Changed local pages:", ", ".join(sorted(changed_pages)))
    print("Mean pilot passage overlap:",
          f"{sum(before_scores.values()) / len(before_scores):.1%} before →",
          f"{sum(after_scores.values()) / len(after_scores):.1%} after")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=ROOT.parent / "exports/seo/city-content-pilot-review.html")
    args = parser.parse_args()
    build_report(args.baseline, args.output)