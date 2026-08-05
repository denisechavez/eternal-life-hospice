#!/usr/bin/env python3
"""
Eternal Life Hospice — City Page Generator
==========================================
Reads city-data.json, writes one HTML file per published city
into website/elh-preview/.

Run from repo root:
    python3 website/build-cities.py

Or for a single city:
    python3 website/build-cities.py --slug thousand-oaks
"""

import json, os, re, sys, textwrap, argparse

def _hero_img_tag(slug: str, city: str) -> str:
    """Return a <picture> element for the city hero image.

    Always emits the full WebP-source + JPEG-fallback <picture> so every
    generated page has an <img class="hero-bg"> in the hero section.
    Hero images (assets/img/city/{slug}.webp and .jpg) are deployed
    separately; their on-disk presence is NOT checked here.
    """
    return (
        f'<picture>'
        f'<source srcset="assets/img/city/{slug}.webp" type="image/webp">'
        f'<img class="hero-bg" src="assets/img/city/{slug}.jpg"'
        f' alt="{city}, California" width="1536" height="1024"'
        f' loading="eager" decoding="async">'
        f'</picture>'
    )

def _hero_preload_tag(slug: str) -> str:
    """Return the <link rel="preload"> tag for the city hero image.

    Always emits a WebP preload so browsers begin fetching the hero image
    before the CSS is parsed.  The JPEG is the fallback inside the <picture>
    element; the preload always targets the WebP variant.
    Hero images are deployed separately; on-disk presence is NOT checked here.
    """
    return (
        f'<link rel="preload" as="image" '
        f'href="assets/img/city/{slug}.webp" '
        f'type="image/webp" fetchpriority="high">'
    )

BASE = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE, "city-data.json")
OUT_DIR   = os.path.join(BASE, "elh-preview")

# ── Deferred script snippets (must NOT be inside an f-string — JS braces clash) ─

HEAD_SCRIPTS = (
    '<script defer src="/assets/analytics.js?v=20260727h"></script>\n'
    # UserWay accessibility widget — requestIdleCallback deferred (never DOMContentLoaded)
    '<script>(function(d){var load=function(){var s=d.createElement(\'script\');'
    's.setAttribute(\'data-color\',\'#6793AC\');'
    's.setAttribute(\'data-trigger\',\'elh-ada-trigger\');'
    's.setAttribute(\'data-account\',\'puHleOAe1C\');'
    's.src=\'https://cdn.userway.org/widget.js\';d.body.appendChild(s)};'
    '\'requestIdleCallback\'in window?window.requestIdleCallback(load):window.addEventListener(\'load\',load)})(document)'
    '</script>\n'
    '<noscript>Please ensure Javascript is enabled for purposes of '
    '<a href="https://userway.org">website accessibility</a></noscript>\n'
    # WhatConverts lead tracking — window load deferred (never inline async)
    '<script>window.addEventListener(\'load\',function(){'
    'var f=function(a){return JSON.parse(JSON.stringify(a))};'
    'window.$wc_leads=window.$wc_leads||{doc:{url:f(document.URL),ref:f(document.referrer),'
    'search:f(location.search),hash:f(location.hash)}};'
    'var s=document.createElement(\'script\');'
    's.src=\'//s.ksrndkehqnwntyxlhgto.com/172406.js\';document.body.appendChild(s)});</script>'
)

# ── Shared HTML fragments ──────────────────────────────────────────────────────

