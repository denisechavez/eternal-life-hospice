#!/usr/bin/env python3
"""
DeepL static page builder for ELH.
Generates /es/ /ru/ /uk/ /ko/ /zh/ subdirectories under website/elh-preview/.

Usage:
  python3 website/tools/deepl_translate.py --pilot        # 5 priority pages × all 5 langs
  python3 website/tools/deepl_translate.py                # all 163 pages × all 5 langs
  python3 website/tools/deepl_translate.py --lang es      # all pages, Spanish only
  python3 website/tools/deepl_translate.py --pilot --lang es
"""

import os, re, sys, json, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
DEEPL_KEY = os.environ.get('DEEPL_API_KEY', '')
SITE_DIR  = Path('website/elh-preview')
SITE_URL  = 'https://eternallifehospice.com'

# DeepL-supported subset of the 10 footer languages
LANGS = {
    'es': {'deepl': 'ES', 'html_lang': 'es'},
    'ru': {'deepl': 'RU', 'html_lang': 'ru'},
    'uk': {'deepl': 'UK', 'html_lang': 'uk'},
    'ko': {'deepl': 'KO', 'html_lang': 'ko'},
    'zh': {'deepl': 'ZH', 'html_lang': 'zh-Hans'},
}

# Langs NOT supported by DeepL (kept as Google Translate redirect)
GOOGLE_ONLY = {'hy', 'tl', 'vi', 'ar', 'fa'}

# data-lang values that map to our static subdirs
# zh-CN in the footer pill → zh subdir
FOOTERPILL_TO_DIR = {'es':'es','ru':'ru','uk':'uk','ko':'ko','zh-CN':'zh'}

PILOT_PAGES = [
    'index.html',
    'hospice-thousand-oaks-ca.html',
    'hospice-ventura-ca.html',
    'hospice-oxnard-ca.html',
    'hospice-westlake-village-ca.html',
]

RATE_DELAY = 0.5   # seconds between API calls (paid tier is lenient)


# ── DeepL API ────────────────────────────────────────────────────────────────
def _deepl_call(texts, target_lang, tag_handling=None):
    """Single POST to DeepL. Returns list of translated strings."""
    params = [('source_lang', 'EN'), ('target_lang', target_lang),
              ('split_sentences', 'nonewlines')]
    for t in texts:
        params.append(('text', t))
    if tag_handling:
        params.append(('tag_handling', tag_handling))
        params.append(('ignore_tags', 'script,style,code,pre,noscript'))

    body = urllib.parse.urlencode(params).encode()

    for endpoint in ['https://api.deepl.com/v2/translate',
                     'https://api-free.deepl.com/v2/translate']:
        try:
            req = urllib.request.Request(
                endpoint, data=body,
                headers={
                    'Authorization': f'DeepL-Auth-Key {DEEPL_KEY}',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'ELH-Translator/1.0',
                })
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read())
                return [t['text'] for t in result['translations']]
        except urllib.error.HTTPError as e:
            if e.code == 456:
                print('ERROR: DeepL quota exceeded', file=sys.stderr); sys.exit(1)
            if e.code in (401, 403) and 'free' not in endpoint:
                continue   # try free endpoint
            body_text = e.read().decode()
            print(f'  DeepL HTTP {e.code} from {endpoint}: {body_text[:200]}', file=sys.stderr)
            if 'free' in endpoint:
                raise
        except Exception as ex:
            print(f'  DeepL error ({endpoint}): {ex}', file=sys.stderr)
            if 'free' in endpoint:
                raise
    raise RuntimeError('Both DeepL endpoints failed')


# ── HTML helpers ─────────────────────────────────────────────────────────────
def _attr(html, attr, new_val):
    """Replace first occurrence of attr="..." with attr="new_val"."""
    return re.sub(
        rf'({re.escape(attr)}=")[^"]*(")',
        lambda m: m.group(1) + new_val + m.group(2),
        html, count=1)


