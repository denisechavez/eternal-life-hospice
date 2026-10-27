"""Approved transactional copy and stable request categories; no transport calls."""
from acknowledgment_layout import render_document

CTA_LINES = (
    "Need to speak with someone now?",
    "We're here for you 24 hours a day, 7 days a week.",
    "Call 805.953.7273",
)
CTA_TEXT = "\n".join(CTA_LINES)
CTA_HTML = (
    '<p style="margin:24px 0 8px;font-weight:bold">Need to speak with someone now?</p>'
    '<p style="margin:0 0 12px">We&#x27;re here for you 24 hours a day, 7 days a week.</p>'
    '<p style="margin:0 0 24px"><a href="tel:18059537273" '
    'style="display:inline-block;padding:12px 18px;background:#5B2E59;color:#fff;'
    'font:bold 16px Arial,sans-serif;text-decoration:underline">Call 805.953.7273</a></p>'
)
PRIVACY = (
    "To help protect patient privacy, please share medical details with our team "
    "by phone or through an approved secure communication channel rather than replying to this email."
)
EMERGENCY = "If you are experiencing a medical emergency, call 911."
INTEREST_LABELS = {
    "share-voice": "Share my voice in The Eternal Care Brief",
    "be-featured": "Be featured in a future issue",
    "education-session": "Schedule an education session with The Eternal Team",
    "speaking-engagement": "Schedule a speaking engagement with Aleksandra",
    "general-meeting": "Set up a time to connect",
    "all-interests": "All of the above",
    "aleksandra-meeting": "Request a meeting with Aleksandra Dubina",
}
INTEREST_ALIASES = {v.casefold(): k for k, v in INTEREST_LABELS.items()}
INTEREST_ALIASES.update({k: k for k in INTEREST_LABELS})
FLAGS = {
    "share-voice": "CARE BRIEF — EDITORIAL REQUEST",
    "be-featured": "CARE BRIEF — EDITORIAL REQUEST",
    "education-session": "EDUCATIONAL SESSION REQUEST",
    "speaking-engagement": "ALEKSANDRA — SCHEDULING REQUEST",
    "aleksandra-meeting": "ALEKSANDRA — SCHEDULING REQUEST",
}
FORM_TEMPLATE = {
    "elh-family": "family",
    "elh-physician": "physician",
    "elh-casemanager": "case-manager",
    "elh-coordinator": "coordinator",
    "elh-chat-callback": "callback",
    "elh-careers": "career",
    "elh-care-brief-signup": "subscriber",
}
CARE_TEMPLATES = {"family", "physician", "case-manager", "coordinator", "callback", "general-meeting"}

