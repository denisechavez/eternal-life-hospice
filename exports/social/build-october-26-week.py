#!/usr/bin/env python3
"""Build a private, review-only organic social package; never posts to an API."""
import base64
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import textwrap
import zipfile

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-artifacts/social-2026-10-26"
PUBLIC = ROOT / "website/elh-preview"
ORIGIN = "https://eternallifehospice.com"  # Confirmed via deployment metadata.
PLATFORMS = {
    "Facebook": (1080, 1350),
    "GBP": (1200, 900),
    "Pinterest": (1000, 1500),
    "LinkedIn": (1200, 627),
}
TOPICS = [
    {
        "date": "2026-10-26", "day": "Monday",
        "slug": "hospice-and-home-health-which-questions-clarify-the-difference",
        "headline": "Start with a question.\nNot a crisis.",
        "support": "Home health and hospice:\nunderstanding the difference",
        "keywords": [22, 7, 8, 15], "cities": "Regional education; Ventura and Los Angeles counties",
        "alt": "An empty wooden bench in autumn sunlight, paired with the words Start with a question. Not a crisis.",
        "posts": {
            "Facebook": {
                "title": "Home health and hospice: start with the questions",
                "copy": """“We know we need help. We’re just not sure what kind.”

You don’t have to know the right words before you call.

Home health and hospice can both bring care into a home, but their goals and eligibility differ. Hospice care focuses on comfort and quality of life for someone with a life-limiting illness. Home health generally addresses skilled needs through a treatment or rehabilitation plan.

An earlier conversation can help you ask: What matters most to our person? Who visits? What help will we still need between visits?

Hospice at home is not a live-in caregiver service. Visits follow an individualized plan; 24/7 on-call clinical support is not continuous bedside nursing.

At Eternal Life Hospice, personalization begins with listening on the first call—not asking your family to fit a template.

Read the questions to bring to that conversation:
{url}

#HospiceCare #FamilyCaregiving #EternalLifeHospice""",
            },
            "GBP": {
                "title": "Home health and hospice: which support fits?",
                "copy": """Not sure whether to ask about home health and hospice? Start with what your family needs—not with having every answer.

Our new Eternal Journal article explains how hospice care and home health differ, what to ask about visits and how to plan for help between them. Hospice at home does not mean a live-in caregiver or continuous bedside nursing; 24/7 on-call clinical support is different.

At Eternal Life Hospice, the first call starts with your person’s wishes, daily routines and questions. Eligibility is individualized and physician-certified. Asking about care earlier gives you room to understand your options.

Select Learn more to read the guide.""",
            },
            "Pinterest": {
                "title": "Home Health and Hospice: Questions to Ask Before Deciding",
                "copy": """Home health and hospice can both happen at home, but they serve different goals. This family guide explains hospice care, visit planning and the difference between 24/7 on-call support and continuous bedside nursing. Explore questions about hospice at home before a crisis forces the conversation. Save this guide for a future care conversation.""",
                "board": "Hospice questions for families",
            },
            "LinkedIn": {
                "title": "Make the first care conversation easier",
                "copy": """A family should not have to become fluent in healthcare language before asking for help.

“Home health and hospice” often arrive in the same conversation. Yet goals, eligibility and visit plans differ—and those differences affect everyday family life.

Clear explanations should cover what hospice care can provide, who is present between visits and why 24/7 on-call clinical support does not mean continuous bedside nursing.

An earlier hospice consultation can be a conversation about options, not an enrollment commitment. At Eternal Life Hospice, we begin by listening to the person’s priorities and the household’s practical needs.

Our Journal guide offers questions families and referral partners can use to make that discussion more useful:
{url}

#HospiceCare #CareCoordination #PatientCenteredCare""",
            },
        },
    },
    {
        "date": "2026-10-28", "day": "Wednesday",
        "slug": "the-hospice-election-statement-read-it-as-a-conversation",
        "headline": "Your questions\nbelong in the room.",
        "support": "Understanding hospice paperwork\nwithout losing the person",
        "keywords": [7, 15, 87, 92], "cities": "Regional education; Ventura and Los Angeles counties",
        "alt": "A sunlit living room with a sofa, desk and brick walls, with the words Your questions belong in the room.",
        "posts": {
            "Facebook": {
                "title": "A hospice form is also a conversation",
                "copy": """“Can we slow down and go over that again?”

Yes. Your questions belong in the room.

The hospice election statement is part of Medicare hospice enrollment. It should be explained in plain language—not handed over as something you are expected to understand on your own.

During a hospice consultation, bring the questions you really have:
• Does Medicare cover hospice at home?
• Which services relate to the terminal illness and related conditions?
• Who do we call when something changes?
• Can you switch hospice providers?

Hospice care is about a person’s life, wishes and comfort—not just completing paperwork. The election statement is also different from an advance directive or a DNR order.

At Eternal Life Hospice, listening begins on the first call. You do not need a polished question to deserve a clear explanation.

Read our plain-language conversation guide:
{url}

#HospiceCare #InformedChoices #FamilySupport""",
            },
            "GBP": {
                "title": "Bring your questions to the hospice conversation",
                "copy": """Hospice paperwork should make choices clearer—not make a family feel rushed.

Our Eternal Journal guide explains how to approach the hospice election statement as a conversation. During a hospice consultation, ask what you are choosing, how related services are coordinated and who can explain anything that is unclear.

“Does Medicare cover hospice at home?” and “Can you switch hospice providers?” are reasonable questions to bring. Individual eligibility and coverage details need careful explanation.

Hospice care begins with the person, not the form. At Eternal Life Hospice, we listen to your wishes and concerns from the first call.

Select Learn more to read the conversation guide.""",
            },
            "Pinterest": {
                "title": "Hospice Election Statement: Questions Families Can Bring",
                "copy": """Prepare for a hospice consultation with questions about the election statement, care choices and who to contact. Does Medicare cover hospice at home? Can you switch hospice providers? This Eternal Journal guide helps you start the conversation and explains why hospice enrollment paperwork is different from an advance directive or DNR order. Save it for a thoughtful, unhurried review.""",
                "board": "Understanding hospice and Medicare",
            },
            "LinkedIn": {
                "title": "Informed hospice choices begin before a signature",
                "copy": """A signed form is not the same as an understood choice.

The hospice election statement deserves a plain-language conversation about care, related services and the person’s priorities.

During a hospice consultation, families may ask, “Does Medicare cover hospice at home?” or “Can you switch hospice providers?” These are opportunities to explain—not interruptions to move past.

The election statement is not an advance directive or a DNR order. Keeping those distinctions clear supports informed hospice care.

At Eternal Life Hospice, personalization begins on the first call. The paperwork should reflect that listening, not replace it.

Our latest Journal article offers a practical framework for a clearer enrollment conversation:
{url}

#HospiceCare #HealthLiteracy #PatientAutonomy""",
            },
        },
    },
    {
        "date": "2026-10-30", "day": "Friday",
        "slug": "calabasas-plan-a-calm-handoff-between-home-and-assisted-living",
        "headline": "A new address.\nThe same person.",
        "support": "A calmer care handoff\nfor Calabasas families",
        "keywords": [27, 7, 8, 16], "cities": "Calabasas",
        "alt": "The courtyard and Spanish Colonial Revival architecture at King Gillette Ranch in Calabasas, with the words A new address. The same person. This is a local landmark, not a care facility.",
        "posts": {
            "Facebook": {
                "title": "Calabasas: keep the person at the center of a move",
                "copy": """A favorite blanket. A quieter morning. Knowing who will answer when you call.

When someone moves from home to assisted living, these details still matter.

For families exploring hospice care in Calabasas, a calmer handoff starts before moving day. Ask who handles medications, which daily needs facility staff support, who coordinates hospice visits and who the family should contact if something changes.

Hospice at home and hospice in assisted living both need a clear plan for care between visits. Neither should depend on relatives guessing who is responsible.

Include the person’s comfort preferences, too. If sound bathing or nonclinical end-of-life doula support interests them, ask about consent, fit and availability. Choosing quiet is equally valid. These optional supports never replace licensed clinical care.

Eternal Life Hospice starts with the person’s routines and wishes from the first call.

Read the Calabasas handoff guide:
{url}

#Calabasas #HospiceCare #FamilyCaregiving""",
            },
            "GBP": {
                "title": "A calmer hospice handoff in Calabasas",
                "copy": """A move to assisted living changes an address. It should not erase the routines and preferences that make someone feel like themselves.

For Calabasas families planning hospice care, our new Journal checklist covers medication responsibilities, daily support, hospice visits and the contacts everyone should have before moving day.

Whether you are asking about hospice at home or care in assisted living, start with the person’s wishes and clarify who is responsible between visits. A hospice evaluation can help determine whether care is appropriate; eligibility is individualized.

At Eternal Life Hospice, personalization begins on the first call.

Select Learn more for the Calabasas handoff checklist.""",
            },
            "Pinterest": {
                "title": "Calabasas Hospice Care: An Assisted Living Handoff Checklist",
                "copy": """Planning a move from home to assisted living in Calabasas? This hospice care checklist helps families clarify medications, daily support, visit coordination and the right contact when needs change. Whether you are exploring hospice at home or a new care setting, keep familiar routines and the person’s wishes in the plan. Save this checklist before moving day.""",
                "board": "Calabasas family care planning",
            },
            "LinkedIn": {
                "title": "Calabasas care transitions need shared responsibilities",
                "copy": """A good care transition transfers more than a medication list.

For a Calabasas family moving a loved one into assisted living, comfort also depends on familiar routines, communication preferences and knowing who is responsible.

A hospice evaluation addresses eligibility. A coordinated handoff should also clarify daily support, medication responsibilities, hospice visits and the contact for a change in needs.

Whether the starting point is hospice at home or a facility discussion, 24/7 on-call support is not a substitute for a written plan between visits.

At Eternal Life Hospice, that plan begins with listening on the first call.

Our Calabasas Journal checklist supports a person-centered conversation between families, facility staff and hospice teams:
{url}

#Calabasas #HospiceCare #CareTransitions""",
            },
        },
    },
]