def _build_translate_bar_script(current_lang_dir, slug):
    """
    Replace the Google-Translate-only JS with one that links to:
    - Static paths for DeepL-supported langs
    - Google Translate (English source) for unsupported langs
    The current language pill gets a bold/underline active marker.
    """
    orig_path = f'{SITE_URL}/{slug}' if slug not in ('index', '') else SITE_URL

    static_map = {}
    for pill_lang, dir_name in FOOTERPILL_TO_DIR.items():
        page_slug = slug if slug not in ('index', '') else ''
        static_map[pill_lang] = (f'{SITE_URL}/{dir_name}/{page_slug}'
                                 if page_slug else f'{SITE_URL}/{dir_name}/')

    # Map current_lang_dir → pill lang value
    dir_to_pill = {v: k for k, v in FOOTERPILL_TO_DIR.items()}
    active_pill = dir_to_pill.get(current_lang_dir, '')

    static_json = json.dumps(static_map)
    return f"""<script>
    (function(){{
      var origUrl = '{orig_path}';
      var staticPaths = {static_json};
      var activePill = '{active_pill}';
      document.querySelectorAll('.ft-lang').forEach(function(a){{
        var lang = a.getAttribute('data-lang');
        if (staticPaths[lang]) {{
          a.href = staticPaths[lang];
          if (lang === activePill) {{ a.style.fontWeight='700'; a.style.outline='1px solid currentColor'; }}
        }} else {{
          a.href = 'https://translate.google.com/translate?sl=en&tl=' + lang + '&u=' + encodeURIComponent(origUrl);
        }}
      }});
    }})();
  </script>"""


# ── Core translator ───────────────────────────────────────────────────────────
def translate_page(html_path: Path, lang_code: str) -> str:
    lang_info  = LANGS[lang_code]
    deepl_code = lang_info['deepl']
    html_lang  = lang_info['html_lang']

    html = html_path.read_text(encoding='utf-8')
    slug = html_path.stem   # filename without .html

    orig_url  = f'{SITE_URL}/{slug}' if slug != 'index' else SITE_URL
    trans_url = (f'{SITE_URL}/{lang_code}/{slug}'
                 if slug != 'index' else f'{SITE_URL}/{lang_code}/')

    # ── 1. Extract plain-text head strings ──
    title_m   = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    desc_m    = re.search(r'<meta name="description" content="([^"]*)"', html)
    og_t_m    = re.search(r'<meta property="og:title" content="([^"]*)"', html)
    og_d_m    = re.search(r'<meta property="og:description" content="([^"]*)"', html)

    originals  = [
        title_m.group(1)  if title_m  else '',
        desc_m.group(1)   if desc_m   else '',
        og_t_m.group(1)   if og_t_m   else '',
        og_d_m.group(1)   if og_d_m   else '',
    ]
    non_empty  = [(i, t) for i, t in enumerate(originals) if t.strip()]

    if non_empty:
        tr_plain = _deepl_call([t for _, t in non_empty], deepl_code)
        for (i, _), val in zip(non_empty, tr_plain):
            originals[i] = val
    title_tr, desc_tr, og_title_tr, og_desc_tr = originals
    time.sleep(RATE_DELAY)

    # ── 2. Translate body HTML ──
    body_m = re.search(r'(<body[^>]*>)(.*?)(</body>)', html, re.DOTALL)
    if not body_m:
        print(f'  WARN: no <body> found in {html_path.name}', file=sys.stderr)
        return html

    body_open, body_content, body_close = body_m.groups()
    [body_tr] = _deepl_call([body_content], deepl_code, tag_handling='html')
    time.sleep(RATE_DELAY)

    # ── 3. Reassemble ──
    out = html

    # html lang
    out = re.sub(r'<html lang="[^"]*"', f'<html lang="{html_lang}"', out, count=1)

    # <base href> — so all relative asset/link paths resolve from site root
    out = out.replace('<head>', f'<head>\n  <base href="{SITE_URL}/">', 1)

    # head meta
    if title_tr:
        out = re.sub(r'<title>.*?</title>', f'<title>{title_tr}</title>',
                     out, flags=re.DOTALL, count=1)
    if desc_tr:
        out = _attr(out, 'name="description" content', desc_tr)
    if og_title_tr:
        out = _attr(out, 'property="og:title" content', og_title_tr)
    if og_desc_tr:
        out = _attr(out, 'property="og:description" content', og_desc_tr)

    # canonical → translated URL
    out = _attr(out, 'rel="canonical" href', trans_url)

    # og:url → translated URL
    out = re.sub(
        r'(<meta property="og:url" content=")[^"]*(")',
        lambda m: m.group(1) + trans_url + m.group(2),
        out, count=1)

    # replace body
    out = out.replace(body_open + body_content + body_close,
                      body_open + body_tr + body_close, 1)

    # ── 4. Update translate bar JS ──
    bar_script_pattern = (
        r'<script>\s*\(function\(\)\{[^<]{0,80}document\.querySelectorAll'
        r'\(\'\.ft-lang\'\)[^<]*\}\)\(\);\s*</script>'
    )
    new_bar = _build_translate_bar_script(lang_code, slug)
    out_replaced = re.sub(bar_script_pattern, new_bar, out, flags=re.DOTALL)
    if out_replaced == out:
        # Pattern didn't match — append bar script before </footer>
        out_replaced = out.replace('</footer>', new_bar + '\n</footer>', 1)
    out = out_replaced

    return out


