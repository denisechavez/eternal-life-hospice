#!/usr/bin/env python3
"""Validate reviewed city drafts, then explicitly apply content-only updates."""
import argparse
from datetime import datetime
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
PILOTS = {"thousand-oaks", "westlake-village", "simi-valley", "calabasas", "ventura"}
FIELDS = {
    "title", "h1", "heroIntroduction", "searchMetaDescription", "atAGlanceSummary",
    "localIntroductionHeading", "localIntroduction", "localNearbyParagraph",
    "serviceOverviewHtml", "serviceResourcesHtml", "beginningCareHeading",
    "beginningCareHtml", "coverageHeading", "coverageHtml", "resourcesHeading",
    "resourcesHtml", "providerContext", "familyContext", "careSettings", "faqItems",
}
INNER_FIELDS = {"localNearbyParagraph", "serviceOverviewHtml",
                "serviceResourcesHtml", "providerContext"}
spec = importlib.util.spec_from_file_location("city_builder", ROOT / "build-cities.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MarkupCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag not in {"p", "a", "b", "strong", "em", "ul", "ol", "li", "br"}:
            raise ValueError(f"Unexpected editorial markup: {tag}")
        for key, value in attrs:
            if key != "href" or tag != "a":
                raise ValueError(f"Unexpected editorial attribute: {tag}.{key}")
            if not value.startswith("/") and not value.startswith("hospice-"):
                raise ValueError(f"Unexpected editorial link: {value}")
            target = value.split("#")[0].split("?")[0].lstrip("/")
            if target and not ((PUBLIC / target).is_file() or
                               (PUBLIC / (target + ".html")).is_file() or
                               (PUBLIC / target).is_dir()):
                raise ValueError(f"Broken editorial link: {value}")


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)


def edit_field(page, field, original, replacement):
    parts = field.split(".")
    parent = page
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
    if parent[key].count(original) != 1:
        return False
    parent[key] = parent[key].replace(original, replacement, 1)
    return True


def cleanup(text):
    # Match the project's no-Oxford-comma convention without changing facts.
    text = re.sub(r", (and|or) ", r" \1 ", text)
    # Do not introduce an unsupported certification/security claim for intake.
    text = re.sub(r"\bsecure referral\b", "professional referral", text, flags=re.I)
    # Preserve ordinary distinctions while avoiding categorical room/board claims.
    text = re.sub(r"(?<!generally )does not cover(?=.{0,65}room and board)",
                  "generally does not cover", text, flags=re.I)
    return text


