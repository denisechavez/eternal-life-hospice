"""Export one Thryv CSV using existing, publicly hosted Journal photographs."""
import csv
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
posts = json.loads((ROOT / "generated-artifacts/social-2026-10-27-31/posts.json").read_text())
articles = json.loads((ROOT / "website/content/30-day-journal/additional-2026-q4.json").read_text())
photos = {row["slug"]: row["heroImage"] for row in articles}
columns = ["Link", "Image", "Caption", "Title", "Approved", "Recycle", "Comment", "Schedule"]
target = ROOT / "generated-artifacts/Eternal-Thryv-October-27-31-2026.csv"
rows = []
for post in posts:
    row = dict(post["row"])
    origin = urlsplit(row["Link"])
    row["Image"] = f"{origin.scheme}://{origin.netloc}" + photos[post["slug"]]
    row["Caption"] = row["Caption"].replace("CC BY-SA 4.0; cropped.", "CC BY-SA 4.0; resized.")
    row["Approved"], row["Recycle"], row["Schedule"] = "FALSE", "FALSE", ""
    row["Comment"] = (
        f"{post['platform']} | Proposed date {post['proposedDate']} | "
        "Posting time not selected (America/Los_Angeles). "
        "Original publicly hosted Journal photograph, not the newly formatted branded graphic. "
        "Select the matching social profile in Thryv; the CSV has no network-assignment column. "
        "Keep unapproved until reviewed; confirm the article is live before posting. "
        f"Photo: {post['photo']['author']} / {post['photo']['license']}."
    )
    rows.append(row)
assert len(rows) == 14
with target.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
with target.open(encoding="utf-8-sig", newline="") as stream:
    parsed = list(csv.DictReader(stream))
assert parsed == rows
assert all(row["Image"].startswith("https://") and row["Approved"] == "FALSE"
           and not row["Schedule"] for row in parsed)
print(f"Created and verified {len(rows)} rows: {target.relative_to(ROOT)}")
