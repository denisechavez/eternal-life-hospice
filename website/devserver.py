#!/usr/bin/env python3
"""Local preview server for the static site.

Mimics Netlify's "pretty URLs": /care-brief resolves to care-brief.html,
so internal links behave the same in the Replit preview as on the live site.
Not published (lives outside elh-preview/).
"""
import http.server
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Dev switcher bar ──────────────────────────────────────────────────────────
# Injected before </body> on every HTML page served locally.
# Never touches the published files — it lives only in the dev server response.
_DEV_BAR = """
<style id="_elh-dev-bar-css">
#_elh-dev-bar{
  position:fixed;bottom:0;left:0;right:0;z-index:2147483647;
  background:#3E1F3E;display:flex;align-items:center;gap:6px;flex-wrap:nowrap;
  padding:0 14px;height:42px;
  font:500 12px/1 'Segoe UI',Arial,sans-serif;
  box-shadow:0 -2px 10px rgba(0,0,0,.35);
  white-space:nowrap;overflow-x:auto;
}
#_elh-dev-bar ._dbb{color:#C9B07E;font-weight:700;letter-spacing:.05em;margin-right:6px;flex-shrink:0}
#_elh-dev-bar a,#_elh-dev-bar button{
  color:rgba(245,240,235,.82);background:transparent;
  border:1px solid rgba(245,240,235,.22);border-radius:20px;
  padding:5px 13px;font:inherit;text-decoration:none;cursor:pointer;
  flex-shrink:0;transition:border-color .15s,color .15s,background .15s;
}
#_elh-dev-bar a:hover,#_elh-dev-bar button:hover{color:#fff;border-color:#C9B07E}
#_elh-dev-bar a._on,#_elh-dev-bar button._on{background:#C9B07E;border-color:#C9B07E;color:#2A0F28;font-weight:700}
#_elh-dev-bar select{
  color:rgba(245,240,235,.82);background:#4A2A4A;
  border:1px solid rgba(245,240,235,.22);border-radius:20px;
  padding:5px 10px;font:inherit;cursor:pointer;outline:none;flex-shrink:0;
}
#_elh-dev-bar select:hover{border-color:#C9B07E}
body{padding-bottom:42px!important}
</style>
<div id="_elh-dev-bar">
  <span class="_dbb">ELH ▸</span>
  <a href="/" id="_dba-site">Website</a>
  <a href="/tracker/" id="_dba-tracker">Marketing Outreach</a>
  <select aria-label="Publications" onchange="if(this.value){location=this.value;this.selectedIndex=0}">
    <option value="">Publications ▾</option>
    <optgroup label="Care Brief">
      <option value="/care-brief/hospice-is-part-of-life-a-continuation-of-care">Care Brief — Issue One</option>
      <option value="/care-brief">Care Brief Library</option>
    </optgroup>
    <optgroup label="Guides &amp; Kit">
      <option value="/family-guide">Family Guide</option>
      <option value="/media-kit">Media Kit</option>
    </optgroup>
    <optgroup label="Blog — Eternal Journal">
      <option value="/blog">Journal Index</option>
      <option value="/blog/caring-for-the-caregiver">Caring for the Caregiver</option>
      <option value="/blog/the-caregiver-who-needs-care">Rest, Renewal and the Work of Caring</option>
      <option value="/blog/five-hospice-myths-that-cause-families-to-wait">Five Hospice Myths That Delay Care</option>
      <option value="/blog/talking-with-children-when-a-loved-one-is-seriously-ill">Talking with Children About Illness</option>
      <option value="/blog/music-at-the-bedside">Music at the Bedside</option>
      <option value="/blog/sound-baths-ancient-comfort-for-body-and-spirit">Sound Baths: Ancient Comfort</option>
      <option value="/blog/the-quiet-work-of-hospice-volunteers">The Quiet Work of Hospice Volunteers</option>
    </optgroup>
  </select>
  <select aria-label="Events" onchange="if(this.value){location=this.value;this.selectedIndex=0}">
    <option value="">Events ▾</option>
    <option value="/events">Events Index</option>
    <optgroup label="Upcoming">
      <option value="/events/caregiver-support-workshop">Caregiver Support Workshop — Sep 18</option>
      <option value="/events/community-grief-circle">Community Grief Circle — Oct 8</option>
    </optgroup>
  </select>
  <select aria-label="Emails" onchange="if(this.value){location=this.value;this.selectedIndex=0}">
    <option value="">Emails ▾</option>
    <option value="/canvas-hub/emails/eternal-care-brief-introduction-email.html">Intro Email (Campaign 1)</option>
    <option value="/canvas-hub/emails/eternal-care-brief-new-issue-template.html">New-Issue Template</option>
    <option value="/canvas-hub/emails/eternal-life-email-signature-aleksandra-dubina.html">Sig — Aleksandra</option>
    <option value="/canvas-hub/emails/eternal-life-email-signature-TEMPLATE.html">Sig — Template</option>
  </select>
  <script>
  (function(){
    var p=location.pathname;
    var onTracker=p==='/tracker'||p.startsWith('/tracker/');
    if(onTracker)
      document.getElementById('_dba-tracker').className='_on';
    else
      document.getElementById('_dba-site').className='_on';
    // Lift any existing fixed bottom bar (e.g. tracker Save/Clear bar) so it
    // sits above the dev switcher and isn't hidden behind it.
    function liftFixedBars(){
      var barH=document.getElementById('_elh-dev-bar');
      if(!barH)return;
      var h=barH.offsetHeight||42;
      // Explicitly lift the tracker Save/Clear bar by ID — display:none at load
      // time means getComputedStyle returns 'auto' for bottom on some browsers,
      // so the generic loop below misses it. Set it unconditionally here.
      var trackerBar=document.getElementById('bar');
      if(trackerBar){trackerBar.style.bottom=h+'px';}
      // Generic lift for any other fixed-bottom element on this page
      document.querySelectorAll('*').forEach(function(el){
        if(el.id==='_elh-dev-bar'||el.id==='bar')return;
        var s=getComputedStyle(el);
        if(s.position==='fixed'&&(s.bottom==='0px'||s.bottom==='0')){
          el.style.bottom=h+'px';
        }
      });
      // Also nudge any toast that references bottom:96px
      var toast=document.getElementById('toast');
      if(toast){toast.style.bottom=(96+h)+'px';}
    }
    if(document.readyState==='loading'){
      document.addEventListener('DOMContentLoaded',liftFixedBars);
    } else {
      liftFixedBars();
    }
    // Re-run whenever a hidden class is removed (e.g. tracker Save bar appearing)
    var _mo=new MutationObserver(function(muts){
      var needsLift=muts.some(function(m){
        return m.type==='attributes'&&m.attributeName==='class';
      });
      if(needsLift)liftFixedBars();
    });
    _mo.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
  })();
  </script>
</div>
"""

