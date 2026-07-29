#!/usr/bin/env python3
"""
DeepL static page builder — Eternal Life Hospice
Pre-generates translated HTML for each page × language so visitors land on a
fully-translated native page instead of a Google Translate proxy.

Usage:
  python3 website/tools/deepl-translate.py            # pilot: 20 highest-traffic pages
  python3 website/tools/deepl-translate.py --all      # every hospice-*.html page
  python3 website/tools/deepl-translate.py --dry-run  # estimate chars/cost, no API calls
  python3 website/tools/deepl-translate.py --slug hospice-torrance-ca  # single page

Requires: DEEPL_API_KEY environment variable.
Output:   website/elh-preview/{lang}/hospice-*.html
"""

import os, sys, re, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────

DEEPL_KEY = os.environ.get('DEEPL_API_KEY', '')
if not DEEPL_KEY and '--dry-run' not in sys.argv:
    sys.exit('ERROR: DEEPL_API_KEY not set')

# Free-tier keys end with :fx; paid keys use the non-free endpoint
API_BASE = (
    'https://api-free.deepl.com' if DEEPL_KEY.endswith(':fx')
    else 'https://api.deepl.com'
)
TRANSLATE_URL = f'{API_BASE}/v2/translate'

SITE_ROOT   = Path(__file__).parent.parent / 'elh-preview'
BASE_DOMAIN = 'https://eternallifehospice.com'
TODAY       = date.today().isoformat()

# ── Language table ────────────────────────────────────────────────────────────
# DeepL target code → (output directory under elh-preview/, html lang= attribute)
LANGS = {
    'ES': ('es',    'es'),
    'RU': ('ru',    'ru'),
    'UK': ('uk',    'uk'),
    'KO': ('ko',    'ko'),
    'VI': ('vi',    'vi'),
    'ZH': ('zh-CN', 'zh-CN'),
    'AR': ('ar',    'ar'),
}
# These three are NOT supported by DeepL; translate.js will fall back to Google
GOOGLE_ONLY = ['hy', 'tl', 'fa']

# ── 20 highest-traffic pilot pages (priority 0.8 in sitemap) ─────────────────
PILOT_SLUGS = [
    'hospice-ventura-and-los-angeles-county-ca',
    'hospice-torrance-ca',
    'hospice-long-beach-ca',
    'hospice-arcadia-ca',
    'hospice-van-nuys-ca',
    'hospice-rancho-palos-verdes-ca',
    'hospice-san-marino-ca',
    'hospice-culver-city-ca',
    'hospice-alhambra-ca',
    'hospice-reseda-ca',
    'hospice-ojai-ca',
    'hospice-santa-paula-ca',
    'hospice-fillmore-ca',
    'hospice-port-hueneme-ca',
    'hospice-santa-clarita-ca',
    'hospice-hawthorne-ca',
    'hospice-inglewood-ca',
    'hospice-lancaster-ca',
    'hospice-manhattan-beach-ca',
    'hospice-mission-hills-ca',
]

# ── DeepL API call ────────────────────────────────────────────────────────────

