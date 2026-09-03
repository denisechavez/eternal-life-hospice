#!/usr/bin/env python3
"""
Eternal Life Hospice — City Page Generator
------------------------------------------
Reads city-data.json, writes one HTML file per published city
into website/elh-preview/.

CANONICAL SOURCE RULE
---------------------
city-data.json is the single source of truth for all city page content.
The generated HTML files in elh-preview/ are build artifacts — do not
hand-edit them.  Any prose changes (summaries, intro paragraphs, nearby
city text, FAQ answers) must be made in city-data.json first, then the
HTML regenerated.

OVERWRITE PROTECTION
--------------------
By default, this script will NOT overwrite an HTML file that already
exists on disk.  This prevents accidentally clobbering hand-crafted
edits that have not yet been merged back into city-data.json.

To overwrite existing files, pass --force explicitly:

    python3 website/build-cities.py --force
    python3 website/build-cities.py --slug thousand-oaks --force

Run from repo root:
    python3 website/build-cities.py            # skips cities that already have HTML
    python3 website/build-cities.py --force    # overwrites all published cities
    python3 website/build-cities.py --slug thousand-oaks
    python3 website/build-cities.py --dry-run  # show what would be written without writing
"""

import json, os, re, sys, textwrap, argparse
from fragments import HEADER_HTML


def meta_description(c: dict) -> str:
    """Build a locally specific search snippet near the 150–160 character target."""
    city = c["city"]
    subregion = c["subregion"]
    county = c["county"]

    if city == "Conejo Valley":
        territory = "Thousand Oaks and Westlake Village"
    elif city in {"Thousand Oaks", "Westlake Village"}:
        territory = "the Conejo Valley and Ventura County"
    else:
        territory = subregion.split(" · ", 1)[0]
        if county.lower() not in territory.lower():
            territory = f"{territory}, {county}"

    prefixes = (
        "Medicare-certified hospice care in",
        "Eternal Life Hospice offers Medicare-certified hospice care in",
        "Eternal Life Hospice provides Medicare-certified hospice care in",
    )
    connectors = ("— serving", "—")
    differentiators = (
        "Physician-supported care at home.",
        "Physician-supported comfort care at home.",
        "Compassionate, physician-supported care at home.",
        "Care at home, supported by our hospice physician.",
    )
    calls_to_action = ("Call 805.953.7273.", "Call for guidance: 805.953.7273.")

    candidates = [
        f"{prefix} {city}, CA {connector} {territory}. {differentiator} {cta}"
        for prefix in prefixes
        for connector in connectors
        for differentiator in differentiators
        for cta in calls_to_action
    ]
    in_range = [text for text in candidates if 150 <= len(text) <= 160]
    return min(in_range or candidates, key=lambda text: abs(len(text) - 155))

def _hero_img_tag(slug: str, city: str) -> str:
    """Return a responsive <picture> element for the city hero image.

    Emits a mobile 640px variant (<= 768 px) and the full-size WebP for
    wider screens, with a JPEG fallback.  Hero images are deployed
    separately; their on-disk presence is NOT checked here.
    """
    return (
        f'<picture class="hero-bg">'
        f'<source srcset="assets/img/city/{slug}-mobile.webp" media="(max-width:768px)" type="image/webp">'
        f'<source srcset="assets/img/city/{slug}.webp" type="image/webp">'
        f'<img class="hero-bg" src="assets/img/city/{slug}.jpg"'
        f' alt="{city}, California" width="1536" height="1024"'
        f' loading="eager" decoding="async">'
        f'</picture>'
    )

def _hero_preload_tag(slug: str) -> str:
    """Return responsive <link rel="preload"> tags for the city hero image.

    Emits two preload hints: a mobile 640px WebP for narrow screens and the
    full-size WebP for wider screens, mirroring the homepage hero pattern.
    Hero images are deployed separately; on-disk presence is NOT checked here.
    """
    return (
        f'<link rel="preload" as="image" '
        f'href="assets/img/city/{slug}-mobile.webp" '
        f'media="(max-width:768px)" type="image/webp" fetchpriority="high">\n  '
        f'<link rel="preload" as="image" '
        f'href="assets/img/city/{slug}.webp" '
        f'media="(min-width:769px)" type="image/webp" fetchpriority="high">'
    )

BASE = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE, "city-data.json")
OUT_DIR   = os.path.join(BASE, "elh-preview")

