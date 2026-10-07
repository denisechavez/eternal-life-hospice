#!/usr/bin/env python3
"""Make a self-contained editorial review file from the authoritative sources."""
import base64
import csv
import html
import importlib.util
import io
import json
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
OUT = ROOT.parent / "exports/journal"
spec = importlib.util.spec_from_file_location("journal_builder", ROOT / "build-journal-campaign.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def export():
    articles = json.loads((ROOT / "content/30-day-journal/additional-2026-q4.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    blocks = []
    for index, a in enumerate(articles, 1):
        with Image.open(PUBLIC / a["heroImage"].lstrip("/")) as image:
            image = image.convert("RGB")
            image.thumbnail((800, 600))
            stream = io.BytesIO()
            image.save(stream, format="JPEG", quality=78, optimize=True)
        photo = base64.b64encode(stream.getvalue()).decode()
        body = builder.render_body(a)
        body = body.replace('href="/', 'href="https://eternallifehospice.com/')
        body = body.replace('href="../blog"', 'href="https://eternallifehospice.com/blog"')
        body = re.sub(r'<section class="hero hero--photo"[^>]*>', '<section>', body)
        blocks.append(
            f'<details data-month="{a["date"][5:7]}"><summary><span>{a["date"]} · '
            f'{html.escape(a["location"])} · {a["readMinutes"]} min</span>'
            f'<strong>{index:02d}. {html.escape(a["title"])}</strong></summary>'
            f'<img src="data:image/jpeg;base64,{photo}" alt="{html.escape(a["heroImageAlt"], quote=True)}">'
            f'<div class="copy">{body}<aside><strong>{html.escape(a["ctaHeading"])}</strong>'
            f'<p>{html.escape(a["ctaCopy"])}</p></aside></div></details>'
        )
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Eternal Journal · Q4 editorial review</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#faf8f6;color:#302b34;font:17px/1.65 Georgia,serif}
header,main{max-width:960px;margin:auto;padding:28px}header{border-bottom:1px solid #dfd6de}
h1{color:#58335b;line-height:1.2;font-size:36px}nav{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}
button,select{padding:10px 14px;background:white;border:1px solid #806584;border-radius:4px;color:#58335b;font:15px Arial}
details{background:white;border:1px solid #e2dbe3;margin:18px 0;border-radius:6px;overflow:hidden}
summary{cursor:pointer;padding:20px}summary span{display:block;font:13px Arial;color:#6c6271;margin-bottom:8px}
summary strong{font-size:21px;line-height:1.3}details>img{display:block;width:100%;max-height:430px;object-fit:cover}
.copy{padding:24px 30px}.copy h2{font-size:26px;color:#58335b;line-height:1.3;margin-top:30px}
a{color:#69456d;text-underline-offset:3px}.byline,.article-sub,.journal-photo-credit{color:#6c6271}
.note-panel,aside{background:#f5eff5;padding:20px;margin:24px 0;border-left:3px solid #a8896d}
[hidden]{display:none}@media(max-width:600px){header,main{padding:16px}.copy{padding:18px}h1{font-size:29px}}
@media print{nav{display:none}details{break-before:page;border:0}.copy{padding:0}}
</style></head><body><header><p>ETERNAL LIFE HOSPICE · THE ETERNAL JOURNAL</p>
<h1>October 22–December 31, 2026</h1>
<p>71 scheduled articles · 48 national topics · 23 local articles · 71 distinct photographs.</p>
<p><strong>Editorial review copy.</strong> These entries are staged, not an assertion that they are already live.
Future articles remain hidden until their Los Angeles publication date. Clinical and business claims should receive the team's final sign-off.</p>
<nav><label>Month <select id="month"><option value="">All months</option><option value="10">October</option>
<option value="11">November</option><option value="12">December</option></select></label>
<button id="open">Expand visible articles</button><button id="close">Collapse articles</button></nav>
</header><main>""" + "\n".join(blocks) + """</main><script>
const entries=[...document.querySelectorAll('details')];
document.querySelector('#month').onchange=e=>entries.forEach(x=>x.hidden=!!e.target.value&&x.dataset.month!==e.target.value);
document.querySelector('#open').onclick=()=>entries.filter(x=>!x.hidden).forEach(x=>x.open=true);
document.querySelector('#close').onclick=()=>entries.forEach(x=>x.open=false);
</script></body></html>"""
    (OUT / "q4-2026-editorial-review.html").write_text(page)
    with (OUT / "q4-2026-editorial-calendar.csv").open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("Date", "Title", "Focus", "Category", "Reading minutes", "Article path", "Photo license"))
        for a in articles:
            writer.writerow((a["date"], a["title"], a["location"], a["category"],
                             a["readMinutes"], "/blog/" + a["slug"], a["photoCredit"]["license"]))
    print("Exported self-contained editorial review and CSV calendar.")


if __name__ == "__main__":
    export()
