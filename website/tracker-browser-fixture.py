"""Loopback-only consent fixture with production response CSP, no intake routes."""
import http.server
import json
import sys
import threading
from urllib.parse import urlsplit

from analytics_assets import ANALYTICS_FILE
from devserver import PrettyURLHandler


class TrackerFixture(PrettyURLHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/analytics.js":
            body = ANALYTICS_FILE.read_bytes()
            content_type = "text/javascript"
        elif path in ("/", "/no-eval"):
            body = (
                '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<h1>Consent fixture</h1><button id="footer" onclick="elhCookieSettings()">'
                'Cookie Settings</button><script>window.__noClarity=true</script>'
                '<script src="/analytics.js"></script>'
            ).encode()
            content_type = "text/html"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_header(self, keyword, value):
        # The inherited end_headers generates the actual response policy.
        # Strip only eval for the negative-control document.
        if keyword.lower() == "content-security-policy" and urlsplit(self.path).path == "/no-eval":
            value = value.replace(" 'unsafe-eval'", "")
        super().send_header(keyword, value)

    def do_POST(self):
        self.send_error(405, "No intake or delivery in tracker fixtures")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), TrackerFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({"port": server.server_port}), flush=True)
    try:
        sys.stdin.read()
    finally:
        server.shutdown()
        server.server_close()