# ── Deferred script snippets (must NOT be inside an f-string — JS braces clash) ─

HEAD_SCRIPTS = (
    '<script defer src="/assets/analytics.js?v=20260727h"></script>'
    # UserWay (accessibility, essential) and WhatConverts (call-tracking, marketing)
    # are both bootstrapped by analytics.js to respect the cookie consent gate.
)

# ── Shared HTML fragments ──────────────────────────────────────────────────────

HEADER = HEADER_HTML

CRED_STRIP = """\
<div class="cred-strip"><div class="cred-track">
    <a class="lc cms" href="https://www.medicare.gov/care-compare/?providerType=Hospice" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-cms.webp" srcset="assets/img/cred-cms-1x.webp 1x, assets/img/cred-cms.webp 2x" alt="CMS Medicare Certified"><div class="ct"><span class="cl">Medicare Certified</span><span class="csub">Centers for Medicare &amp; Medicaid Services</span><span class="ext">medicare.gov &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="lc cdph" href="https://www.cdph.ca.gov/Programs/CHCQ/LCP/CalHealthFind/pages/home.aspx" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-cdph.webp" srcset="assets/img/cred-cdph-1x.webp 1x, assets/img/cred-cdph.webp 2x" alt="CDPH Licensed"><div class="ct"><span class="cl">CDPH Licensed</span><span class="csub">California Dept. of Public Health</span><span class="ext">cdph.ca.gov &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="lc achc" href="https://achc.org/search-facilities/" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-achc.webp" alt="ACHC Accredited"><div class="ct"><span class="cl">ACHC Accredited</span><span class="csub">Accreditation Commission for Health Care</span><span class="ext">achc.org &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="ic" href="/#first48"><svg viewBox="0 0 48 48" width="44" height="44" fill="none"><circle cx="24" cy="24" r="15" stroke="#D8CDBF" stroke-width="1.5"/><line x1="24" y1="12" x2="24" y2="24" stroke="#5B2E59" stroke-width="2.5" stroke-linecap="round"/><line x1="24" y1="24" x2="33" y2="24" stroke="#C9B07E" stroke-width="2.5" stroke-linecap="round"/><circle cx="24" cy="24" r="2.5" fill="#5B2E59"/></svg><div class="ct"><span class="cl">Same-Day Admissions</span><span class="csub">24/7 On-Call Nursing</span></div></a>
    <div class="csep"></div>
    <a class="ic" href="/#medicare"><svg viewBox="0 0 48 48" width="44" height="44" fill="none"><path d="M24 9l13 4.5v9.8c0 7.5-5.5 13-13 16-7.5-3-13-8.5-13-16v-9.8L24 9z" stroke="#5B2E59" stroke-width="1.4" fill="none"/><polyline points="18,24 22,28 30,20" stroke="#C9B07E" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="ct"><span class="cl">Little to no out-of-pocket cost</span><span class="csub">For most covered hospice services</span></div></a>
    <div class="csep"></div>
</div></div>"""

# ── County-specific footer location shortcuts ──────────────────────────────────
# Ventura County pages surface West-Valley/Ventura cities; LA County pages
# surface LA-area cities so the 3 shortcuts are relevant to the visitor.

_FOOT_LOC_VENTURA = (
    '<a href="/hospice-thousand-oaks-ca">Thousand Oaks</a>'
    '<a href="/hospice-simi-valley-ca">Simi Valley</a>'
    '<a href="/hospice-calabasas-ca">Calabasas</a>'
    '<a href="/hospice-ventura-and-los-angeles-county-ca">County Coverage</a>'
)

_FOOT_LOC_LA = (
    '<a href="/hospice-thousand-oaks-ca">Thousand Oaks</a>'
    '<a href="/hospice-simi-valley-ca">Simi Valley</a>'
    '<a href="/hospice-calabasas-ca">Calabasas</a>'
    '<a href="/hospice-ventura-and-los-angeles-county-ca">County Coverage</a>'
)


