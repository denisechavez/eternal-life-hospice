#!/usr/bin/env python3
"""Local preview server for the static site.

Mimics Netlify's "pretty URLs": /care-brief resolves to care-brief.html,
so internal links behave the same in the Replit preview as on the live site.
Not published (lives outside elh-preview/).
"""
import http.server
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elh-preview")


class PrettyURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path):
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
