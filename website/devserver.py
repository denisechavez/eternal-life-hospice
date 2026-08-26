#!/usr/bin/env python3
"""Static-site server and production form intake endpoint.

Mimics Netlify's "pretty URLs": /care-brief resolves to care-brief.html,
so internal links behave the same in the Replit preview as on the live site.
The Replit deployment also serves the public domain, so POST /api/form-submit
is the production form processor. It delivers through Brevo and never stores
submission data locally.
"""
import http.server
import json
import os
import sys
from urllib.parse import urlsplit

from form_intake import (
    DeliveryError,
    FORM_CLIENT_RATE_LIMITER,
    FORM_GLOBAL_RATE_LIMITER,
    IntakeError,
    MAX_BODY_BYTES,
    json_response_payload,
    notify_delivery_failure,
    parse_form_body,
    process_submission,
)

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "elh-preview")
# Internal-only routes for the workspace canvas hub (never published to the site):
CANVAS_HUB = os.path.join(BASE, "canvas-hub")
EMAILS_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "email"))
NEWSLETTER_DIR = os.path.abspath(os.path.join(BASE, "..", "exports", "newsletter"))
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

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/form-submit":
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

    def _send_json(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
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