def make_footer(county: str) -> str:
    """Return the full city-page footer with the shared Service Areas links."""
    loc_links = _FOOT_LOC_LA if county == "Los Angeles County" else _FOOT_LOC_VENTURA
    return (
        '<footer id="site-footer">\n'
        '  <div class="foot-grid">\n'
        '    <div><div class="foot-logo"><a href="/" aria-label="Eternal Life Hospice &mdash; home">'
        '<img loading="lazy" decoding="async" src="assets/img/elh-logo-cream-g.webp" alt="Eternal Life Hospice logo">'
        '</a></div><p class="foot-tag">Care That Honors Life.</p>'
        '<p class="foot-legal">Medicare-Certified &middot; CDPH-Licensed &middot; ACHC-Accredited. '
        'Serving families across Ventura and Los Angeles Counties.</p>'
        '<div class="foot-qr"><img src="assets/img/qr-cream.webp" alt="Scan to visit eternallifehospice.com" '
        'width="96" height="96" loading="lazy"><span>Scan to visit<br>on your phone</span></div></div>\n'
        '    <div class="foot-col"><h2>Hospice Care</h2>'
        '<a href="/hospice-care">What Is Hospice Care?</a>'
        '<a href="/resources/when-is-it-time">When Is It Time?</a>'
        '<a href="/resources/first-48-hours">The First 48 Hours</a>'
        '<a href="/resources/medicare-hospice-benefit">What Hospice Covers</a>'
        '<a href="/resources/how-to-choose-a-hospice">How to Choose a Hospice</a></div>'
        '<div class="foot-col"><h2>Services</h2>'
        '<a href="/services">All Services</a>'
        '<a href="/resources/pain-symptom-management">Pain &amp; Symptom Management</a>'
        '<a href="/resources/comfort-therapies">Integrative &amp; Whole-Person Care</a>'
        '<a href="/sound-bath">Sound Bath</a>'
        '<a href="/services/medical-aid-in-dying-california">End-of-Life Care &amp; Choices</a></div>'
        '<div class="foot-col"><h2>Resources</h2>'
        '<a href="/family-guide">Family Guide</a>'
        '<a href="/blog">The Eternal Journal</a>'
        '<a href="/care-brief">Care Brief</a>'
        '<a href="/volunteer">Volunteer</a>'
        '<a href="/media-kit">Media Kit</a>'
        '<a href="/careers">Careers</a></div>'
        f'<div class="foot-col"><h2>Service Areas</h2>{loc_links}</div>'
        '<div class="foot-col"><h2>About</h2>'
        '<a href="/about/aleksandra-dubina">Our Founder</a>'
        '<a href="/#care-team">Our Team</a>'
        '<a href="/#accreditations">Accreditations</a>'
        '<a href="/#standard">Eternal Standard</a>'
        '</div>'
        '<div class="foot-col"><h2>Contact</h2>\n'
        '      <a class="fc-line" href="tel:18059537273">'
        '<svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>'
        '</svg><span>805.953.7273</span></a>'
        '<span class="fc-line fc-direct">'
        '<svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>'
        '</svg><span>805.953.7273 \u00b7 Direct</span></span>\n'
        '      <span class="fc-line fc-fax">'
        '<svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 6 2 18 2 18 9"/>'
        '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
        '<rect x="6" y="14" width="12" height="8"/>'
        '</svg><span>805.953.8530 fax</span></span>\n'
        '      <a class="fc-line" href="mailto:info@eternallifehospice.com">'
        '<svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/>'
        '<polyline points="22,6 12,13 2,6"/>'
        '</svg><span>info@eternallifehospice.com</span></a>\n'
        '      <a class="fc-line fc-addr" href="https://maps.google.com/?cid=9771388271577679785" target="_blank" rel="noopener">'
        '<svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
        '<circle cx="12" cy="10" r="3"/>'
         '</svg><span>4165 E Thousand Oaks Blvd, Suite 325B<br>Westlake Village, CA 91362</span></a>\n'
         '      <div class="foot-subgroup"><h2>For Professionals</h2>'
         '<a href="/refer#referral-form">Physicians &amp; Referrals</a>'
         '<a href="/referral-card">Referral eCard</a>'
         '<a href="/?lead=voice#leadcap">Schedule a Session</a></div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <nav class="foot-social" aria-label="Eternal Life Hospice on social media">'
        '<span class="fs-label">Stay Connected</span>'
        '<a href="https://www.linkedin.com/company/eternal-life-hospice/" target="_blank" rel="noopener" aria-label="LinkedIn">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4V9h4v1.57A6 6 0 0 1 16 8z"/>'
        '<rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg></a>'
        '<a href="https://www.facebook.com/eternallifehospiceinc" target="_blank" rel="noopener" aria-label="Facebook">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>'
        '<a href="https://www.instagram.com/eternallifehospice/" target="_blank" rel="noopener" aria-label="Instagram">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>'
        '<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>'
        '<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>'
        '<a href="https://www.youtube.com/@EternalLifeHospice" target="_blank" rel="noopener" aria-label="YouTube">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/>'
        '<polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/></svg></a></nav>\n'
        '  <div class="foot-disclaimer"><strong style="color:var(--gold)">Disclaimer:</strong> '
        'Eternal Life Hospice Inc. is a licensed and Medicare-certified hospice care provider. '
        'The integrative modalities described are complementary care offered for patient comfort and wellbeing; '
        'they are not intended to diagnose, treat, cure or prevent any medical condition. '
        'Medicare coverage details are subject to change; confirm current eligibility with your care team or call '
        '<a href="tel:18006334227" style="color:inherit;text-decoration:none">1.800.MEDICARE</a>.</div>\n'
        '  <div class="foot-bottom"><span>&copy; 2026 Eternal Life Hospice Inc. All rights reserved.</span>'
        '<span class="foot-bottom-links">'
        '<a href="/privacy-policy" style="text-decoration:none">Privacy Policy</a> &nbsp;&middot;&nbsp; '
        '<a href="/terms" style="text-decoration:none">Terms &amp; Conditions</a> &nbsp;&middot;&nbsp; '
        '<a href="#" onclick="window.elhCookieSettings&amp;&amp;window.elhCookieSettings();return false;" '
        'style="color:inherit;text-decoration:none">Cookie Settings</a>'
        '<button id="elh-ada-trigger" class="foot-access" type="button" aria-label="Accessibility options">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">'
        '<circle cx="12" cy="4.5" r="2"/><path d="M17 8h-4.15l-.85-2H7v2h3.15l.85 2H8c-1.1 0-2 .9-2 2v5h2v-4.5h1.35L11 16h2l-1.5-3.5V12h4l1 4h2l-1.25-5H17z"/></svg>'
        '<span class="sr-only">Accessibility</span></button></span></div>\n'
        '</footer>\n'
        '<script src="assets/header.js?v=20260901d" defer></script>'
        '<script src="/assets/chat.js?v=20260805" defer></script>\n'
        '<div class="search-overlay" id="searchOverlay" role="dialog" aria-modal="true" '
        'aria-label="Site search" aria-hidden="true">\n'
        '  <div class="search-box">'
        '<input type="text" id="searchInput" placeholder="Search pages, cities, resources..." '
        'autocomplete="off" aria-label="Search">'
        '<button class="search-close" id="searchClose" aria-label="Close search">&times;</button></div>\n'
        '  <p class="search-hint">Press Enter to open the first result, or Escape to close</p>\n'
        '  <div class="search-results" id="searchResults"></div>\n'
        '</div>'
    )

