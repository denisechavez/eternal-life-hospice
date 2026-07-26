#!/usr/bin/env python3
"""
Breadcrumb injector for Eternal Life Hospice static site.
Run from repo root: python3 website/elh-preview/assets/inject_breadcrumbs.py
"""
import os, re, glob, html as htmlmod

BASE     = "website/elh-preview"
CANON    = "https://www.eternallifehospice.com"
SVCAREA  = "/hospice-ventura-and-los-angeles-county-ca"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crumb_nav(crumbs):
    """crumbs = [(label, href_or_None), ...]  None = current page (no link)"""
    lis = []
    for label, href in crumbs:
        if href:
            lis.append(f'<li><a href="{href}">{label}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{label}</li>')
    return (
        '<nav class="breadcrumb" aria-label="Breadcrumb">'
        '<ol>' + ''.join(lis) + '</ol>'
        '</nav>'
    )

def jsonld_script(crumbs, page_path):
    """Build BreadcrumbList JSON-LD. page_path is the canonical path."""
    items = []
    for i, (label, href) in enumerate(crumbs, 1):
        url = CANON + (href if href else page_path)
        safe_label = label.replace('"', '&quot;').replace('\\', '\\\\')
        items.append(
            f'{{"@type":"ListItem","position":{i},"name":"{safe_label}","item":"{url}"}}'
        )
    return (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"BreadcrumbList",'
        '"itemListElement":[' + ','.join(items) + ']}'
        '</script>'
    )

def has_breadcrumb(html):
    return 'class="breadcrumb"' in html

def has_breadcrumb_jsonld(html):
    return '"BreadcrumbList"' in html

def city_label(slug):
    """hospice-thousand-oaks-ca  →  Thousand Oaks"""
    name = re.sub(r'^hospice-', '', slug)
    name = re.sub(r'-ca$', '', name)
    return ' '.join(w.capitalize() for w in name.split('-'))

def h1_text(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if not m: return 'Article'
    raw = m.group(1)
    raw = re.sub(r'<[^>]+>', '', raw)            # strip tags
    raw = raw.replace('&mdash;', '\u2014')
    raw = raw.replace('&ndash;', '\u2013')
    raw = raw.replace('&nbsp;', ' ')
    raw = raw.replace('&amp;', '&')
    raw = raw.replace('&rsquo;', '\u2019')
    return raw.strip()

processed = []
skipped   = []

def save(fpath, html):
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(html)
    processed.append(fpath)

# ---------------------------------------------------------------------------
# 1. City pages (inject nav AFTER hero </section>, BEFORE first .sec.wrap)
# ---------------------------------------------------------------------------
city_files = sorted(glob.glob(f"{BASE}/hospice-*-ca.html"))

for fpath in city_files:
    slug = os.path.basename(fpath).replace('.html', '')
    html = open(fpath, encoding='utf-8').read()

    if has_breadcrumb(html):
        skipped.append(fpath); continue

    if slug == 'hospice-ventura-and-los-angeles-county-ca':
        crumbs    = [("Home", "/"), ("Service Areas", None)]
        page_path = SVCAREA
    else:
        city = city_label(slug)
        crumbs    = [("Home", "/"), ("Service Areas", SVCAREA), (city, None)]
        page_path = f"/{slug}"

    nav = crumb_nav(crumbs)
    ld  = jsonld_script(crumbs, page_path)

    # Inject nav: right after the hero closing </section>, before next <section
    # Pattern: </section>\n\n<section  (city pages have blank line between sections)
    html_new = re.sub(
        r'(</section>)(\s*\n\s*<section)',
        r'\1\n' + nav + r'\2',
        html,
        count=1
    )

    if html_new == html:
        # Fallback: inject right after </header> if no hero-section gap found
        html_new = re.sub(r'(</header>)', r'\1\n' + nav, html, count=1)

    # Inject JSON-LD before </head>
    if not has_breadcrumb_jsonld(html_new):
        html_new = html_new.replace('</head>', ld + '\n</head>', 1)

    save(fpath, html_new)

# ---------------------------------------------------------------------------
# 2. Care-brief articles (JSON-LD already present; add visible nav only)
# ---------------------------------------------------------------------------
cb_articles = sorted(glob.glob(f"{BASE}/care-brief/*.html"))

for fpath in cb_articles:
    fname = os.path.basename(fpath)
    if fname == 'index.html':
        skipped.append(fpath); continue

    html = open(fpath, encoding='utf-8').read()

    if has_breadcrumb(html):
        skipped.append(fpath); continue

    title  = h1_text(html)
    slug   = fname.replace('.html', '')
    crumbs = [("Home", "/"), ("Care Brief", "/care-brief"), (title, None)]
    page_path = f"/care-brief/{slug}"
    nav    = crumb_nav(crumbs)

    # Care-brief articles have no standard <header>; inject before <section class="cb-hero">
    html_new = html.replace('<section class="cb-hero">', nav + '\n<section class="cb-hero">', 1)

    if html_new == html:
        # Fallback: after </header>
        html_new = re.sub(r'(</header>)', r'\1\n' + nav, html, count=1)

    # Add JSON-LD only if missing
    if not has_breadcrumb_jsonld(html_new):
        ld = jsonld_script(crumbs, page_path)
        html_new = html_new.replace('</head>', ld + '\n</head>', 1)

    save(fpath, html_new)

# ---------------------------------------------------------------------------
# 3. Individual non-city pages that need nav + JSON-LD
# ---------------------------------------------------------------------------
individual = {
    f"{BASE}/referral-card.html": {
        "crumbs":    [("Home", "/"), ("Providers", "/refer"), ("Referral eCard", None)],
        "page_path": "/referral-card",
        "after":     "</header>",
    },
    f"{BASE}/media-kit.html": {
        "crumbs":    [("Home", "/"), ("Media Kit", None)],
        "page_path": "/media-kit",
        "after":     "</header>",
    },
}

for fpath, conf in individual.items():
    if not os.path.exists(fpath):
        print(f"MISSING: {fpath}")
        continue

    html = open(fpath, encoding='utf-8').read()

    if has_breadcrumb(html):
        skipped.append(fpath); continue

    nav = crumb_nav(conf["crumbs"])
    ld  = jsonld_script(conf["crumbs"], conf["page_path"])

    anchor = conf["after"]
    html_new = html.replace(anchor, anchor + '\n' + nav, 1)

    if not has_breadcrumb_jsonld(html_new):
        html_new = html_new.replace('</head>', ld + '\n</head>', 1)

    save(fpath, html_new)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print(f"\nProcessed ({len(processed)}):")
for f in processed:
    print(f"  + {os.path.relpath(f, BASE)}")

print(f"\nSkipped — already had breadcrumb ({len(skipped)}):")
for f in skipped:
    print(f"  ~ {os.path.relpath(f, BASE)}")
