#!/usr/bin/env python3
"""Export the existing three canvas designs; never publish or submit a form."""
import base64
import html
from html.parser import HTMLParser
import mimetypes
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "artifacts/review-design-sandbox"
COMPONENTS = SANDBOX / "src/components/mockups/elh-google-ppc-thanks"
README = ROOT / "exports/google-ppc-thank-you-options/README.md"
OUTPUT = ROOT / "generated-artifacts/google-ppc-three-options"
STEM = "ELH-Google-PPC-Three-Thank-You-Options"
OPTIONS = (
    ("PersonalLetter", "Personal Letter", "01-Personal-Letter.html"),
    ("AmethystAssurance", "Amethyst Assurance", "02-Amethyst-Assurance.html"),
    ("QuietWelcome", "Quiet Welcome", "03-Quiet-Welcome.html"),
)
PRIVACY = (
    "To help protect your privacy and the privacy of your loved one, please avoid "
    "sending medical details by email. Our care team can guide you to an "
    "appropriate way to share this information."
)


def run(args):
    result = subprocess.run(
        list(map(str, args)), check=True, capture_output=True, text=True, timeout=90
    )
    return result.stdout


class MainContent(HTMLParser):
    """Keep only the rendered main element, without the development runtime."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.parts = []
        self.finished = False

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.depth += 1
        if self.depth:
            if tag == "script":
                raise ValueError("Unexpected script inside the visual design")
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append(f"</{tag}>")
        if tag == "main" and self.depth:
            self.depth -= 1
            self.finished = self.depth == 0

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if self.depth:
            self.parts.append(f"&#{name};")


def embed_assets(text):
    def replace(match):
        relative = match.group(1)
        path = (SANDBOX / "public" / relative).resolve()
        if not path.is_relative_to((SANDBOX / "public").resolve()):
            raise ValueError("Asset outside the sandbox public directory")
        raw = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    return re.sub(r"/__reviews-mockup/([^\"'()\s<>]+)", replace, text)


def document(title, css, content, label):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        '<meta name="referrer" content="no-referrer">'
        f"<title>{html.escape(title)}</title>"
        "<style>html,body{margin:0;padding:0}*,*::before,*::after{box-sizing:border-box}"
        ".handoff-print-label{display:none}"
        + css
        + """