HEADER = """\
  <header id="hdr"><div class="hdr-in">
    <a class="hdr-logo" href="/"><img class="s sym-cream" src="assets/img/elh-logo-h2-cream.webp" alt="Eternal Life Hospice logo"><img class="s sym-plum" src="assets/img/elh-logo-h2-plum.webp" alt="" aria-hidden="true"><span class="hdr-wordmark">Eternal<small>Life Hospice</small></span></a>
    <nav>
      <div class="nav-group"><a href="/#standard" class="nav-parent">The Eternal Standard</a><div class="nav-sub"><a href="/#standard">Four Pillars : One Standard</a></div></div>
      <div class="nav-group"><a href="/#first48" class="nav-parent">The First 48 Hours</a><div class="nav-sub"><a href="/#faq">Common Questions Answered</a><a href="family-guide">Family eGuide</a></div></div>
      <div class="nav-group"><a href="/#modalities" class="nav-parent">Integrative Therapies</a><div class="nav-sub"><a href="/#clinical-mobile">Clinical &amp; Mobile Services</a></div></div>
      <a href="/#medicare">Insurance &amp; Medicare</a>
      <div class="nav-group"><a href="/#coverage" class="nav-parent">Coverage Area</a><div class="nav-sub"><a href="/#settings">Care Wherever Home Is</a></div></div>
      <div class="nav-group"><a href="/#founder" class="nav-parent">About Eternal</a><div class="nav-sub"><a href="/#founder-welcome">A Founder&rsquo;s Welcome</a><a href="/#amethyst">Our Origin</a><a href="resources">Resources</a><a href="volunteer">Volunteer</a></div></div>
      <div class="nav-group"><a href="/refer" class="nav-parent">For Providers</a><div class="nav-sub"><a href="/refer">Refer With Confidence</a><a href="/?lead=voice#leadcap">Schedule an Educational Session</a></div></div>
    </nav>
    <div class="hdr-cta-wrap"><span class="hdr-cta-note">Here in Moments That Matter Most</span><a href="tel:18059537273" class="hdr-cta">805.953.7273</a></div>
    <button class="search-btn" id="searchBtn" aria-label="Search"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="9" r="7"/><line x1="15" y1="15" x2="19" y2="19"/></svg></button>
    <button class="menu-btn" aria-label="Menu" aria-expanded="false"><svg width="22" height="16" viewBox="0 0 22 16"><line x1="0" y1="2" x2="22" y2="2" stroke="#F5F0EB" stroke-width="2" stroke-linecap="round"/><line x1="0" y1="8" x2="22" y2="8" stroke="#F5F0EB" stroke-width="2" stroke-linecap="round"/><line x1="0" y1="14" x2="22" y2="14" stroke="#F5F0EB" stroke-width="2" stroke-linecap="round"/></svg></button>
  </div></header>"""

CRED_STRIP = """\
<div class="cred-strip"><div class="cred-track">
    <a class="lc cms" href="https://www.medicare.gov/care-compare/?providerType=Hospice" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-cms.webp" alt="CMS Medicare Certified"><div class="ct"><span class="cl">Medicare Certified</span><span class="csub">Centers for Medicare &amp; Medicaid Services</span><span class="ext">medicare.gov &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="lc cdph" href="https://www.cdph.ca.gov/Programs/CHCQ/LCP/CalHealthFind/pages/home.aspx" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-cdph.webp" alt="CDPH Licensed"><div class="ct"><span class="cl">CDPH Licensed</span><span class="csub">California Dept. of Public Health</span><span class="ext">cdph.ca.gov &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="lc achc" href="https://achc.org/search-facilities/" target="_blank" rel="noopener"><img loading="lazy" decoding="async" src="assets/img/cred-achc.webp" alt="ACHC Accredited"><div class="ct"><span class="cl">ACHC Accredited</span><span class="csub">Accreditation Commission for Health Care</span><span class="ext">achc.org &#8599;</span></div></a>
    <div class="csep"></div>
    <a class="ic" href="/#first48"><svg viewBox="0 0 48 48" width="44" height="44" fill="none"><circle cx="24" cy="24" r="15" stroke="#D8CDBF" stroke-width="1.5"/><line x1="24" y1="12" x2="24" y2="24" stroke="#5B2E59" stroke-width="2.5" stroke-linecap="round"/><line x1="24" y1="24" x2="33" y2="24" stroke="#C9B07E" stroke-width="2.5" stroke-linecap="round"/><circle cx="24" cy="24" r="2.5" fill="#5B2E59"/></svg><div class="ct"><span class="cl">Same-Day Admissions</span><span class="csub">24/7 On-Call Nursing</span></div></a>
    <div class="csep"></div>
    <a class="ic" href="/#medicare"><svg viewBox="0 0 48 48" width="44" height="44" fill="none"><path d="M24 9l13 4.5v9.8c0 7.5-5.5 13-13 16-7.5-3-13-8.5-13-16v-9.8L24 9z" stroke="#5B2E59" stroke-width="1.4" fill="none"/><polyline points="18,24 22,28 30,20" stroke="#C9B07E" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><div class="ct"><span class="cl">Little to no out-of-pocket cost</span><span class="csub">For most covered hospice services</span></div></a>
    <div class="csep"></div>
</div></div>"""

