"""Export one Thryv CSV using existing, publicly hosted Journal photographs."""
import csv
import json
from pathlib import Path
import re
from social_copy_contract import expected_rows, validate_rows

ROOT = Path(__file__).resolve().parents[2]
source_posts = json.loads((ROOT / "generated-artifacts/social-2026-10-27-31/posts.json").read_text())
articles = json.loads((ROOT / "website/content/30-day-journal/additional-2026-q4.json").read_text())
copy = {row["slug"]: row for row in json.loads(
    (ROOT / "exports/social/october-27-31-2026-copy.json").read_text())}
credits = {row["slug"]: row for row in json.loads(
    (ROOT / "website/content/journal-q4-photo-sources.json").read_text())}
expected = expected_rows(
    json.loads((ROOT / "exports/social/october-27-31-2026-copy.json").read_text()),
    {row["slug"]: row for row in articles}, credits, source_posts)
# Captions define the current cadence; the original review packet only supplies
# article links and photo credits, which are shared across the platforms.
posts = []
for article in copy.values():
    template = next(post for post in source_posts if post["slug"] == article["slug"])
    for platform in article["posts"]:
        posts.append({**template, "platform": platform})
keywords = {row["id"]: row for row in json.loads(
    (ROOT / "website/content/seo-keyword-master.json").read_text())["keywords"]}
targets = {
    "2026-10-27": [7, 8, 95],
    "2026-10-28": [7, 12, 87, 89, 95],
    "2026-10-29": [7, 81, 95],
    "2026-10-30": [7, 8, 12, 27, 95],
    "2026-10-31": [7, 81, 95],
}
columns = ["Link", "Image", "Caption", "Title", "Approved", "Recycle", "Comment", "Schedule"]
target = ROOT / "generated-artifacts/Eternal-Thryv-October-27-31-2026-SEO-Daily-All-Platforms.csv"
rows, audit = [], []
for post in posts:
    row = dict(post["row"])
    spec = copy[post["slug"]]["posts"][post["platform"]]
    row.update(expected[post["proposedDate"], post["platform"]])
    row["Comment"] = (
        f"{post['platform']} | Proposed date {post['proposedDate']} | "
        "Posting time not selected (America/Los_Angeles). "
        "Original publicly hosted Journal photograph, not the newly formatted branded graphic. "
        "Select the matching social profile in Thryv; the CSV has no network-assignment column. "
        "Keep unapproved until reviewed; confirm the article is live before posting. "
        f"Photo: {post['photo']['author']} / {post['photo']['license']}."
    )
    matched = []
    for identifier in targets[post["proposedDate"]]:
        phrase = keywords[identifier]["phrase"]
        assert post["proposedDate"] in keywords[identifier]["draftDates"], (identifier, "Not matched to article")
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", row["Caption"], re.IGNORECASE):
            matched.append({"id": identifier, "phrase": phrase, "coverage": "exact"})
        elif identifier == 27 and "hospice care in calabasas" in row["Caption"].casefold():
            matched.append({"id": identifier, "phrase": phrase, "coverage": "semantic",
                            "publicWording": "hospice care in Calabasas"})
        else:
            raise AssertionError((post["proposedDate"], post["platform"], identifier, "Keyword missing"))
    assert len(matched) >= 3
    limit = {"GBP": 1500, "Facebook": 63206, "LinkedIn": 3000, "Pinterest": 500}[post["platform"]]
    assert len(row["Caption"]) <= limit, (post["platform"], len(row["Caption"]))
    assert post["platform"] != "Pinterest" or len(spec["title"]) <= 100
    assert post["platform"] != "LinkedIn" or len(row["Caption"].splitlines()[0]) <= 110
    row["Comment"] += " SEO alignment: " + "; ".join(
        f"{item['id']} {item['phrase']} ({item['coverage']})" for item in matched) + "."
    audit.append({"date": post["proposedDate"], "platform": post["platform"],
                  "article": row["Link"], "characters": len(row["Caption"]),
                  "keywordMatches": matched})
    rows.append(row)
assert len(rows) == 20
expected_days = {article["date"] for article in copy.values()}
for platform in ("GBP", "Pinterest", "Facebook", "LinkedIn"):
    assert {post["proposedDate"] for post in posts if post["platform"] == platform} == expected_days
assert len({(post["proposedDate"], post["platform"]) for post in posts}) == 20
validate_rows(rows, expected)
with target.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
with target.open(encoding="utf-8-sig", newline="") as stream:
    parsed = list(csv.DictReader(stream))
assert parsed == rows
assert all(row["Image"].startswith("https://") and row["Approved"] == "FALSE"
           and not row["Schedule"] for row in parsed)
target.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False))
print(f"Created and verified {len(rows)} rows: {target.relative_to(ROOT)}")
