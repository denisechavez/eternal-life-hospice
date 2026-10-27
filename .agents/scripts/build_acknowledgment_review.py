#!/usr/bin/env python3
"""Build offline review proofs directly from the development email renderer."""
import base64
import html
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "website"))
import acknowledgments as ack

OUT = ROOT / "generated-artifacts/email-review"
OUT.mkdir(parents=True, exist_ok=True)
LOGO = "data:image/png;base64," + base64.b64encode(
    (ROOT / "website/elh-preview/assets/logo-cream.png").read_bytes()
).decode()
LABELS = {
    "family": "Family care request",
    "physician": "Physician / professional referral",
    "case-manager": "Case manager referral",
    "coordinator": "Care coordinator inquiry",
    "callback": "Chat callback request",
    "career": "Career application",
    "subscriber": "Care Brief subscription",
    "share-voice": "Care Brief contributor",
    "speaking-engagement": "Speaking engagement with Aleksandra",
    "education-session": "Educational session with the Eternal Team",
    "general-meeting": "General meeting request",
    "be-featured": "Request to be featured",
    "all-interests": "All of the above",
    "aleksandra-meeting": "Request a meeting with Aleksandra Dubina",
}
CSS = """
*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:#f5f0eb;color:#3c1c3b;font:15px/1.6 Arial,sans-serif}
a{color:#5b2e59}header{background:#432440;color:#fff8ec;padding:40px;max-width:none}
header img{width:125px;height:auto}h1{font:42px/1.15 Georgia,serif;margin:20px 0 12px}
h2{font:27px/1.2 Georgia,serif}header p{max-width:760px}main{display:grid;grid-template-columns:230px minmax(0,850px);gap:30px;max-width:1200px;margin:30px auto;padding:0 22px}
nav{position:sticky;top:18px;align-self:start;background:#fffaf2;padding:20px;border-top:3px solid #b5a279}
nav a{display:block;padding:7px 0;text-decoration:none;border-bottom:1px solid #e4dacf;font-size:13px}
nav a:hover,nav a:focus{text-decoration:underline;color:#315f79}
.preview{scroll-margin-top:18px;background:#fffaf5;border:1px solid #d8cdbf;padding:22px;margin-bottom:30px}
.status{font-size:11px;letter-spacing:.08em;color:#415d4c}.subject{background:#eee6d9;padding:12px 16px}
.email-stage{margin-top:20px}.note{font-size:12px;color:#655c55}.report{max-width:980px;margin:30px auto;padding:24px;background:white}
table.audit{width:100%;border-collapse:collapse;font-size:13px}.audit td,.audit th{text-align:left;vertical-align:top;padding:10px;border:1px solid #d8cdbf}
.confirmation{padding:24px;border:1px solid #d8cdbf;background:#fff}
@media(max-width:760px){header{padding:24px}h1{font-size:32px}main{display:block;padding:0 10px}nav{position:static;margin-bottom:20px}.preview{padding:12px}}
@media print{@page{size:letter;margin:12mm}body{background:white;-webkit-print-color-adjust:exact;print-color-adjust:exact}header{padding:20px}h1{font-size:30px}main{display:block;padding:0;margin:0}nav{display:none}.preview{break-before:page;break-inside:avoid;margin:0;padding:10px}.email-stage td{font-size:12px!important;line-height:1.4!important;padding:14px!important}.email-stage p{margin-bottom:10px!important}.email-stage img{width:105px!important}.preview h2{font-size:22px}.subject{font-size:12px;padding:8px}.report{break-before:page}.note{font-size:10px}}
"""