FOOTER = """\
<footer id="site-footer">
  <div class="foot-grid">
    <div><div class="foot-logo"><a href="/" aria-label="Eternal Life Hospice &mdash; home"><img loading="lazy" decoding="async" src="assets/img/elh-logo-cream-g.webp" alt="Eternal Life Hospice logo"></a></div><p class="foot-tag">Care That Honors Life.</p><p class="foot-legal">Medicare-Certified &middot; CDPH-Licensed &middot; ACHC-Accredited. Serving families across Ventura and Los Angeles Counties.</p><div class="foot-qr"><img src="assets/img/qr-cream.webp" alt="Scan to visit eternallifehospice.com" width="96" height="96" loading="lazy"><span>Scan to visit<br>on your phone</span></div></div>
    <div class="foot-col"><h4>For Families</h4><a href="family-guide">Family eGuide</a><a href="resources">Resources</a><a href="blog">Journal</a><a href="volunteer">Volunteer</a><a href="careers">Careers</a><a href="/#coverage">Coverage Area</a></div>
    <div class="foot-col"><h4>For Providers</h4><a href="/refer">Refer With Confidence</a><a href="/referral-card">Referral eCard</a><a href="/?lead=voice#leadcap">Schedule an Educational Session</a></div>
    <div class="foot-col"><h4>Resources</h4><a href="/media-kit">Media Kit</a><a href="/care-brief/hospice-is-part-of-life-a-continuation-of-care">Care Brief</a><a href="family-guide">Family eGuide</a></div>
    <div class="foot-col"><h4>Our Care</h4><a href="/#standard">The Eternal Standard</a><a href="/#first48">The First 48 Hours</a><a href="/#modalities">Integrative Therapies</a><a href="/#clinical-mobile">Clinical &amp; Mobile Services</a><a href="/#medicare">Insurance &amp; Medicare</a></div>
    <div class="foot-col"><h4>Contact</h4>
      <a class="fc-line" href="tel:18059537273"><svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg><span>805.953.7273</span></a>
      <span class="fc-line fc-fax"><svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg><span>805.953.8530 fax</span></span>
      <a class="fc-line" href="mailto:info@eternallifehospice.com"><svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><polyline points="22,6 12,13 2,6"/></svg><span>info@eternallifehospice.com</span></a>
      <a class="fc-line fc-addr" href="https://maps.google.com/?cid=9771388271577679785" target="_blank" rel="noopener"><svg class="fci" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><span>4165 E Thousand Oaks Blvd, Suite 325B<br>Westlake Village, CA 91362</span></a>
    </div>
  </div>
  <nav class="foot-social" aria-label="Eternal Life Hospice on social media"><span class="fs-label">Stay Connected</span><a href="https://www.linkedin.com/company/eternal-life-hospice/" target="_blank" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4V9h4v1.57A6 6 0 0 1 16 8z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg></a><a href="https://www.facebook.com/eternallifehospiceinc" target="_blank" rel="noopener" aria-label="Facebook"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a><a href="https://www.instagram.com/eternallifehospice/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a><a href="https://www.youtube.com/@EternalLifeHospice" target="_blank" rel="noopener" aria-label="YouTube"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/></svg></a></nav>
  <div class="foot-disclaimer"><strong style="color:rgba(245,240,235,.5)">Disclaimer:</strong> Eternal Life Hospice Inc. is a licensed and Medicare-certified hospice care provider. The integrative modalities described are complementary care offered for patient comfort and wellbeing; they are not intended to diagnose, treat, cure or prevent any medical condition. Medicare coverage details are subject to change; confirm current eligibility with your care team or call <a href="tel:18006334227" style="color:inherit;text-decoration:none">1.800.MEDICARE</a>.</div>
  <div class="foot-bottom"><span>&copy; 2026 Eternal Life Hospice Inc. All rights reserved. &middot; A <a href="https://conduitint.com" target="_blank" rel="noopener" style="color:inherit;text-decoration:none">Conduit International</a> build</span><span class="foot-bottom-links"><a href="/privacy-policy" style="text-decoration:none">Privacy Policy</a> &nbsp;&middot;&nbsp; <a href="/terms" style="text-decoration:none">Terms &amp; Conditions</a> &nbsp;&middot;&nbsp; <a href="#" onclick="window.elhCookieSettings&amp;&amp;window.elhCookieSettings();return false;" style="color:inherit;text-decoration:none">Cookie Settings</a></span></div>
  <div class="foot-translate">
    <span class="ft-label">Translate this page</span>
    <div class="ft-lang-btns">
      <a class="ft-lang" data-lang="es">\U0001f1f2\U0001f1fd Espa\u00f1ol</a>
      <a class="ft-lang" data-lang="ru">\U0001f1f7\U0001f1fa \u0420\u0443\u0441\u0441\u043a\u0438\u0439</a>
      <a class="ft-lang" data-lang="uk">\U0001f1fa\U0001f1e6 \u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430</a>
      <a class="ft-lang" data-lang="ko">\U0001f1f0\U0001f1f7 \ud55c\uad6d\uc5b4</a>
      <a class="ft-lang" data-lang="hy">🇦🇲 Հայերեն</a>
      <a class="ft-lang" data-lang="tl">\U0001f1f5\U0001f1ed Filipino</a>
      <a class="ft-lang" data-lang="vi">\U0001f1fb\U0001f1f3 Ti\u1ebfng Vi\u1ec7t</a>
      <a class="ft-lang" data-lang="zh-CN">\U0001f1e8\U0001f1f3 \u4e2d\u6587</a>
      <a class="ft-lang" data-lang="ar">\U0001f1f8\U0001f1e6 \u0627\u0644\u0639\u0631\u0628\u064a\u0629</a>
      <a class="ft-lang" data-lang="fa">\U0001f1ee\U0001f1f7 \u0641\u0627\u0631\u0633\u06cc</a>
    </div>
  </div>
</footer>
<script src="assets/header.js?v=20260805" defer></script><script src="/assets/chat.js?v=20260805" defer></script>
<div class="search-overlay" id="searchOverlay" role="dialog" aria-modal="true" aria-label="Site search" aria-hidden="true">
  <div class="search-box"><input type="text" id="searchInput" placeholder="Search pages, cities, resources..." autocomplete="off" aria-label="Search"><button class="search-close" id="searchClose" aria-label="Close search">&times;</button></div>
  <p class="search-hint">Press Enter to open the first result, or Escape to close</p>
  <div class="search-results" id="searchResults"></div>
</div>
<script defer src="/assets/translate.js?v=20260805"></script>"""