# Each body excludes only the greeting, confirmation number and shared footers.
# {cta} replaces the superseded availability paragraph in the supplied copy.
TEMPLATES = {
    "family": ("We're Here for You | Eternal Life Hospice", """Thank you for reaching out to Eternal Life Hospice.

We understand that seeking care for someone you love can bring important questions and difficult decisions. We want you to know that your concerns matter and that you deserve thoughtful guidance every step of the way.

Your request has reached our team. Someone will contact you personally to listen, answer your questions and help you understand the options available to your family.

There is no need to have everything figured out before we speak. We can begin with what matters most to you and your loved one.

{cta}

With care,

The Eternal Life Hospice Team

Here in Moments That Matter Most."""),
    "physician": ("Referral Received | Eternal Life Hospice", """Thank you for placing your confidence in Eternal Life Hospice.

We recognize the importance of a thoughtful transition into hospice care and appreciate the trust involved in referring a patient to our team.

Your referral has been received. Our intake team will connect with you to discuss the next steps and help coordinate care with attention to the patient's clinical needs and the family's wishes.

Our goal is to make communication clear and the referral process as seamless as possible.

{cta}

With appreciation,

The Eternal Life Hospice Intake Team

Care That Honors Life."""),
    "case-manager": ("Thank You for Your Referral | Eternal Life Hospice", """Thank you for considering Eternal Life Hospice for your patient's care.

We appreciate the important role you play in helping patients and families navigate care transitions. We know that clear communication and dependable coordination make a meaningful difference in that process.

Your referral has reached our intake team. We will contact you to review the next steps and coordinate the information needed to move forward.

We value the opportunity to support you and the families who place their trust in your guidance.

{cta}

With appreciation,

The Eternal Life Hospice Intake Team"""),
    "coordinator": ("Thank You for Connecting With Us | Eternal Life Hospice", """Thank you for contacting Eternal Life Hospice.

Every care situation is unique and we appreciate the opportunity to learn more about how we may support you.

Your inquiry has been received. A member of our team will reach out personally to answer your questions and discuss the care and guidance available.

Whether you are exploring care options for someone you love or coordinating support for another family, we are here to listen and help you understand the next steps.

{cta}

With care,

The Eternal Life Hospice Team

Here in Moments That Matter Most."""),
    "callback": ("We'll Be in Touch | Eternal Life Hospice", """Thank you for connecting with Eternal Life Hospice.

We received your request for a phone call and appreciate you taking a moment to reach out.

A member of our team will call you at the number you provided to learn more about how we may support you and answer your questions.

{cta}

With care,

The Eternal Life Hospice Team"""),
    "career": ("Thank You for Your Interest in Eternal Life Hospice", """Thank you for your interest in becoming part of Eternal Life Hospice.

The work we do is deeply personal. Every member of our team contributes to the comfort, dignity and experience of the patients and families we serve.

We appreciate the time you took to introduce yourself and share your experience with us.

Your application has been received and will be reviewed by our team. If your qualifications align with an available opportunity, we will contact you regarding the next steps.

Thank you again for considering Eternal Life Hospice.

Warm regards,

The Eternal Life Hospice Team"""),
    "subscriber": ("Welcome to The Eternal Care Brief | Eternal Life Hospice", """Welcome to The Eternal Care Brief.

We're glad you're here.

The Eternal Care Brief was created to share meaningful information about hospice care, caregiving and the experiences that shape how we care for one another.

Our hope is that each edition offers something valuable — a clearer understanding, a helpful perspective or a little more confidence in navigating life's important care decisions.

Thank you for joining our community of readers.

Warmly,

The Eternal Life Hospice Team

Care That Honors Life."""),
    "share-voice": ("Thank You for Sharing Your Voice | The Eternal Care Brief", """Thank you for your interest in contributing to The Eternal Care Brief.

We believe that meaningful conversations about care grow stronger when people share their knowledge, professional experience and personal perspectives.

We appreciate your willingness to contribute to that conversation.

Your submission has been received and our editorial team will review it thoughtfully. We will be in touch if your contribution aligns with an upcoming edition.

Thank you for helping us create a resource that informs, connects and supports our community.

With appreciation,

The Eternal Life Hospice Editorial Team"""),
    "speaking-engagement": ("Thank You for Your Invitation to Connect With Aleksandra Dubina", """Thank you for reaching out to Eternal Life Hospice and for your interest in connecting with Aleksandra Dubina, our Founder and Chief Executive Officer.

Aleksandra believes deeply in the value of education, meaningful conversation and sharing knowledge that helps families and professionals approach hospice care with greater clarity and confidence.

We appreciate your interest in having her participate in your upcoming conversation or event.

Your request has been received. A member of our team will be in touch to learn more about your plans and explore scheduling opportunities with Aleksandra.

We look forward to learning more about your organization and the conversations you hope to create together.

With care,

The Eternal Life Hospice Team

Care That Honors Life."""),
    "education-session": ("Let's Connect About an Educational Session | Eternal Life Hospice", """Thank you for your interest in bringing an Eternal Life Hospice educational session to your organization or community.

We believe that thoughtful education opens the door to better conversations, greater understanding and more informed care decisions.

We would welcome the opportunity to learn about your audience and the topics that would be most meaningful to them.

Your request has been received. A member of our team will reach out to discuss your interests and explore scheduling options.

We appreciate the opportunity to share knowledge and build meaningful connections within our community.

With care,

The Eternal Life Hospice Team

Care That Honors Life."""),
    "general-meeting": ("We Look Forward to Connecting | Eternal Life Hospice", """Thank you for reaching out to Eternal Life Hospice.

We appreciate your interest in connecting with our team and welcome the opportunity to learn more about you and the conversation you would like to have.

Your request has been received. A member of our team will be in touch to learn more about your interests and explore a convenient time to connect.

If your inquiry involves care for yourself or someone you love:

{cta}

We look forward to speaking with you.

With care,

The Eternal Life Hospice Team

Care That Honors Life."""),
    "be-featured": ("Thank You for Your Interest in The Eternal Care Brief", """Thank you for your interest in being featured in a future edition of The Eternal Care Brief.

We believe every meaningful story has the potential to encourage understanding, inspire thoughtful conversation and bring people closer together.

We appreciate your willingness to share your experience and perspective with our readers.

Your request has been received. Our editorial team will review your interest and reach out if there is an opportunity to explore a feature together.

Thank you for being part of the Eternal community.

With appreciation,

The Eternal Life Hospice Editorial Team"""),
    "all-interests": ("Thank You for Connecting With Eternal Life Hospice", """Thank you for your interest in connecting with Eternal Life Hospice in so many meaningful ways.

We appreciate your willingness to share your voice, contribute to The Eternal Care Brief and explore opportunities for education and conversation with our team and Aleksandra Dubina.

Your request has been received. Our team will review the areas you've expressed interest in and reach out to discuss appropriate next steps.

Whether through shared stories, educational conversations or community connections, we believe each opportunity can help create greater awareness and understanding of hospice care.

We look forward to getting to know you.

With care,

The Eternal Life Hospice Team

Care That Honors Life."""),
    "aleksandra-meeting": ("Thank You for Reaching Out to Aleksandra Dubina", """Thank you for your interest in connecting personally with Aleksandra Dubina, Founder and Chief Executive Officer of Eternal Life Hospice.

Aleksandra values meaningful conversations and opportunities to connect with those who share an interest in thoughtful care, education and community support.

Your request has been received. A member of our team will reach out to learn more about the purpose of your meeting and explore scheduling options.

We appreciate you taking the time to connect.

With care,

The Eternal Life Hospice Team"""),
}


