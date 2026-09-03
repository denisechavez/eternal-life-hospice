#!/usr/bin/env python3
"""Static-site server and production API endpoints.

Mimics Netlify's "pretty URLs": /care-brief resolves to care-brief.html,
so internal links behave the same in the Replit preview as on the live site.
The Replit deployment serves the public domain and owns form intake, reviews,
chat, and coverage lookup without requiring Netlify functions.
"""
import http.server
import gzip
import io
import json
import os
import socket
import sys
from urllib.parse import parse_qs, urlsplit

from chat_api import (
    ChatProviderError,
    ChatRequestError,
    MAX_CHAT_BODY_BYTES,
    process_chat,
)
from coverage_api import lookup_coverage

from form_intake import (
    DeliveryError,
    FORM_CLIENT_RATE_LIMITER,
    FORM_GLOBAL_RATE_LIMITER,
    IntakeError,
    MAX_BODY_BYTES,
    SlidingWindowRateLimiter,
    json_response_payload,
    notify_delivery_failure,
    parse_form_body,
    process_submission,
)
from google_reviews import GoogleReviewsError, get_reviews

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "elh-preview")
# Internal-only routes for the workspace canvas hub (never published to the site):
CANVAS_HUB = os.path.join(BASE, "canvas-hub")
EMAILS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "email"))
NEWSLETTER_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "newsletter"))
REPORTS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "campaign-reports"))
CHAT_CLIENT_RATE_LIMITER = SlidingWindowRateLimiter(20, 10 * 60)
CHAT_GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter(120, 10 * 60)
CANONICAL_HTML_ROUTES = {
    "/hospice-care",
    "/resources",
    "/blog",
    "/services",
    "/care-brief",
}

# The marketing site owns these historical page aliases. Keep API and tracker
# forwarding rules out of this table: those services have separate ownership.
LEGACY_PAGE_REDIRECTS = {
    "/hospice-ventura-county-ca": "/hospice-ventura-and-los-angeles-county-ca",
    "/hospice-los-angeles-county-ca": "/hospice-ventura-and-los-angeles-county-ca",
    "/refer-a-patient": "/refer",
    "/referral": "/refer",
    "/refer-patient": "/refer",
    "/providers": "/refer",
    "/kit": "/media-kit",
    "/presskit": "/media-kit",
    "/press-kit": "/media-kit",
    "/media": "/media-kit",
    "/aleksandra": "/about/aleksandra-dubina",
    "/denise": "/card-denise-chavez",
    "/resources/what-hospice-covers": "/resources/medicare-hospice-benefit",
    "/resources/medical-aid-in-dying-california": "/services/medical-aid-in-dying-california",
    "/aleksandradubina": "/about/aleksandra-dubina",
    "/insurance": "/resources/medicare-hospice-benefit",
    "/insurance/": "/resources/medicare-hospice-benefit",
    "/faqs": "/resources",
    "/faqs/": "/resources",
    "/about-us": "/about/aleksandra-dubina",
    "/about-us/": "/about/aleksandra-dubina",
    "/contact": "/refer",
    "/contact/": "/refer",
    "/terms/": "/terms",
    "/privacy-policy/": "/privacy-policy",
    "/assets/og-image-v2.jpg": "/assets/og-image.jpg",
    "/care-brief/": "/care-brief",
    "/care-brief/hospice-is-part-of-life-a-continuation-of-care": "/care-brief/issue-1",
    "/care-brief/caring-for-the-caregiver": "/blog/the-caregiver-who-needs-care",
    "/blog/caring-for-the-caregiver": "/blog/the-caregiver-who-needs-care",
    "/blog/the-second-patient": "/blog/the-caregiver-who-needs-care",
}


class PrettyURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

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
        # These hubs have extensionless canonical URLs. Resolve them before
        # SimpleHTTPRequestHandler sees the /resources/ or /blog/ directory
        # redirect stub, so the canonical archive URL serves the final
        # document directly.
        if clean.rstrip("/") in CANONICAL_HTML_ROUTES:
            return os.path.join(ROOT, clean.rstrip("/").lstrip("/") + ".html")
        resolved = super().translate_path(path)
        if not os.path.exists(resolved):
            root, ext = os.path.splitext(resolved)
            if not ext and os.path.isfile(resolved + ".html"):
                return resolved + ".html"
        return resolved

    def _has_header(self, name):
        prefix = f"{name.lower()}:".encode("ascii")
        return any(
            header.lower().startswith(prefix)
            for header in getattr(self, "_headers_buffer", [])
        )

    def _cache_control_for_path(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/") or path in ("/health", "/healthz"):
            return None
        if path in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
            return "public, max-age=300, must-revalidate"
        if path == "/assets/search-index.json":
            return "public, max-age=0, must-revalidate"
        if path.startswith("/assets/"):
            return "public, max-age=31536000, immutable"
        if path.endswith(".html") or not os.path.splitext(path)[1]:
            return "public, max-age=0, must-revalidate"
        return "public, max-age=300"

    def _is_internal_artifact(self):
        path = urlsplit(self.path).path
        return (
            path.startswith("/assets/social/")
            or path.startswith("/assets/img/amethyst-tmp/gallery")
        )

    def send_head(self):
        """Serve compressible static responses with a smaller wire payload.

        Conditional and range requests stay on the stdlib implementation so
        Last-Modified and byte-range semantics remain intact.
        """
        path = self.translate_path(self.path)
        suffix = os.path.splitext(path)[1].lower()
        compressible = {
            ".css",
            ".html",
            ".js",
            ".json",
            ".svg",
            ".txt",
            ".webmanifest",
            ".xml",
        }
        if (
            suffix not in compressible
            or not os.path.isfile(path)
            or self.headers.get("Range")
            or self.headers.get("If-Modified-Since")
            or "gzip" not in (self.headers.get("Accept-Encoding") or "").lower()
        ):
            return super().send_head()

        try:
            with open(path, "rb") as source:
                raw = source.read()
                modified = os.fstat(source.fileno()).st_mtime
        except OSError:
            return super().send_head()

        if len(raw) < 512:
            return super().send_head()

        compressed = gzip.compress(raw, compresslevel=6, mtime=0)
        self.send_response(200)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(compressed)))
        self.send_header("Last-Modified", self.date_time_string(modified))
        self.end_headers()
        return io.BytesIO(compressed)

    def end_headers(self):
        if not self._has_header("Cache-Control"):
            cache_control = self._cache_control_for_path()
            if cache_control:
                self.send_header("Cache-Control", cache_control)
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' "
                "https://i.replit.com https://www.googletagmanager.com "
                "https://www.clarity.ms https://scripts.clarity.ms "
                "https://cdn.brevo.com https://sibautomation.com "
                "https://www.google-analytics.com "
                "https://s.ksrndkehqnwntyxlhgto.com "
                "https://tracker.metricool.com https://cdn.userway.org; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
                "https://cdn.userway.org; "
                "font-src 'self' https://fonts.gstatic.com data: "
                "https://cdn.userway.org; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://www.google-analytics.com "
                "https://region1.google-analytics.com https://www.clarity.ms "
                "https://in.clarity.ms https://cdn.brevo.com https://api.brevo.com "
                "https://stats.g.doubleclick.net https://www.google.com "
                "https://s.ksrndkehqnwntyxlhgto.com "
                "https://p.ksrndkehqnwntyxlhgto.com "
                "https://process.iconnode.com https://cdn.userway.org "
                "https://widget.userway.org https://api.userway.org "
                "https://tracker.metricool.com; "
                "media-src 'self'; frame-src https://cdn.userway.org; "
                "frame-ancestors 'self'; form-action 'self';"
            ),
        }
        for name, value in security_headers.items():
            if not self._has_header(name):
                self.send_header(name, value)
        if self._is_internal_artifact() and not self._has_header("X-Robots-Tag"):
            self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()

    def _send_health(self, head_only=False):
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _send_canonical_redirect(self, parsed):
        destination = LEGACY_PAGE_REDIRECTS.get(parsed.path)
        if not destination and parsed.path in ("/blog/", "/services/"):
            destination = parsed.path.rstrip("/")
        if not destination:
            return False
        self._send_redirect(destination, parsed.query)
        return True

    def do_HEAD(self):
        parsed = urlsplit(self.path)
        if parsed.path in ("/health", "/healthz"):
            self._send_health(head_only=True)
            return
        if self._send_canonical_redirect(parsed):
            return
        super().do_HEAD()

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path in ("/health", "/healthz"):
            self._send_health()
            return
        if self._send_canonical_redirect(parsed):
            return
        if parsed.path == "/api/chat":
            self._send_json(
                405,
                {"error": "method_not_allowed", "message": "Use POST /api/chat."},
            )
            return
        if parsed.path == "/api/form-submit":
            self._send_json(
                405,
                {
                    "error": "method_not_allowed",
                    "message": "Use POST /api/form-submit.",
                },
                extra_headers={"Allow": "POST"},
            )
            return
        if parsed.path == "/api/coverage":
            status, payload, cache_seconds = lookup_coverage(
                parse_qs(parsed.query, keep_blank_values=True)
            )
            self._send_json(
                status,
                payload,
                cache_control=f"public, max-age={cache_seconds}",
                extra_headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                },
            )
            return
        if parsed.path == "/api/google-reviews":
            try:
                payload = get_reviews()
                self._send_json(200, payload)
            except GoogleReviewsError:
                self._send_json(
                    503,
                    {
                        "ok": False,
                        "error": "reviews_unavailable",
                        "message": (
                            "Live Google reviews are temporarily unavailable. "
                            "Please use the Google profile link to see the latest reviews."
                        ),
                        "googleMapsUrl": (
                            "https://maps.google.com/?cid=9771388271577679785"
                        ),
                    },
                )
            return
        super().do_GET()

    def _send_redirect(self, destination, query=""):
        location = destination + (f"?{query}" if query else "")
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/coverage":
            self._send_json(
                405,
                {
                    "error": "method_not_allowed",
                    "message": "Use GET /api/coverage?city=CityName.",
                },
            )
            return
        if path == "/api/chat":
            self._handle_chat()
            return
        if path != "/api/form-submit":
            self._send_json(
                404,
                json_response_payload(
                    False,
                    error="unknown_endpoint",
                    message="This submission endpoint does not exist.",
                ),
            )
            return

        if not self._is_same_origin():
            self._send_json(
                403,
                json_response_payload(
                    False,
                    error="invalid_origin",
                    message=(
                        "This form must be submitted from the Eternal Life "
                        "Hospice website."
                    ),
                ),
            )
            return

        if not FORM_GLOBAL_RATE_LIMITER.allow(self._peer_key()):
            self._send_json(
                429,
                json_response_payload(
                    False,
                    error="rate_limited",
                    message=(
                        "The website is receiving too many requests. Please "
                        "wait and try again, or call 805.953.7273 for immediate help."
                    ),
                ),
            )
            return

        if not FORM_CLIENT_RATE_LIMITER.allow(self._client_key()):
            self._send_json(
                429,
                json_response_payload(
                    False,
                    error="rate_limited",
                    message=(
                        "Too many requests were received. Please wait and try "
                        "again, or call 805.953.7273 for immediate help."
                    ),
                ),
            )
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._send_json(
                413,
                json_response_payload(
                    False,
                    error="payload_too_large",
                    message="The submission is too large.",
                ),
            )
            return

        body = self.rfile.read(length)
        try:
            fields, files = parse_form_body(
                self.headers.get("Content-Type", ""), body
            )
            result = process_submission(fields, files)
            form_name = fields.get("form-name", "unknown")
            receipt = result.get("receipt_id", "honeypot")
            print(
                f"FORM_ACCEPTED form={form_name} receipt={receipt} "
                f"ack={bool(result.get('acknowledgement_sent'))}",
                file=sys.stderr,
            )
            response_data = dict(result)
            response_data.pop("ok", None)
            self._send_json(200, json_response_payload(True, **response_data))
        except IntakeError as exc:
            self._send_json(
                exc.status,
                json_response_payload(
                    False, error=exc.code, message=exc.message
                ),
            )
        except DeliveryError:
            print("FORM_DELIVERY_FAILED provider=brevo", file=sys.stderr)
            notify_delivery_failure()
            self._send_json(
                502,
                json_response_payload(
                    False,
                    error="delivery_unavailable",
                    message=(
                        "We could not confirm delivery. Please try again or call "
                        "805.953.7273 for immediate help."
                    ),
                ),
            )
        except Exception as exc:
            # Never log the request body or submitted fields.
            print(
                f"FORM_PROCESSING_FAILED type={type(exc).__name__}",
                file=sys.stderr,
            )
            self._send_json(
                500,
                json_response_payload(
                    False,
                    error="processing_error",
                    message=(
                        "We could not confirm delivery. Please try again or call "
                        "805.953.7273 for immediate help."
                    ),
                ),
            )

    def do_OPTIONS(self):
        if self.path.split("?", 1)[0] == "/api/coverage":
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _handle_chat(self):
        if not self._is_same_origin():
            self._send_json(
                403,
                {
                    "error": "invalid_origin",
                    "message": "This chat must be used from the Eternal Life Hospice website.",
                },
            )
            return
        if not CHAT_GLOBAL_RATE_LIMITER.allow("global"):
            self._send_json(
                429,
                {"error": "rate_limited", "message": "Please wait and try again."},
            )
            return
        if not CHAT_CLIENT_RATE_LIMITER.allow(self._client_key()):
            self._send_json(
                429,
                {"error": "rate_limited", "message": "Please wait and try again."},
            )
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_CHAT_BODY_BYTES:
            self._send_json(
                413,
                {"error": "payload_too_large", "message": "The chat request is too large."},
            )
            return
        try:
            previous_timeout = self.connection.gettimeout()
            self.connection.settimeout(10)
            try:
                body = self.rfile.read(length)
            finally:
                self.connection.settimeout(previous_timeout)
            status, payload = process_chat(body)
            self._send_json(status, payload)
        except (socket.timeout, TimeoutError):
            self._send_json(
                408,
                {"error": "request_timeout", "message": "The chat request timed out."},
            )
        except ChatRequestError as exc:
            self._send_json(
                exc.status, {"error": exc.code, "message": exc.message}
            )
        except ChatProviderError:
            # Never log message bodies or provider response bodies.
            print("CHAT_PROVIDER_FAILED", file=sys.stderr)
            self._send_json(
                502,
                {
                    "reply": "",
                    "error": "chat_unavailable",
                    "message": "Chat is temporarily unavailable.",
                },
            )
        except Exception as exc:
            # Never log message bodies or submitted fields.
            print(f"CHAT_FAILED type={type(exc).__name__}", file=sys.stderr)
            self._send_json(
                500,
                {
                    "reply": "",
                    "error": "chat_unavailable",
                    "message": "Chat is temporarily unavailable.",
                },
            )

    def _is_same_origin(self):
        origin = (self.headers.get("Origin") or "").strip()
        host = (self.headers.get("Host") or "").strip().lower()
        if not origin or not host:
            return False
        try:
            parsed = urlsplit(origin)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return parsed.netloc.lower() == host

    def _client_key(self):
        # A compliant reverse proxy appends its observed client address to the
        # right edge. Never trust a caller-supplied leading XFF value. Because
        # Replit does not document a sanitized-header contract, the independent
        # socket-peer circuit breaker above remains authoritative even if every
        # forwarded value is attacker-controlled.
        forwarded = [
            item.strip()
            for item in (self.headers.get("X-Forwarded-For") or "").split(",")
            if item.strip()
        ]
        candidate = forwarded[-1] if forwarded else self.client_address[0]
        # Avoid unbounded attacker-controlled keys.
        return candidate[:64]

    def _peer_key(self):
        return ("peer:" + self.client_address[0])[:80]

    def _send_json(
        self, status, body, cache_control="no-store", extra_headers=None
    ):
        if not isinstance(body, (bytes, bytearray)):
            if not isinstance(body, str):
                body = json.dumps(
                    body, ensure_ascii=False, separators=(",", ":")
                )
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


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
