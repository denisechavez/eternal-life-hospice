#!/usr/bin/env python3
"""Inject missing foot-translate bar into city pages that lost it during rebase."""
import glob, re

FOOT_TRANSLATE = (
    '  <div class="foot-translate">\n'
    '    <span class="ft-label">Translate this page</span>\n'
    '    <div class="ft-lang-btns">\n'
    '      <a class="ft-lang" data-lang="es">\U0001f1f2\U0001f1fd Espa\u00f1ol</a>\n'
    '      <a class="ft-lang" data-lang="ru">\U0001f1f7\U0001f1fa \u0420\u0443\u0441\u0441\u043a\u0438\u0439</a>\n'
    '      <a class="ft-lang" data-lang="uk">\U0001f1fa\U0001f1e6 \u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430</a>\n'
    '      <a class="ft-lang" data-lang="ko">\U0001f1f0\U0001f1f7 \ud55c\uad6d\uc5b4</a>\n'
    '      <a class="ft-lang" data-lang="hy">\U0001f1e6\U0001f1f2 \u0540\u0561\u0575\u0565\u0580\u0565\u576</a>\n'
    '      <a class="ft-lang" data-lang="tl">\U0001f1f5\U0001f1ed Filipino</a>\n'
    '      <a class="ft-lang" data-lang="vi">\U0001f1fb\U0001f1f3 Ti\u1ebfng Vi\u1ec7t</a>\n'
    '      <a class="ft-lang" data-lang="zh-CN">\U0001f1e8\U0001f1f3 \u4e2d\u6587</a>\n'
    '      <a class="ft-lang" data-lang="ar">\U0001f1f8\U0001f1e6 \u0627\u0644\u0639\u0631\u0628\u064a\u0629</a>\n'
    '      <a class="ft-lang" data-lang="fa">\U0001f1ee\U0001f1f7 \u0641\u0627\u0631\u0633\u06cc</a>\n'
    '    </div>\n'
    '  </div>\n'
)

# Matches the translate.js script tag immediately before </body></html>
SCRIPT_PAT = re.compile(
    r'(<script[^>]+translate\.js[^>]*></script>\n?</body></html>)',
    re.IGNORECASE
)

fixed = skipped = 0
for fpath in sorted(glob.glob('website/elh-preview/hospice-*.html')):
    html = open(fpath, encoding='utf-8').read()
    if 'ft-lang' in html:
        skipped += 1
        continue
    m = SCRIPT_PAT.search(html)
    if not m:
        print(f'  WARN (no translate script tag): {fpath}')
        skipped += 1
        continue
    new_html = html[:m.start()] + FOOT_TRANSLATE + m.group(1)
    open(fpath, 'w', encoding='utf-8').write(new_html)
    fixed += 1

print(f'Fixed: {fixed}  Skipped: {skipped}')
