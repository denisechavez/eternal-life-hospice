#!/usr/bin/env python3
"""Offline authoring tool. Normal site builds never call AI or download photos.

The fixed briefs below the content directory are expanded into editorial drafts,
date-scheduled source JSON. Credentials are used only inside runtime requests.
Run --photos and --articles independently, then --assemble.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import math
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
BRIEFS = ROOT / "content" / "journal-q4-briefs.tsv"
CACHE = ROOT.parent / ".local" / "journal-q4-authoring"
PHOTO_DIR = PUBLIC / "assets" / "img" / "journal" / "q4"
PHOTO_SOURCES = ROOT / "content" / "journal-q4-photo-sources.json"
PHOTO_REVIEW = ROOT / "content" / "journal-q4-photo-review.json"
OUTPUT = ROOT / "content" / "30-day-journal" / "additional-2026-q4.json"
UA = "EternalLifeHospice/1.0 (https://eternallifehospice.com; editorial photographs)"
PHOTO_LOCK = threading.Lock()
TARGETS = (500, 800, 650, 1050, 450, 750, 900, 550, 700, 400)
CITY_ROUTES = {
    "Thousand Oaks": "/hospice-thousand-oaks-ca",
    "Westlake Village": "/hospice-westlake-village-ca",
    "Calabasas": "/hospice-calabasas-ca",
    "Camarillo": "/hospice-camarillo-ca",
    "Conejo Valley": "/hospice-conejo-valley-ca",
    "Ventura": "/hospice-ventura-ca",
    "Oxnard": "/hospice-oxnard-ca",
}
SOURCES = {
    "medicare": {"title": "Medicare.gov: Hospice care coverage",
                 "url": "https://www.medicare.gov/coverage/hospice-care"},
    "cms": {"title": "CMS: The Medicare hospice benefit",
            "url": "https://www.cms.gov/medicare/payment/fee-for-service-providers/hospice"},
    "weather": {"title": "Ready LA County: Preparing for rainy weather",
                "url": "https://ready.lacounty.gov/rain/"},
    "power": {"title": "Ready.gov: Power outage preparedness",
              "url": "https://www.ready.gov/power-outages"},
    "ventura": {"title": "Ready Ventura County: Make a Plan",
                "url": "https://ready.venturacounty.gov/plan/"},
}
FACTS = """
Publication identity: The Eternal Journal; author The Eternal Life Hospice Team.
Eternal Life Hospice personalizes support from the first call by listening to the
person's wishes, household circumstances and questions. The first call is not
automatic admission or an eligibility determination.
Hospice eligibility is individualized and physician-certified. For Medicare,
the certification concerns a prognosis of six months or less if the illness
runs its normal course; this is an estimate, not a countdown or a six-month
maximum stay. Medicare has two 90-day benefit periods, followed by unlimited
60-day periods while continued eligibility is certified under applicable rules.
Core hospice services depend on the individualized plan and related-care rules.
On-call clinical guidance 24/7 is not continuous bedside nursing, a live-in aide
or replacement for family or privately arranged daily caregiving.
Medicare hospice election, advance directives and decision-maker documents have
different purposes. Legal and coverage questions require the appropriate
professional; do not promise all treatments, room and board or unrelated care
are covered. Direct benefit specifics to the site's Medicare resource.
Sound bathing and end-of-life (death) doula support are optional, preference-led
integrative comfort offerings. Sound bathing is for comfort/quality of life,
not intended to diagnose, treat or cure, and never substitutes for symptom
assessment, medications or licensed care. Avoid claims about healing frequencies,
pain reduction, sleep improvement, cortisol, nervous-system reset or evidence
of therapeutic efficacy. A person may choose quiet instead.
An end-of-life doula provides nonclinical emotional, practical and legacy support;
training and services vary. Do not claim a statutory license or standardized
credential, legal decision-making authority, nursing functions, medication
advice, prognosis expertise or mandatory bedside availability. Doula support
coordinates with the hospice team and respects consent and privacy.
These integrative modalities are not covered by Medicare or Medi-Cal.
Eternal Life Hospice covers their expense at no additional expense to families.
Keep that separate from the core clinical hospice benefit and discuss
individual preferences and availability with the team; never promise any
particular modality will be appropriate or available for every patient.
Local guidance uses actual addresses to confirm care availability with intake.
Do not invent facilities, partnerships, offices, staff, testimonials, response
times, demographics, visit frequencies or universal coverage by city.
No invented news, statistics, trend growth, survey findings or future policy
changes. Contemporary subjects here are digital coordination, choice,
nonclinical support and seasonal planning, not claims that popularity has
been measured. No medical procedures, dosing, treatment directions, diagnosis,
eligibility checklists or emergency directions contrary to the patient's plan.
Official sources for fact-checking: Medicare.gov hospice coverage; CMS hospice
overview (updated September 2026); Ready LA County rainy-weather planning;
Ready.gov power outage planning. Local authorities' directions and the
individual hospice emergency plan take precedence in emergencies.
"""


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_briefs():
    lines = BRIEFS.read_text().splitlines()[1:]
    result = []
    for index, line in enumerate(lines):
        title, angle, place, category, photo_query, style = line.split("|")
        links = [
            {"label": "hospice care", "url": "/hospice-care"},
            {"label": "Family Guide", "url": "/family-guide"},
        ]
        if place != "national":
            links += [
                {"label": f"care questions in {place}", "url": CITY_ROUTES[place]},
                {"label": "service-area guidance", "url": "/hospice-ventura-and-los-angeles-county-ca"},
            ]
        elif category == "Integrative Comfort":
            links += [
                {"label": "integrative comfort options", "url": "/resources/comfort-therapies"},
                {"label": "sound-bath information", "url": "/sound-bath"},
            ]
        else:
            links.append({"label": "Medicare hospice resource", "url": "/resources/medicare-hospice-benefit"})
        result.append({
            "date": (date(2026, 10, 22) + timedelta(days=index)).isoformat(),
            "title": title, "slug": slugify(title), "angle": angle,
            "place": place, "category": category, "photoQuery": photo_query,
            "style": style, "targetWords": TARGETS[index % len(TARGETS)],
            "links": links,
        })
    if len(result) != 71 or result[-1]["date"] != "2026-12-31":
        raise ValueError("Q4 briefs must contain exactly 71 daily entries")
    return result


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def words(article):
    text = " ".join([article["lede"]] + [
        s["heading"] + " " + " ".join(s["paragraphs"]) for s in article["sections"]
    ])
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return len(re.findall(r"\b[\w’'-]+\b", text))


def validate_article(article, brief):
    required = {"description", "lede", "sections", "ctaHeading", "ctaCopy"}
    if not required <= article.keys() or not isinstance(article["sections"], list):
        raise ValueError("Invalid article structure")
    if len(article["sections"]) < 3:
        raise ValueError("Article needs at least three substantive sections")
    if any(not s.get("heading") or not s.get("paragraphs") or
           not all(isinstance(p, str) and len(p.split()) >= 20 for p in s["paragraphs"])
           for s in article["sections"]):
        raise ValueError("Invalid or thin article section")
    text = " ".join([article["lede"]] + [p for s in article["sections"] for p in s["paragraphs"]])
    link_paths = re.findall(r"\[[^\]]+\]\((/[^)\s]+)\)", text)
    if len(link_paths) < 3 or len(set(link_paths)) < 3:
        raise ValueError("Article needs three distinct contextual internal links")
    if any(path not in {a["url"] for a in brief["links"]} for path in link_paths):
        raise ValueError("Unapproved or potentially broken internal link")
    if re.search(r"overwhelm|in today.s fast.paced|healing frequenc|cortisol|nervous.system reset", text, re.I):
        raise ValueError("Prohibited language or medical claim")
    count = words(article)
    if not max(350, int(brief["targetWords"] * .8)) <= count <= brief["targetWords"] * 1.3:
        raise ValueError(f"Length is {count}; target is {brief['targetWords']}")
    if not 100 <= len(article["description"]) <= 220:
        raise ValueError("Description length outside editorial range")
    if "hospice" not in text.lower():
        raise ValueError("Missing contextual hospice language")
    return count


def author_one(brief, all_briefs, existing_titles):
    path = CACHE / "articles" / (brief["slug"] + ".json")
    if path.exists():
        article = json.loads(path.read_text())
        validate_article(article, brief)
        return article
    # Values stay inside the request and are never printed or serialized.
    key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "")
    base = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "").rstrip("/")
    if not key or not base:
        raise RuntimeError("The existing AI integration is not configured")
    system = (
        "You are drafting original family-facing healthcare editorial copy for "
        "The Eternal Journal. Work only from the supplied fact packet and brief. "
        "Do not invent claims or news. Return one complete article as JSON. "
        "Plain, warm, specific prose; no metaphors for explaining care. "
        "Avoid Oxford commas and all forms of 'overwhelm'. No fear-based marketing, "
        "no fake patients, dialogue or statistics, no generic repeated boilerplate. "
        "Vary sentence rhythm and section structure to match the requested style. "
        "Each article must answer its narrow question, rather than repeat a service "
        "landing page. Use the shared theme 'hospice care' naturally and article-specific "
        "terms. Personalization begins with listening on the first call. "
        "Include at least THREE DIFFERENT contextual internal links spread through "
        "the body using [natural anchor text](/approved-path) syntax, only from the "
        "provided links. Never put literal HTML in the response. "
        "Use sound bathing and death/end-of-life doula support prominently where "
        "relevant, without forcing it into unrelated benefit details. "
        "If a complementary modality is mentioned, maintain consent, nonclinical "
        "boundaries and accurate funding. Do not use 'at no cost' next to benefit "
        "coverage. Cite no source, regulation or statistic not in the fact packet. "
        "No medical or legal advice. Use positive, team-based reassurance and a "
        "specific no-pressure CTA, not negative contrasts. "
        "Return exactly: description (100-220 chars), lede (40-80 words), sections "
        "(array of {heading, paragraphs: [strings]}), ctaHeading and ctaCopy. "
        "Each paragraph is substantive (at least 20 words); at least three sections. "
        "The complete lede and sections must reach the assigned target word "
        "count within 20 percent. Follow the section and paragraph word budgets "
        "in structure_requirements. Develop specific practical questions and "
        "considerations within the narrow topic; do not pad with repeated assurances."
    )
    feedback = ""
    for attempt in range(3):
        payload = {
            "model": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({
                    "facts": FACTS, "brief": brief,
                    "existing_topics_to_avoid_repeating": existing_titles,
                    "other_new_titles_with_distinct_jobs": [b["title"] for b in all_briefs],
                    "structure_requirements": {
                        "section_count": max(3, math.ceil(brief["targetWords"] / 140)),
                        "paragraphs_per_section": 2,
                        "words_per_paragraph": "60-85" if brief["targetWords"] >= 750 else "45-65",
                        "minimum_total_words": max(350, int(brief["targetWords"] * .8)),
                        "target_total_words": brief["targetWords"],
                    },
                    "revision_needed": feedback,
                })},
            ],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": 6500,
        }
        req = urllib.request.Request(
            base + "/chat/completions", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.load(response)
            article = json.loads(data["choices"][0]["message"]["content"])
            count = validate_article(article, brief)
            article.update({k: brief[k] for k in ("date", "slug", "title", "category")})
            article["seoTitle"] = brief["title"]
            article["readMinutes"] = max(2, math.ceil(count / 220))
            article["editorialFocus"] = brief["angle"]
            article["format"] = brief["style"]
            if "Medicare" in brief["title"] or "Election Statement" in brief["title"] or \
                    "Six Months" in brief["title"] or "Home Health" in brief["title"]:
                article["sources"] = [SOURCES["medicare"], SOURCES["cms"]]
            elif "Power" in brief["title"]:
                article["sources"] = [SOURCES["power"]]
            elif "Weather" in brief["title"] or "Rainy" in brief["title"]:
                article["sources"] = [SOURCES["ventura"] if brief["place"] == "Ventura" else SOURCES["weather"]]
            atomic_json(path, article)
            print(f"ARTICLE {brief['date']} {count} words {brief['slug']}", flush=True)
            return article
        except urllib.error.HTTPError as error:
            # Do not echo response bodies or request headers containing credentials.
            feedback = f"HTTP status {error.code}"
            if error.code in (400, 401, 403, 404):
                raise RuntimeError(f"AI integration request failed with status {error.code}") from None
        except (ValueError, KeyError, TimeoutError, urllib.error.URLError) as error:
            feedback = str(error)[:250]
        time.sleep(2 + attempt)
    raise RuntimeError(f"Could not finish article {brief['slug']}: {feedback}")


def strip_markup(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(value)))).strip()


def dhash(image):
    values = list(image.convert("L").resize((9, 8)).getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (values[y * 9 + x] > values[y * 9 + x + 1])
    return bits


def query_photos(query):
    params = {
        "action": "query", "generator": "search", "gsrsearch": query + " filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 24, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1800, "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as response:
        data = json.load(response)
    return sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 999))


def prepare_photos(briefs):
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    records = json.loads(PHOTO_SOURCES.read_text()) if PHOTO_SOURCES.exists() else []
    local_slugs = {b["slug"] for b in briefs if b["place"] != "national"}
    review = json.loads(PHOTO_REVIEW.read_text()) if PHOTO_REVIEW.exists() else {}
    selected = {r["slug"]: r for r in records
                if r["slug"] in local_slugs and
                r["sourceUrl"] != review.get(r["slug"], {}).get("rejectSource") and
                (not review.get(r["slug"], {}).get("sourceTitle") or
                 r["sourceTitle"] == review[r["slug"]]["sourceTitle"]) and
                not re.search(r"hotel|hampton inn", r["sourceTitle"], re.I)}
    stock_records = {r["slug"]: r for r in records if r.get("sourceName") == "Pexels"}
    selected.update(stock_records)
    original_urls = {r["sourceUrl"] for r in records}
    hashes = []
    # Reject the same work in a different crop/encoding, including existing Journal photos.
    current_paths = set()
    for source in (ROOT / "content" / "30-day-journal").glob("*.json"):
        for article in json.loads(source.read_text()):
            if article.get("heroImage"):
                current_paths.add(PUBLIC / article["heroImage"].lstrip("/"))
    for page in (PUBLIC / "blog").glob("*.html"):
        m = re.search(r'property="og:image" content="https://eternallifehospice.com(/assets/img/[^"]+)', page.read_text())
        if m:
            current_paths.add(PUBLIC / m.group(1).lstrip("/"))
    current_paths.update(PHOTO_DIR.glob("*.jpg"))
    for path in current_paths:
        if path.exists():
            with Image.open(path) as image:
                hashes.append(dhash(image))
    banned = re.compile(r"\b(map|diagram|drawing|painting|logo|coat of arms|floor plan|document|flag of|coat-of-arms|chart|scanned|scan of|hotel|hospital|clinic|inn|prisoner|foundation|handwriting|responsive web)\b", re.I)
    for brief in briefs:
        if brief["place"] == "national":
            continue
        if brief["slug"] in selected and (PUBLIC / selected[brief["slug"]]["heroImage"].lstrip("/")).exists():
            continue
        queries = [review.get(brief["slug"], {}).get("photoQuery", brief["photoQuery"])]
        if brief["place"] != "national":
            queries += [brief["place"] + " California", brief["place"] + " park California"]
        else:
            queries += [brief["photoQuery"].replace(" photograph", ""), "California garden landscape photograph"]
        chosen = None
        for query in queries:
            candidates = query_photos(query)
            time.sleep(2)
            for candidate in candidates:
                info = candidate.get("imageinfo", [{}])[0]
                meta = info.get("extmetadata", {})
                license_name = strip_markup(meta.get("LicenseShortName", {}).get("value", ""))
                license_url = meta.get("LicenseUrl", {}).get("value", "")
                title = candidate.get("title", "").removeprefix("File:")
                approved_title = review.get(brief["slug"], {}).get("sourceTitle")
                if approved_title and title != approved_title:
                    continue
                if info.get("mime") != "image/jpeg" or \
                        info.get("width", 0) < 900 or info.get("height", 0) < 500 or \
                        banned.search(title):
                    continue
                if not (license_name.startswith("CC BY") or license_name in
                        ("CC0", "Public domain", "PDM", "CC-zero")) or \
                        "NC" in license_name or "ND" in license_name:
                    continue
                source_url = info.get("descriptionurl", "")
                if not source_url or source_url in original_urls:
                    continue
                description = strip_markup(meta.get("ImageDescription", {}).get("value", title))
                # Exact location must be supported by source metadata for local stories.
                if brief["place"] != "national" and brief["place"].lower() not in \
                        (title + " " + description).lower():
                    continue
                download_url = info.get("thumburl") or info.get("url", "")
                if not download_url:
                    continue
                try:
                    req = urllib.request.Request(download_url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=60) as response:
                        raw = response.read(30_000_001)
                    if len(raw) > 30_000_000:
                        continue
                    import io
                    image = Image.open(io.BytesIO(raw)).convert("RGB")
                    image_hash = dhash(image)
                    if any((image_hash ^ old).bit_count() <= 6 for old in hashes):
                        continue
                    image.thumbnail((1800, 1400))
                    path = PHOTO_DIR / (brief["slug"] + ".jpg")
                    image.save(path, quality=86, optimize=True)
                    if not license_url:
                        license_url = "https://creativecommons.org/publicdomain/mark/1.0/"
                    if license_url.startswith("//"):
                        license_url = "https:" + license_url
                    license_url = license_url.replace("http://", "https://")
                    chosen = {
                        "slug": brief["slug"], "heroImage": "/" + str(path.relative_to(PUBLIC)),
                        "heroImageAlt": ("Photograph of " + description)[:240],
                        "author": strip_markup(meta.get("Artist", {}).get("value", "Wikimedia Commons contributor")),
                        "sourceUrl": source_url, "sourceName": "Wikimedia Commons", "license": license_name,
                        "licenseUrl": license_url, "sourceTitle": title,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    hashes.append(image_hash)
                    original_urls.add(source_url)
                    break
                except (OSError, urllib.error.URLError, ValueError):
                    continue
            if chosen:
                break
        if not chosen:
            raise RuntimeError(f"No distinct licensed photograph found for {brief['slug']}")
        selected[brief["slug"]] = chosen
        atomic_json(PHOTO_SOURCES, [selected[b["slug"]] for b in briefs if b["slug"] in selected])
        print(f"PHOTO {brief['date']} {chosen['sourceTitle']} [{chosen['license']}]", flush=True)


def prepare_stock_photos(briefs):
    """Use only free Pexels photographic search results, never premium previews."""
    import io
    candidates_path = ROOT.parent / "attached_assets/image_search/q4-photo-candidates.json"
    candidates = json.loads(candidates_path.read_text())
    records = json.loads(PHOTO_SOURCES.read_text()) if PHOTO_SOURCES.exists() else []
    local_slugs = {b["slug"] for b in briefs if b["place"] != "national"}
    review = json.loads(PHOTO_REVIEW.read_text()) if PHOTO_REVIEW.exists() else {}
    selected = {r["slug"]: r for r in records
                if r["slug"] in local_slugs or (r.get("sourceName") == "Pexels" and
                (not review.get(r["slug"], {}).get("stockId") or
                 r.get("stockId") == review[r["slug"]]["stockId"]))}
    used_ids = {r.get("stockId") for r in selected.values()}
    hashes = []
    for r in selected.values():
        with Image.open(PUBLIC / r["heroImage"].lstrip("/")) as im:
            hashes.append(dhash(im))
    for page in (PUBLIC / "blog").glob("*.html"):
        match = re.search(r'property="og:image" content="https://eternallifehospice.com(/assets/img/[^"]+)', page.read_text())
        if match:
            with Image.open(PUBLIC / match.group(1).lstrip("/")) as im:
                hashes.append(dhash(im))
    pool = []
    for c in candidates:
        url = c.get("imageUrl", "")
        match = re.search(r"https://images\.pexels\.com/photos/(\d+)/", url)
        approved_ids = {r.get("stockId") for r in review.values()}
        if not match or (match.group(1) not in approved_ids and re.search(
                r"\b(woman|man|child|parents|couple|gardener|person)\b", c.get("title", ""), re.I)):
            continue
        c["stockId"] = match.group(1)
        pool.append(c)
    download_dir = ROOT.parent / "attached_assets/image_search/q4"
    download_dir.mkdir(parents=True, exist_ok=True)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    for brief in briefs:
        if brief["place"] != "national" or brief["slug"] in selected:
            continue
        terms = set(re.findall(r"[a-z]{4,}", brief["photoQuery"].lower()))
        ranked = sorted(pool, key=lambda c: -len(terms & set(re.findall(
            r"[a-z]{4,}", (c.get("title", "") + " " + c.get("query", "")).lower()))))
        approved_id = review.get(brief["slug"], {}).get("stockId")
        if approved_id:
            ranked = [c for c in ranked if c["stockId"] == approved_id]
        chosen = None
        for c in ranked:
            if c["stockId"] in used_ids:
                continue
            url = c["imageUrl"].split("?")[0] + "?auto=compress&cs=tinysrgb&w=1800"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=50) as response:
                    raw = response.read(25_000_001)
                if len(raw) > 25_000_000:
                    continue
                image = Image.open(io.BytesIO(raw)).convert("RGB")
                image_hash = dhash(image)
                if image.width < 900 or image.height < 500 or \
                        any((image_hash ^ old).bit_count() <= 7 for old in hashes):
                    continue
                (download_dir / (c["stockId"] + ".jpg")).write_bytes(raw)
                image.thumbnail((1800, 1400))
                path = PHOTO_DIR / (brief["slug"] + ".jpg")
                image.save(path, quality=86, optimize=True)
                title = re.sub(r"^Free\s+|\s+Stock Photo$", "", c["title"]).strip()
                chosen = {
                    "slug": brief["slug"], "heroImage": "/" + str(path.relative_to(PUBLIC)),
                    "heroImageAlt": title[:240], "author": "Pexels contributor",
                    "sourceName": "Pexels", "sourceUrl": c["imageUrl"].split("?")[0],
                    "license": "Pexels License", "licenseUrl": "https://www.pexels.com/license/",
                    "sourceTitle": title, "stockId": c["stockId"],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                used_ids.add(c["stockId"])
                hashes.append(image_hash)
                break
            except (OSError, urllib.error.URLError, ValueError):
                continue
        if not chosen:
            raise RuntimeError(f"No distinct suitable stock photograph for {brief['slug']}")
        selected[brief["slug"]] = chosen
        atomic_json(PHOTO_SOURCES, [selected[b["slug"]] for b in briefs if b["slug"] in selected])
        print(f"STOCK PHOTO {brief['date']} {chosen['stockId']}: {chosen['sourceTitle']}", flush=True)


def assemble(briefs):
    if OUTPUT.exists():
        raise RuntimeError("The final editorial source already exists. Edit that source directly; do not overwrite reviewed copy.")
    photos = {r["slug"]: r for r in json.loads(PHOTO_SOURCES.read_text())}
    articles = []
    paragraphs = set()
    for brief in briefs:
        article = json.loads((CACHE / "articles" / (brief["slug"] + ".json")).read_text())
        article["lede"] = article["lede"].replace("death-end-of-life doula", "end-of-life doula")
        for section in article["sections"]:
            section["paragraphs"] = [p.replace("death-end-of-life doula", "end-of-life doula")
                                     for p in section["paragraphs"]]
        validate_article(article, brief)
        photo = photos[brief["slug"]]
        if not (PUBLIC / photo["heroImage"].lstrip("/")).exists():
            raise ValueError("Photograph is missing")
        article["heroImage"] = photo["heroImage"]
        article["heroImageAlt"] = photo["heroImageAlt"]
        article["photoCredit"] = {k: photo[k] for k in ("author", "sourceUrl", "license", "licenseUrl")}
        article["photoCredit"]["sourceName"] = photo.get("sourceName", "Wikimedia Commons")
        article["location"] = brief["place"]
        text = " ".join([article["lede"]] + [p for s in article["sections"] for p in s["paragraphs"]])
        article["integrativeNote"] = bool(re.search(r"sound bath|doula|integrative|complementary", text, re.I))
        for section in article["sections"]:
            for p in section["paragraphs"]:
                normalized = re.sub(r"\W+", "", p.lower())
                if normalized in paragraphs:
                    raise ValueError("Repeated full paragraph across Q4 stories")
                paragraphs.add(normalized)
        articles.append(article)
    if len({a["heroImage"] for a in articles}) != 71:
        raise ValueError("Every new story needs a different photograph")
    atomic_json(OUTPUT, articles)
    report = ["# Eternal Journal — October 22–December 31, 2026", "",
              "71 complete daily articles; America/Los_Angeles publication dates.",
              "All images are distinct licensed photographs, with visible credit on each page.",
              "Future pages remain hidden by the existing server-side publication gate.", "",
              "| Date | Article | Words | Read time | Format |", "|---|---|---:|---:|---|"]
    for article in articles:
        report.append(f"| {article['date']} | {article['title']} | {words(article)} | {article['readMinutes']} min | {article['format']} |")
    atomic_json(ROOT / "content" / "journal-q4-editorial-metrics.json", [
        {"date": a["date"], "slug": a["slug"], "title": a["title"], "words": words(a),
         "readMinutes": a["readMinutes"], "format": a["format"]} for a in articles
    ])
    report_path = ROOT.parent / "exports" / "journal" / "q4-2026-editorial-calendar.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n")
    print(f"ASSEMBLED {len(articles)} articles; {min(words(a) for a in articles)}–{max(words(a) for a in articles)} words", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--articles", action="store_true")
    parser.add_argument("--photos", action="store_true")
    parser.add_argument("--stock-photos", action="store_true")
    parser.add_argument("--assemble", action="store_true")
    args = parser.parse_args()
    briefs = load_briefs()
    if args.articles:
        existing_titles = []
        for path in (ROOT / "content" / "30-day-journal").glob("*.json"):
            existing_titles.extend(a["title"] for a in json.loads(path.read_text()))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(author_one, b, briefs, existing_titles) for b in briefs]
            for future in concurrent.futures.as_completed(futures):
                future.result()
    if args.photos:
        prepare_photos(briefs)
    if args.stock_photos:
        prepare_stock_photos(briefs)
    if args.assemble:
        assemble(briefs)


if __name__ == "__main__":
    main()