# ── Runner ───────────────────────────────────────────────────────────────────
def run(pilot=False, lang_filter=None):
    if not DEEPL_KEY:
        print('ERROR: DEEPL_API_KEY env var not set', file=sys.stderr)
        sys.exit(1)

    langs = {k: v for k, v in LANGS.items()
             if lang_filter is None or k == lang_filter}

    all_pages = sorted(SITE_DIR.glob('*.html'))
    pages = ([SITE_DIR / p for p in PILOT_PAGES] if pilot
             else [p for p in all_pages
                   if p.name not in ('404.html',)])  # skip 404

    total  = len(pages) * len(langs)
    done   = 0
    errors = []

    print(f'Building {len(pages)} pages × {len(langs)} languages = {total} files')
    print(f'Langs: {", ".join(langs.keys())}')
    if pilot:
        print(f'Pages: {[p.name for p in pages]}')
    print()

    for lang_code in langs:
        out_dir = SITE_DIR / lang_code
        out_dir.mkdir(exist_ok=True)
        print(f'── {lang_code.upper()} ──────────────────────')

        for page in pages:
            out_path = out_dir / page.name
            print(f'  {page.name} → {lang_code}/{page.name}', end=' ', flush=True)
            try:
                translated = translate_page(page, lang_code)
                out_path.write_text(translated, encoding='utf-8')
                done += 1
                print('✓')
            except Exception as ex:
                errors.append((lang_code, page.name, str(ex)))
                print(f'✗ {ex}')

        print()

    print(f'Done: {done}/{total} files')
    if errors:
        print(f'Errors ({len(errors)}):')
        for lc, pg, err in errors:
            print(f'  {lc}/{pg}: {err}')
    return len(errors) == 0


if __name__ == '__main__':
    pilot      = '--pilot' in sys.argv
    lang_arg   = None
    if '--lang' in sys.argv:
        idx      = sys.argv.index('--lang')
        lang_arg = sys.argv[idx + 1].lower()
        if lang_arg not in LANGS:
            print(f'Unknown lang {lang_arg!r}. Choose from: {", ".join(LANGS)}',
                  file=sys.stderr)
            sys.exit(1)

    ok = run(pilot=pilot, lang_filter=lang_arg)
    sys.exit(0 if ok else 1)
