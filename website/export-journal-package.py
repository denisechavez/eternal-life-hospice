#!/usr/bin/env python3
"""Export private review copies without editing or publishing any site content."""
import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import zipfile
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from journal_seo_review_tools import article, heading, hero, plain
from journal_image_revisions import apply_image_revision, image_revisions
from journal_release import revision as journal_revision

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "website/elh-preview"
CONTENT = ROOT / "website/content"
AUDIT = ROOT / "exports/site-audits/journal-seo-optimization"
START, END = date(2026, 10, 8), date(2026, 12, 31)
OUTPUT = ROOT / "generated-artifacts/journal-oct08-dec31-2026"
CITIES = ("Thousand Oaks", "Westlake Village", "Simi Valley", "Calabasas",
          "Camarillo", "Moorpark", "Newbury Park", "Oxnard", "Ventura",
          "Conejo Valley", "Los Angeles", "Glendale", "Pasadena", "Long Beach",
          "Malibu", "Santa Monica", "Burbank", "Agoura Hills")
NOTES = (
    "Private editorial export, not a publication or sending instruction. "
    "Dates and URLs are the existing publication schedule, not proof of approval "
    "or current public availability. SEO revisions remain pending Studio review. "
    "Authoritative production approval and final imagery approval are not verified "
    "by this export. Four replacement photographs require fresh Studio approval; "
    "the other source photographs are unchanged. "
    "Keyword assignments are coverage candidates, not confirmed coverage or rankings."
)


class Markdown(HTMLParser):
    """Readable article transcription preserving headings, lists and link destinations."""
    def __init__(self, domain):
        super().__init__(convert_charrefs=True)
        self.domain = domain
        self.parts = []
        self.links = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag in ("h1", "h2", "h3", "h4"):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("p", "ul", "ol", "aside", "blockquote"):
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "a":
            href = attributes.get("href", "")
            self.links.append(urljoin(self.domain, href) if href else "")
            self.parts.append("[")
        elif tag in ("b", "strong"):
            self.parts.append("**")
        elif tag in ("i", "em"):
            self.parts.append("*")

    def handle_endtag(self, tag):
        if tag == "a":
            self.parts.append("](" + self.links.pop() + ")")
        elif tag in ("b", "strong"):
            self.parts.append("**")
        elif tag in ("i", "em"):
            self.parts.append("*")
        elif tag in ("p", "li", "h1", "h2", "h3", "h4", "aside"):
            self.parts.append("\n\n")

    def handle_data(self, value):
        self.parts.append(re.sub(r"\s+", " ", value))

    def result(self):
        return re.sub(r"\n[ \t]+", "\n", re.sub(r"\n{3,}", "\n\n", "".join(self.parts))).strip()


def clean_body(source):
    body = article(source)
    body = re.sub(r'<a\b[^>]*class="backlink"[^>]*>.*?</a>', "", body, flags=re.S)
    body = re.sub(r'<div class="blog-byline">.*?</div>', "", body, flags=re.S)
    assert not re.search(r"<(?:script|iframe|style)\b", body, re.I)
    return body