def interest_id(value):
    """Resolve new identifiers and unchanged historical display labels."""
    return INTEREST_ALIASES.get(str(value).strip().casefold())


def request_categories(value):
    category = interest_id(value)
    if category == "all-interests":
        # The appended personal meeting option is separate from the original
        # six-option "All of the above" selection.
        return list(INTEREST_LABELS)[:5]
    return [category] if category else []


def template_key(form_name, fields):
    if form_name == "elh-voice":
        return interest_id(fields.get("interest", "")) or "share-voice"
    return FORM_TEMPLATE[form_name]


def render(key, first_name, receipt_id, contact_email):
    """Render both alternatives from the same approved paragraphs."""
    subject, body = TEMPLATES[key]
    greeting = ("Hello " if key == "subscriber" else "Dear ") + first_name + "," if first_name else "Hello,"
    paragraphs = [greeting, *body.split("\n\n"), f"Confirmation number: {receipt_id}"]
    if key in CARE_TEMPLATES:
        paragraphs.append(PRIVACY)
        if key in {"family", "coordinator", "callback", "general-meeting"}:
            paragraphs.append(EMERGENCY)
    if key == "speaking-engagement":
        paragraphs.append("Important: This confirms receipt of the invitation. It does not confirm Aleksandra's availability or a scheduled engagement.")
    text = "\n\n".join(p.replace("{cta}", CTA_TEXT) for p in paragraphs)
    document = render_document(
        [p.replace("{cta}", CTA_TEXT) for p in paragraphs], contact_email
    )
    return subject, text, document
