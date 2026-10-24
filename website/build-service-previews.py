#!/usr/bin/env python3
"""Build the ten review-only service pages from approved editorial copy."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "website" / "previews"
SEED = OUT / "care-community.html"
ORIGIN = "https://eternallifehospice.com"
SHARED_SEARCH = '''
<div class="search-overlay" id="searchOverlay" role="dialog" aria-modal="true" aria-label="Site search" aria-hidden="true">
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="Search pages, cities, resources..." autocomplete="off" aria-label="Search">
    <button class="search-close" id="searchClose" aria-label="Close search">&times;</button>
  </div>
  <p class="search-hint">Press Enter to open the first result, or Escape to close</p>
  <div class="search-results" id="searchResults"></div>
</div>
'''

PAGES = [
    {
        "slug": "in-home-hospice-care",
        "title": "In-Home Hospice Care",
        "seo": "In-Home Hospice Care | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "Hospice care at home from one interdisciplinary team of physicians, nurses, aides, social workers and chaplains across Ventura and Los Angeles counties.",
        "eyebrow": "Hospice care at home across Ventura and Los Angeles counties",
        "subline": "Care That Honors Life, in the place your loved one knows best.",
        "intro": "In-home hospice care is for patients with a life-limiting illness and the families caring for them. One interdisciplinary team of physicians, nurses, aides, social workers and chaplains brings comfort, guidance and clinical care into the home. Families deserve calm direction and clear answers, and that is where every visit begins.",
        "first_heading": "What in-home hospice care includes",
        "tiles": [
            "Physician-led pain and symptom management",
            "Scheduled nursing visits and 24/7 nurse access by phone",
            "Hospice aide help with bathing, grooming and daily comfort",
            "Medications, supplies and equipment related to the terminal illness and related conditions, as included in the hospice plan of care, delivered to the home",
            "Social work, spiritual care and bereavement support for the family",
        ],
        "second_heading": "The first 48 hours",
        "second_text": "",
        "timeline": [
            ("First call", "We listen and identify the next step."),
            ("Evaluation & admission", "The nurse assesses; the physician determines eligibility."),
            ("Plan of care", "Built around comfort, dignity and clinical need."),
            ("Medications & equipment", "Coordinated and delivered."),
            ("Family guidance", "What to expect and when to call."),
            ("24/7 support", "Nurse access day, night, weekends and holidays."),
        ],
        "coverage_text": "Hospice care is covered under the Medicare Hospice Benefit and Medi-Cal. Most private insurance plans also cover hospice, subject to eligibility and policy terms. Eternal reviews coverage before care begins.",
        "faq": [
            ("Can hospice care be provided in a private home?", "Yes. Most hospice care happens at home, with the team visiting on a schedule and a nurse available by phone at any hour."),
            ("Does a family member need to be with the patient at all times?", "Families plan a caregiver schedule, since hospice visits on a schedule rather than staying around the clock. The care team helps build that plan and connects families with support."),
            ("How quickly can care begin?", "The team reviews eligibility and care needs, then explains the earliest appropriate start date. Ask about current availability when you call."),
            ("Who is on the care team?", "A hospice physician, registered nurses, hospice aides, a medical social worker and a chaplain."),
        ],
        "related": ["Pain & Symptom Management", "24/7 Nurse Access", "Hospice Evaluation", "Levels of Hospice Care"],
        "hero_alt": "Illustrative scene of a hospice nurse in plum scrubs sitting with an older woman in her living room",
        "wide_alt": "Illustrative scene of a hospice nurse reviewing a care folder with a family member at a kitchen table",
        "wide_heading": "The first 48 hours",
        "wide_text": "",
    },
    {
        "slug": "hospice-in-assisted-living-and-skilled-nursing",
        "title": "Hospice in Assisted Living & Skilled Nursing",
        "seo": "Hospice in Assisted Living & Skilled Nursing | Eternal Life Hospice",
        "meta": "Hospice care on site in assisted living, skilled nursing and board and care communities across Ventura and Los Angeles counties.",
        "eyebrow": "Hospice care in care communities across Ventura and Los Angeles counties",
        "subline": "The same standard of care, wherever your loved one lives.",
        "intro": "This service is for residents of assisted living, skilled nursing and board and care communities. The Eternal team works alongside facility staff to manage comfort, coordinate medications and keep the family informed. Care is provided on site, so the resident stays in a familiar room with familiar faces.",
        "first_heading": "How hospice works inside a care community",
        "first_text": "Facility staff continue daily care. The hospice team adds physician-led symptom management, nursing visits, aide support, social work and spiritual care. One plan of care is shared with the facility, so every caregiver follows the same comfort goals.",
        "second_heading": "Communication with families and facility staff",
        "tiles": [
            "A clear point of contact for the family and the facility",
            "Updates after visits and whenever the plan of care changes",
            "24/7 nurse access by phone for families and facility staff",
        ],
        "extra_heading": "Coverage",
        "extra_text": "The Medicare Hospice Benefit covers eligible hospice services in a care community. It generally does not cover ongoing facility room and board. Short-term inpatient or respite care arranged by the hospice follows different coverage rules. Medi-Cal or other coverage may help with room and board depending on eligibility and the setting. Eternal reviews the family's coverage and potential costs before care begins.",
        "faq": [
            ("Can a resident receive hospice without moving?", "Yes. Hospice comes to the resident in assisted living, skilled nursing or board and care."),
            ("Who leads daily care?", "Facility staff provide daily care, and the hospice team directs comfort-focused care and symptom management."),
            ("Does hospice pay for room and board?", "The Medicare Hospice Benefit generally does not pay for ongoing facility room and board. It may cover a short-term inpatient or respite stay arranged by the hospice when the applicable requirements are met. Medi-Cal and other coverage have different rules. Ask Eternal to review the facility charges and your coverage before care begins."),
        ],
        "related": ["In-Home Hospice Care", "Hospice Care for Dementia", "Hospice Evaluation"],
        "hero_alt": "Illustrative scene of a hospice nurse talking with an older man in his assisted living apartment",
        "wide_alt": "Illustrative scene of a hospice nurse and facility caregiver reviewing a tablet in a community hallway",
    },
    {
        "slug": "levels-of-hospice-care",
        "title": "Levels of Hospice Care",
        "seo": "Levels of Hospice Care: Continuous, Respite & Inpatient | Eternal Life Hospice",
        "meta": "Continuous Home Care, Inpatient Respite Care and General Inpatient Care: the Medicare hospice levels of care and when each one applies.",
        "eyebrow": "Medicare hospice levels of care, explained",
        "subline": "The level of care changes as needs change.",
        "intro": "Medicare defines four levels of hospice care. Routine home care usually involves scheduled visits. When needs change, the hospice team assesses whether another level is appropriate under Medicare guidelines and coordinates the care setting.",
        "first_heading": "Three levels beyond routine home care",
        "first_text": "These levels address specific needs. The team reassesses the appropriate level and care setting as needs change.",
        "levels": [
            ("Continuous Home Care", "Continuous Home Care is a short-term level for periods of crisis when Medicare criteria are met. It is provided in an eligible home setting and consists mainly of nursing care. The hospice team determines whether this level is appropriate and available for the patient's situation."),
            ("Inpatient Respite Care", "Inpatient respite care gives the usual caregiver a short rest while the patient continues to receive hospice care. The hospice arranges an occasional stay in an approved inpatient facility for up to five consecutive days."),
            ("General Inpatient Care", "For patients whose pain or symptoms need management beyond what is possible at home. Short-term inpatient care directed by the hospice team. Provided in a contracted facility."),
        ],
        "second_heading": "Inpatient Respite Care",
        "second_text": "Inpatient respite care gives the usual caregiver a short rest while the patient continues to receive hospice care. The hospice arranges an occasional stay in an approved inpatient facility for up to five consecutive days.",
        "faq": [
            ("Who decides the level of care?", "The hospice physician and care team decide, based on the patient's needs and Medicare guidelines."),
            ("Can respite be used more than once?", "Respite is offered on an occasional basis. The team plans it with the family."),
            ("What happens after inpatient care?", "When the inpatient level is no longer needed, the team reassesses the patient's needs and coordinates the next appropriate level and setting. Returning to a previous home or care community depends on the individual situation."),
        ],
        "related": ["In-Home Hospice Care", "24/7 Nurse Access", "Hospice Evaluation"],
        "hero_alt": "Illustrative scene of a hospice nurse sitting quietly beside a hospital bed at home at night",
        "wide_alt": "Illustrative scene of a granddaughter beside her grandmother in a bright home-like inpatient room",
    },
    {
        "slug": "24-7-nurse-access",
        "title": "24/7 Nurse Access",
        "seo": "24/7 Hospice Nurse Access | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "A hospice nurse available by phone day, night, weekends and holidays, with visits arranged when symptoms change.",
        "eyebrow": "24/7 hospice nurse access by phone across Ventura and Los Angeles counties",
        "subline": "You always know who to reach.",
        "intro": "24/7 nurse access gives enrolled patients and families a way to reach hospice nursing support by phone at any hour. The nurse assesses the concern, guides next steps and arranges a visit when clinically needed under the plan of care.",
        "first_heading": "When to call the nurse",
        "tiles": [
            "Pain or breathing that medications are not easing",
            "A fall, new confusion or a sudden change",
            "Questions about medications or equipment",
            "Signs that death may be near, or after a death at home",
        ],
        "second_heading": "What happens when you call",
        "second_text": "A hospice nurse discusses what has changed, provides guidance and coordinates the next step under the patient's plan of care. Keep 805.953.7273 and the team's written contact instructions close by.",
        "faq": [
            ("Who answers after hours?", "A hospice nurse."),
            ("Will a nurse come to the home at night?", "The nurse assesses the concern and arranges a visit when clinically needed under the plan of care."),
            ("Who should we call when symptoms change?", "Follow the contact and emergency instructions in the patient's care plan. The hospice nurse can guide the response to hospice-related concerns. Ask the team to explain what to do for urgent concerns and emergencies before a situation arises."),
        ],
        "related": ["In-Home Hospice Care", "Pain & Symptom Management", "Levels of Hospice Care"],
        "hero_alt": "Illustrative scene of a hospice nurse parked in her car at night speaking calmly on the phone",
        "wide_alt": "Illustrative scene of a woman in her softly lit kitchen at night speaking on the phone",
    },
    {
        "slug": "hospice-care-for-dementia",
        "title": "Hospice Care for Dementia",
        "seo": "Hospice Care for Dementia & Alzheimer's | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "Comfort-focused hospice care for late-stage Alzheimer's and other dementias, at home, in memory care or in board and care.",
        "eyebrow": "Alzheimer's and dementia hospice care across Ventura and Los Angeles counties",
        "subline": "Calm routines, steady comfort and support for the family through each change.",
        "intro": "Hospice care for dementia is for patients in the later stages of Alzheimer's or another dementia and the families beside them. The team focuses on comfort, calm routines and caregiver support. Care is provided at home, in memory care or in board and care settings.",
        "first_heading": "When hospice may be the right step",
        "first_text": "Families often consider hospice when a loved one needs help with most daily activities, speaks very little, eats less or has repeated infections or hospital visits. A hospice nurse can assess the patient, and the hospice physician determines eligibility.",
        "second_heading": "How the team cares for a person with dementia",
        "tiles": [
            "Comfort-focused management of pain, agitation and restlessness, which can be hard to read in late-stage dementia",
            "Guidance on eating, swallowing and safe positioning",
            "Consistent visit times and familiar faces where possible",
            "Aide help with bathing and personal care",
            "Caregiver guidance on what changes to expect and when to call",
        ],
        "extra_heading": "Support for the family",
        "extra_text": "Dementia often means years of caregiving before hospice begins. Social work, spiritual care and bereavement support are part of the plan, so the family has steady help through the final stage.",
        "faq": [
            ("Is dementia a qualifying diagnosis for hospice?", "Yes, when the hospice physician determines the illness has reached a stage where life expectancy is six months or less if it follows its expected course."),
            ("Can hospice care happen in memory care?", "Yes. The team works on site with memory care staff."),
            ("Will hospice stop all medications?", "The physician reviews every medication and keeps those that support comfort."),
        ],
        "related": ["Hospice Evaluation", "Hospice in Assisted Living & Skilled Nursing", "Pain & Symptom Management"],
        "hero_alt": "Illustrative scene of an adult son and his older father looking through a family photo album",
        "wide_alt": "Illustrative scene of a caregiver sharing tea with an older woman in a calm memory care room",
    },
    {
        "slug": "hospice-care-for-advanced-cancer",
        "title": "Hospice Care for Advanced Cancer",
        "seo": "Hospice Care for Advanced Cancer | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "Comfort-focused hospice care for advanced cancer: pain and symptom management, medication coordination and family support.",
        "eyebrow": "Cancer hospice care across Ventura and Los Angeles counties",
        "subline": "Comfort first, with every symptom watched closely.",
        "intro": "This service is for patients with advanced cancer who are focusing on comfort. The hospice team manages pain and symptoms, coordinates medications and supports the family. Care is provided at home or in the patient's care community.",
        "first_heading": "Comfort-focused cancer care",
        "tiles": [
            "Pain management reviewed as needs change",
            "Relief for nausea, appetite loss, fatigue and breathlessness",
            "Medication and equipment coordination",
            "Emotional and spiritual support for the patient and family",
        ],
        "second_heading": "When to consider hospice",
        "second_text": "Families often consider hospice when treatment no longer helps, when the patient chooses to stop treatment or when hospital visits become frequent. An evaluation gives clear answers before any decision.",
        "extra_heading": "Working with the oncology team",
        "extra_text": "The patient's oncologist can stay informed and involved. The hospice physician directs comfort care and keeps the attending physician updated.",
        "faq": [
            ("Can my oncologist stay involved?", "Yes. The attending physician can remain part of care."),
            ("Does hospice mean stopping every treatment?", "Hospice focuses on comfort. Treatments that relieve symptoms may continue when the hospice physician includes them in the plan of care."),
            ("How is cancer pain managed at home?", "The physician sets a medication plan, the nurse reviews it at each visit and a nurse is available by phone at any hour."),
        ],
        "related": ["Pain & Symptom Management", "In-Home Hospice Care", "24/7 Nurse Access"],
        "hero_alt": "Illustrative scene of a woman in a soft headscarf resting on a sofa with a visiting nurse",
        "wide_alt": "Illustrative scene of an older couple sharing a quiet moment on a shaded back porch",
    },
    {
        "slug": "hospice-care-for-heart-failure",
        "title": "Hospice Care for Heart Failure",
        "seo": "Hospice Care for Heart Failure | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "Hospice care for advanced heart failure: relief for breathlessness, fatigue and fluid-related discomfort, with clear guidance for families.",
        "eyebrow": "Heart failure hospice care across Ventura and Los Angeles counties",
        "subline": "Comfort-focused support for breathing changes and a clear plan for what comes next.",
        "intro": "This service is for patients with advanced heart failure and the families caring for them. The team manages breathlessness, fatigue and fluid-related discomfort with clear guidance on what to expect. Care is provided at home or in the patient's care community.",
        "first_heading": "How the team manages heart failure symptoms",
        "tiles": [
            "Relief for breathlessness at rest and during activity",
            "Guidance on swelling, fluid and comfortable positioning",
            "Review of heart medications, keeping those that support comfort",
            "Warning signs to watch and when to call the nurse",
        ],
        "second_heading": "When to consider hospice",
        "second_text": "Families often consider hospice when symptoms appear at rest, hospital visits repeat or the patient chooses to focus on comfort.",
        "faq": [
            ("Can heart medications continue?", "Medications that support comfort often continue. The hospice physician reviews each one."),
            ("Is hospice only for the last days of life?", "Hospice can support a patient for months when eligibility continues, which gives families more time with steady help."),
        ],
        "related": ["Respiratory Care", "24/7 Nurse Access", "Hospice Evaluation"],
        "hero_alt": "Illustrative scene of a hospice nurse listening to an older man's heart as he rests in a recliner",
        "wide_alt": "Illustrative scene of an older couple walking arm in arm along a garden path",
    },
    {
        "slug": "respiratory-care",
        "title": "Respiratory Care",
        "seo": "Respiratory Care & COPD Hospice Support | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "Hospice respiratory care for COPD, lung disease and heart failure: oxygen coordination, breathing-focused medications and bedside guidance.",
        "eyebrow": "COPD and lung disease hospice care across Ventura and Los Angeles counties",
        "subline": "Steadier breathing and a calm plan for hard moments.",
        "intro": "Respiratory support within hospice is for eligible patients with COPD, lung disease or heart failure who experience shortness of breath. The team develops a comfort-focused plan that may include medications, equipment coordination and guidance for caregivers. Care is provided at home or in the patient's care community.",
        "first_heading": "Hospice support for COPD",
        "tiles": [
            "Oxygen and equipment related to the terminal illness and related conditions, as included in the hospice plan of care, coordinated by the team",
            "Medications that ease breathlessness and the anxiety it brings",
            "Positioning and pacing techniques for easier breathing",
            "A clear plan for breathing episodes and when to call",
        ],
        "second_heading": "Guidance for families",
        "second_text": "Watching a loved one struggle to breathe is frightening. The nurse teaches the family what helps, what to watch and how to reach the team at any hour.",
        "faq": [
            ("Will oxygen be provided?", "Oxygen and equipment related to the terminal illness and related conditions, as included in the hospice plan of care, are coordinated by the hospice team."),
            ("What helps breathlessness at home?", "The hospice team assesses the cause and the person's needs. The plan may include medication, positioning, airflow and other measures appropriate to the patient. The nurse explains what to try and when to call for further help."),
        ],
        "related": ["Hospice Care for Heart Failure", "24/7 Nurse Access", "Pain & Symptom Management"],
        "hero_alt": "Illustrative scene of an older man with home oxygen reading by a window",
        "wide_alt": "Illustrative scene of a hospice nurse showing an adult daughter an oxygen concentrator",
    },
    {
        "slug": "bereavement-support",
        "title": "Bereavement Support",
        "seo": "Bereavement Support & Grief Care | Eternal Life Hospice",
        "meta": "Bereavement support for hospice families, with information about grief resources, check-ins and support before and after a loss.",
        "eyebrow": "Grief support for hospice families across Ventura and Los Angeles counties",
        "subline": "Care for the family continues after a loss.",
        "intro": "Bereavement support is for family members and close loved ones affected by the loss of a person in hospice care. The team discusses available support, how it is provided and how long it continues.",
        "first_heading": "What bereavement support includes",
        "tiles": [
            "Regular check-ins by phone",
            "Written resources on grief and what to expect",
            "Remembrance and memorial support",
            "Referrals to grief groups and counseling in the community",
        ],
        "second_heading": "Support before a loss",
        "second_text": "Grief often begins before a death. Social work and spiritual care help the family through that time, so support is already in place.",
        "coverage_title": "Understanding bereavement support",
        "coverage_text": "Ask the team which bereavement services are included in the hospice bereavement plan. Outside counseling or community programs may have their own eligibility requirements, availability and fees.",
        "faq": [
            ("When does bereavement support begin?", "Support begins during hospice care and continues after the loss."),
            ("Who can receive support?", "Family members and close loved ones, including children."),
        ],
        "related": ["In-Home Hospice Care", "Levels of Hospice Care", "24/7 Nurse Access"],
        "hero_alt": "Illustrative scene of two adult sisters on a garden bench, one leaning on the other's shoulder",
        "wide_alt": "Illustrative scene of family members around a kitchen table looking through photographs",
    },
    {
        "slug": "hospice-evaluation",
        "title": "Hospice Evaluation",
        "seo": "Hospice Evaluation | Ventura & Los Angeles Counties | Eternal Life Hospice",
        "meta": "A nurse assessment reported to the hospice physician, who determines eligibility, with a clear explanation of the Medicare Hospice Benefit.",
        "eyebrow": "Hospice evaluations at home, in the hospital or in a care community",
        "subline": "Clear answers before any decision is made.",
        "intro": "A hospice evaluation is for families, physicians and hospitals considering hospice for a patient. A hospice nurse completes an assessment and reports to the hospice physician, who determines eligibility. Families leave with a clear explanation of the Medicare Hospice Benefit and what care looks like.",
        "first_heading": "How an evaluation works",
        "timeline": [
            ("First call", "We listen, answer questions and identify the next appropriate step."),
            ("Nurse assessment", "A hospice nurse reviews symptoms, medications, safety needs and family priorities."),
            ("Physician review", "The hospice physician reviews the assessment and determines eligibility."),
            ("Next steps", "Admission timing depends on physician-confirmed eligibility, the patient's needs and care coordination. Eternal explains the next steps and anticipated timing during the evaluation."),
        ],
        "second_heading": "Who can request an evaluation",
        "second_text": "Families, physicians, discharge planners, case managers and care communities can request an evaluation by phone or through Refer a Patient.",
        "extra_heading": "What eligibility means",
        "extra_text": "A physician certifies that life expectancy is six months or less if the illness follows its expected course. Patients are re-certified over time, and a patient can leave hospice at any time.",
        "faq": [
            ("Does an evaluation commit us to hospice?", "An evaluation provides information and does not enroll a patient in hospice. The patient or authorized representative decides whether to elect hospice after eligibility and care options are explained."),
            ("Who decides eligibility?", "The hospice physician determines eligibility, together with the patient's attending physician when there is one."),
            ("Can an evaluation happen in the hospital?", "Yes. Evaluations are held at home, in the hospital or in a care community."),
        ],
        "related": ["In-Home Hospice Care", "Hospice Care for Dementia", "Levels of Hospice Care"],
        "hero_alt": "Illustrative scene of a hospice nurse checking an older man's blood pressure at home with his wife beside him",
        "wide_alt": "Illustrative scene of a hospice nurse explaining options to adult siblings in a hospital family lounge",
    },
]

GROUPS = [
    ("Getting Started", ["hospice-evaluation"]),
    ("Where We Provide Care", ["in-home-hospice-care", "hospice-in-assisted-living-and-skilled-nursing", "levels-of-hospice-care", "24-7-nurse-access"]),
    ("Care for Specific Conditions", ["hospice-care-for-dementia", "hospice-care-for-advanced-cancer", "hospice-care-for-heart-failure", "respiratory-care"]),
    ("Comfort & Support", ["Pain & Symptom Management", "Integrative & Whole-Person Care", "Sound Bath", "bereavement-support"]),
]
EXISTING = {
    "Pain & Symptom Management": ("/resources/pain-symptom-management", "Skilled, physician-directed nursing care to relieve pain, ease breathlessness and manage distress — around the clock, wherever the patient calls home."),
    "Integrative & Whole-Person Care": ("/resources/comfort-therapies", "Music therapy, gentle massage, aromatherapy and more — offered gently at the bedside to bring ease and presence to each day."),
    "Sound Bath": ("/sound-bath", "Original soundscapes and singing bowls, brought quietly to the bedside for rest, calm and comfort — a signature offering of Eternal Life Hospice."),
}

def esc(value: str) -> str:
    return html.escape(value, quote=True)

CONTEXT_LINKS = {
    "in-home-hospice-care": [
        ("pain and symptom management", "/resources/pain-symptom-management"),
        ("24/7 nurse access", "/services/24-7-nurse-access"),
    ],
    "hospice-in-assisted-living-and-skilled-nursing": [
        ("physician-led symptom management", "/resources/pain-symptom-management"),
        ("24/7 nurse access", "/services/24-7-nurse-access"),
    ],
    "levels-of-hospice-care": [
        ("Routine home care", "/services/in-home-hospice-care"),
        ("Medicare guidelines", "/resources/medicare-hospice-benefit"),
    ],
    "24-7-nurse-access": [
        ("Pain or breathing", "/resources/pain-symptom-management"),
        ("written contact instructions", "/resources/first-48-hours"),
    ],
    "hospice-care-for-dementia": [
        ("memory care or in board and care", "/services/hospice-in-assisted-living-and-skilled-nursing"),
        ("bereavement support", "/services/bereavement-support"),
    ],
    "hospice-care-for-advanced-cancer": [
        ("Pain management", "/resources/pain-symptom-management"),
        ("An evaluation", "/services/hospice-evaluation"),
    ],
    "hospice-care-for-heart-failure": [
        ("breathlessness", "/services/respiratory-care"),
        ("at home", "/services/in-home-hospice-care"),
    ],
    "respiratory-care": [
        ("heart failure", "/services/hospice-care-for-heart-failure"),
        ("at home", "/services/in-home-hospice-care"),
    ],
    "bereavement-support": [
        ("Written resources on grief", "/resources"),
        ("Social work and spiritual care", "/services/in-home-hospice-care"),
    ],
    "hospice-evaluation": [
        ("Medicare Hospice Benefit", "/resources/medicare-hospice-benefit"),
        ("care communities", "/services/hospice-in-assisted-living-and-skilled-nursing"),
    ],
}


def contextual_content(page: dict, markup: str) -> str:
    """Wrap existing copy only; never change wording, metadata or FAQ data."""
    remaining = dict(CONTEXT_LINKS[page["slug"]])
    parts = re.split(r"(<[^>]+>)", markup)
    inside_link = False
    for index, part in enumerate(parts):
        if part.startswith("<"):
            if re.match(r"<a\b", part):
                inside_link = True
            elif part.startswith("</a>"):
                inside_link = False
            continue
        if inside_link:
            continue
        for phrase, url in list(remaining.items()):
            text = esc(phrase)
            if text in part:
                part = part.replace(
                    text, '<a class="cc-context-link" href="' + esc(url) + '">'
                    + text + '</a>', 1)
                del remaining[phrase]
        parts[index] = part
    if remaining:
        raise ValueError("Missing contextual phrases for " + page["slug"] + ": "
                         + ", ".join(remaining))
    return "".join(parts)

def icon(index: int) -> str:
    paths = [
        '<path d="M6 7.5h24v17H17l-7 5v-5H6z"/><path d="M11 13h14M11 18h9"/>',
        '<path d="M8 6.5h20v23H8z"/><path d="M12 12h12M12 17h12M12 22h8"/>',
        '<path d="M18 29s-10-6.4-10-14a5.5 5.5 0 0 1 10-3.2A5.5 5.5 0 0 1 28 15c0 7.6-10 14-10 14Z"/><path d="M13 18h3l2-4 3 8 2-4h2"/>',
    ]
    return '<svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">' + paths[index % len(paths)] + '</svg>'

def render_tiles(items: list[str], home_visual: bool = False, balanced_pairs: bool = False) -> str:
    visual = (
        '<div class="cc-tile cc-tile--visual" aria-hidden="true">'
        '<svg class="cc-home-visual" viewBox="0 0 120 120" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 55 60 20l41 35M29 48v49h62V48"/>'
        '<path d="M60 83S41 72 41 61a10 10 0 0 1 19-4 10 10 0 0 1 19 4c0 11-19 22-19 22Z"/>'
        '<path d="M18 106h84M60 8v-3M14 22l-4-4M106 22l4-4"/>'
        '</svg></div>'
    ) if home_visual else ""
    layout = ' data-layout="balanced-pairs"' if balanced_pairs else ""
    return '<div class="cc-tiles"' + layout + '>' + "".join(
        '<div class="cc-tile">' + icon(i) + '<span>' + esc(item) + '</span></div>'
        for i, item in enumerate(items)
    ) + visual + '</div>'

def render_faq(items: list[tuple[str, str]]) -> str:
    visible = "".join(
        '<details><summary>' + esc(question) + '</summary><p>' + esc(answer) + '</p></details>'
        for question, answer in items
    )
    return '<section class="cc-faq"><div class="cc-wrap"><h2>Questions Families Ask</h2><div class="cc-faq-list">' + visible + '</div></div></section>'

def render_coverage(page: dict) -> str:
    heading = page.get("coverage_title", "Understanding your hospice coverage")
    body = page.get("coverage_text", "Hospice coverage depends on eligibility and the rules of your Medicare, Medi-Cal or private insurance plan. Eternal reviews benefits, coverage arrangements and potential costs before care begins.")
    return ('<section class="cc-plan"><div class="cc-wrap cc-plan-panel">'
            '<h2>' + esc(heading) + '</h2><p>' + esc(body) + '</p></div></section>')

def render_first(page: dict) -> str:
    result = '<section class="cc-section cc-how"><div class="cc-wrap cc-copy"><h2 class="cc-section-heading">' + esc(page["first_heading"]) + '</h2>'
    if page.get("first_text") and not page.get("levels"):
        result += '<p>' + esc(page["first_text"]) + '</p>'
    if page.get("levels"):
        result += '<p>' + esc(page["first_text"]) + '</p><div class="cc-levels">'
        result += "".join('<article class="cc-level"><h3>' + esc(title) + '</h3><p>' + esc(text) + '</p></article>' for title, text in page["levels"])
        result += '</div>'
    elif page.get("tiles") and page["slug"] not in (
            "hospice-in-assisted-living-and-skilled-nursing", "hospice-care-for-dementia"):
        result += render_tiles(
            page["tiles"],
            home_visual=page["slug"] == "in-home-hospice-care",
            balanced_pairs=page["slug"] in ("bereavement-support", "hospice-care-for-heart-failure"),
        )
    elif page.get("timeline") and page["slug"] == "hospice-evaluation":
        result += '<ol class="cc-timeline">' + "".join('<li><div><strong>' + esc(label) + ':</strong> ' + esc(text) + '</div></li>' for label, text in page["timeline"]) + '</ol>'
    result += '</div></section>'
    return result

def render_second(page: dict) -> str:
    alt = esc(page["wide_alt"])
    img_name = "communication.webp" if page["slug"] == "hospice-in-assisted-living-and-skilled-nursing" else page["slug"] + "-communication.webp"
    img = '/__service-preview-assets/' + img_name
    result = '<section class="cc-communication"><figure class="cc-communication-photo"><img loading="lazy" decoding="async" src="' + img + '" alt="' + alt + '"></figure>'
    result += '<div class="cc-wrap cc-communication-copy"><h2 class="cc-section-heading">' + esc(page["second_heading"]) + '</h2>'
    if page.get("second_text"):
        result += '<p>' + esc(page["second_text"]) + '</p>'
    if page.get("tiles") and page["slug"] in (
            "hospice-in-assisted-living-and-skilled-nursing", "hospice-care-for-dementia"):
        result += render_tiles(page["tiles"])
    elif page.get("timeline") and page["slug"] == "in-home-hospice-care":
        result += '<ol class="cc-timeline">' + "".join('<li><div><strong>' + esc(label) + ':</strong> ' + esc(text) + '</div></li>' for label, text in page["timeline"]) + '</ol>'
    result += '</div></section>'
    return result

def render_extra(page: dict) -> str:
    if not page.get("extra_heading"):
        if page.get("coverage_text") and page["slug"] == "hospice-in-assisted-living-and-skilled-nursing":
            return '<section class="cc-section cc-coverage"><div class="cc-wrap"><h2 class="cc-section-heading">' + esc(page["extra_heading"]) + '</h2><p>' + esc(page["extra_text"]) + '</p></div></section>'
        return ""
    return '<section class="cc-section cc-coverage"><div class="cc-wrap"><h2 class="cc-section-heading">' + esc(page["extra_heading"]) + '</h2><p>' + esc(page["extra_text"]) + '</p></div></section>'

def related_links(page: dict) -> str:
    links = []
    for name in page["related"]:
        known = next((p for p in PAGES if p["title"] == name), None)
        if known:
            href = "/services/" + known["slug"]
        else:
            href = EXISTING.get(name, ("#", ""))[0]
        links.append('<a href="' + esc(href) + '">' + esc(name) + '</a>')
    return '<section class="cc-related"><div class="cc-wrap"><h2>RELATED SERVICES</h2><div class="cc-related-links">' + "".join(links) + '</div></div></section>'

def standard_band() -> str:
    pillars = [
        ("Clinical Confidence", "Physician-supported hospice care for the moments families need certainty"),
        ("Guided Presence", "You always know what is happening, what comes next and who to reach"),
        ("Whole-Person Comfort", "Comfort for the whole person – mind, body, spirit and family"),
        ("Compliance-Led Care", "Accurate, private and ethical at every step"),
    ]
    return '<section class="cc-standard" aria-labelledby="cc-standard-title"><div class="cc-wrap"><p class="cc-eyebrow">The Eternal Standard</p><h2 id="cc-standard-title">Four Pillars. One Standard of Care.</h2><div class="cc-pillars">' + "".join('<article class="cc-pillar"><h3>' + esc(h) + '</h3><p>' + esc(t) + '</p></article>' for h, t in pillars) + '</div></div></section>'

def schema(page: dict) -> str:
    crumbs = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": ORIGIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "Services", "item": ORIGIN + "/services"},
            {"@type": "ListItem", "position": 3, "name": page["title"], "item": ORIGIN + "/services/" + page["slug"]},
        ],
    }
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in page["faq"]],
    }
    return '<script type="application/ld+json">' + json.dumps(crumbs, ensure_ascii=False, separators=(",", ":")) + '</script>\n<script type="application/ld+json">' + json.dumps(faq, ensure_ascii=False, separators=(",", ":")) + '</script>'

def page_template(page: dict, header: str, footer: str) -> str:
    hero = '/__service-preview-assets/hero.webp' if page["slug"] == "hospice-in-assisted-living-and-skilled-nursing" else '/__service-preview-assets/' + page["slug"] + '-hero.webp'
    first_sentence = page["intro"].split(". ", 1)[0] + "."
    cover = render_coverage(page)
    first = render_first(page)
    second = render_second(page)
    extra = render_extra(page)
    crumb_title = esc(page["title"])
    intro = '<section class="cc-intro" aria-label="' + crumb_title + '"><div class="cc-wrap cc-intro-inner"><span class="cc-quote-mark" aria-hidden="true">“</span><p>' + esc(page["intro"]) + '</p></div></section>'
    body_content = contextual_content(
        page, intro + first
        + '<section class="cc-pullquote" aria-label="A promise to families"><blockquote>Families deserve calm direction and clear answers.</blockquote></section>'
        + second + extra)
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page["seo"])}</title><meta name="description" content="{esc(page["meta"])}"><meta name="robots" content="noindex,nofollow">
<link rel="preload" as="font" href="/assets/fonts/fraunces-latin.woff2" type="font/woff2" crossorigin fetchpriority="high">
<link rel="preload" as="font" href="/assets/fonts/fraunces-italic-latin.woff2" type="font/woff2" crossorigin fetchpriority="high">
<link rel="icon" type="image/png" href="/assets/favicon.png">
<link rel="stylesheet" href="/assets/elh.css?v=20260901">
<link rel="stylesheet" href="/assets/header-nav.css?v=20260920a">
<link rel="stylesheet" href="/assets/internal-links.css?v=20261007-inline">
<link rel="stylesheet" href="/__service-preview-assets/service-pages.css">
{schema(page)}
<script async src="/assets/analytics.js?v=8a19c4a3a193"></script>
</head><body>
<a class="skip-link" href="#main-content">Skip to main content</a>
{header}
<main id="main-content" tabindex="-1">
  <div id="service-page"{' class="bereavement-service-page"' if page["slug"] == "bereavement-support" else ""}>
    <section class="cc-hero" aria-labelledby="cc-title"><div class="cc-hero-inner">
      <div class="cc-hero-copy"><p class="cc-eyebrow">{esc(page["eyebrow"])}</p><h1 id="cc-title">{crumb_title}</h1><p class="cc-subline">{esc(page["subline"])}</p>
        <div class="cc-actions"><a class="cc-button" href="tel:8059537273">Call Today for Care Options · 805.953.7273</a><a class="cc-button cc-button--outline" href="/refer#referral-form">Refer a Patient</a></div>
      </div>
      <figure class="cc-hero-photo"><img fetchpriority="high" src="{hero}" alt="{esc(page["hero_alt"])}"></figure>
    </div></section>
    {body_content}
    {standard_band()}
    {cover}
    {render_faq(page["faq"])}
    {related_links(page)}
    <section class="cc-closing"><h2>Here in Moments That Matter Most</h2><div class="cc-actions"><a class="cc-button cc-button--outline" href="tel:8059537273">805.953.7273</a><a class="cc-button" href="tel:8059537273">Call Today for Care Options</a></div></section>
  </div>
</main>
{footer}
{SHARED_SEARCH}
<script src="/assets/header.js?v=20260920"></script>
<script src="/assets/chat.js?v=20260805" defer></script>
</body></html>'''

def directory_template(header: str, footer: str) -> str:
    groups_html = []
    by_slug = {p["slug"]: p for p in PAGES}
    for group_name, items in GROUPS:
        cards = []
        for item in items:
            if item in by_slug:
                p = by_slug[item]
                href, label, summary = "/services/" + p["slug"], p["title"], p["intro"].split(". ", 1)[0] + "."
            else:
                href, summary = EXISTING[item]
                label = item
            cards.append('<article class="directory-item"><a href="' + esc(href) + '">' + esc(label) + '</a><p>' + esc(summary) + '</p></article>')
        group_class = "directory-group directory-group--getting-started" if group_name == "Getting Started" else "directory-group"
        if group_name == "Care for Specific Conditions":
            group_class += " directory-group--conditions"
        groups_html.append('<section class="' + group_class + '"><h2>' + esc(group_name) + '</h2>' + "".join(cards) + '</section>')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hospice Services | Eternal Life Hospice</title><meta name="description" content="Explore hospice care services across Ventura and Los Angeles counties."><meta name="robots" content="noindex,nofollow"><link rel="icon" href="/assets/favicon.png">
<link rel="preload" as="font" href="/assets/fonts/fraunces-latin.woff2" type="font/woff2" crossorigin fetchpriority="high"><link rel="preload" as="font" href="/assets/fonts/fraunces-italic-latin.woff2" type="font/woff2" crossorigin fetchpriority="high">
<link rel="stylesheet" href="/assets/elh.css?v=20260901"><link rel="stylesheet" href="/assets/header-nav.css?v=20260920a"><link rel="stylesheet" href="/assets/internal-links.css?v=20261007-inline"><link rel="stylesheet" href="/__service-preview-assets/service-pages.css"><script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":"https://eternallifehospice.com/"},{"@type":"ListItem","position":2,"name":"Services","item":"https://eternallifehospice.com/services"}]}</script><script async src="/assets/analytics.js?v=8a19c4a3a193"></script></head><body>
<a class="skip-link" href="#main-content">Skip to main content</a>''' + header + '''
<main id="main-content" tabindex="-1"><div id="service-page" class="services-directory-page">
<section class="cc-hero"><div class="cc-hero-inner"><div class="cc-hero-copy"><p class="cc-eyebrow">Services</p><h1>Our Services</h1><div class="cc-actions"><a class="cc-button" href="tel:8059537273">Call Today for Care Options · 805.953.7273</a><a class="cc-button cc-button--outline" href="/refer#referral-form">Refer a Patient</a></div></div><figure class="cc-hero-photo"><img src="/__service-preview-assets/hero.webp" alt="Illustrative hospice care scene"></figure></div></section>
<section class="cc-section cc-how"><div class="cc-wrap"><div class="directory-groups">''' + "".join(groups_html) + '''</div></div></section>
<section class="cc-closing"><h2>Here in Moments That Matter Most</h2><div class="cc-actions"><a class="cc-button cc-button--outline" href="tel:8059537273">805.953.7273</a><a class="cc-button" href="tel:8059537273">Call Today for Care Options</a></div></section></div></main>''' + footer + '''
''' + SHARED_SEARCH + '''<script src="/assets/header.js?v=20260920"></script><script src="/assets/chat.js?v=20260805" defer></script></body></html>'''

def main() -> None:
    source = SEED.read_text(encoding="utf-8")
    header_match = re.search(r'<header id="hdr">.*?</header>', source, re.S)
    footer_match = re.search(r'<footer id="site-footer">.*?</footer>', source, re.S)
    if not header_match or not footer_match:
        raise RuntimeError("Approved care-community seed must contain the shared header and footer.")
    header, footer = header_match.group(0), footer_match.group(0)
    catalog = []
    for page in PAGES:
        rendered = page_template(page, header, footer)
        (OUT / (page["slug"] + ".html")).write_text(rendered, encoding="utf-8")
        if page["slug"] == "hospice-in-assisted-living-and-skilled-nursing":
            (OUT / "care-community.html").write_text(rendered, encoding="utf-8")
        catalog.append({
            "slug": page["slug"],
            "title": page["title"],
            "summary": page["intro"].split(". ", 1)[0] + ".",
            "hero": "/__service-preview-assets/" + ("hero.webp" if page["slug"] == "hospice-in-assisted-living-and-skilled-nursing" else page["slug"] + "-hero.webp"),
            "wide": "/__service-preview-assets/" + ("communication.webp" if page["slug"] == "hospice-in-assisted-living-and-skilled-nursing" else page["slug"] + "-communication.webp"),
        })
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "services-directory.html").write_text(directory_template(header, footer), encoding="utf-8")

if __name__ == "__main__":
    main()