# ── Schema builders ────────────────────────────────────────────────────────────

def webpage_schema(c):
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": c["canonicalUrl"] + "#webpage",
        "url": c["canonicalUrl"],
        "name": c["title"],
        "description": meta_description(c),
        "isPartOf": {"@id": "https://eternallifehospice.com/#website"},
        "about": {"@id": "https://eternallifehospice.com/#organization"},
        "breadcrumb": {"@id": c["canonicalUrl"] + "#breadcrumb"},
        "inLanguage": "en-US",
        "dateModified": c["lastMaterialUpdate"]
    }

def service_schema(c):
    """Describe service coverage without redefining the canonical organization.

    The organization's physical address and GeoCoordinates live in the
    homepage entity. City pages reference that entity and describe their
    verified coverage as a Service, so a service-area centroid cannot be
    mistaken for the hospice's office location.
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Service",
        "@id": c["canonicalUrl"] + "#service",
        "name": f"Hospice care in {c['city']}, California",
        "description": f"Medicare-certified hospice care serving {c['city']}, {c['county']} and surrounding communities.",
        "provider": {"@id": "https://eternallifehospice.com/#organization"},
        "areaServed": [
            {"@type": "City", "name": f"{c['city']}, California"},
            {"@type": "AdministrativeArea", "name": f"{c['county']}, California"}
        ]
    }
    return schema

def breadcrumb_schema(c):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "@id": c["canonicalUrl"] + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://eternallifehospice.com"},
            {"@type": "ListItem", "position": 2, "name": "Service Areas", "item": "https://eternallifehospice.com/hospice-ventura-and-los-angeles-county-ca"},
            {"@type": "ListItem", "position": 3, "name": f"Hospice Care in {c['city']}", "item": c["canonicalUrl"]}
        ]
    }

def faq_schema(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "provider": {"@id": "https://eternallifehospice.com/#organization"},
        "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faqs
        ]
    }

# ── FAQ HTML builder ────────────────────────────────────────────────────────────

def faq_html(faqs):
    parts = []
    for i, f in enumerate(faqs):
        open_attr = " open" if i == 0 else ""
        parts.append(f'  <details class="faq-item"{open_attr}><summary>{f["q"]}</summary><p>{f["a"]}</p></details>')
    return "\n".join(parts)


def local_faqs(faqs):
    """Keep the city FAQ focused on questions with location-specific value.

    The general hospice, Medicare and timing explainers already have dedicated
    resource pages. Each city page keeps its service-area answer and its final
    locally tailored question, so the FAQ remains useful without repeating the
    same educational block across the entire local cluster.
    """
    if not faqs:
        return []
    selected = [faqs[0]]
    if len(faqs) > 1 and faqs[-1] != faqs[0]:
        selected.append(faqs[-1])
    return selected

# ── Nearby-city links builder ───────────────────────────────────────────────────

def nearby_links_html(nearby_city_pages):
    if not nearby_city_pages:
        return ""
    links = [f'<a href="{p["slug"]}">{p["city"]}</a>' for p in nearby_city_pages]
    return "Explore hospice care in " + ", ".join(links[:-1]) + (" and " if len(links) > 1 else "") + links[-1] + \
           '. Or <a href="hospice-ventura-and-los-angeles-county-ca">explore hospice care across our full service area</a>.'

def care_settings_html(settings):
    items = "\n".join(f'      <div><span>&#10003;</span><span>{s}</span></div>' for s in settings)
    return f'  <div class="prov">\n{items}\n  </div>'

# ── Full page renderer ─────────────────────────────────────────────────────────

def intro_html(intro: str) -> str:
    """Render localIntroduction as one or more <p> tags.

    city-data.json stores multi-paragraph intros joined with double-newline.
    Each segment becomes its own <p> so the HTML output matches hand-authored
    pages that had multiple paragraphs in the intro section.
    """
    segments = [s.strip() for s in intro.split("\n\n") if s.strip()]
    return "\n".join(f"  <p>{s}</p>" for s in segments)


def render_page(c):
    slug        = c["slug"]
    city        = c["city"]
    county      = c["county"]
    subregion   = c["subregion"]
    canonical   = c["canonicalUrl"]
    title       = c["title"]
    meta_desc   = meta_description(c)
    h1          = c["h1"]
    eyebrow     = c["heroEyebrow"]
    at_a_glance = c["atAGlanceSummary"]
    intro       = c["localIntroduction"]
    nearby_para = c.get("localNearbyParagraph", "")
    provider_ctx= c.get("providerContext", "")
    family_ctx  = c.get("familyContext", "")
    settings    = c.get("careSettings", [
        f"<b>Private residences</b> &mdash; at home in {city} and surrounding neighborhoods",
        "<b>Assisted-living communities</b> &mdash; coordinated with the facility&rsquo;s care team",
        "<b>Residential care facilities</b> &mdash; including memory care settings",
        f"<b>Board-and-care homes</b> &mdash; small group settings in {city} and nearby communities",
        "<b>Skilled-nursing facilities</b> &mdash; layered onto existing nursing care"
    ])
    faqs        = local_faqs(c["faqItems"])
    last_update = c.get("lastMaterialUpdate", "2026-07-22")

    schemas = [
        json.dumps(webpage_schema(c), ensure_ascii=False),
        json.dumps(service_schema(c), ensure_ascii=False),
        json.dumps(breadcrumb_schema(c), ensure_ascii=False),
        json.dumps(faq_schema(faqs), ensure_ascii=False)
    ]
    schema_tags = "\n".join(
        f'  <script type="application/ld+json">{s}</script>' for s in schemas
    )

    nearby_html = nearby_links_html(c.get("nearbyCityPages", []))

    page = f"""<!doctype html><html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{meta_desc}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">
  <meta property="og:site_name" content="Eternal Life Hospice"><meta property="og:locale" content="en_US"><meta property="og:image:width" content="2400"><meta property="og:image:height" content="1260"><meta property="og:image:alt" content="{title}">
  <meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@EternalLifeHospice"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{meta_desc}"><meta name="twitter:image" content="https://eternallifehospice.com/assets/og-image-v2.jpg">
  <link rel="icon" type="image/png" href="assets/favicon.png">
  {_hero_preload_tag(slug)}
  <link rel="preload" as="font" href="assets/fonts/fraunces-latin.woff2" type="font/woff2" crossorigin fetchpriority="high">
  <link rel="preload" as="font" href="assets/fonts/fraunces-italic-latin.woff2" type="font/woff2" crossorigin fetchpriority="high">
  <link rel="preload" as="font" href="assets/fonts/JostELH-Regular.woff2" type="font/woff2" crossorigin>
  <link rel="preload" as="font" href="assets/fonts/JostELH-SemiBold.woff2" type="font/woff2" crossorigin>
  <link rel="preload" href="assets/elh.css?v=20260901" as="style">
  <link rel="stylesheet" href="assets/elh.css?v=20260901">
  <link rel="stylesheet" href="/assets/header-nav.css?v=20260901ab">
{schema_tags}
{HEAD_SCRIPTS}
</head><body>
<a class="skip-link" href="#main-content">Skip to main content</a>
{HEADER}
{CRED_STRIP}
<main id="main-content" tabindex="-1">
<section class="hero hero--city hero--tall">{_hero_img_tag(slug, city)}
    <div class="eyebrow">{eyebrow}</div>
    <h1>{h1}</h1>
    <p>Eternal Life Hospice provides physician-supported hospice care for eligible patients and families in {city} and surrounding communities. Care may be provided in private homes, assisted-living communities, residential-care settings and skilled-nursing facilities throughout {county}.</p>
    <div class="hero-btns"><a class="btn-gold" href="tel:18059537273">Call for Hospice Guidance</a><a class="btn-ghost" href="family-guide">Read the Family Guide &#8594;</a><a class="btn-ghost" href="/refer">Refer a Patient &#8594;</a></div>