def font(name, size):
    return ImageFont.truetype(io.BytesIO(FONTS[name]), size)


def lines(draw, text, face, width):
    result = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            test = (line + " " + word).strip()
            if line and draw.textlength(test, font=face) > width:
                result.append(line)
                line = word
            else:
                line = test
        result.append(line)
    return result


def graphic(topic, platform, source, logo):
    w, h = PLATFORMS[platform]
    canvas = Image.new("RGB", (w, h), "#F5F0EB")
    draw = ImageDraw.Draw(canvas)
    wide = platform == "LinkedIn"
    if wide:
        panel = (0, 0, 560, h)
        canvas.paste(ImageOps.fit(source, (w - 560, h), centering=(0.53, 0.5)), (560, 0))
        x, y, tw, title_size = 42, 160, 470, 55
        logo_width = 205
    else:
        photo_height = int(h * (0.53 if platform == "Pinterest" else 0.60))
        canvas.paste(ImageOps.fit(source, (w, photo_height)), (0, 0))
        panel = (0, photo_height, w, h)
        x, y, tw = int(w * .06), photo_height + (108 if platform == "GBP" else int(h * .10)), int(w * .88)
        title_size = 66 if platform == "Pinterest" else (50 if platform == "GBP" else 68)
        logo_width = 205 if platform == "GBP" else 230
    # Natural source colors; no tint, purple overlay or invented patient scene.
    draw.line((panel[0], panel[1], panel[2], panel[1]), fill="#C9B07E", width=4)
    scaled = logo.copy()
    scaled.thumbnail((logo_width, 70 if platform == "GBP" else 100))
    logo_y = 36 if wide else panel[1] + 22
    canvas.paste(scaled, (x, logo_y), scaled)
    face = font("serif", title_size)
    wrapped = lines(draw, topic["headline"], face, tw)
    for line in wrapped:
        draw.text((x, y), line, font=face, fill="#5B2E59")
        y += int(title_size * 1.16)
    y += 18
    small = font("sans", 26 if platform == "GBP" else 27 if wide else 30)
    for line in lines(draw, topic["support"], small, tw):
        draw.text((x, y), line, font=small, fill="#51454C")
        y += 32 if platform == "GBP" else 39
    if y > h - 45:
        raise ValueError(f"Text overflows {topic['date']} {platform}: {y}/{h}")
    draw.text((x, h - 42), "eternallifehospice.com", font=font("sans", 22), fill="#5B2E59")
    return canvas


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    FONTS = {}
    for key, filename in [("serif", "fraunces-latin.woff2"), ("sans", "JostELH-Regular.woff2")]:
        ttf = TTFont(PUBLIC / "assets/fonts" / filename)
        ttf.flavor = None
        b = io.BytesIO()
        ttf.save(b)
        FONTS[key] = b.getvalue()
    logo = Image.open(PUBLIC / "assets/logo-eternal-trans.png").convert("RGBA")
    logo = logo.crop(logo.getbbox())
    articles = json.loads((ROOT / "website/content/30-day-journal/additional-2026-q4.json").read_text())
    sources = json.loads((ROOT / "website/content/journal-q4-photo-sources.json").read_text())
    master = {k["id"]: k["phrase"] for k in json.loads(
        (ROOT / "website/content/seo-keyword-master.json").read_text())["keywords"]}
    posts, sections, notes = [], [], []
    for topic in TOPICS:
        article = next(a for a in articles if a["slug"] == topic["slug"])
        credit = next(a for a in sources if a["slug"] == topic["slug"])
        source = Image.open(PUBLIC / article["heroImage"].lstrip("/")).convert("RGB")
        for platform, spec in topic["posts"].items():
            url = ORIGIN + "/blog/" + topic["slug"]
            copy = spec["copy"].format(url=url)
            filename = f"{topic['date']}-{platform.lower()}.jpg"
            image = graphic(topic, platform, source, logo)
            image.save(OUT / filename, quality=94, subsampling=0)
            limit = 500 if platform == "Pinterest" else 1500 if platform == "GBP" else 3000 if platform == "LinkedIn" else 63206
            assert len(copy) <= limit, (platform, len(copy))
            assert len(spec["title"]) <= 100 if platform == "Pinterest" else True
            if platform == "LinkedIn":
                assert len(copy.split("\n")[0]) <= 110
            post = {
                "date": topic["date"], "day": topic["day"], "platform": platform,
                "status": "DRAFT — requires social approval and live article check",
                "time": "Not scheduled; article release is 06:30 America/Los_Angeles",
                "article_title": article["title"], "article_url": url,
                "title": spec["title"], "copy": copy,
                "button": "Learn more" if platform == "GBP" else "",
                "destination_url": url, "image": filename,
                "width": image.width, "height": image.height,
                "alt_text": topic["alt"], "board_suggestion": spec.get("board", ""),
                "target_cities": topic["cities"],
                "keyword_ids": topic["keywords"],
                "keywords": [master[k] for k in topic["keywords"]],
                "exact_keyword_matches": [master[k] for k in topic["keywords"] if master[k].lower() in (copy + " " + spec["title"]).lower()],
                "photo_source": credit["sourceUrl"], "photo_license": credit["license"],
                "photo_author": credit["author"], "characters": len(copy),
            }
            posts.append(post)
            encoded = base64.b64encode((OUT / filename).read_bytes()).decode()
            e = html.escape
            sections.append(f"""<section class="post"><div class="eyebrow">REVIEW DRAFT · {e(topic['day'])} {topic['date']} · {platform}</div>
<h2>{e(spec['title'])}</h2><div class="layout"><div><img src="data:image/jpeg;base64,{encoded}" alt="{e(topic['alt'])}">
<p class="meta">{image.width} × {image.height} px · JPEG<br>{e(filename)}</p></div>
<div class="caption">{e(copy)}</div></div>
<p class="meta"><b>Article:</b> {e(article['title'])}<br><a href="{url}">{url}</a><br>
<b>Keyword IDs:</b> {', '.join(map(str,topic['keywords']))} · {e('; '.join(post['keywords']))}<br>
<b>Location:</b> {e(topic['cities'])} · <b>Characters:</b> {len(copy)}<br>
<b>Photo:</b> {e(credit['author'])} · {e(credit['license'])} · <a href="{e(credit['sourceUrl'])}">Source</a><br>
<b>Release gate:</b> Social approval required. Confirm the article returns its public content before posting.
{('<br>GBP button: Learn more → article URL (do not paste the title as a separate GBP field).') if platform == 'GBP' else ''}
{('<br>Pinterest: paste the title, description, destination link and alt text into their separate fields. Suggested board: '+e(spec['board'])) if platform == 'Pinterest' else ''}
</p></section>""")
            notes.append(f"{topic['day']} {topic['date']} — {platform}\n{'='*60}\nTITLE: {spec['title']}\n\n{copy}\n\nDESTINATION: {url}\nIMAGE: {filename} ({image.width}x{image.height})\nALT TEXT: {topic['alt']}\nKEYWORDS: {'; '.join(post['keywords'])}\nSTATUS: {post['status']}\n")
    (OUT / "posts.json").write_text(json.dumps(posts, indent=2, ensure_ascii=False))
    fields = list(posts[0])
    with (OUT / "posts.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: "; ".join(map(str,v)) if isinstance(v,list) else v for k,v in p.items()} for p in posts)
    (OUT / "captions.txt").write_text("\n\n".join(notes))
    css = """body{margin:0;background:#eee8e0;color:#352b34;font:16px/1.5 Arial,sans-serif}
main{max-width:1100px;margin:auto}.intro,.post{background:#fffdf9;padding:36px;margin:24px 0}
h1,h2{font-family:Georgia,serif;color:#5b2e59;line-height:1.15}h1{font-size:40px}h2{font-size:28px}
.eyebrow{color:#765d38;letter-spacing:1px;font-size:12px}.layout{display:grid;grid-template-columns:40% 1fr;gap:28px}
img{width:100%;max-height:500px;object-fit:contain;object-position:top}.caption{white-space:pre-wrap;font-size:15px}
.meta{font-size:11px;line-height:1.45;overflow-wrap:anywhere}a{color:#5b2e59}
@media(max-width:700px){.layout{display:block}.post,.intro{padding:22px;margin:12px}img{max-height:400px}}
@page{size:letter;margin:.45in}@media print{body{background:white}main{max-width:none}.intro,.post{margin:0;padding:5px;break-after:page;break-inside:avoid}.layout{grid-template-columns:36% 1fr;gap:18px}.caption{font-size:10.5px;line-height:1.45}h2{font-size:22px}.meta{font-size:8px}img{max-height:310px}.intro{break-after:page}h1{font-size:36px}}"""
    intro = """<div class="intro"><div class="eyebrow">ETERNAL LIFE HOSPICE · ORGANIC SOCIAL REVIEW</div>
<h1>A conversation before a crisis.</h1><p>October 26, 28 and 30, 2026 · Facebook, Google Business Profile, Pinterest and LinkedIn</p>
<p><b>12 draft posts. Nothing has been posted or scheduled.</b></p>
<p>Three Journal topics, adapted for four platforms. The campaign invites earlier questions and treats hospice as support for living with serious illness—not a failure or a countdown.</p>
<p>Uses each matching Journal article’s existing licensed photograph in natural color, with no purple overlay, generated people or patient testimonials. The Calabasas image is a local landmark, not an affiliated facility.</p>
<p>Facebook: 1080 × 1350 · GBP: 1200 × 900 · Pinterest: 1000 × 1500 · LinkedIn: 1200 × 627. Images are separate upload-ready JPEGs.</p>
<p>Keyword assignments reference the existing 101-term master list. Natural variants are intentional; exact phrase matches are recorded separately in posts.json and posts.csv. Assignment and inclusion are not ranking evidence.</p>
<p><b>Before posting:</b> obtain social approval, verify each corresponding Journal article is publicly available, then choose social posting times. Journal releases remain 6:30 a.m. Pacific; social times have not been chosen. GBP uses Learn more; Pinterest uses its destination-link field. Image alt descriptions are supplied for platforms that support them.</p>
<p>No Care Brief work is included. No account connections, website edits or publication actions are made by this package.</p></div>"""
    document = f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Eternal social review · October 26 week</title><style>{css}</style><main>{intro}{''.join(sections)}</main></html>"
    (OUT / "review.html").write_text(document)
    thumbnails = "".join(
        f"<figure><img src='data:image/jpeg;base64,{base64.b64encode((OUT / p['image']).read_bytes()).decode()}'"
        f" alt='{html.escape(p['alt_text'])}'><figcaption>{p['date']} · {p['platform']}<br>"
        f"{p['width']} × {p['height']}</figcaption></figure>" for p in posts)
    (OUT / "image-contact-sheet.html").write_text(
        "<!doctype html><html lang='en'><meta charset='utf-8'><title>Eternal social image review</title>"
        "<style>body{background:#f5f0eb;color:#5b2e59;font:14px Arial;margin:24px}h1{font:30px Georgia}"
        ".grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}figure{margin:0}img{width:100%;"
        "height:260px;object-fit:contain;object-position:top}figcaption{text-align:center;margin:8px}"
        "</style><h1>Eternal Life Hospice · October 26 week</h1><p>REVIEW DRAFT · 12 upload-ready "
        "images · Natural photography · No publication or scheduling</p><div class='grid'>"
        + thumbnails + "</div></html>")
    (OUT / "README.txt").write_text(textwrap.dedent("""\
        ETERNAL LIFE HOSPICE — OCTOBER 26 WEEK
        REVIEW DRAFT ONLY. Nothing posted or scheduled.
        12 posts: October 26, 28, 30 × Facebook, GBP, Pinterest, LinkedIn.
        Open review.html for images and copy; review.pdf is the printable version.
        captions.txt contains paste-ready copy. posts.csv and posts.json contain
        titles, captions, exact/assigned keywords, alt text, image sizes and sources.
        Separate JPG files are the actual upload assets, not PDF screenshots.
        GBP: use the body copy plus Learn more button pointed at destination_url.
        Pinterest: use separate title, description, destination link and alt fields.
        LinkedIn and Facebook: copy includes the article link.
        Article URLs are scheduled destinations, not a claim that they are live now.
        Confirm each article is public before publishing its corresponding post.
        Reused photographs match their own Journal articles; three distinct sources.
        No patient scene, facility partnership or testimonial is being represented.
        Photos: Pexels License (Mon/Wed), public domain (Fri). See per-post sources.
        No stock-photo copyright is transferred; applicable source licenses remain.
        Care Brief excluded. Social approval is separate from Journal approval.
        """))
    # Print PDF separately, then rerun with --zip after verification.
    import sys
    if "--zip" in sys.argv:
        with zipfile.ZipFile(OUT.parent / "eternal-social-october-26-2026.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(OUT.iterdir()):
                if path.is_file():
                    z.write(path, arcname="eternal-social-october-26-2026/" + path.name)
    print(f"Built {len(posts)} draft posts and {len(list(OUT.glob('*.jpg')))} image assets in {OUT}")
