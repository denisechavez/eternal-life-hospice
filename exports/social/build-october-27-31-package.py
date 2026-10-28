#!/usr/bin/env python3
"""Generate a private social review package. No posting or network writes."""
import argparse
import base64
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import zipfile

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "website/elh-preview"
OUT = ROOT / "generated-artifacts/social-2026-10-27-31"
FORMATS = {"GBP": (1200, 900), "Facebook": (1080, 1350),
           "LinkedIn": (1200, 627), "Pinterest": (1000, 1500)}
COLUMNS = ["Link", "Image", "Caption", "Title", "Approved", "Recycle", "Comment", "Schedule"]
FONTS = {}


def face(name, size):
    return ImageFont.truetype(io.BytesIO(FONTS[name]), size)


def wrap(draw, text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            trial = (line + " " + word).strip()
            if line and draw.textlength(trial, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def graphic(topic, platform, source, logo, credit):
    w, h = FORMATS[platform]
    image = Image.new("RGB", (w, h), "#F5F0EB")
    draw = ImageDraw.Draw(image)
    wide = platform == "LinkedIn"
    if wide:
        photo_box = (int(w * .49), 0, w, h)
        title_x, title_y, title_width = 45, 95, int(w * .42)
        title_size = 52
        logo_width = 180
    else:
        photo_height = int(h * (.64 if platform == "Pinterest" else .61 if platform == "GBP" else .65))
        photo_box = (0, 0, w, photo_height)
        title_x, title_y, title_width = int(w * .055), photo_height + 28, int(w * .88)
        title_size = 56 if platform == "GBP" else 66
        logo_width = 180 if platform == "GBP" else 195
    pw, ph = photo_box[2] - photo_box[0], photo_box[3] - photo_box[1]
    image.paste(ImageOps.fit(source, (pw, ph), centering=(.5, .5)), photo_box[:2])
    if wide:
        draw.line((photo_box[0], 0, photo_box[0], h), fill="#C9B07E", width=4)
        # Give the bottom-right logo a consistent, legible cream field.
        draw.rectangle((w - 255, h - 122, w, h), fill="#F5F0EB")
    else:
        draw.line((0, photo_box[3], w, photo_box[3]), fill="#C9B07E", width=4)
    font = face("serif", title_size)
    y = title_y
    for line in wrap(draw, topic["headline"], font, title_width):
        draw.text((title_x, y), line, font=font, fill="#48213F")
        y += int(title_size * 1.12)
    y += 13
    small = face("sans", 24 if wide else 25 if platform == "GBP" else 29)
    for line in wrap(draw, topic["support"], small, title_width):
        draw.text((title_x, y), line, font=small, fill="#494349")
        y += int(small.size * 1.2)
    if y > h - (62 if wide else 125):
        raise ValueError(f"Text exceeds safe area: {topic['date']} {platform}")
    brand = logo.copy()
    brand.thumbnail((logo_width, 83))
    image.paste(brand, (w - brand.width - 28, h - brand.height - 24), brand)
    if platform != "LinkedIn":
        draw.text((title_x, h - 45), "eternallifehospice.com", font=face("sans", 20), fill="#594657")
    if credit["license"] == "CC BY-SA 4.0":
        # Keep required photo attribution visible on the exported image too.
        text = "Photo: Niceley · CC BY-SA 4.0 · cropped · links in caption"
        font = face("sans", 15 if wide else 17)
        height = 30
        top = photo_box[1] if wide else photo_box[3] - height
        box = (photo_box[0], top, photo_box[2], top + height)
        draw.rectangle(box, fill="#F5F0EB")
        draw.text((box[0] + 10, box[1] + 5), text, font=font, fill="#494349")
    return image


def build(origin):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    (OUT / "thryv-drafts").mkdir(exist_ok=True)
    for key, filename in [("serif", "fraunces-latin.woff2"), ("sans", "JostELH-Regular.woff2")]:
        font = TTFont(PUBLIC / "assets/fonts" / filename)
        font.flavor = None
        stream = io.BytesIO()
        font.save(stream)
        FONTS[key] = stream.getvalue()
    logo = Image.open(PUBLIC / "assets/logo-eternal-trans.png").convert("RGBA")
    logo = logo.crop(logo.getbbox())
    # The plum logo is the site's official asset; do not invent a new mark.
    topics = json.loads(Path(__file__).with_name("october-27-31-2026-copy.json").read_text())
    articles = json.loads((ROOT / "website/content/30-day-journal/additional-2026-q4.json").read_text())
    sources = json.loads((ROOT / "website/content/journal-q4-photo-sources.json").read_text())
    posts, sections, summary, notes = [], [], [], []
    for topic in topics:
        article = next(row for row in articles if row["slug"] == topic["slug"])
        credit = next(row for row in sources if row["slug"] == topic["slug"])
        source_path = PUBLIC / article["heroImage"].lstrip("/")
        source = Image.open(source_path).convert("RGB")
        summary.append(f"<tr><td>{topic['date']}</td><td>{html.escape(article['title'])}</td>"
                       f"<td>{', '.join(topic['posts'])}</td></tr>")
        for platform, spec in topic["posts"].items():
            url = origin + "/blog/" + topic["slug"]
            caption = spec["caption"].replace("{url}", url)
            if credit["license"] == "CC BY-SA 4.0":
                caption += ("\n\nPhoto: Niceley, CC BY-SA 4.0; cropped.\n" +
                            credit["sourceUrl"] + "\nhttps://creativecommons.org/licenses/by-sa/4.0/")
            limit = {"GBP": 1500, "Facebook": 63206, "LinkedIn": 3000, "Pinterest": 500}[platform]
            assert len(caption) <= limit, (platform, topic["date"], len(caption))
            assert platform != "Pinterest" or len(spec["title"]) <= 100
            assert platform != "LinkedIn" or len(caption.splitlines()[0]) <= 110
            assert platform != "GBP" or not any(s in caption for s in ("805.", "805-"))
            filename = topic["date"] + "-" + platform.lower() + ".jpg"
            rendered = graphic(topic, platform, source, logo, credit)
            rendered.save(OUT / "images" / filename, quality=88, optimize=True, subsampling=0)
            image_url = origin + "/assets/social/2026-10-27-31/" + filename
            note = (f"REVIEW DRAFT | {platform} | Proposed date {topic['date']} | "
                    "Time not selected; America/Los_Angeles. Image URL is staged, NOT LIVE: "
                    "host the supplied JPEG before import. Confirm article is live before approval. "
                    "No automatic recycling. ")
            if platform == "GBP":
                note += "Use Learn more if Thryv offers a CTA button. "
            if platform == "Pinterest":
                note += "Title is an internal CSV field; verify whether Thryv also maps it to Pin title. "
            note += f"Photo: {credit['author']} / {credit['license']}."
            post = {
                "platform": platform, "proposedDate": topic["date"],
                "articleTitle": article["title"], "slug": topic["slug"],
                "row": {"Link": url, "Image": image_url, "Caption": caption,
                        "Title": f"{platform} | {topic['date']} | {spec['title']}",
                        "Approved": "FALSE", "Recycle": "FALSE",
                        "Comment": note, "Schedule": ""},
                "imageFile": "images/" + filename,
                "dimensions": FORMATS[platform], "characters": len(caption),
                "pinTitle": spec["title"] if platform == "Pinterest" else None,
                "altText": credit["heroImageAlt"] + " Branded graphic: " +
                           topic["headline"].replace("\n", " ") + ".",
                "photo": credit, "sourceDigest": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "imageHostingStatus": "NOT LIVE — awaiting approved hosting",
            }
            posts.append(post)
            encoded = base64.b64encode((OUT / post["imageFile"]).read_bytes()).decode()
            e = html.escape
            sections.append(f"""<section class="post page"><div class="eyebrow">REVIEW DRAFT · {topic['date']} · {platform}</div>
<h2>{e(spec['title'])}</h2><div class="layout"><div class="visual">
<img src="data:image/jpeg;base64,{encoded}" alt="{e(post['altText'])}"><p class="small">{rendered.width} × {rendered.height} · {e(filename)}</p></div>
<div><div class="caption">{e(caption)}</div><p class="small"><b>Article:</b> {e(article['title'])}<br>
<a href="{e(url)}">{e(url)}</a><br><b>Review status:</b> Unapproved, unscheduled. Image hosting pending.<br>
<b>Photo:</b> {e(credit['author'])} · {e(credit['license'])}. Photograph reused from the matching Journal article; cropped for this format.</p>
{('<p class="small"><b>Pin title:</b> '+e(spec['title'])+'</p>') if platform == 'Pinterest' else ''}</div></div></section>""")
            notes.append(f"{topic['date']} | {platform}\n{spec['title']}\n\n{caption}\n\n"
                         f"LINK: {url}\nIMAGE: {post['imageFile']}\nALT: {post['altText']}\n\n{'='*65}\n")
    assert len(posts) == 14
    for platform in FORMATS:
        selected = [post["row"] for post in posts if post["platform"] == platform]
        assert len(selected) == (5 if platform == "GBP" else 3)
        with (OUT / "thryv-drafts" / (platform.lower() + "-DRAFT.csv")).open(
                "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(selected)
    (OUT / "posts.json").write_text(json.dumps(posts, indent=2, ensure_ascii=False))
    (OUT / "captions.txt").write_text("\n".join(notes))
    css = """
    *{box-sizing:border-box}body{background:#f5f0eb;color:#393438;margin:0;font:16px/1.55 Arial,sans-serif}
    main{max-width:1180px;margin:auto;padding:30px}.page{background:#fffdfa;padding:35px;margin-bottom:28px;border-top:4px solid #b6a373}
    h1,h2{font-family:Georgia,serif;color:#48213f;line-height:1.15}h1{font-size:36px}h2{font-size:25px}
    .eyebrow{text-transform:uppercase;letter-spacing:.1em;color:#65565f;font-size:12px;font-weight:bold}
    .layout{display:grid;grid-template-columns:38% 1fr;gap:32px}.visual img{width:100%;max-height:570px;object-fit:contain}
    .caption{white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px}.small{font-size:11px;color:#625b60;overflow-wrap:anywhere}
    table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #ddd4ca}
    .notice{border-left:3px solid #b6a373;padding:15px;background:#f5f0eb}a{color:#48213f}
    @media(max-width:700px){.layout{grid-template-columns:1fr}main{padding:10px}.page{padding:20px}}
    @page{size:11in 8.5in;margin:.35in}
    @media print{body{background:white;font-size:12px}main{padding:0;max-width:none}.page{padding:12px;margin:0;break-after:page;border-top:3px solid #b6a373;min-height:7.65in}
    .layout{grid-template-columns:35% 1fr;gap:25px}.visual img{max-height:555px;width:100%}.caption{font-size:12px;line-height:1.42}
    .small{font-size:9px}h1{font-size:30px}h2{font-size:21px;margin:12px 0}.eyebrow{font-size:10px}.page:last-child{break-after:auto}}
    """
    overview = f"""<section class="page"><div class="eyebrow">Eternal Life Hospice · Social review · October 27–31, 2026</div>
<h1>Four platforms.<br>One thoughtful conversation.</h1><p>14 posts: GBP daily; Facebook, LinkedIn and Pinterest Tuesday, Thursday and Saturday. TikTok and YouTube video work is separate.</p>
<table><thead><tr><th>Proposed date</th><th>Matching Journal article</th><th>Platforms</th></tr></thead><tbody>{''.join(summary)}</tbody></table>
<p class="notice"><b>Review only. Nothing is scheduled or approved.</b> CSVs use the supplied Thryv columns with Approved=FALSE, Recycle=FALSE and Schedule blank. Dates are proposed; choose times in America/Los_Angeles. The formatted-image URLs are not live yet. Host the JPEGs and verify article availability before importing or approving a post.</p>
<p class="small">The October 28–31 articles are future-dated at preparation time. Do not publish social links before the corresponding article is publicly available. Thryv network assignment and Pinterest title mapping still require a sample import check.</p></section>"""
    review = "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Eternal social review · October 27–31</title><style>" + css + "</style><main>" + overview + "".join(sections) + "</main></html>"
    (OUT / "REVIEW.html").write_text(review)
    (OUT / "README.txt").write_text(
        "ETERNAL LIFE HOSPICE — OCTOBER 27–31, 2026\n"
        "REVIEW PACKAGE, NOT YET IMPORT-READY\n\n"
        "14 posts: GBP daily (5); Facebook, LinkedIn, Pinterest Tue/Thu/Sat (3 each).\n"
        "All Approved=FALSE; Recycle=FALSE; Schedule blank. No posts were sent or scheduled.\n"
        "Suggested dates appear in Title, Comment and the review packet. Posting times remain to be chosen.\n\n"
        "IMAGE HOSTING REQUIRED:\nThe Image fields point to planned /assets/social/2026-10-27-31/ URLs.\n"
        "These URLs are NOT LIVE. Do not import until all 14 JPEGs are hosted and return image/jpeg.\n"
        "The images/ folder supplies the exact matching files. Nothing was published to host them.\n\n"
        "ARTICLE GATE:\nOctober 28–31 articles are not due yet. Confirm each article is live before posting.\n"
        "Keep drafts unapproved until the owner approves the social copy, imagery and timing.\n\n"
        "THRYV:\nFour separate draft CSVs use Link, Image, Caption, Title, Approved, Recycle, Comment, Schedule.\n"
        "Assign the intended social profile when importing; CSV has no platform column.\n"
        "Test one row first. Verify Pinterest Pin-title mapping; its Title column was described as internal.\n"
        "Use a GBP Learn more button if supported. Do not paste an internal title into the caption.\n\n"
        "PHOTO CREDITS:\nSee posts.json for original source URLs and licenses. All photos match their Journal articles.\n"
        "October 27: Niceley, Wikimedia Commons, CC BY-SA 4.0; cropped. Caption and artwork carry attribution.\n"
        "October 27 adapted photographic graphics are shared under CC BY-SA 4.0.\n"
        "Eternal Life Hospice names and logos remain trademarks; no trademark rights are granted.\n"
        "October 30: Eoghanacht, Wikimedia Commons, public domain. Other photos: Pexels License.\n"
    )
    print(f"Built {len(posts)} draft posts and JPEGs in {OUT.relative_to(ROOT)}")
    for platform in FORMATS:
        selected = [p for p in posts if p["platform"] == platform]
        print(platform, len(selected), "posts; maximum caption length", max(p["characters"] for p in selected))


def package():
    target = OUT.parent / "Eternal-Social-October-27-31-2026-REVIEW.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUT))
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--zip-only", action="store_true")
    args = parser.parse_args()
    if not args.zip_only:
        build(args.origin.rstrip("/"))
    else:
        package()