def normalize(page):
    for field, value in list(page.items()):
        if isinstance(value, str):
            page[field] = cleanup(value)
    page["careSettings"] = [cleanup(v) for v in page["careSettings"]]
    for faq in page["faqItems"]:
        faq["q"], faq["a"] = cleanup(faq["q"]), cleanup(faq["a"])
    for field in INNER_FIELDS:
        # Defensive normalization of accidental block markup inside rendered <p>.
        page[field] = re.sub(r"</?p\b[^>]*>", " ", page[field]).strip()
    if "hospice-ventura-and-los-angeles-county-ca" not in page["localNearbyParagraph"]:
        page["localNearbyParagraph"] += (
            ' Review the <a href="/hospice-ventura-and-los-angeles-county-ca">'
            'Ventura and Los Angeles County coverage guide</a> and confirm '
            'availability for the actual care address.'
        )
    if not any('href="/services"' in s for s in strings(page)):
        page["serviceResourcesHtml"] += (
            ' Explore <a href="/services">Eternal Life Hospice services</a> '
            'for an overview of the team.'
        )
    if not any('href="/family-guide"' in s for s in strings(page)):
        page["resourcesHtml"] += (
            '<p>The <a href="/family-guide">Family Guide</a> can help you '
            'prepare questions for a care conversation.</p>'
        )
    if page["slug"] == "avalon":
        page["heroIntroduction"] = (
            "If you are exploring hospice care in Avalon, first ask Eternal Life "
            "Hospice to confirm whether in-person service is currently feasible at "
            "the patient's actual island address. Do this before planning travel "
            "or a care transition. Our team can discuss clinical needs, access and "
            "current logistical limits; an inquiry does not confirm availability."
        )
        page["careSettings"] = [
            "<b>Current island residence</b> — ask whether in-person service is "
            "currently feasible before planning an evaluation",
            "<b>A proposed care location</b> — confirm clinical needs, everyday "
            "caregiver support and address-level availability before a move",
            "<b>Another care arrangement</b> — if island visits are not feasible, "
            "ask the treating clinician about appropriate local options",
        ]
        page["faqItems"][2]["a"] = (
            "Ask what travel limitations could mean for the proposed care plan "
            "before arranging services. Phone contact is not a substitute for "
            "clinically necessary in-person care. Our team must first determine "
            "whether it can reliably meet the patient's needs at the island "
            "address; do not assume virtual or backup visits are available."
        )
    if page["slug"] == "conejo-valley":
        paragraphs = page["localIntroduction"].split("\n\n")
        paragraphs[0] = (
            "The Conejo Valley is a region spanning Ventura and Los Angeles "
            "counties, not a single city. If care is being considered in Thousand "
            "Oaks, Westlake Village, Newbury Park or Agoura Hills, begin with the "
            "patient's actual street address and who provides everyday support "
            "there. The proposed care location matters more than a regional label "
            "when confirming service availability and planning visits."
        )
        page["localIntroduction"] = "\n\n".join(paragraphs)
    if page["slug"] == "point-mugu":
        page["faqItems"][2]["a"] = (
            "The Medicare hospice benefit can cover medications for the terminal "
            "illness and related conditions under the individualized plan. A "
            "long-standing health problem is not automatically unrelated. Ask "
            "the clinical team which medicines fall under the elected benefit "
            "and how any unrelated care or separate coverage should be handled."
        )
    # Do not imply Medicare hospice imposes equipment/supply copayments.
    # Uniform clinical facts may remain consistent; originality is not a reason
    # to change coverage rules.
    copay_edits = {
        "bellflower": ("Copayments for medications or medical equipment may apply "
                      "depending on the specific care plan.",
                      "Limited copayments may apply for covered outpatient drugs "
                      "or inpatient respite in specific circumstances."),
        "diamond-bar": ("certain medications or supplies", "covered outpatient "
                        "drugs or inpatient respite"),
        "el-segundo": ("certain medications or supplies", "covered outpatient "
                       "drugs or inpatient respite"),
        "la-mirada": ("Some medications or medical equipment may require copayments",
                     "Limited copayments may apply for covered outpatient drugs "
                     "or inpatient respite"),
        "la-verne": ("some medications or equipment", "covered outpatient drugs "
                     "or inpatient respite"),
        "long-beach": ("certain medications or durable medical equipment",
                      "covered outpatient drugs or inpatient respite"),
        "maywood": ("medications or equipment", "covered outpatient drugs "
                   "or inpatient respite"),
        "san-gabriel": ("medications or supplies", "covered outpatient drugs "
                       "or inpatient respite"),
        "san-marino": ("medications or specific supplies related to your comfort plan",
                      "covered outpatient drugs or inpatient respite"),
        "san-pedro": ("certain medications or supplies", "covered outpatient drugs "
                     "or inpatient respite"),
        "sherman-oaks": ("potential copayments or out-of-pocket costs associated "
                        "with certain medications or equipment",
                        "which medicines and equipment are included under the "
                        "benefit and where limited copayments or separate "
                        "expenses might apply"),
        "tarzana": ("certain medications or durable medical equipment",
                    "covered outpatient drugs or inpatient respite"),
        "west-hills": ("certain medications or supplies", "covered outpatient "
                      "drugs or inpatient respite"),
    }
    if page["slug"] in copay_edits:
        original, replacement = copay_edits[page["slug"]]
        if page["coverageHtml"].count(original) != 1:
            raise ValueError(f"{page['slug']}: review coverage correction against draft")
        page["coverageHtml"] = page["coverageHtml"].replace(original, replacement, 1)
    if page["slug"] == "hollywood":
        page["coverageHtml"] = page["coverageHtml"].replace(
            "though specific inpatient or respite care may be available if symptoms "
            "cannot be managed at home.",
            "though covered inpatient symptom management and inpatient respite "
            "have their own criteria. Ask the team how those circumstances differ."
        )
    # These were outcome promises rather than confirmed operational facts.
    if page["slug"] == "moorpark":
        page["beginningCareHtml"] = page["beginningCareHtml"].replace(
            "maintaining an uninterrupted clinical plan",
            "planning clinical support at the proposed address"
        )
    if page["slug"] == "south-gate":
        page["beginningCareHtml"] = page["beginningCareHtml"].replace(
            "reaches the right person without delay",
            "can be shared with the appropriate contact"
        )
    return page