def _inject_dev_bar(html: bytes) -> bytes:
    """Insert the dev switcher bar before </body>. Falls back to appending."""
    tag = b"</body>"
    bar = _DEV_BAR.encode()
    idx = html.lower().rfind(tag)
    if idx != -1:
        return html[:idx] + bar + html[idx:]
    return html + bar
ROOT = os.path.join(BASE, "elh-preview")
# Internal-only routes for the workspace canvas hub (never published to the site):
CANVAS_HUB = os.path.join(BASE, "canvas-hub")
EMAILS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "email"))
NEWSLETTER_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "newsletter"))
REPORTS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "campaign-reports"))


class PrettyURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ------------------------------------------------------------------
    # Tracker proxy — forwards /tracker and /tracker/* to the Outreach
    # Tracker app running on port 3000 so the preview pane can reach it
    # without switching ports.
    # ------------------------------------------------------------------
    def _proxy_tracker(self):
        import urllib.request, urllib.error, re
        raw = self.path  # e.g. /tracker/  /tracker/contacts  /api/auth/check
        # /tracker/* → strip the /tracker prefix; /api/* → forward as-is
        if raw.startswith("/tracker"):
            sub = raw[len("/tracker"):]
            if not sub or sub[0] not in ("/", "?", "#"):
                sub = "/" + sub
            if not sub:
                sub = "/"
        else:
            sub = raw  # already a root-relative path like /api/auth/check
        target = "http://127.0.0.1:3000" + sub
        try:
            # Read request body for POST/PUT/PATCH
            body_data = None
            if self.command in ("POST", "PUT", "PATCH"):
                length = int(self.headers.get("Content-Length") or 0)
                body_data = self.rfile.read(length) if length else b""
            req = urllib.request.Request(target, data=body_data,
                                         method=self.command)
            for h in ("Accept", "Accept-Encoding", "Accept-Language",
                      "Cookie", "Content-Type", "X-Requested-With",
                      "X-Forwarded-Proto"):
                if self.headers.get(h):
                    req.add_header(h, self.headers[h])
            # HTTPError is a subclass of URLError but carries a valid HTTP
            # response (4xx / 5xx from Express).  Catch it first so login
            # failures, rate-limit 429s, and validation 400s reach the client
            # intact; reserve the URLError handler for genuine connection faults.
            try:
                resp_obj = urllib.request.urlopen(req, timeout=5)
                status = resp_obj.status
                resp_headers = resp_obj.headers
                body = resp_obj.read()
                resp_obj.close()
            except urllib.error.HTTPError as http_err:
                status = http_err.code
                resp_headers = http_err.headers
                body = http_err.read()
                http_err.close()
            ct = resp_headers.get("Content-Type", "")
            # Rewrite root-relative asset paths in HTML so the browser
            # fetches them under /tracker/* (which this proxy handles)
            if "text/html" in ct:
                text = body.decode("utf-8", errors="replace")
                # href="/  src="/  action="/  → prefixed with /tracker
                def _rewrite(m):
                    attr, path = m.group(1), m.group(2)
                    # leave absolute URLs and anchors unchanged
                    if path.startswith(("http", "//", "#", "mailto")):
                        return m.group(0)
                    return f'{attr}="/tracker{path}"'
                text = re.sub(
                    r'(href|src|action)="(/[^"]*)"', _rewrite, text
                )
                body = _inject_dev_bar(text.encode("utf-8"))
                ct = "text/html; charset=utf-8"
            self.send_response(status)
            self.send_header("Content-Type", ct)
            for key, val in resp_headers.items():
                if key.lower() in ("set-cookie", "cache-control"):
                    self.send_header(key, val)
                elif key.lower() == "location":
                    # rewrite redirect targets too
                    loc = val
                    if loc.startswith("/") and not loc.startswith("/tracker"):
                        loc = "/tracker" + loc
                    self.send_header("Location", loc)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.URLError:
            # Only fires for genuine connection failures (refused, timeout) —
            # HTTPError is caught above and forwarded normally.
            body = (
                b"<html><body style='font-family:sans-serif;padding:2rem'>"
                b"<h2>Outreach Tracker not running</h2>"
                b"<p>Start the <b>Outreach Tracker</b> workflow, then reload.</p>"
                b"</body></html>"
            )
            self.send_response(503)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _is_tracker_path(self):
        """True if this request should be forwarded to the tracker on port 3000."""
        p = self.path
        # /tracker/  and  /tracker?  (bare /tracker redirects first)
        if p.startswith("/tracker/") or p.startswith("/tracker?"):
            return True
        # /api/* — tracker JS calls these with a root-relative path; the static
        # dev server has no API routes so forwarding is always correct here.
        if p.startswith("/api/"):
            return True
        return False

    def _serve_site_html(self, fspath):
        """Read a local HTML file, inject the dev bar, and send the response."""
        try:
            with open(fspath, "rb") as f:
                raw = f.read()
        except OSError:
            self.send_error(404, "File not found")
            return
        body = _inject_dev_bar(raw)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/tracker":
            # Redirect bare /tracker → /tracker/ so relative asset paths
            # (styles.css, app.js) resolve as /tracker/styles.css etc.
            self.send_response(301)
            self.send_header("Location", "/tracker/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self._is_tracker_path():
            self._proxy_tracker()
            return
        # For HTML files served from the static site, inject the dev bar.
        # translate_path returns a directory for paths like / — resolve index.
        fspath = self.translate_path(self.path)
        if os.path.isdir(fspath):
            for idx in ("index.html", "index.htm"):
                candidate = os.path.join(fspath, idx)
                if os.path.isfile(candidate):
                    fspath = candidate
                    break
        if os.path.isfile(fspath) and fspath.endswith(".html"):
            self._serve_site_html(fspath)
            return
        super().do_GET()

    def do_HEAD(self):
        # HEAD must not write a response body; proxy only the redirect,
        # then fall through to the base class for all other paths.
        if self.path == "/tracker":
            self.send_response(301)
            self.send_header("Location", "/tracker/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        if self._is_tracker_path():
            self._proxy_tracker()
            return
        # Netlify handles form POSTs on the live site; in this preview we
        # accept them so the on-page "thank you" flow works (nothing is stored).
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        body = (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>Preview only</title></head>"
            "<body style=\"font-family:Georgia,serif;background:#F5F0EB;color:#3C1C3B;"
            "display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0\">"
            "<div style=\"max-width:460px;text-align:center;padding:2rem\">"
            "<h1 style=\"font-weight:400\">Preview mode</h1>"
            "<p>This is the workspace preview &mdash; form submissions are only "
            "recorded on the live site (eternallifehospice.com).</p>"
            "<p><a href=\"/care-brief#signup\" style=\"color:#5B2E59\">&larr; Back</a></p>"
            "</div></body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self._is_tracker_path():
            self._proxy_tracker()

    def do_PATCH(self):
        if self._is_tracker_path():
            self._proxy_tracker()

    def do_DELETE(self):
        if self._is_tracker_path():
            self._proxy_tracker()

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/canvas-hub/"):
            rel = os.path.normpath(clean[len("/canvas-hub/"):]).lstrip("/")
            if rel.startswith("emails/"):
                base, rel = EMAILS_DIR, rel[len("emails/"):]
            elif rel.startswith("newsletter/"):
                base, rel = NEWSLETTER_DIR, rel[len("newsletter/"):]
            elif rel.startswith("campaign-reports/"):
                base, rel = REPORTS_DIR, rel[len("campaign-reports/"):]
            else:
                base, rel = CANVAS_HUB, rel
            resolved = os.path.abspath(os.path.join(base, rel))
            try:
                inside = os.path.commonpath([base, resolved]) == base
            except ValueError:
                inside = False
            if inside and (
                os.path.exists(resolved) or os.path.isfile(resolved + ".html")
            ):
                return resolved if os.path.exists(resolved) else resolved + ".html"
            return os.path.join(base, "__not_found__")
        resolved = super().translate_path(path)
        if not os.path.exists(resolved):
            root, ext = os.path.splitext(resolved)
            if not ext and os.path.isfile(resolved + ".html"):
                return resolved + ".html"
        return resolved

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class QuietHTTPServer(http.server.ThreadingHTTPServer):
    """Suppress client-disconnect noise that Python logs as full tracebacks.

    BrokenPipeError and ConnectionResetError mean the client closed the
    connection before we finished sending — common with uptime monitors,
    browser tab closes, and bulk-file operations.  They are not server
    errors; logging them as tracebacks causes false outage alerts.
    Real server errors still surface via the default handler.
    """
    def handle_error(self, request, client_address):
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            return  # harmless client disconnect — ignore silently
        super().handle_error(request, client_address)


if __name__ == "__main__":
    QuietHTTPServer(("0.0.0.0", 5000), PrettyURLHandler).serve_forever()