</section>
<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="hospice-ventura-and-los-angeles-county-ca">Service Area</a></li><li aria-current="page">{city} Hospice Care</li></ol></nav>

<section class="sec wrap" id="at-a-glance">
  <h2>Hospice Care in {city} at a Glance</h2>
  <p class="at-a-glance-summary">{at_a_glance}</p>
</section>

<section class="sec wrap">
  <h2>Hospice care at home in {city}, California</h2>
{intro_html(intro)}
  {"<p>" + nearby_para + "</p>" if nearby_para else ""}
  {"<p>" + nearby_html + "</p>" if nearby_html else ""}
</section>

<section class="sec wrap">
  <h2>Hospice services for {city} families</h2>
  <p>Hospice care is comfort-focused care for an eligible patient with a terminal illness, provided under physician direction after a clinical evaluation. Eternal Life Hospice coordinates nursing, aide support, social work, chaplaincy, medications, equipment and family education around one individualized plan of care.</p>
  <p>Read <a href="/resources/when-is-it-time">when it may be time to consider hospice</a>, <a href="/resources/first-48-hours">what happens in the first 48 hours</a>, and <a href="/resources/medicare-hospice-benefit">how the Medicare hospice benefit works</a>. A conversation with our team can clarify the next step without pressure.</p>