# ── Schema builders ────────────────────────────────────────────────────────────

def webpage_schema(c):
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": c["canonicalUrl"] + "#webpage",
        "url": c["canonicalUrl"],
        "name": c["title"],
        "description": c["metaDescription"],
        "isPartOf": {"@id": "https://eternallifehospice.com/#website"},
        "about": {"@id": "https://eternallifehospice.com/#organization"},
        "breadcrumb": {"@id": c["canonicalUrl"] + "#breadcrumb"},
        "inLanguage": "en-US",
        "dateModified": c["lastMaterialUpdate"]
    }

def org_schema(c):
    schema = {
        "@context": "https://schema.org",
        "@type": ["MedicalOrganization", "LocalBusiness"],
        "@id": "https://eternallifehospice.com/#organization",
        "name": "Eternal Life Hospice, Inc.",
        "url": "https://eternallifehospice.com",
        "description": f"Medicare-certified hospice care in {c['city']}, {c['county']} — serving {c['subregion']} and surrounding communities.",
        "telephone": "+18059537273",
        "email": "info@eternallifehospice.com",
        "hasMap": "https://maps.google.com/?cid=9771388271577679785",
        "sameAs": [
            "https://www.facebook.com/eternallifehospiceinc",
            "https://www.instagram.com/eternallifehospice/",
            "https://www.linkedin.com/company/eternal-life-hospice/",
            "https://www.youtube.com/@EternalLifeHospice",
            "https://maps.google.com/?cid=9771388271577679785"
        ],
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "4165 E Thousand Oaks Blvd, Suite 325B",
            "addressLocality": "Westlake Village",
            "addressRegion": "CA",
            "postalCode": "91362",
            "addressCountry": "US"
        },
        "areaServed": [
            {"@type": "City", "name": f"{c['city']}, California"},
            {"@type": "AdministrativeArea", "name": f"{c['county']}, California"}
        ],
        "medicalSpecialty": "https://schema.org/Hospice",
        "image": "https://eternallifehospice.com/assets/og-image.jpg"
    }
    if c.get("latitude") and c.get("longitude"):
        schema["geo"] = {"@type": "GeoCoordinates", "latitude": c["latitude"], "longitude": c["longitude"]}
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

