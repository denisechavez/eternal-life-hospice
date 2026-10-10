"""Protected delivery of Studio's compiled application and Clerk's FAPI proxy."""
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

import studio_auth

BUILD = Path(__file__).resolve().parent / "studio-build"
PROXY = "/api/__clerk"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Forward Location to the browser; never forward secret headers to a
        # different host by following an upstream redirect.
        return None


def public_assets():
    """Only the login entry's static dependencies; never draft dynamic chunks."""
    manifest = json.loads((BUILD / ".vite/manifest.json").read_text())
    allowed = set()
    def visit(key):
        row = manifest[key]
        if row["file"] in allowed:
            return
        allowed.add(row["file"])
        allowed.update(row.get("css", []))
        for dependency in row.get("imports", []):
            visit(dependency)
    visit("index.html")
    return allowed


def serve(handler):
    path = urlsplit(handler.path).path
    if path != "/studio" and not path.startswith("/studio/"):
        return False
    if handler.command not in {"GET", "HEAD"}:
        handler._send_json(405, {"message": "Use GET"})
        return True
    relative = unquote(path.removeprefix("/studio").lstrip("/"))
    if not relative or (not (BUILD / relative).is_file() and not Path(relative).suffix):
        relative = "index.html"
    target = (BUILD / relative).resolve()
    if not target.is_relative_to(BUILD) or not target.is_file():
        handler._send_json(503, {"message": "Studio build unavailable"})
        return True
    try:
        if relative not in {"index.html", "favicon.svg"} and relative not in public_assets():
            studio_auth.reviewer(handler.headers)
        body = target.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Robots-Tag", "noindex, nofollow")
        handler.end_headers()
        if handler.command != "HEAD":
            handler.wfile.write(body)
    except PermissionError:
        handler._send_json(401, {"message": "Sign in as the designated Studio reviewer."})
    except Exception:
        handler._send_json(503, {"message": "Studio unavailable"})
    return True


def proxy(handler):
    """Python equivalent of the managed Clerk proxy template."""
    parsed = urlsplit(handler.path)
    if parsed.path != PROXY and not parsed.path.startswith(PROXY + "/"):
        return False
    if os.environ.get("REPLIT_DEPLOYMENT") != "1":
        handler._send_json(404, {"message": "Clerk proxy is production-only"})
        return True
    host = (handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host", "")).split(",")[0].strip()
    if "https://" + host not in studio_auth.allowed_origins():
        handler._send_json(403, {"message": "Untrusted Clerk proxy host"})
        return True
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        if length < 0 or length > 1024 * 1024:
            raise ValueError("Request too large")
        data = handler.rfile.read(length) if length else None
        suffix = parsed.path[len(PROXY):] or "/"
        if parsed.query:
            suffix += "?" + parsed.query
        headers = {key: value for key, value in handler.headers.items()
                   if key.lower() in {"accept", "content-type", "cookie", "origin", "user-agent", "authorization"}}
        headers.update({"Clerk-Proxy-Url": "https://" + host + PROXY,
                        "Clerk-Secret-Key": os.environ["CLERK_SECRET_KEY"],
                        "X-Forwarded-For": (handler.headers.get("X-Forwarded-For") or handler.client_address[0]).split(",")[0].strip()})
        request = Request("https://frontend-api.clerk.dev" + suffix, data=data,
                          headers=headers, method=handler.command)
        try:
            upstream = build_opener(NoRedirect).open(request, timeout=20)
        except HTTPError as error:
            upstream = error
        with upstream:
            body = upstream.read()
            handler.send_response(upstream.status)
            for key, value in upstream.headers.raw_items():
                if key.lower() not in {"content-length", "transfer-encoding", "connection", "keep-alive"}:
                    handler.send_header(key, value)
            if upstream.status not in {204, 304}:
                handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            if handler.command != "HEAD" and upstream.status not in {204, 304}:
                handler.wfile.write(body)
    except Exception:
        handler._send_json(502, {"message": "Studio sign-in provider unavailable"})
    return True