def validate(page, city):
    if set(page) != FIELDS | {"slug"}:
        raise ValueError(f"{city['slug']}: incomplete draft fields")
    for field in ("title", "h1", "searchMetaDescription"):
        if city["city"] not in html.unescape(page[field]):
            raise ValueError(f"{city['slug']}: missing city in {field}")
        if any(char in page[field] for char in '<>"&'):
            raise ValueError(f"{city['slug']}: unsafe plain text in {field}")
    if not 120 <= len(html.unescape(page["searchMetaDescription"])) <= 175:
        raise ValueError(f"{city['slug']}: unsuitable meta-description length")
    if len(page["localIntroduction"].split("\n\n")) < 2:
        raise ValueError(f"{city['slug']}: missing substantive introduction")
    if not 3 <= len(page["faqItems"]) <= 4:
        raise ValueError(f"{city['slug']}: expected 3-4 FAQs")
    for field in ("beginningCareHtml", "coverageHtml", "resourcesHtml"):
        if not page[field].startswith("<p>"):
            raise ValueError(f"{city['slug']}: expected paragraph blocks in {field}")
    for value in strings(page):
        MarkupCheck().feed(value)
    links = set(re.findall(r'href="(/(?:resources/[^"#]+|services))"',
                           " ".join(strings(page))))
    if len(links) < 3:
        raise ValueError(f"{city['slug']}: insufficient relevant resource links")
    if not any('/refer#referral-form' in s for s in strings(page)):
        raise ValueError(f"{city['slug']}: missing referral pathway")


