#!/usr/bin/env python3
"""Local preview server for the static site.

Mimics Netlify's "pretty URLs": /care-brief resolves to care-brief.html,
so internal links behave the same in the Replit preview as on the live site.
Not published (lives outside elh-preview/).
"""
import http.server
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "elh-preview")
# Internal-only routes for the workspace canvas hub (never published to the site):
CANVAS_HUB = os.path.join(BASE, "canvas-hub")
EMAILS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "email"))
REPORTS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "campaign-reports"))


class PrettyURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/canvas-hub/"):
            rel = os.path.normpath(clean[len("/canvas-hub/"):]).lstrip("/")
            if rel.startswith("emails/"):
                base, rel = EMAILS_DIR, rel[len("emails/"):]
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

    def do_POST(self):
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


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", 5000), PrettyURLHandler).serve_forever()
