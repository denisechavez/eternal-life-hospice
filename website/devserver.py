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


class PrettyURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/canvas-hub/"):
            rel = os.path.normpath(clean[len("/canvas-hub/"):]).lstrip("/")
            if rel.startswith("emails/"):
                base, rel = EMAILS_DIR, rel[len("emails/"):]
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


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", 5000), PrettyURLHandler).serve_forever()