</section>

<section class="sec wrap">
  <h2>Care settings in {city}</h2>
{care_settings_html(settings)}
</section>

<section class="sec wrap">
  <h2>Medicare hospice coverage</h2>
  <p>Most Medicare-covered hospice services have little to no out-of-pocket cost. Limited copayments may apply in specific circumstances. Coverage depends on eligibility, the terminal diagnosis and the individualized plan of care. <a href="/resources/medicare-hospice-benefit">Learn about Medicare hospice coverage</a>.</p>
</section>

<section class="sec wrap">
  <h2>Resources for families in {city}</h2>
  <p>Use the <a href="family-guide">Family Guide</a> to compare providers and prepare for a hospice conversation, or read <a href="/resources/how-to-choose-a-hospice">how to choose a hospice</a>. These resources explain the general process; our team can answer questions about care in {city} and {county}.</p>
</section>

<section class="sec wrap">
  <h2>For physicians and care professionals in {city}</h2>
  <p>{provider_ctx if provider_ctx else f"Physicians, discharge planners and care coordinators serving {city} and {subregion} can refer an eligible patient for hospice evaluation through our professional pathway."}</p>
  <a class="county-link" href="/refer">Refer a Hospice Patient &#8594;</a>
</section>

<section class="sec wrap lfaq">
  <h2>Common questions about hospice in {city}</h2>
{faq_html(faqs)}
</section>

