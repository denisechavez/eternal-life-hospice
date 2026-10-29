"""Real public pages/headers on loopback; no API handlers or external transports."""
import http.server
import json
import os
import socket
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from devserver import PrettyURLHandler, ROOT


# Deliberately independent of the browser allowlist: never open all service or
# resource routes (or an API handler) just to exercise representative pages.
PUBLIC_PAGES = frozenset({
    "/", "/refer", "/services", "/services/in-home-hospice-care",
    "/resources", "/resources/when-is-it-time",
})

AUDIT = []
PROXY_AUDIT = []
WORKER = """fetch('https://www.google-analytics.com/g/collect?probe=worker',
{method:'POST', mode:'no-cors', body:'synthetic'})
.then(() => postMessage('done'), () => postMessage('blocked'));"""
NEW_TAB = """<!doctype html><html><head><title>Synthetic consent tab</title>
<script>
window.__newTabProbe = {
  armed: window.__consentHarnessArmed,
  consent: localStorage.getItem('elh_cc'),
  topLevel: window === window.top
};
window.dataLayer = [['config', 'G-SYNTHETIC-NEW-TAB']];
window.__newTabProbe.done = false;
Promise.all([
  fetch('https://www.google-analytics.com/g/collect?probe=new-tab',
    {method:'POST', mode:'no-cors', body:'synthetic'}).catch(() => {}),
  fetch('/api/form-submit', {method:'POST', body:'synthetic'}).catch(() => {})
]).then(() => { window.__newTabProbe.done = true; });
</script></head><body>Synthetic negative control only</body></html>"""


class DenyProxy(http.server.BaseHTTPRequestHandler):
    """Independent fail-closed boundary for targets CDP might not intercept."""
    def do_GET(self):
        PROXY_AUDIT.append({"method": self.command, "url": self.path, "status": 403,
                            "upgrade": self.headers.get("Upgrade", "").lower()})
        self.send_error(403, "No outbound transport in consent regression")

    do_CONNECT = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = do_GET

    def log_message(self, *args):
        pass


class LandingConsentFixture(PrettyURLHandler):
    def _preview_chrome(self, document, route=None):
        document = super()._preview_chrome(document, route)
        # In-memory negative controls only: never edit approval-controlled HTML.
        probe = parse_qs(urlsplit(self.path).query).get("__consent_probe", [""])[0]
        if probe == "inline":
            document += """<script>
              window.dataLayer = window.dataLayer || [];
              window.dataLayer.push(['config', 'G-SYNTHETIC-BYPASS']);
            </script>"""
        elif probe == "tag":
            document += '<script src="https://www.googletagmanager.com/gtag/js?id=G-SYNTHETIC-BYPASS"></script>'
        elif probe == "frame":
            document += '<iframe hidden src="https://cdn.userway.org/__consent-frame"></iframe>'
        elif probe == "worker":
            document += '<script>window.__probeWorker = new Worker("/assets/__consent-worker.js");</script>'
        elif probe == "new-tab":
            document += """<script>window.__openConsentProbe = () =>
              !!window.open('/assets/__consent-new-tab.html', '_blank');</script>"""
        elif probe == "beacon":
            document += """<script>navigator.sendBeacon(
              'https://www.google-analytics.com/g/collect?probe=beacon', 'synthetic');</script>"""
        elif probe in ("websocket", "eventsource"):
            # Same-origin WS is permitted by the unchanged public CSP. The
            # browser's HTTP-only proxy bypass must NOT bypass this handshake.
            transport = (
                'new WebSocket(location.origin.replace("http", "ws") + '
                '"/assets/__consent-websocket?probe=websocket")'
                if probe == "websocket" else
                'new EventSource("https://www.google-analytics.com/g/collect?probe=eventsource")'
            )
            document += f"""<script>
              window.__consentTransportEvents = [];
              window.__consentTransport = {transport};
              for (const name of ['open', 'message', 'error', 'close']) {{
                window.__consentTransport.addEventListener(name, () => {{
                  window.__consentTransportEvents.push(name);
                  if (name === 'error') window.__consentTransport.close();
                }});
              }}
            </script>"""
        elif probe in ("redirect", "redirect-mutation"):
            document += f"""<script>fetch('/assets/__consent-{probe}', {{
              method:'{'POST' if probe == 'redirect-mutation' else 'GET'}',
              mode:'no-cors'
            }}).catch(() => {{}});</script>"""
        return document

    def _probe_response(self):
        path = urlsplit(self.path).path
        if path == "/__consent-audit" and self.command == "GET":
            body = json.dumps({"requests": AUDIT, "proxy": PROXY_AUDIT}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif path == "/assets/__consent-worker.js" and self.command == "GET":
            body = WORKER.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
        elif path == "/assets/__consent-new-tab.html" and self.command == "GET":
            body = NEW_TAB.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        elif (path, self.command) in (
            ("/assets/__consent-redirect", "GET"),
            ("/assets/__consent-redirect-mutation", "POST"),
        ):
            body = b""
            self.send_response(307)
            self.send_header("Location", "/api/form-submit" if self.command == "POST" else
                             "https://www.google-analytics.com/g/collect?probe=redirect")
        else:
            return False
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True

    def do_GET(self):
        AUDIT.append({"method": self.command, "path": urlsplit(self.path).path})
        if self._probe_response():
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/api/google-reviews":
            body = b'{"available":false,"reviews":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        asset = (Path(ROOT) / path.lstrip("/")).resolve()
        if path in PUBLIC_PAGES or (
            path.startswith("/assets/") and
            asset.is_relative_to((Path(ROOT) / "assets").resolve()) and asset.is_file()
        ):
            # Use the real public serving pipeline, including HTML transforms,
            # versioned analytics asset and inherited production security headers.
            super().do_GET()
            return
        self.send_error(405, "No APIs or non-static routes in consent regression")

    def do_HEAD(self):
        self.send_error(405)

    def do_POST(self):
        AUDIT.append({"method": self.command, "path": urlsplit(self.path).path})
        if self._probe_response():
            return
        self.send_error(405, "No mutations in consent regression")

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_POST

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if os.environ.get("REPLIT_DEPLOYMENT") == "1":
        raise SystemExit("Never run browser fixtures in production")
    # Only this isolated child uses public rendering, not workspace draft
    # navigation. Routes and outbound sockets remain independently denied.
    os.environ["REPLIT_DEPLOYMENT"] = "1"
    # Defense in depth: the server can accept loopback requests but cannot
    # open outbound connections, even if a future static handler regresses.
    def no_connect(*args, **kwargs):
        raise RuntimeError("Outbound network disabled in consent fixture")

    socket.socket.connect = no_connect
    socket.socket.connect_ex = no_connect
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), LandingConsentFixture)
    proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DenyProxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    print(json.dumps({"port": server.server_port, "proxyPort": proxy.server_port}), flush=True)
    try:
        sys.stdin.read()
    finally:
        server.shutdown()
        server.server_close()
        proxy.shutdown()
        proxy.server_close()
