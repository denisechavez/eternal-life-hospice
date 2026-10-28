"""Exact input contract shared by the Thryv and manual social exporters."""
from urllib.parse import urlsplit

PLATFORMS = {"GBP", "Facebook", "LinkedIn", "Pinterest"}
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
THRYV_CREDIT = "Photo: Niceley, CC BY-SA 4.0; resized."
MANUAL_CREDIT = "Photo: Niceley, CC BY-SA 4.0; cropped and color-adjusted."


def thryv_caption(spec, link, credit):
    caption = spec["caption"].replace("{url}", link)
    if credit["license"] == "CC BY-SA 4.0":
        # Preserve the approved credit transformation, but do not silently
        # attribute a future photograph to the current photographer.
        if (credit["author"] != "Niceley"
                or credit["licenseUrl"].rstrip("/") != LICENSE_URL.rstrip("/")):
            raise ValueError("Unsupported CC BY-SA credit: review the caption attribution")
        caption += f"\n\n{THRYV_CREDIT}\n{credit['sourceUrl']}\n{LICENSE_URL}"
    return caption.replace("CC BY-SA 4.0; cropped.", "CC BY-SA 4.0; resized.")


def manual_caption(caption):
    return caption.replace(THRYV_CREDIT, MANUAL_CREDIT)


def expected_rows(topics, articles, credits, source_posts):
    """Build authoritative fields without trusting the generated CSV."""
    expected, dates, slugs = {}, set(), set()
    for topic in topics:
        date, slug = topic["date"], topic["slug"]
        if date in dates or slug in slugs:
            raise ValueError(f"Duplicate source date or slug: {date} / {slug}")
        dates.add(date)
        slugs.add(slug)
        if set(topic["posts"]) != PLATFORMS:
            raise ValueError(f"Incomplete source platforms for {date}")
        if slug not in articles or slug not in credits:
            raise ValueError(f"Missing article or photo credit: {slug}")
        templates = [post for post in source_posts if post["slug"] == slug]
        if not templates:
            raise ValueError(f"Missing source article link: {slug}")
        links = {post["row"]["Link"] for post in templates}
        if len(links) != 1 or any(post["proposedDate"] != date for post in templates):
            raise ValueError(f"Source link/date mismatch: {date} / {slug}")
        link = links.pop()
        origin = urlsplit(link)
        if (origin.scheme != "https" or not origin.netloc
                or origin.path != f"/blog/{slug}" or origin.query or origin.fragment):
            raise ValueError(f"Source URL/slug mismatch: {date} / {slug}")
        for platform, spec in topic["posts"].items():
            expected[date, platform] = {
                "Title": f"{platform} | {date} | {spec['title']}",
                "Caption": thryv_caption(spec, link, credits[slug]),
                "Link": link,
                "Image": f"{origin.scheme}://{origin.netloc}{articles[slug]['heroImage']}",
                "Approved": "FALSE", "Recycle": "FALSE", "Schedule": "",
            }
    if len(expected) != 20:
        raise ValueError(f"Expected 20 source posts, found {len(expected)}")
    return expected


def validate_rows(rows, expected):
    lookup = {}
    for row in rows:
        parts = row.get("Title", "").split(" | ", 2)
        if len(parts) != 3:
            raise ValueError("Malformed CSV Title; rebuild the Thryv CSV")
        platform, date, _ = parts
        key = date, platform
        if key in lookup:
            raise ValueError(f"Duplicate CSV pair: {date} / {platform}")
        if key not in expected:
            raise ValueError(f"Unexpected CSV pair: {date} / {platform}")
        for field, value in expected[key].items():
            if row.get(field) != value:
                raise ValueError(
                    f"Stale CSV {field}: {date} / {platform}; "
                    "rebuild with create-thryv-upload-csv.py before packaging")
        lookup[key] = row
    missing = expected.keys() - lookup.keys()
    if missing:
        raise ValueError(f"Missing CSV pairs: {sorted(missing)}; rebuild the Thryv CSV")
    return lookup


def validate_manifest(manifest, topics, articles, formats):
    expected = {
        (topic["date"], platform): (topic, articles[topic["slug"]])
        for topic in topics for platform in topic["posts"]
    }
    seen = set()
    for record in manifest:
        key = record["date"], record["platform"]
        if key in seen or key not in expected:
            raise ValueError(f"Duplicate or unexpected image manifest pair: {key}")
        seen.add(key)
        topic, article = expected[key]
        width, height = formats[key[1]]
        fields = {
            "image_file": f"{key[1]}/{key[0]}.jpg",
            "headline": topic["headline"].replace("\n", " "),
            "source_photo": "website/elh-preview" + article["heroImage"],
            "dimensions": {"width": width, "height": height},
        }
        for field, value in fields.items():
            if record.get(field) != value:
                raise ValueError(f"Stale image manifest {field}: {key}; render images again")
    if seen != expected.keys():
        raise ValueError(f"Missing image manifest pairs: {sorted(expected.keys() - seen)}")