<div class="creds">Medicare-Certified <span class="cd-sep" aria-hidden="true">&#8226;</span> CDPH-Licensed <span class="cd-sep" aria-hidden="true">&#8226;</span> ACHC-Accredited <span class="cd-sep" aria-hidden="true">&#8226;</span> 24/7 Availability</div>

<section class="cta">
  <h2>Hospice Guidance for Families in {city}</h2>
  <p>{family_ctx if family_ctx else "A conversation costs nothing and brings clarity. We will guide you from there."}</p>
  <div class="btns"><a class="btn-gold" href="tel:18059537273">Call Eternal Life Hospice</a><a class="btn-ghost" href="family-guide">Read the Family Guide &#8594;</a><a class="btn-ghost" href="/refer">Refer a Patient &#8594;</a></div>
</section>
</main>
{make_footer(county)}
</body></html>"""
    return page

# ── Main ───────────────────────────────────────────────────────────────────────

def _normalise(html: str) -> str:
    """Collapse whitespace for drift comparison (ignores indent/newline noise)."""
    return re.sub(r"\s+", " ", html).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Generate city HTML pages from city-data.json."
    )
    parser.add_argument("--slug", help="Build only this city slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print filenames only, do not write")
    parser.add_argument("--check", action="store_true",
                        help="Drift-detection mode: generate HTML in memory and "
                             "compare with on-disk files. Exit non-zero if any "
                             "city page is out of sync with city-data.json. "
                             "Does not write any files.")
    parser.add_argument("--force", action="store_true",
                        help="(Deprecated — no longer needed. Kept for backward "
                             "compatibility. Builds always write output now that "
                             "city-data.json is the canonical source.)")
    args = parser.parse_args()

    with open(DATA_FILE, encoding="utf-8") as f:
        cities = json.load(f)

    if args.check:
        # ── Drift-check mode ──────────────────────────────────────────────────
        # Generate HTML from JSON in memory and compare with on-disk pages.
        # Reports any city where the two diverge; exits 1 if drift is found.
        drifted = []
        missing = []
        for c in cities:
            if c.get("publishStatus") != "published":
                continue
            if args.slug and c["slug"] != args.slug:
                continue
            out = os.path.join(OUT_DIR, f"hospice-{c['slug']}-ca.html")
            if not os.path.exists(out):
                missing.append(c["slug"])
                continue
            generated = _normalise(render_page(c))
            on_disk   = _normalise(open(out, encoding="utf-8").read())
            if generated != on_disk:
                drifted.append(c["slug"])
                print(f"  DRIFT: {c['slug']}")
        if missing:
            print(f"\nMissing HTML (not yet built): {', '.join(missing)}")
        if drifted:
            print(f"\nDrift detected in {len(drifted)} city page(s).")
            print("Run  python3 website/build-cities.py  to regenerate.")
            sys.exit(1)
        else:
            checked = len([c for c in cities
                           if c.get("publishStatus") == "published"
                           and (not args.slug or c["slug"] == args.slug)
                           and os.path.exists(
                               os.path.join(OUT_DIR, f"hospice-{c['slug']}-ca.html")
                           )])
            print(f"OK — {checked} city page(s) match city-data.json.")
        return

    # ── Normal build mode ─────────────────────────────────────────────────────
    built         = []
    skipped_draft = []

    for c in cities:
        if c.get("publishStatus") != "published":
            skipped_draft.append(c["slug"])
            continue
        if args.slug and c["slug"] != args.slug:
            continue

        html = render_page(c)
        out  = os.path.join(OUT_DIR, f"hospice-{c['slug']}-ca.html")

        if args.dry_run:
            action = "overwrite" if os.path.exists(out) else "write"
            print(f"  [DRY] would {action} {out}")
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            built.append(c["slug"])
            print(f"  ✓ hospice-{c['slug']}-ca.html")

    print(f"\nBuilt: {len(built)} pages")
    print(f"Skipped (draft/future): {len(skipped_draft)} cities")
    if skipped_draft:
        print("  Drafts:", ", ".join(skipped_draft[:20]))

if __name__ == "__main__":
    main()