@page{size:1280px 1400px;margin:0}
@media print{
  html,body{width:1280px;margin:0;print-color-adjust:exact;-webkit-print-color-adjust:exact}
  .handoff-print-label{display:block;height:40px;padding:12px 30px;background:#f6f1e8;
    color:#655d63;font:12px Arial,sans-serif;letter-spacing:.04em}
  .elh-letter-page,.aa-page{min-height:1160px}
  .quiet-welcome{min-height:1100px}
  .qw-scene{min-height:350px;height:350px}
  .qw-content{padding-bottom:40px}
  a{text-decoration:none}
}
"""
        + "</style></head><body>"
        + f'<div class="handoff-print-label">{html.escape(label)}</div>'
        + content
        + "</body></html>"
    )


def page_count(path):
    info = run(["pdfinfo", path])
    match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
    if not match:
        raise ValueError(f"No page count for {path}")
    return int(match.group(1))


def render(source, destination):
    run([
        "chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-background-networking", "--no-first-run",
        "--window-size=1280,1400",
        "--no-pdf-header-footer", "--virtual-time-budget=3000",
        f"--print-to-pdf={destination}", source.as_uri(),
    ])
    if page_count(destination) != 1:
        text = run(["pdftotext", destination, "-"])
        raise ValueError(f"Expected one page: {source.name}. Trailing text: {text[-900:]}")


def notes_document():
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Eternal Life Hospice — Google PPC handoff</title><style>
@page{size:1280px 1400px;margin:0}*{box-sizing:border-box}
body{margin:0;padding:65px 80px;background:#fbf8f2;color:#3f3940;
font:18px/1.55 Arial,sans-serif;print-color-adjust:exact;-webkit-print-color-adjust:exact}
h1{font:48px/1.1 Georgia,serif;color:#432440;margin:16px 0 24px}
h2{font:26px Georgia,serif;color:#432440;margin:22px 0 10px}
p{margin:10px 0}.label{font-size:13px;letter-spacing:.15em;text-transform:uppercase;color:#886735}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:50px}
.notice{padding:20px;border-left:3px solid #b5a279;background:#f1ebe0}
li{margin-bottom:10px}code{overflow-wrap:anywhere;font-size:16px}
footer{border-top:1px solid #ded5c7;margin-top:24px;padding-top:16px;font-size:14px}
</style>
<p class="label">Eternal Life Hospice · Google PPC · Implementation handoff</p>
<h1>Three options. One verified confirmation.</h1>
<p class="notice">For RealTop to review with Eternal Life Hospice. Choose one option,
then obtain Eternal's approval before publication. These files have not been
connected to the external landing-page form.</p>
<div class="grid"><section><h2>What is included</h2>
<p>1 · Personal Letter<br>2 · Amethyst Assurance<br>3 · Quiet Welcome</p>
<p>Each HTML file is self-contained with embedded fonts and images. Open locally
for desktop and mobile review. No scripts, form handling or conversion events
are included. Detailed instructions are in README.md.</p>
<h2>What we need from the form administrator</h2><ul>
<li>Form provider, saved/accepted success response and available redirect or callback.</li>
<li>Who controls the landing page, where requests go and who can verify receipt.</li>
<li>Agreed HTTPS thank-you URL, hosting, consent handling and existing conversion owner.</li>
</ul><h2>Image quality</h2><p>Text remains selectable; decoration is vector.
Quiet Welcome includes the original 1080 × 1350 photograph, not a screenshot.
For full-width Retina sharpness, supply the same licensed image at least 2560 pixels wide.</p>
</section><section><h2>Confirm receipt without delay</h2><p>Show a sending state immediately.
Show thanks only after acceptance and saving are verified. Do not wait for staff,
email delivery or analytics. Measure actual timing in testing.</p>
<p>Failed or pending requests need honest status and retry/call guidance.
A direct visit without verified submission needs neutral guidance, not a receipt claim.</p>
<h2>Preserve tracking and privacy</h2><p>Use <strong>805.409.9262</strong> /
<code>tel:+18054099262</code>. Verify Nimbata number replacement and call routing.</p>
<p>Inspect existing Google Ads tracking. Choose one verified-success conversion owner,
not both the form and thank-you page. Respect consent and prevent repeats on reload,
history navigation and duplicate callbacks.</p>
<p>Destination: <code>AW-18384023405/JC8lCKGQ9qsdEO3el75E</code><br>Supplied value: 1.0 USD.</p>
<p>Never place patient or contact details in URLs, tracking or logs.
Email acknowledgment is separate and uses approved company Gmail, not Brevo.</p>
<h2>Before launch</h2><p>With authorization, test accepted, failed, pending, duplicate,
direct-visit and consent states using synthetic data. Verify request receipt,
mobile links and one eligible conversion. No real patient requests or calls.</p>
</section></div><footer>External campaign: https://eternal-life-hospice.rt-go.com/ ·
Replit project changes do not automatically update its form. No publication or email
sending is performed by this packet.</footer></html>"""


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".build-", dir=OUTPUT) as temp:
        stage = Path(temp)
        deliverables = []
        pages = []
        for index, (component, title, filename) in enumerate(OPTIONS, 1):
            dom = run([
                "chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
                "--no-first-run", "--virtual-time-budget=3000", "--dump-dom",
                f"http://127.0.0.1:21921/__reviews-mockup/preview/elh-google-ppc-thanks/{component}",
            ])
            parser = MainContent()
            parser.feed(dom)
            if not parser.finished:
                raise ValueError(f"Rendered design not found: {title}")
            markup = "".join(parser.parts)
            if PRIVACY not in markup or "tel:+18054099262" not in markup:
                raise ValueError(f"Missing approved copy or phone: {title}")
            if "Not connected to the live form" in markup or "qw-sprig" in markup:
                raise ValueError(f"Removed artwork reappeared in {title}")
            css = (COMPONENTS / f"{component}.css").read_text()
            # Keep mobile layout for browser review, not the desktop PDF spread.
            css = re.sub(r"@media\s+\(max-width", "@media screen and (max-width", css)
            output = embed_assets(document(
                f"Eternal Life Hospice — {title}", css, markup,
                f"OPTION {index} · {title} · Eternal Life Hospice",
            ))
            if "<script" in output.lower() or "/__reviews-mockup/" in output:
                raise ValueError("Unexpected runtime or non-embedded asset")
            path = stage / filename
            path.write_text(output)
            deliverables.append(path)
            pdf = stage / f"{index}.pdf"
            render(path, pdf)
            pages.append(pdf)
        notes = stage / "04-Implementation-Notes.html"
        notes.write_text(notes_document())
        render(notes, stage / "4.pdf")
        pages.append(stage / "4.pdf")
        packet = stage / f"{STEM}.pdf"
        run(["pdfunite", *pages, packet])
        if page_count(packet) != 4:
            raise ValueError("Comparison PDF must contain exactly four pages")
        readme = stage / "README.md"
        readme.write_text(README.read_text())
        deliverables += [notes, readme, packet]
        archive = OUTPUT / f"{STEM}-Handoff.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in deliverables:
                bundle.write(path, arcname=path.name)
        for path in deliverables:
            (OUTPUT / path.name).write_bytes(path.read_bytes())
        print(f"PDF: {(OUTPUT / packet.name).relative_to(ROOT)}")
        print(f"ZIP: {archive.relative_to(ROOT)} ({archive.stat().st_size:,} bytes)")
        print("Verified: 3 self-contained designs; 4 PDF pages; no scripts or live integration.")


if __name__ == "__main__":
    main()
