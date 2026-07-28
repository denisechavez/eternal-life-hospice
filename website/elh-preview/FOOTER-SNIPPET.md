# Footer Snippet — canonical foot-bottom-links block

Every `.html` page under `elh-preview/` that loads `/assets/analytics.js`
**must** include the `foot-bottom-links` span so visitors can access their
Cookie Settings at any time.

---

## Full site footer (main pages)

Copy the entire `<footer id="site-footer">` block from `index.html` verbatim
into any new full-site page.  The critical line is the `.foot-bottom` div:

```html
<div class="foot-bottom">
  <span>© 2026 Eternal Life Hospice Inc. All rights reserved. · A <a
    href="https://conduitint.com" target="_blank" rel="noopener"
    style="color:inherit;text-decoration:none">Conduit International</a> build</span>
  <span class="foot-bottom-links">
    <a href="/privacy-policy" style="text-decoration:none">Privacy Policy</a>
    &nbsp;·&nbsp;
    <a href="/terms" style="text-decoration:none">Terms &amp; Conditions</a>
    &nbsp;&middot;&nbsp;
    <a href="#" onclick="window.elhCookieSettings&&window.elhCookieSettings();return false;"
       style="color:inherit;text-decoration:none">Cookie Settings</a>
  </span>
</div>
```

The `.foot-bottom` and `.foot-bottom-links` styles live in `assets/elh.css`.

---

## Minimal pages (business cards, standalone viewers)

For pages that use a custom minimal footer (e.g. `card-*.html`,
`family-guide.html`), add at least the Cookie Settings trigger link.

### Option A — styled `.foot-links` div (business card pages)

Add to inline `<style>`:
```css
.foot-links{margin-top:10px;padding-bottom:16px;}
.foot-links a{font-size:9.5px;letter-spacing:.4px;color:#8A7080;text-decoration:none;
              border-bottom:1px solid rgba(138,112,128,.25);}
.foot-links a:hover{color:#5B2E59;}
```

Add inside the `.foot` section, after `.foot-logo`:
```html
<div class="foot-links">
  <a href="#" onclick="window.elhCookieSettings&&window.elhCookieSettings();return false;">
    Cookie Settings
  </a>
</div>
```

### Option B — inline bar (dark-background viewer pages)

Add just before `</body>`:
```html
<div style="text-align:center;padding:10px 1rem 14px;font-size:11px;
            color:rgba(245,240,235,.38);background:#3C1C3B">
  <a href="#"
     onclick="window.elhCookieSettings&&window.elhCookieSettings();return false;"
     style="color:inherit;text-decoration:none;border-bottom:1px solid rgba(245,240,235,.18)">
    Cookie Settings
  </a>
</div>
```

---

## Lint check

Before publishing run:

```bash
bash website/check-cookie-settings.sh
```

Exit 0 = all clear.  Exit 1 = lists the offending files.

### Intentional exclusions

| File | Reason |
|------|--------|
| `aleksandradubina.html` | `noindex,nofollow`; no analytics loaded; pure mobile-redirect card |

To add a new exclusion, edit the `EXCLUDE` array in `check-cookie-settings.sh`.