def render_page(c):
    slug        = c["slug"]
    city        = c["city"]
    county      = c["county"]
    subregion   = c["subregion"]
    canonical   = c["canonicalUrl"]
    title       = c["title"]
    meta_desc   = c["metaDescription"]
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
    faqs        = c["faqItems"]
    last_update = c.get("lastMaterialUpdate", "2026-07-22")

    schemas = [
        json.dumps(webpage_schema(c), ensure_ascii=False),
        json.dumps(org_schema(c), ensure_ascii=False),
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
  <meta property="og:image" content="https://eternallifehospice.com/assets/og-image.jpg">
  <meta property="og:site_name" content="Eternal Life Hospice">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/png" href="assets/favicon.png">
  {_hero_preload_tag(slug)}
  <link rel="stylesheet" href="assets/elh.css?v=20260714c">
{schema_tags}
{HEAD_SCRIPTS}
</head><body>
<a class="skip-link" href="#main-content">Skip to main content</a>
{HEADER}
{CRED_STRIP}
<main id="main-content">
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
  <p>{intro}</p>
  {"<p>" + nearby_para + "</p>" if nearby_para else ""}
  {"<p>" + nearby_html + "</p>" if nearby_html else ""}
</section>

<section class="sec wrap">
  <h2>At a glance</h2>
  <div class="prov">
    <div><span>&#10003;</span><span><b>Physician-supported hospice care</b> &mdash; with a nurse on call 24/7</span></div>
    <div><span>&#10003;</span><span><b>Medicare-certified</b> &mdash; Medicare Part A eligible</span></div>
    <div><span>&#10003;</span><span><b>CDPH-licensed</b> &mdash; California Dept. of Public Health</span></div>
    <div><span>&#10003;</span><span><b>ACHC-accredited</b> &mdash; Accreditation Commission for Health Care</span></div>
    <div><span>&#10003;</span><span><b>{county} service area</b> &mdash; serving {city} and {subregion}</span></div>
    <div><span>&#10003;</span><span><b>Same-day evaluation</b> &mdash; may be available when clinically appropriate and operationally available</span></div>
  </div>
</section>

<section class="sec wrap">
  <h2>When to consider hospice</h2>
  <p>Hospice is appropriate when a patient and their physicians agree that comfort is the right priority. Common signs that a conversation with a hospice team may be timely include:</p>
  <ul class="body-list">
    <li>Increased hospitalizations or emergency care visits</li>
    <li>Progressive functional decline despite ongoing treatment</li>
    <li>Growing need for daily personal care assistance</li>
    <li>Uncontrolled pain, breathlessness or other distressing symptoms</li>
    <li>Unexplained weight loss or reduced appetite</li>
    <li>Significant caregiver burden within the household</li>
    <li>A shift in goals toward comfort and quality of remaining time</li>
  </ul>
  <p>Eligibility requires a clinical evaluation and physician certification. Call 805.953.7273 and we will guide you through the process clearly.</p>
</section>

<section class="sec wrap">
  <h2>The First 48 Hours of Hospice Care</h2>
  <p><a href="/resources/first-48-hours">Review the First 48 Hours of Hospice Care</a> for a complete walkthrough of what to expect when care begins.</p>
  <div class="prov">
    <div><span>1</span><span><b>First call and eligibility conversation</b> &mdash; we answer questions and gather what is needed to begin</span></div>
    <div><span>2</span><span><b>Clinical evaluation and admission</b> &mdash; a nurse visits the patient to complete enrollment</span></div>
    <div><span>3</span><span><b>Medication review</b> &mdash; the team transitions to a comfort-focused medication plan</span></div>
    <div><span>4</span><span><b>Equipment and supply coordination</b> &mdash; Medications, equipment and supplies are coordinated and delivered based on the patient&rsquo;s clinical needs</span></div>
    <div><span>5</span><span><b>Family education</b> &mdash; we explain the plan, what to expect and how to reach us at any hour</span></div>
    <div><span>6</span><span><b>Ongoing communication</b> &mdash; scheduled visits begin and a nurse remains on call around the clock</span></div>
  </div>
</section>

<section class="sec wrap">
  <h2>The Eternal Standard</h2>
  <div class="prov">
    <div><span>&#8227;</span><span><b>Clinical Confidence</b> &mdash; Physician support, skilled nursing, symptom management and coordinated care.</span></div>
    <div><span>&#8227;</span><span><b>Guided Presence</b> &mdash; Families understand what is happening, what comes next and who to reach.</span></div>
    <div><span>&#8227;</span><span><b>Whole-Person Comfort</b> &mdash; Medical, emotional, social and spiritual support centered on the patient and family.</span></div>
    <div><span>&#8227;</span><span><b>Compliance-Led Care</b> &mdash; Accurate information, privacy, ethical operations and responsible documentation.</span></div>
  </div>
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
  <h2>Helpful resources for families in {city}</h2>
  <div class="prov">
    <div><span>&#8227;</span><span><a href="family-guide"><b>Family Guide</b></a> &mdash; eligibility, what to expect and questions to ask when choosing a provider</span></div>
    <div><span>&#8227;</span><span><a href="/resources/first-48-hours"><b>The First 48 Hours</b></a> &mdash; what happens when hospice care begins</span></div>
    <div><span>&#8227;</span><span><a href="/resources/medicare-hospice-benefit"><b>Medicare Hospice Benefit</b></a> &mdash; what Medicare covers and how it works</span></div>
    <div><span>&#8227;</span><span><a href="/resources/what-hospice-covers"><b>What Hospice Covers</b></a> &mdash; services, medications, equipment and support</span></div>
    <div><span>&#8227;</span><span><a href="/resources/how-to-choose-a-hospice"><b>How to Choose a Hospice</b></a> &mdash; questions to ask before enrolling</span></div>
  </div>
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
{FOOTER}
</body></html>"""
    return page

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", help="Build only this city slug")
    parser.add_argument("--dry-run", action="store_true", help="Print filenames only, do not write")
    args = parser.parse_args()

    with open(DATA_FILE, encoding="utf-8") as f:
        cities = json.load(f)

    built = []
    skipped = []

    for c in cities:
        if c.get("publishStatus") != "published":
            skipped.append(c["slug"])
            continue
        if args.slug and c["slug"] != args.slug:
            continue

        html = render_page(c)
        out  = os.path.join(OUT_DIR, f"hospice-{c['slug']}-ca.html")

        if args.dry_run:
            print(f"  [DRY] would write {out}")
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            built.append(c["slug"])
            print(f"  ✓ hospice-{c['slug']}-ca.html")

    print(f"\nBuilt: {len(built)} pages")
    print(f"Skipped (draft/future): {len(skipped)} cities")
    if skipped:
        print("  Drafts:", ", ".join(skipped[:20]))

if __name__ == "__main__":
    main()