def meta(source, name):
    match = re.search(r'<meta (?:name|property)="' + re.escape(name) + r'" content="([^"]*)"', source)
    return html.unescape(match[1]) if match else ""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_file(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(domain):
    original_hashes = {p: digest(p) for p in PUBLIC.rglob("*.html")}
    with (AUDIT / "article-optimization-record.csv").open(newline="") as handle:
        inventory = [row for row in csv.DictReader(handle)
                     if START.isoformat() <= row["Date"] <= END.isoformat()]
    expected = [(START + timedelta(days=i)).isoformat() for i in range((END - START).days + 1)]
    assert sorted(row["Date"] for row in inventory) == expected, "Missing or duplicate daily article"
    private = json.loads((CONTENT / "seo-journal-review.json").read_text())["articles"]
    keywords = json.loads((CONTENT / "seo-keyword-master.json").read_text())["keywords"]
    assert [k["id"] for k in keywords] == list(range(1, 102))
    editorial = {}
    for path in sorted((CONTENT / "30-day-journal").glob("*.json")):
        for record in json.loads(path.read_text()):
            editorial[record["slug"]] = record
    if OUTPUT.exists():
        # This is only this tool's reproducible, ignored output directory.
        shutil.rmtree(OUTPUT)
    (OUTPUT / "articles").mkdir(parents=True)
    (OUTPUT / "original-reference").mkdir()
    documents, spreadsheet, photographs = [], [], []
    for row in sorted(inventory, key=lambda row: (row["Date"], row["Slug"])):
        slug, scheduled = row["Slug"], row["Date"]
        source = (PUBLIC / "blog" / (slug + ".html")).read_text()
        revision = private.get(slug)
        photo_review = image_revisions().get(slug)
        review = apply_image_revision(slug, revision["reviewHtml"] if revision else source)
        if photo_review:
            assert hero(source) == row["Hero image"] == photo_review["originalImage"]
            row = {**row, "Hero image": photo_review["heroImage"]}
        assert heading(review) == heading(source) == row["Title"]
        assert hero(review) == row["Hero image"]
        if not photo_review:
            assert hero(review) == hero(source)
        title, description = heading(review), meta(review, "description")
        body = clean_body(review)
        intro = re.search(r"<section\b[^>]*class=\"hero[^\"]*\"[^>]*>(.*?)</section>", review, re.S)
        summary = "".join(re.findall(r"<p\b[^>]*>.*?</p>", intro[1], re.S)) if intro else ""
        # Export all article prose, including the hero summary and clinical asides.
        prose_html = summary + body
        converter = Markdown(domain)
        converter.feed(prose_html)
        text = converter.result()
        mapped = [k for k in keywords if scheduled in k.get("draftDates", [])]
        local = editorial.get(slug, {}).get("location", "")
        localized_headings = " ".join(plain(h) for h in re.findall(r"<h[123]\b[^>]*>.*?</h[123]>", review, re.S))
        localized_sections = " ".join(
            section["heading"] + " " + " ".join(section["paragraphs"])
            for section in (revision or {}).get("sections", []))
        geographic_text = " ".join((local, title, description, localized_headings, localized_sections))
        # National articles can have an explicitly localized private nursing section.
        # County references alone must not be misclassified as city-focused content.
        cities = [city for city in CITIES if re.search(
            r"\b" + re.escape(city) + r"\b(?!\s+County)", geographic_text, re.I)]
        regions = [region for region in ("Ventura County", "Los Angeles County")
                   if region.lower() in geographic_text.lower()]
        audience = "Local educational content" if cities else "National / not explicitly city-specific"
        image_path = (PUBLIC / row["Hero image"].lstrip("/")).resolve()
        assert image_path.is_relative_to(PUBLIC.resolve()) and image_path.is_file()
        image_relative = "images/" + image_path.relative_to(PUBLIC).as_posix()
        packaged_image = OUTPUT / image_relative
        packaged_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image_path, packaged_image)
        record = editorial.get(slug, {})
        credit = record.get("photoCredit", {})
        photo = {
            "Date": scheduled, "Title": title, "Slug": slug,
            "Image file in package": image_relative,
            "Site image reference": row["Hero image"],
            "Image URL": urljoin(domain, row["Hero image"]),
            "SHA256": digest(image_path),
            "Alt / description": record.get("heroImageAlt") or meta(review, "og:image:alt"),
            "Credit": credit.get("author", ""),
            "Source URL": credit.get("sourceUrl", ""),
            "License": credit.get("license", ""),
            "License URL": credit.get("licenseUrl", ""),
            "Approval": "Existing source image; final Studio approval not verified",
        }
        if photo_review:
            assert photo["SHA256"] == photo_review["sha256"]
            photo.update({
                "Alt / description": photo_review["alt"],
                "Credit": "Pexels; illustrative stock photograph, not Eternal staff or patients",
                "Source URL": photo_review["sourcePage"],
                "License": "Pexels License",
                "License URL": "https://www.pexels.com/license/",
                "Approval": "Replacement photograph; fresh Studio approval required",
            })
        photographs.append(photo)
        url = domain.rstrip("/") + "/blog/" + slug
        document = {
            "date": scheduled, "title": title, "seo_title": html.unescape(re.search(r"<title>(.*?)</title>", review, re.S)[1]),
            "description": description, "slug": slug, "url": url,
            "target_cities": cities, "target_regions": regions, "audience": audience,
            "city_mapping_basis": "Editorial location and localized title, summary or headings; not navigation/footer mentions",
            "keywords": [{"id": k["id"], "phrase": k["phrase"], "intent": k["intent"]}
                         for k in mapped],
            "keyword_mapping_status": "Editorial coverage candidates; not confirmed coverage or rankings",
            "version": ("Private image review revision" if photo_review else
                        "Private SEO review revision" if revision else "Existing original article"),
            "revision": journal_revision(review) if photo_review else revision["revision"] if revision else "",
            "approval_status": "Authoritative Studio approval not verified",
            "image": photo, "article_markdown": text, "article_html": prose_html,
            "cta_html": (re.search(r'<section class="cta">(.*?)</section>', review, re.S)[1]
                         if re.search(r'<section class="cta">(.*?)</section>', review, re.S) else ""),
        }
        documents.append(document)
        metadata = (
            f"# {title}\n\nPublication date: {scheduled} (America/Los_Angeles)\n\n"
            f"Article URL: {url}\n\nVersion: {document['version']}\n\n"
            f"Target cities: {'; '.join(cities) or audience}\n\n"
            f"Target regions: {'; '.join(regions) or 'Not separately specified'}\n\n"
            f"Keywords (coverage candidates): {'; '.join(str(k['id']) + ': ' + k['phrase'] for k in mapped) or 'No assigned master-list candidate; see tracker'}\n\n"
            f"Image: {image_relative} | Site reference: {row['Hero image']}\n\n"
            "Approval: Not verified; review required in Eternal Studio.\n\n"
        )
        filename = scheduled + "--" + slug + ".md"
        (OUTPUT / "articles" / filename).write_text(metadata + text + "\n", encoding="utf-8")
        if revision:
            baseline = Markdown(domain)
            baseline.feed(clean_body(source))
            (OUTPUT / "original-reference" / filename).write_text(
                f"# {title}\n\nUnrevised original for comparison only.\n\n" + baseline.result() + "\n")
        spreadsheet.append({
            "Publication date": scheduled, "Title": title, "SEO title": document["seo_title"],
            "Article URL": url, "Slug": slug, "Target cities": "; ".join(cities) or audience,
            "Target regions": "; ".join(regions), "Audience": audience,
            "Keyword IDs": "; ".join(str(k["id"]) for k in mapped),
            "Keywords (coverage candidates)": "; ".join(k["phrase"] for k in mapped),
            "Keyword status": document["keyword_mapping_status"],
            "Version": document["version"], "Revision": document["revision"],
            "Approval status": document["approval_status"],
            "Image file": image_relative, "Image URL": photo["Image URL"],
            "Article text file": "articles/" + filename,
        })
    (OUTPUT / "journal-content.json").write_text(json.dumps({
        "start": START.isoformat(), "end": END.isoformat(), "timezone": "America/Los_Angeles",
        "count": len(documents), "notes": NOTES, "articles": documents,
    }, ensure_ascii=False, indent=2) + "\n")
    csv_file(OUTPUT / "article-index.csv", spreadsheet)
    csv_file(OUTPUT / "image-references.csv", photographs)
    csv_file(OUTPUT / "keyword-master-101.csv", [
        {"ID": k["id"], "Phrase": k["phrase"], "Intent": k["intent"],
         "Geography": k["geography"], "Source": k["source"]} for k in keywords])
    shutil.copyfile(AUDIT / "keyword-coverage-101-optimized.csv", OUTPUT / "keyword-coverage-cycles.csv")
    combined = ["# Eternal Journal — October 8–December 31, 2026\n\n" + NOTES]
    cards = []
    for document, row in zip(documents, spreadsheet):
        combined.append((OUTPUT / row["Article text file"]).read_text())
        body = re.sub(r'(href=["\'])(/[^"\']*)',
                      lambda match: match[1] + html.escape(urljoin(domain, match[2]), quote=True),
                      document["article_html"])
        cards.append(
            '<article id="' + document["slug"] + '"><p class="label">' + document["date"] +
            ' · ' + html.escape(document["version"]) + '</p><h2>' + html.escape(document["title"]) +
            '</h2><p><a href="' + html.escape(document["url"]) + '">' + html.escape(document["url"]) +
            '</a></p><p><strong>Target cities:</strong> ' +
            html.escape("; ".join(document["target_cities"]) or document["audience"]) +
            '</p><p><strong>Keywords (candidates):</strong> ' + html.escape(row["Keywords (coverage candidates)"] or "No assigned candidate") +
            '</p><img src="' + document["image"]["Image file in package"] + '" alt="' +
            html.escape(document["image"]["Alt / description"], quote=True) + '"><div class="prose">' +
            body + '</div></article>')
    (OUTPUT / "all-articles.md").write_text("\n\n---\n\n".join(combined) + "\n")
    toc = "".join('<li><a href="#' + doc["slug"] + '">' + doc["date"] + ' — ' +
                  html.escape(doc["title"]) + "</a></li>" for doc in documents)
    (OUTPUT / "START-HERE.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Eternal Journal — Private Content Export</title><style>'
        'body{max-width:960px;margin:40px auto;padding:0 20px;background:#faf7f3;color:#302b33;font:17px/1.7 Georgia,serif}'
        'h1,h2,h3{line-height:1.3;color:#543852}h1{font-size:32px}.label,nav{font:14px/1.7 Arial,sans-serif}'
        'a{color:#603f64}article{padding:30px;margin:30px 0;background:white;border:1px solid #ded7df}'
        'img{display:block;width:100%;height:auto;margin:25px 0}.notice{background:#eee6f0;padding:20px}'
        'nav li{margin:6px 0}.prose h2{font-size:23px;margin-top:30px}@media print{nav{display:none}article{break-before:page}}'
        '</style><body><h1>Eternal Journal: October 8–December 31, 2026</h1><p>85 scheduled articles.</p>'
        '<p class="notice">' + html.escape(NOTES) + '</p><nav><h2>Article index</h2><ol>' + toc +
        '</ol></nav>' + "".join(cards) + "</body></html>")
    revisions = sum(bool(doc["revision"]) for doc in documents)
    (OUTPUT / "README.txt").write_text(
        "ETERNAL JOURNAL CONTENT PACKAGE\nOctober 8–December 31, 2026, inclusive\n"
        f"85 daily articles; {revisions} private review revisions and {85-revisions} unchanged originals.\n\n"
        + NOTES + "\n\nHOW TO USE\nUnzip the entire package, then open START-HERE.html for a readable "
        "offline collection with photographs. The image folder must remain beside the HTML file.\n"
        "article-index.csv: dates, titles, master keyword IDs/phrases, cities, URLs, version labels and image references.\n"
        "all-articles.md: one complete text collection, including contextual link destinations.\n"
        "articles/: one Markdown text file per article.\n"
        "original-reference/: unrevised body copies for comparison with private SEO revisions.\n"
        "journal-content.json: complete machine-readable text, metadata, CTA HTML and photographs.\n"
        "image-references.csv: original source paths, file hashes, credits/licenses where supplied and approval limitations.\n"
        "keyword-master-101.csv and keyword-coverage-cycles.csv: original IDs and coverage evidence; no rankings claimed.\n\n"
        "Scope: Journal only. No email or Care Brief material is included. This export does not change the site, "
        "its publishing controls, or any referral cards. Existing recruitment references, if any, remain unchanged "
        "pending approval of the separate takedown recommendation.\n")
    manifest = {p.relative_to(OUTPUT).as_posix(): digest(p) for p in sorted(OUTPUT.rglob("*")) if p.is_file()}
    (OUTPUT / "file-integrity.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = OUTPUT.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(OUTPUT.rglob("*")):
            if path.is_file():
                package.write(path, OUTPUT.name + "/" + path.relative_to(OUTPUT).as_posix())
    assert original_hashes == {p: digest(p) for p in PUBLIC.rglob("*.html")}, "Public content changed"
    validate(archive)
    print(f"PASS: 85 articles; {revisions} private revisions; 85 verified hero image files. {archive.relative_to(ROOT)}")


def validate(archive):
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        prefix = OUTPUT.name + "/"
        data = json.loads(package.read(prefix + "journal-content.json"))
        assert data["count"] == len(data["articles"]) == 85
        assert data["articles"][0]["date"] == START.isoformat()
        assert data["articles"][-1]["date"] == END.isoformat()
        assert len({doc["url"] for doc in data["articles"]}) == 85
        assert len({doc["image"]["SHA256"] for doc in data["articles"]}) == 85
        manifest = json.loads(package.read(prefix + "file-integrity.json"))
        for filename, sha in manifest.items():
            assert hashlib.sha256(package.read(prefix + filename)).hexdigest() == sha, filename
        for doc in data["articles"]:
            assert doc["article_markdown"].strip() and "<p" in doc["article_html"]
            assert not re.search(r"<(?:script|iframe)\b", doc["article_html"], re.I)
            assert hashlib.sha256(package.read(prefix + doc["image"]["Image file in package"])).hexdigest() == doc["image"]["SHA256"]
    print("PASS: ZIP integrity, complete daily dates, unique URLs/photos and all indexed file hashes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="Verified published origin")
    parser.add_argument("--check", action="store_true", help="Validate existing archive only")
    args = parser.parse_args()
    assert re.fullmatch(r"https://[A-Za-z0-9.-]+", args.domain), "Supply the verified HTTPS origin"
    if args.check:
        validate(OUTPUT.with_suffix(".zip"))
    else:
        build(args.domain)