def chrome(page):
    """Invariant portions that must not change in a content-only rewrite."""
    return {
        "header": re.search(r"<header\b.*?</header>", page, re.S).group(),
        "footer": re.search(r"<footer\b.*?</footer>", page, re.S).group(),
        "scripts": re.findall(r"<script(?! type=\"application/ld\+json\").*?</script>",
                              page, re.S),
        "stylesheets": re.findall(r"<link[^>]+(?:stylesheet|as=\"style\")[^>]*>", page),
        "hero_image": re.search(r'<section class="hero[^>]*>(.*?)<div class="eyebrow">',
                                page, re.S).group(1),
        "canonical": re.search(r'<link rel="canonical"[^>]+>', page).group(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly write validated source and rendered pages")
    parser.add_argument("--update-date", default=datetime.now(
        ZoneInfo("America/Los_Angeles")).date().isoformat())
    parser.add_argument("--preservation-report", type=Path,
                        default=ROOT.parent / "exports/seo/city-rewrite-preservation.json")
    args = parser.parse_args()
    cities = json.loads((ROOT / "city-data.json").read_text())
    expected = {c["slug"] for c in cities
                if c.get("publishStatus") == "published" and c["slug"] not in PILOTS}
    drafts = [p for f in sorted(args.drafts_dir.glob("rewrite-*.json"))
              for p in json.loads(f.read_text())["pages"]]
    pages = {p["slug"]: p for p in drafts}
    if len(drafts) != len(pages) or set(pages) != expected:
        raise ValueError("Draft inventory must match the remaining city pages exactly")
    accepted_edits = 0
    for f in sorted(args.drafts_dir.glob("review-*.json")):
        for edit in json.loads(f.read_text())["edits"]:
            # Review suggestions are evidence, not authority. Preserve valid
            # clinical caveats, coverage distinctions and referral pathways.
            original = edit["original"]
            if not re.search(r"ensure|seamless|smooth|uninterrupted", original, re.I):
                continue
            if re.search(r"\b(?:not|cannot|can't|never)\b", original, re.I):
                continue
            if edit["field"] == "coverageHtml":
                continue
            if edit["original"] and edit["replacement"]:
                accepted_edits += edit_field(pages[edit["slug"]], edit["field"],
                                             original, edit["replacement"])
    rendered = {}
    for city in cities:
        slug = city["slug"]
        if slug not in expected:
            continue
        page = normalize(pages[slug])
        validate(page, city)
        original = (PUBLIC / f"hospice-{slug}-ca.html").read_text()
        if builder._normalise(original) != builder._normalise(builder.render_page(city)):
            raise ValueError(f"{slug}: resolve existing source/page drift before rewriting")
        city.update({field: page[field] for field in FIELDS})
        city["metaDescription"] = city["searchMetaDescription"]
        city["displayFaqItems"] = city["faqItems"]
        city["lastMaterialUpdate"] = args.update_date
        updated = builder.render_page(city)
        if chrome(original) != chrome(updated):
            raise ValueError(f"{slug}: non-editorial page changes detected")
        rendered[slug] = updated
    protected = [PUBLIC / f"hospice-{s}-ca.html" for s in sorted(PILOTS)]
    protected.append(PUBLIC / "hospice-ventura-and-los-angeles-county-ca.html")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    print(f"Validated {len(rendered)} rewrites; {accepted_edits} reviewed corrections.")
    if not args.apply:
        print("Dry run only. Use --apply to write these validated editorial updates.")
        return
    args.preservation_report.parent.mkdir(parents=True, exist_ok=True)
    args.preservation_report.write_text(json.dumps(hashes, indent=2) + "\n")
    (ROOT / "city-data.json").write_text(
        json.dumps(cities, ensure_ascii=False, indent=2) + "\n")
    for slug, page in rendered.items():
        (PUBLIC / f"hospice-{slug}-ca.html").write_text(page)
    # Refresh only local-page search metadata; preserve keyword/category/order
    # and all unrelated search entries. Pilot page files remain untouched.
    index_path = PUBLIC / "assets/search-index.json"
    index = json.loads(index_path.read_text())
    by_url = {urlsplit(c["canonicalUrl"]).path: c for c in cities}
    for entry in index:
        if entry["url"] in by_url:
            city = by_url[entry["url"]]
            entry["title"] = re.sub(
                r"\s*[|–—]\s*Eternal Life Hospice.*$", "", city["title"]).strip()
            entry["desc"] = builder.meta_description(city)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    sitemap_path = PUBLIC / "sitemap.xml"
    sitemap = sitemap_path.read_text()
    for city in cities:
        if city["slug"] in rendered:
            pattern = (r"(<url><loc>" + re.escape(city["canonicalUrl"]) +
                       r"</loc><lastmod>)[^<]+(</lastmod>)")
            sitemap = re.sub(pattern, lambda m: m[1] + args.update_date + m[2], sitemap)
    sitemap_path.write_text(sitemap)
    assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    print(f"Applied {len(rendered)} pages. Five pilot pages and county hub unchanged.")


if __name__ == "__main__":
    main()