def document(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


articles = []
for i, (key, label) in enumerate(LABELS.items(), 1):
    subject, text, email = ack.render(key, "[First name]", "[Confirmation number]", "info@eternallifehospice.com")
    email = email.replace("https://eternallifehospice.com/assets/logo-cream.png", LOGO)
    body = re.search(r"<body[^>]*>(.*)</body>", email, re.S)[1]
    articles.append(
        f'<article class="preview" id="{key}"><div class="status">APPROVED COPY · DEVELOPMENT PREVIEW · NOT PUBLISHED</div>'
        f'<h2>{i:02d} · {html.escape(label)}</h2><p class="subject"><strong>Subject:</strong> {html.escape(subject)}</p>'
        f'<div class="email-stage">{body}</div></article>'
    )
navigation = "".join(f'<a href="#{key}">{i:02d} · {html.escape(label)}</a>' for i, (key, label) in enumerate(LABELS.items(), 1))
review = document(
    "Approved acknowledgment emails — development review",
    f'<header><img src="{LOGO}" alt="Eternal Life Hospice"><h1>Acknowledgment emails</h1>'
    '<p>Fourteen approved messages with the final standardized care CTA. Development preview only. '
    'No emails have been sent by this review, and nothing has been published. Names and confirmation numbers below are placeholders.</p>'
    '<p>The optional email address is required to receive an email acknowledgment; phone-only requests still receive an on-screen confirmation.</p>'
    f'</header><main><nav aria-label="Email previews">{navigation}<a href="#screen-previews">Confirmation screens</a></nav>'
    '<div>' + "".join(articles)
    + '<article class="preview" id="screen-previews"><h2>Care-related confirmation screen</h2>'
    '<div class="confirmation"><h3>Thank you. We’ve received your message.</h3>'
    '<p>Your request has been received. Confirmation number: [Confirmation number].</p>'
    + ack.CTA_HTML
    + '</div><p class="note">The same CTA is supplied by the server after successful internal submission delivery. '
    'Family, physician, case manager, care coordinator, chat callback and general meeting requests use it. '
    'Career, subscriber, editorial and scheduling confirmations do not imply 24/7 scheduling.</p></article>'
    '</div></main>'
)
(OUT / "ELH-Acknowledgment-Emails-Review.html").write_text(review)
(ROOT / "artifacts/review-design-sandbox/public/email-acknowledgments-review.html").write_text(review)

inventory = [
    ("elh-family", "Homepage — Family · Seeking care", "Family care", "referral@eternallifehospice.com"),
    ("elh-physician", "Homepage physician form and /refer", "Physician referral", "referral@eternallifehospice.com"),
    ("elh-casemanager", "Homepage case manager form", "Case manager referral", "referral@eternallifehospice.com"),
    ("elh-coordinator", "Homepage care coordinator form", "Care coordinator inquiry", "referral@eternallifehospice.com"),
    ("elh-chat-callback", "Shared website chat callback", "Chat callback", "referral@eternallifehospice.com"),
    ("elh-careers", "/careers (public recruitment remains paused)", "Career application", "info@eternallifehospice.com"),
    ("elh-care-brief-signup", "/care-brief subscription", "Care Brief subscription", "info@eternallifehospice.com"),
    ("elh-voice", "Homepage Share Your Voice / founder dropdown", "Seven interest-specific acknowledgments", "info@eternallifehospice.com"),
]
rows = "".join("<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in row) + "</tr>" for row in inventory)
routes = "".join(
    f"<tr><td>{html.escape(label)}</td><td>{html.escape(key)}</td><td>{html.escape(ack.TEMPLATES[key][0])}</td></tr>"
    for key, label in ack.INTEREST_LABELS.items()
)
previous = {
    "care": ("We received your request — Eternal Life Hospice",
             "Our intake team received your request and will follow up by phone. No patient or clinical details are included in this email."),
    "career": ("We received your application — Eternal Life Hospice",
               "We received your application and résumé. A member of our team will review it and be in touch."),
    "subscriber": ("You're on the list — The Eternal Care Brief",
                   "Thank you for signing up for The Eternal Care Brief. We will share each new issue with you."),
    "voice": ("Thank you for raising your hand — The Eternal Care Brief",
              "Thank you for offering your voice. A member of our team will reach out shortly."),
}
comparisons = []
for key, label in LABELS.items():
    old = (
        ("No acknowledgment email", "Internal notification only.")
        if key in {"coordinator", "callback", "aleksandra-meeting"} else
        previous["care" if key in {"family", "physician", "case-manager"} else
                 key if key in {"career", "subscriber"} else "voice"]
    )
    comparisons.append(
        f'<tr><td>{html.escape(label)}</td><td><strong>{html.escape(old[0])}</strong><p>{html.escape(old[1])}</p></td>'
        f'<td><strong>{html.escape(ack.TEMPLATES[key][0])}</strong><p>Complete approved message in the companion review, item {list(LABELS).index(key)+1:02d}.</p></td></tr>'
    )
files = [
    "website/acknowledgments.py — approved copy, shared CTA, stable categories and HTML/plain-text renderer",
    "website/form_intake.py — acknowledgment selection, coordinator/callback receipts, internal flags and delivery-status logging",
    "website/elh-preview/index.html — category IDs, new meeting choice and server-provided confirmation CTA",
    "website/elh-preview/refer.html — referral confirmation CTA, no promised callback deadline",
    "website/elh-preview/assets/chat.js — callback confirmation CTA and mobile call link, no promised callback deadline",
    "website/test-acknowledgments.py — approved-copy, routing, exactly-one-receipt and failure tests",
    "website/test-form-intake.py — coordinator/callback-compatible regression expectations",
    "website/intake-browser-fixture.mjs — synthetic response includes care CTA",
    "website/test-intake-browser.mjs — desktop/mobile CTA and telephone-link assertions",
    ".agents/scripts/build_acknowledgment_review.py — rebuilds offline review and this report from the renderer",
    "artifacts/review-design-sandbox/public/email-acknowledgments-review.html — refreshed canvas review proof",
    "artifacts/review-design-sandbox/src/components/mockups/elh-email-review/Acknowledgments.tsx — updated accessible preview title",
]
report = document(
    "Acknowledgment implementation — approval report",
    f'<header><img src="{LOGO}" alt="Eternal Life Hospice"><h1>Development change report</h1>'
    '<p>Approval required before publishing. No production deployment, real submission or real outbound email was performed.</p></header>'
    '<section class="report"><h2>Affected forms</h2><p>All use POST /api/form-submit and website/form_intake.py. '
    'Existing recipients are retained; the addresses below are the existing defaults, not newly configured recipients.</p>'
    '<table class="audit"><tr><th>Form identifier</th><th>Where it appears</th><th>Acknowledgment</th><th>Unchanged default routing</th></tr>'
    + rows + '</table><h2>Before and after</h2>'
    '<table class="audit"><tr><th>Before</th><th>After</th></tr>'
    '<tr><td>Care receipt: “Our intake team received your request and will follow up by phone.”</td>'
    '<td>Uses the complete approved audience-specific copy supplied on October 26, 2026. All 14 full messages appear in the companion review.</td></tr>'
    '<tr><td>“If you need us right away, call 805.953.7273. We are here 24/7.”</td>'
    f'<td>{html.escape(ack.CTA_TEXT).replace(chr(10), "<br>")}</td></tr>'
    '<tr><td>Coordinator and chat requests had no acknowledgment email.</td><td>One acknowledgment when a valid optional email is provided. Phone-only submissions remain valid.</td></tr>'
    '<tr><td>All contributor interests shared one generic Care Brief email.</td><td>Seven distinct category routes, including one combined acknowledgment for All of the above.</td></tr>'
    '<tr><td>Confirmation screens used different availability statements; chat promised a callback within the hour.</td>'
    '<td>The exact shared CTA is used after successful care submission; callback deadline promises are removed.</td></tr>'
    '<tr><td>Email header used only the name.</td><td>Official Eternal logo, existing plum/cream branding and email-safe tables.</td></tr></table>'
    '<h2>Copy comparison by acknowledgment</h2><p>The former greeting was “Hi [First name],” or “Hello,”. '
    'Every former formatted email ended with “If you need us right away, call 805.953.7273. We are here 24/7.” '
    'The plain-text version additionally signed off “With care, Eternal Life Hospice” with the phone and contact email. '
    'The new renderer uses the supplied audience-specific greetings, paragraphs, signoffs and footers in both formats.</p>'
    '<table class="audit"><tr><th>Type</th><th>Previous subject and message</th><th>Approved replacement</th></tr>'
    + "".join(comparisons) + '</table>'
    '<h2>Dropdown and routing</h2><p>The original six choices retain their wording and order. '
    '“Request a meeting with Aleksandra Dubina” is appended. Original display-label values and stable IDs are both accepted. '
    'All of the above retains the original five categories internally and sends only its combined receipt; '
    'the newly appended personal meeting option remains separate.</p>'
    '<table class="audit"><tr><th>Selection</th><th>Stable ID</th><th>Subject</th></tr>' + routes + '</table>'
    '<p>Scheduling, education and editorial flags are added to the existing internal notifications. Timestamp, '
    'confirmation number and “New — follow-up pending” status are included. No calendar access or automatic scheduling was added.</p>'
    '<h2>Delivery and preservation</h2><p>The existing internal email must be accepted by Brevo before a user acknowledgment is attempted. '
    'If the acknowledgment fails, the original internal request remains accepted, the same receipt stays valid and a failure status is logged without submitted information. '
    'Internal delivery failure still returns an explicit error so the person can retry or call. This project has no independent intake database; '
    'this change preserves the existing email-based intake record and does not introduce local patient storage. '
    'Provider acceptance is not proof of inbox delivery. No automatic acknowledgment retries, bounce tracking or new email integration was added.</p>'
    '<h2>Tests</h2><ul>'
    '<li>14 acknowledgment cases: each configured form plus every dropdown selection; approved subjects, name, confirmation number and unchanged internal destination.</li>'
    '<li>Exactly one acknowledgment per eligible submission, including All of the above.</li>'
    '<li>All supplied body paragraphs preserved, except the explicitly superseded CTA variations.</li>'
    '<li>Six care-related templates: exact CTA in both HTML and plain text, one occurrence and a mobile telephone link.</li>'
    '<li>Historical labels, personal meeting versus speaking engagement, fallback greeting, HTML escaping and no submitted details in receipts.</li>'
    '<li>Internal delivery failure sends no acknowledgment. Acknowledgment failure preserves the original internal record and reports failure.</li>'
    '<li>13 existing intake regression tests passed, including isolated HTTP transport.</li>'
    '<li>Family, referral and chat browser journeys passed desktop/keyboard and mobile/touch checks, including submission errors, retries and confirmation CTA.</li>'
    '<li>All seven dropdown choices passed rendered checks for order, stable IDs and founder-to-form synchronization.</li>'
    '<li>26 anti-spam regression tests passed; verification and duplicate/rate controls remain in place.</li>'
    '</ul><p>Tests use synthetic contacts and isolated transports only. Real inbox delivery and third-party mobile email clients have not been tested. '
    'An initial browser startup attempt did not expose a debugging port; an isolated rerun passed all six rendered journeys.</p>'
    '<h2>Exact modified files</h2><ul>' + "".join(f"<li>{html.escape(f)}</li>" for f in files)
    + '</ul><h2>Approval previews</h2><p>Open the companion acknowledgment review and choose “Family care request” or '
    '“Request a meeting with Aleksandra Dubina.” Both render the same templates used by the development handler.</p>'
    '<h2>Unchanged controls</h2><p>No intake eligibility logic, CAPTCHA protection, recruitment pause, subscription consent, unsubscribe mechanisms, '
    'notification destinations or clinical workflow was changed. No new newsletter send was triggered.</p></section>'
)
(OUT / "ELH-Acknowledgment-Implementation-Report.html").write_text(report)
print("Built fourteen email previews, confirmation preview and approval report.")