def deepl_translate(html_text: str, target_lang: str) -> str:
    """Send an HTML document to DeepL and return the translated HTML."""
    payload = urllib.parse.urlencode({
        'text':            html_text,
        'target_lang':     target_lang,
        'source_lang':     'EN',
        'tag_handling':    'html',
        'split_sentences': 'nonewlines',
    }).encode()
    req = urllib.request.Request(
        TRANSLATE_URL,
        data=payload,
        headers={
            'Authorization': f'DeepL-Auth-Key {DEEPL_KEY}',
            'Content-Type':  'application/x-www-form-urlencoded',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
            return result['translations'][0]['text']
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        raise RuntimeError(f'DeepL HTTP {e.code}: {body}') from e

# ── HTML post-processing ──────────────────────────────────────────────────────

def build_hreflang_block(slug: str) -> str:
    """Build the full hreflang <link> block for a given slug."""
    english_url = f'{BASE_DOMAIN}/{slug}'
    lines = [f'  <link rel="alternate" hreflang="en" href="{english_url}">']
    for _code, (lang_dir, html_lang) in LANGS.items():
        lines.append(
            f'  <link rel="alternate" hreflang="{html_lang}" '
            f'href="{BASE_DOMAIN}/{lang_dir}/{slug}">'
        )
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{english_url}">')
    return '\n' + '\n'.join(lines)


def postprocess(html: str, slug: str, html_lang: str) -> str:
    """
    Fix the translated HTML:
    1. Set correct <html lang="…"> attribute.
    2. Force canonical to point to the English source.
    3. Inject hreflang alternates after the canonical tag.
    """
    # 1. Fix <html lang>
    html = re.sub(
        r'(<html\b[^>]*)lang="[^"]*"',
        rf'\1lang="{html_lang}"',
        html, count=1, flags=re.IGNORECASE,
    )

    # 2. Force canonical → English source
    english_url = f'{BASE_DOMAIN}/{slug}'
    html = re.sub(
        r'<link\s+rel="canonical"\s+href="[^"]*"[^>]*>',
        f'<link rel="canonical" href="{english_url}">',
        html, count=1, flags=re.IGNORECASE,
    )

    # 3. Inject hreflang block after canonical
    hreflang = build_hreflang_block(slug)
    html = re.sub(
        r'(<link\s+rel="canonical"[^>]*>)',
        rf'\1{hreflang}',
        html, count=1, flags=re.IGNORECASE,
    )

    return html

# ── Per-page translation ──────────────────────────────────────────────────────

def translate_page(slug: str, dry_run: bool = False) -> int:
    """Translate one page into all supported languages. Returns total chars sent."""
    src = SITE_ROOT / f'{slug}.html'
    if not src.exists():
        print(f'  SKIP — source not found: {src}')
        return 0

    html = src.read_text(encoding='utf-8')
    char_count = len(html)

    if dry_run:
        print(f'  {slug}: {char_count:,} chars × {len(LANGS)} langs '
              f'= {char_count * len(LANGS):,} chars')
        return char_count * len(LANGS)

    total = 0
    for deepl_code, (lang_dir, html_lang) in LANGS.items():
        out_dir  = SITE_ROOT / lang_dir
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f'{slug}.html'

        if out_file.exists():
            print(f'  ↩  {lang_dir}/{slug}.html  (already exists, skipping)')
            continue

        print(f'  →  {lang_dir}/{slug}.html … ', end='', flush=True)
        try:
            translated = deepl_translate(html, deepl_code)
            processed  = postprocess(translated, slug, html_lang)
            out_file.write_text(processed, encoding='utf-8')
            print('OK')
            total += char_count
        except Exception as exc:
            print(f'ERROR: {exc}')

        time.sleep(0.35)   # stay polite to the rate limiter

    return total

# ── translate.js STATIC_PAGES patch ──────────────────────────────────────────

def patch_translate_js(translated_slugs: list[str]) -> None:
    """
    Rewrite the STATIC_PAGES array inside translate.js so the language pills
    route to pre-built static pages for slugs that have been translated.
    Slugs not in the list continue to fall back to Google Translate.
    """
    js_path = SITE_ROOT / 'assets' / 'translate.js'
    js = js_path.read_text(encoding='utf-8')

    # Collect all slugs that now have files on disk (union of existing + new)
    all_slugs: set[str] = set()
    for _code, (lang_dir, _) in LANGS.items():
        lang_root = SITE_ROOT / lang_dir
        if lang_root.is_dir():
            all_slugs.update(p.stem for p in lang_root.glob('hospice-*.html'))
    all_slugs.update(translated_slugs)

    if not all_slugs:
        return  # nothing to update

    entries = ',\n    '.join(f"'{s}'" for s in sorted(all_slugs))
    new_array = (
        f'  var STATIC_PAGES = [\n    {entries}\n  ];'
    )

    # Replace the existing STATIC_PAGES declaration (single or multi-line)
    js = re.sub(
        r'var STATIC_PAGES\s*=\s*\[[\s\S]*?\];',
        new_array.lstrip(),
        js, count=1,
    )
    js_path.write_text(js, encoding='utf-8')
    print(f'translate.js updated — {len(all_slugs)} slug(s) in STATIC_PAGES')


# ── Sitemap update ────────────────────────────────────────────────────────────

def update_sitemap(translated_slugs: list[str]) -> None:
    """
    Add hreflang <xhtml:link> alternates to each translated English entry and
    append new <url> entries for every translated page.
    """
    sitemap_path = SITE_ROOT / 'sitemap.xml'
    xml = sitemap_path.read_text(encoding='utf-8')

    # Ensure xhtml namespace is declared
    if 'xmlns:xhtml' not in xml:
        xml = xml.replace(
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '         xmlns:xhtml="http://www.w3.org/1999/xhtml"',
        )

    new_entries = []
    for slug in translated_slugs:
        english_url = f'{BASE_DOMAIN}/{slug}'

        # Inject hreflang into the existing English <url> block if not already there
        # Pattern: <url><loc>https://.../{slug}</loc>...</url>
        eng_pattern = re.compile(
            rf'(<url><loc>{re.escape(english_url)}</loc>)(.*?)(</url>)',
            re.DOTALL,
        )
        if eng_pattern.search(xml) and '<xhtml:link' not in eng_pattern.search(xml).group():
            xhtml_links = [
                f'  <xhtml:link rel="alternate" hreflang="en" href="{english_url}"/>',
            ]
            for _code, (lang_dir, html_lang) in LANGS.items():
                xhtml_links.append(
                    f'  <xhtml:link rel="alternate" hreflang="{html_lang}" '
                    f'href="{BASE_DOMAIN}/{lang_dir}/{slug}"/>'
                )
            xhtml_links.append(
                f'  <xhtml:link rel="alternate" hreflang="x-default" href="{english_url}"/>'
            )
            replacement = r'\1\2' + '\n' + '\n'.join(xhtml_links) + '\n' + r'\3'
            xml = eng_pattern.sub(replacement, xml, count=1)

        # Append <url> entries for each translated page
        for _code, (lang_dir, html_lang) in LANGS.items():
            lang_url = f'{BASE_DOMAIN}/{lang_dir}/{slug}'
            if lang_url in xml:
                continue  # already there
            # Build hreflang xhtml:links for this translated entry
            xl = [f'  <xhtml:link rel="alternate" hreflang="en" href="{english_url}"/>']
            for _c2, (ld2, hl2) in LANGS.items():
                xl.append(
                    f'  <xhtml:link rel="alternate" hreflang="{hl2}" '
                    f'href="{BASE_DOMAIN}/{ld2}/{slug}"/>'
                )
            xl.append(
                f'  <xhtml:link rel="alternate" hreflang="x-default" href="{english_url}"/>'
            )
            new_entries.append(
                f'  <url><loc>{lang_url}</loc>'
                f'<lastmod>{TODAY}</lastmod>'
                f'<priority>0.6</priority>\n'
                + '\n'.join(xl) + '\n  </url>'
            )

    if new_entries:
        xml = xml.replace('</urlset>', '\n'.join(new_entries) + '\n</urlset>')

    sitemap_path.write_text(xml, encoding='utf-8')
    print(f'\nSitemap updated → {sitemap_path}')

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run  = '--dry-run' in sys.argv
    do_all   = '--all'     in sys.argv
    slug_idx = sys.argv.index('--slug') + 1 if '--slug' in sys.argv else None

    if slug_idx and slug_idx < len(sys.argv):
        slugs = [sys.argv[slug_idx]]
    elif do_all:
        slugs = sorted(p.stem for p in SITE_ROOT.glob('hospice-*.html'))
    else:
        slugs = PILOT_SLUGS

    print(f'DeepL static build — {len(slugs)} page(s) × {len(LANGS)} languages')
    if dry_run:
        print('DRY RUN — estimating only, no API calls\n')

    total_chars = 0
    translated  = []
    for slug in slugs:
        print(f'\n{slug}')
        chars = translate_page(slug, dry_run=dry_run)
        total_chars += chars
        if chars > 0 and not dry_run:
            translated.append(slug)

    cost_usd = (total_chars / 1_000_000) * 25
    print(f'\n{"DRY RUN ESTIMATE" if dry_run else "COMPLETE"}: '
          f'{total_chars:,} chars (~${cost_usd:.2f} at $25/1M chars)')

    if translated and not dry_run:
        update_sitemap(translated)
        patch_translate_js(translated)


if __name__ == '__main__':
    main()
