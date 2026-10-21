#!/usr/bin/env python3
"""Static-site server and production API endpoints.

Provides extensionless routes such as /care-brief for the static HTML site.
The Replit deployment serves the public domain and owns form intake, reviews,
chat, and coverage lookup.
"""
import http.server
import gzip
import html
import io
import json
import os
import posixpath
import re
import socket
import subprocess
import sys
import footer_contact
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, unquote, urlsplit

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
from journal_preview import render_resources_journal
import journal_release
import studio_auth
import studio_site
import journal_discovery
import form_antispam
import recruitment_policy

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "elh-preview")
JOURNAL_MANIFEST = os.path.join(BASE, "content", "30-day-journal-manifest.json")


def _valid_journal_date(value):
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


# Internal-only routes for the workspace canvas hub (never published to the site):
CANVAS_HUB = os.path.join(BASE, "canvas-hub")
GROWTH_INTELLIGENCE_REPORTER = os.path.join(
    BASE, "growth-intelligence-reporting.mjs"
)
CONFIDENTIAL_CANVAS_NAMESPACES = frozenset(
    {"emails", "newsletter", "campaign-reports"}
)
CHAT_CLIENT_RATE_LIMITER = SlidingWindowRateLimiter(20, 10 * 60)
CHAT_GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter(120, 10 * 60)


def is_production_deployment():
    """Return True only inside a published Replit deployment."""
    return os.environ.get("REPLIT_DEPLOYMENT") == "1"


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
        if clean.rstrip("/") == "/growth-intelligence":
            if is_production_deployment():
                return os.path.join(ROOT, "__not_found__")
            return os.path.join(CANVAS_HUB, "dashboard", "index.html")
        if clean.startswith("/canvas-hub/"):
            if is_production_deployment():
                return os.path.join(ROOT, "__not_found__")
            rel = os.path.normpath(clean[len("/canvas-hub/"):]).lstrip("/")
            namespace = rel.split("/", 1)[0]
            if namespace in CONFIDENTIAL_CANVAS_NAMESPACES:
                return os.path.join(ROOT, "__not_found__")
            base = CANVAS_HUB
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

    @staticmethod
    def _journal_today():
        """Return the publication date in the campaign's local timezone.

        ELH_JOURNAL_DATE is deliberately supported for deterministic previews
        and regression tests; production uses the real America/Los_Angeles date.
        """
        override = os.environ.get("ELH_JOURNAL_DATE") if not is_production_deployment() else None
        if override:
            try:
                return datetime.strptime(override, "%Y-%m-%d").date().isoformat()
            except ValueError:
                return None
        return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()

    @classmethod
    def _journal_manifest(cls):
        try:
            with open(JOURNAL_MANIFEST, encoding="utf-8") as source:
                payload = json.load(source)
            articles = payload["articles"]
            if payload.get("timezone") != "America/Los_Angeles" or not isinstance(articles, list):
                return None
            if any(not isinstance(a, dict) or not isinstance(a.get("slug"), str)
                   or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a["slug"])
                   or not isinstance(a.get("date"), str)
                   or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a["date"])
                   or not _valid_journal_date(a["date"])
                   for a in articles):
                return None
            return articles
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def _released_journal(self):
        if not hasattr(self, "_journal_snapshot"):
            self._journal_snapshot = journal_release.released()
        return self._journal_snapshot[0]

    def _journal_pages(self):
        from internal_links import inventory, PageParser
        pages = {route: entry for route, entry in inventory(self._journal_today()).items()
                 if not route.startswith("/blog/") or route[6:] in self._released_journal()}
        for slug, row in self._released_journal().items():
            route = "/blog/" + slug
            if route in pages:
                pages[route] = (pages[route][0], row["html"], PageParser(row["html"], self._journal_today()))
        return pages

    def _hide_unreleased_links(self, text, route):
        from internal_links import resolve
        def anchor(match):
            attr = re.search(r'\bhref=(["\'])(.*?)\1', match.group(1))
            target = resolve(route, html.unescape(attr[2])) if attr else None
            if target and target[0].startswith("/blog/"):
                slug = target[0][6:].removesuffix(".html")
                if slug not in self._released_journal():
                    return match.group(2)
            return match.group(0)
        return re.sub(r'<a\b([^>]*)>([\s\S]*?)</a>', anchor, text, flags=re.IGNORECASE)

    @classmethod
    def _future_journal_path(cls, path):
        if cls._journal_today() is None:
            return True
        try:
            clean = unquote(path)
            # A second decode catches double-encoded separators/hyphens.
            clean = unquote(clean)
        except Exception:
            return True
        clean = "/" + posixpath.normpath(clean).lstrip("/")
        clean = clean.rstrip("/")
        if clean.endswith(".html"):
            clean = clean[:-5]
        if not clean.startswith("/blog/"):
            return False
        slug = clean[len("/blog/"):]
        manifest = cls._journal_manifest()
        if manifest is None:
            return True
        return slug not in journal_release.released()[0]

    def _studio_api(self):
        if studio_site.proxy(self) or studio_site.serve(self):
            return True
        path = urlsplit(self.path).path
        if path.startswith("/api/journal-photo/"):
            if self.command not in {"GET", "HEAD"}:
                self._send_json(405, {"message": "Use GET"})
                return True
            try:
                record = journal_release.photo(path.rsplit("/", 1)[-1])
                if not record:
                    self.send_error(404)
                    return True
                self.send_response(200)
                self.send_header("Content-Type", record["media_type"])
                self.send_header("Content-Length", str(len(record["body"])))
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(record["body"])
            except Exception:
                self._send_json(503, {"message": "Published photograph unavailable"})
            return True
        if path not in {"/api/studio/session", "/api/studio/journal", "/api/studio/journal/history", "/api/journal-release-status"}:
            return False
        try:
            if path == "/api/journal-release-status":
                if self.command not in {"GET", "HEAD"}:
                    self._send_json(405, {"message": "Use GET"})
                else:
                    self._send_json(200, journal_release.release_status())
                return True
            # Includes private approval history: authenticate reads and writes
            # alike before querying any editorial identities or decisions.
            user = studio_auth.reviewer_identity(self.headers)
            if path == "/api/studio/session":
                if self.command not in {"GET", "HEAD"}:
                    self._send_json(405, {"message": "Use GET"})
                else:
                    self._send_json(200, {"verified": True})
                return True
            if path == "/api/studio/journal/history":
                if self.command not in {"GET", "HEAD"}:
                    self._send_json(405, {"message": "Use GET"})
                    return True
                params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if any(len(values) != 1 for values in params.values()):
                    self._send_json(400, {"message": "Duplicate history parameters"})
                    return True
                try:
                    result = journal_release.article_history(
                        params.get("slug", [""])[0], params.get("limit", ["25"])[0],
                        params.get("cursor", [None])[0])
                except ValueError:
                    self._send_json(400, {"message": "Invalid history page request"})
                    return True
                except LookupError:
                    self._send_json(404, {"message": "Article not found"})
                    return True
                self._send_json(200, result)
                return True
            if self.command == "POST":
                # Cookie-authenticated writes require an exact trusted origin.
                if self.headers.get("Origin") not in studio_auth.allowed_origins():
                    raise PermissionError("Studio request origin is not authorized")
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 4096:
                    raise ValueError("Invalid approval request size")
                payload = json.loads(self.rfile.read(length))
                journal_release.decide(payload["slug"], payload["revision"], payload["action"],
                                       user.user_id, reviewer_name=user.display_name)
            elif self.command not in {"GET", "HEAD"}:
                self._send_json(405, {"message": "Use GET or POST"})
                return True
            self._send_json(200, {"items": journal_release.review_items()})
        except PermissionError as exc:
            self._send_json(403 if "__session" in self.headers.get("Cookie", "") else 401,
                            {"message": str(exc)})
        except (ValueError, KeyError, TypeError):
            self._send_json(409, {"message": "Article changed or request invalid. Reload and review again."})
        except Exception:
            self._send_json(503, {"message": "Journal approval storage unavailable. Nothing was approved."})
        return True

    def _send_journal_artifact(self, path):
        """Filter generated campaign artifacts at request time."""
        if self._journal_today() is None or self._journal_manifest() is None:
            self.send_error(503, "Journal publication schedule unavailable")
            return True
        try:
            with open(path, "rb") as source:
                body = source.read()
        except OSError:
            return False
        visible = self._released_journal()
        def eligible(markup):
            match = re.search(r'href="/?blog/([^"#?]+)', markup)
            return bool(match and match.group(1) in visible)
        # One eligibility set applies to URLs, cards, structured data and search.
        schedule = [{**item, "date": visible[item["slug"]]["date"] if item["slug"] in visible else "9999-12-31"}
                    for item in self._journal_manifest()]
        if path.endswith("/resources.html"):
            try:
                with open(os.path.join(ROOT, "blog.html"), encoding="utf-8") as source:
                    archive = source.read()
                archive = journal_discovery.archive(archive, visible)
                archive = re.sub(
                    r'<a class="rc"[^>]*>[\s\S]*?</a>',
                    lambda match: match.group(0) if eligible(match.group(0)) else "", archive)
                archive = re.sub(
                    r'<div class="blog-featured"[^>]*>[\s\S]*?</div>\s*</div>',
                    lambda match: match.group(0) if eligible(match.group(0)) else "", archive)
                body = render_resources_journal(
                    body.decode("utf-8"), archive, schedule, self._journal_today()
                ).encode("utf-8")
            except (OSError, ValueError):
                self.send_error(503, "Resources Journal stories unavailable")
                return True
        elif path.endswith("/blog.html"):
            text = journal_discovery.archive(body.decode("utf-8"), visible)
            today = self._journal_today()
            feature_slot = "<!-- JOURNAL_FEATURED_SLOT -->"
            featured_match = re.search(
                r'<div class="blog-featured"[^>]+data-publish-date="([^"]+)"[^>]*>[\s\S]*?</div>\s*</div>',
                text,
            )
            if featured_match is None:
                self.send_error(503, "Journal featured story unavailable")
                return True
            card_pattern = (
                r'<a class="rc"[^>]+data-publish-date="([^"]+)"'
                r'[^>]+data-featured="([^"]+)"[^>]*>[\s\S]*?</a>'
            )
            visible_cards = [
                match for match in re.finditer(card_pattern, text)
                if eligible(match.group(0))
            ]
            newest_card = max(visible_cards, key=lambda match: match.group(1), default=None)
            featured_date = featured_match.group(1)
            if eligible(featured_match.group(0)) and (
                newest_card is None or featured_date >= newest_card.group(1)
            ):
                featured = featured_match.group(0)
                chosen_date = featured_date
            elif newest_card is not None:
                featured = html.unescape(newest_card.group(2))
                chosen_date = newest_card.group(1)
            else:
                self.send_error(503, "Journal featured story unavailable")
                return True
            text = text[:featured_match.start()] + feature_slot + text[featured_match.end():]
            featured_slug = re.search(r'href="/?blog/([^"#?]+)', featured).group(1)
            text = re.sub(
                card_pattern,
                lambda match: "" if not eligible(match.group(0)) or
                re.search(r'href="/?blog/([^"#?]+)', match.group(0)).group(1) == featured_slug
                else match.group(0),
                text,
            )
            text = text.replace(feature_slot, featured, 1)
            # Blog JSON-LD is also part of the public archive response.  Filter
            # campaign postings there so crawlers cannot discover tomorrow's
            # URL even though the generated source file is already staged.
            campaign_dates = {"/blog/" + item["slug"]: item.get("date", "")
                              for item in self._journal_manifest()}
            def filter_ld(match):
                try:
                    payload = json.loads(match.group(1))
                    if payload.get("@type") == "Blog" and isinstance(payload.get("blogPost"), list):
                        payload["blogPost"] = [
                            post for post in payload["blogPost"]
                            if urlsplit(post.get("url", "")).path.removeprefix("/blog/") in visible
                        ]
                        for post in payload["blogPost"]:
                            slug = urlsplit(post["url"]).path.removeprefix("/blog/")
                            info = journal_discovery.summary(visible[slug])
                            if info["title"]:
                                post.update(headline=info["title"], description=info["desc"], datePublished=info["date"])
                                if info["image"]:
                                    post["image"] = info["image"]
                        return match.group(0).replace(match.group(1), json.dumps(payload, ensure_ascii=False))
                except (ValueError, TypeError, AttributeError):
                    pass
                return match.group(0)
            text = re.sub(r'<script type="application/ld\+json">([\s\S]*?)</script>',
                          filter_ld, text)
            body = text.encode("utf-8")
        elif path.endswith("search-index.json"):
            try:
                entries = json.loads(body)
                campaign = {"/blog/" + item["slug"]: item.get("date", "")
                            for item in self._journal_manifest()}
                entries = [entry for entry in entries
                           if not urlsplit(entry.get("url", "")).path.startswith("/blog/")
                           or urlsplit(entry["url"]).path.removeprefix("/blog/").removesuffix(".html") in visible]
                for entry in entries:
                    route = urlsplit(entry.get("url", "")).path
                    slug = route.removeprefix("/blog/").removesuffix(".html")
                    if route.startswith("/blog/") and slug in visible:
                        info = journal_discovery.summary(visible[slug])
                        if info["title"]:
                            entry.update(title=info["title"], desc=info["desc"], kw=info["title"]+" "+info["desc"])
                body = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode()
            except (ValueError, TypeError, KeyError):
                return False
        elif path.endswith("sitemap.xml"):
            text = body.decode("utf-8")
            today = self._journal_today()
            campaign = {item["slug"]: item["date"] for item in self._journal_manifest()}
            text = re.sub(
                r'\s*<url>\s*<loc>https://eternallifehospice\.com/blog/([^<]+)</loc>[\s\S]*?</url>',
                lambda match: "" if match.group(1) not in visible else match.group(0),
                text,
            )
            body = text.encode("utf-8")
        else:
            return False
        if path.endswith(".html"):
            from internal_links import render_links
            route = "/" + os.path.basename(path)[:-5]
            body = render_links(body.decode("utf-8"), route, self._journal_today(),
                                pages=self._journal_pages()).encode("utf-8")
            body = self._hide_unreleased_links(body.decode(), route).encode()
            body = footer_contact.public_html(form_antispam.refresh_assets(recruitment_policy.public_html(body.decode()))).encode()
        elif path.endswith("search-index.json"):
            body = recruitment_policy.public_discovery(body.decode(), "search").encode()
        elif path.endswith("sitemap.xml"):
            body = recruitment_policy.public_discovery(body.decode(), "sitemap").encode()
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return True

    def _has_header(self, name):
        prefix = f"{name.lower()}:".encode("ascii")
        return any(
            header.lower().startswith(prefix)
            for header in getattr(self, "_headers_buffer", [])
        )

    def _cache_control_for_path(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        if path.startswith("/api/") or path in ("/health", "/healthz"):
            return None
        if path in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
            return "public, max-age=300, must-revalidate"
        if path in {"/assets/search-index.json", "/assets/intake-security.js"}:
            return "public, max-age=0, must-revalidate"
        if path.startswith("/assets/"):
            # Immutable URLs must change when their bytes change. Shared CSS/JS
            # uses ?v=...; generated images/fonts use a hash in the filename.
            # Plain filenames can be replaced on deploy, so give them a short
            # reusable lifetime instead of making old versions stick for a year.
            versioned = bool(parse_qs(parsed.query).get("v", [""])[0])
            fingerprinted = bool(re.search(
                r"-[a-f0-9]{10,}(?:-\d+)?\.[a-z0-9]+$", path, re.IGNORECASE
            ))
            if versioned or fingerprinted:
                return "public, max-age=31536000, immutable"
            return "public, max-age=3600, must-revalidate"
        if path.endswith(".html") or not os.path.splitext(path)[1]:
            return "public, max-age=0, must-revalidate"
        return "public, max-age=300"

    def _is_internal_artifact(self):
        """Keep workspace-only material out of the public static server.

        Noindex is insufficient here: it still sends the draft to the caller.
        Match decoded paths so percent-encoded requests cannot bypass this rule.
        """
        raw_path = unquote(urlsplit(self.path).path).lower()
        path = "/" + posixpath.normpath(raw_path).lstrip("/")
        parts = raw_path.split("/")
        return (
            path.endswith((".md", ".py"))
            or path.startswith(("/assets/social/", "/assets/img/amethyst-tmp/"))
            or path in ("/assets/social", "/assets/img/amethyst-tmp")
            or any(part.startswith(".") for part in parts[1:] if part != ".well-known")
            or (path.startswith("/assets/") and (
                parts[-1].startswith("test-")
                or parts[-1] in ("build-search-index.js", "update-sitemap-dates.js")
            ))
        )

    def list_directory(self, path):
        # Directory indexes reveal unlinked draft and QA file names.
        self.send_error(404)
        return None

    def send_head(self):
        """Serve compressible static responses with a smaller wire payload.

        Conditional and range requests stay on the stdlib implementation so
        Last-Modified and byte-range semantics remain intact.
        """
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            for index_name in ("index.html", "index.htm"):
                index_path = os.path.join(path, index_name)
                if os.path.isfile(index_path):
                    path = index_path
                    break
        if os.path.dirname(os.path.realpath(path)) == os.path.join(ROOT, "blog") and path.endswith(".html"):
            slug = os.path.basename(path)[:-5]
            record = self._released_journal().get(slug)
            if record is None:
                self.send_error(404)
                return None
            from internal_links import render_links
            # Approved snapshots include the reviewed contextual links. Never
            # inject new article links into a version after its approval.
            body = record["html"].encode()
            body = self._hide_unreleased_links(body.decode(), "/blog/" + slug).encode()
            body = footer_contact.public_html(form_antispam.refresh_assets(recruitment_policy.public_html(body.decode()))).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
            self.send_header("X-Journal-Revision", record["revision"])
            self.end_headers()
            return io.BytesIO(body)
        if path.endswith(".html") and os.path.isfile(path):
            from internal_links import inventory, render_links
            route = urlsplit(self.path).path.rstrip("/") or "/"
            if route.endswith(".html"):
                route = route[:-5]
            if route == "/index":
                route = "/"
            if route in inventory(self._journal_today()):
                with open(path, encoding="utf-8") as source:
                    body = render_links(source.read(), route, self._journal_today(),
                                        pages=self._journal_pages()).encode()
                    body = self._hide_unreleased_links(body.decode(), route).encode()
                    body = footer_contact.public_html(form_antispam.refresh_assets(recruitment_policy.public_html(body.decode()))).encode()
                compressed = "gzip" in (self.headers.get("Accept-Encoding") or "").lower()
                if compressed:
                    body = gzip.compress(body, mtime=0)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
                self.send_header("Vary", "Accept-Encoding")
                if compressed:
                    self.send_header("Content-Encoding", "gzip")
                self.end_headers()
                return io.BytesIO(body)
        # Include pages without contextual-link inventory (such as referral tools).
        if os.path.isfile(path) and (path.endswith(".html") or path.endswith("llms.txt")):
            with open(path, encoding="utf-8") as source:
                text = source.read()
            text = (footer_contact.public_html(form_antispam.refresh_assets(recruitment_policy.public_html(text))) if path.endswith(".html")
                    else recruitment_policy.public_discovery(text, "llms"))
            body = text.encode()
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
            self.end_headers()
            return io.BytesIO(body)
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

    def send_response(self, code, message=None):
        self._response_status = code
        super().send_response(code, message)

    def end_headers(self):
        if not self._has_header("Cache-Control"):
            cache_control = (
                "no-store" if getattr(self, "_response_status", 200) >= 400
                else self._cache_control_for_path()
            )
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
                "https://tags.tiqcdn.com "
                "https://s.ksrndkehqnwntyxlhgto.com "
                "https://tracker.metricool.com https://cdn.userway.org; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
                "https://cdn.userway.org; "
                "font-src 'self' https://fonts.gstatic.com data: "
                "https://cdn.userway.org; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://i.replit.com https://www.google-analytics.com "
                "https://region1.google-analytics.com https://www.clarity.ms "
                "https://in.clarity.ms https://cdn.brevo.com https://api.brevo.com "
                "https://stats.g.doubleclick.net https://www.google.com "
                "https://s.ksrndkehqnwntyxlhgto.com "
                "https://p.ksrndkehqnwntyxlhgto.com "
                "https://process.iconnode.com https://cdn.userway.org "
                "https://widget.userway.org https://api.userway.org "
                "https://tracker.metricool.com https://tags.tiqcdn.com; "
                "media-src 'self'; frame-src https://cdn.userway.org https://challenges.cloudflare.com; "
                "frame-ancestors 'self'; form-action 'self';"
            ),
        }
        if urlsplit(self.path).path.startswith("/studio"):
            # Clerk's development FAPI and CAPTCHA; production JS/API uses
            # the same-origin managed proxy. No change to intake-page policy.
            policy = security_headers.get("Content-Security-Policy", "")
            policy = policy.replace("script-src 'self'", "script-src 'self' https://*.clerk.accounts.dev https://challenges.cloudflare.com")
            policy = policy.replace("connect-src 'self'", "connect-src 'self' https://*.clerk.accounts.dev https://clerk-telemetry.com")
            policy = policy.replace("frame-src 'self'", "frame-src 'self' https://challenges.cloudflare.com")
            policy += "; worker-src 'self' blob:"
            security_headers["Content-Security-Policy"] = policy
        policy = security_headers["Content-Security-Policy"]
        for directive in ("script-src 'self'", "connect-src 'self'"):
            policy = policy.replace(directive, directive + " https://challenges.cloudflare.com")
        security_headers["Content-Security-Policy"] = policy
        for name, value in security_headers.items():
            if not self._has_header(name):
                self.send_header(name, value)
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

    def _withdrawn_recruitment(self):
        if not recruitment_policy.withdrawn(self.path):
            return False
        # Let crawlers see 404 rather than blocking robots and hiding the status.
        # The original files are retained for a future, explicitly approved restore.
        body = (b'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                b'<meta name="robots" content="noindex, nofollow"><title>Page unavailable</title>'
                b'</head><body><h1>This page is unavailable</h1>'
                b'<p><a href="/">Return to Eternal Life Hospice</a></p></body></html>')
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return True

    def do_HEAD(self):
        if self._withdrawn_recruitment():
            return
        if self._studio_api():
            return
        parsed = urlsplit(self.path)
        if self._is_internal_artifact():
            self.send_error(404)
            return
        if parsed.path in ("/health", "/healthz"):
            self._send_health(head_only=True)
            return
        if self._send_canonical_redirect(parsed):
            return
        if self._future_journal_path(parsed.path):
            self.send_error(404)
            return
        if parsed.path in ("/blog", "/blog/", "/blog.html"):
            self._send_journal_artifact(os.path.join(ROOT, "blog.html"))
            return
        if parsed.path in ("/resources", "/resources/", "/resources.html"):
            self._send_journal_artifact(os.path.join(ROOT, "resources.html"))
            return
        if parsed.path in ("/assets/search-index.json", "/sitemap.xml"):
            self._send_journal_artifact(os.path.join(ROOT, parsed.path.lstrip("/")))
            return
        super().do_HEAD()

    def do_GET(self):
        if self._withdrawn_recruitment():
            return
        if self._studio_api():
            return
        parsed = urlsplit(self.path)
        if self._is_internal_artifact():
            self.send_error(404)
            return
        if parsed.path in ("/health", "/healthz"):
            self._send_health()
            return
        if self._send_canonical_redirect(parsed):
            return
        if self._future_journal_path(parsed.path):
            self.send_error(404)
            return
        if parsed.path in ("/blog", "/blog/", "/blog.html"):
            self._send_journal_artifact(os.path.join(ROOT, "blog.html"))
            return
        if parsed.path in ("/resources", "/resources/", "/resources.html"):
            self._send_journal_artifact(os.path.join(ROOT, "resources.html"))
            return
        if parsed.path in ("/assets/search-index.json", "/sitemap.xml"):
            self._send_journal_artifact(os.path.join(ROOT, parsed.path.lstrip("/")))
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
        if parsed.path == "/api/form-security":
            try:
                if not self._is_same_origin():
                    raise IntakeError("invalid_origin", "Open this form from the Eternal website.", 403)
                if not FORM_CLIENT_RATE_LIMITER.allow("challenge:" + self._client_key()):
                    raise IntakeError("rate_limited", "Please wait or call 805.953.7273.", 429)
                form_name = parse_qs(parsed.query).get("form", [""])[0]
                self._send_json(200, form_antispam.issue(form_name, self._client_key()))
            except IntakeError as exc:
                if exc.code == "security_unavailable":
                    print("FORM_SECURITY_UNAVAILABLE", file=sys.stderr)
                self._send_json(exc.status, json_response_payload(False, error=exc.code, message=exc.message))
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
                            "Google reviews are unavailable while the Eternal Life Hospice "
                            "profile is being verified."
                        ),
                    },
                )
            return
        growth_sources = {
            "/canvas-hub/dashboard/api/elh-reporting": "google",
            "/canvas-hub/dashboard/api/whatconverts-reporting": "whatconverts",
            "/canvas-hub/dashboard/api/brevo-reporting": "brevo",
        }
        if parsed.path in growth_sources:
            # These reports belong to the workspace dashboard, never the public
            # deployment. Deny before invoking providers or reading report data.
            if is_production_deployment():
                self.send_error(404)
                return
            try:
                period = parse_qs(parsed.query).get("period", ["last28"])[0]
                completed = subprocess.run(
                    [
                        "node",
                        GROWTH_INTELLIGENCE_REPORTER,
                        growth_sources[parsed.path],
                        period,
                    ],
                    cwd=os.path.dirname(BASE),
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=False,
                )
                payload = json.loads(completed.stdout)
                self._send_json(
                    200 if completed.returncode == 0 else 503,
                    payload,
                    cache_control="private, max-age=300",
                )
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                self._send_json(
                    503,
                    {
                        "live": False,
                        "errors": [
                            f"Growth Intelligence reporting unavailable: {error}"
                        ],
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
        if self._withdrawn_recruitment():
            return
        if self._studio_api():
            return
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
        reservation = None
        try:
            fields, files = parse_form_body(
                self.headers.get("Content-Type", ""), body
            )
            if recruitment_policy.RECRUITMENT_PAUSED and fields.get("form-name") == "elh-careers":
                self._send_json(410, json_response_payload(
                    False, error="recruitment_paused",
                    message="Recruitment submissions are not available on this website."
                ))
                return
            if not fields.get("bot-field", "").strip():
                # Validation precedes reservations so invalid fields cannot
                # consume a legitimate family's duplicate-submission slot.
                from form_intake import validate_submission
                validate_submission(fields, files)
                hostname = urlsplit("https://" + self.headers.get("Host", "")).hostname or ""
                try:
                    reservation = form_antispam.reserve(fields, self._client_key(), hostname)
                except IntakeError:
                    raise
                except Exception:
                    print("FORM_SECURITY_UNAVAILABLE", file=sys.stderr)
                    raise IntakeError("security_unavailable", form_antispam.SAFE_MESSAGE, 503) from None
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
            if exc.code == "security_unavailable":
                print("FORM_SECURITY_UNAVAILABLE", file=sys.stderr)
            else:
                print(f"FORM_BLOCKED reason={exc.code}", file=sys.stderr)
            self._send_json(
                exc.status,
                json_response_payload(
                    False, error=exc.code, message=exc.message
                ),
            )
        except DeliveryError:
            try:
                form_antispam.release_failed(reservation)
            except Exception:
                print("FORM_GUARD_RETRY_CLEANUP_FAILED", file=sys.stderr)
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
        if studio_site.proxy(self):
            return
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
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_PATCH(self):
        if not studio_site.proxy(self):
            self._send_json(405, {"message": "Method not allowed"})

    def do_DELETE(self):
        if not studio_site.proxy(self):
            self._send_json(405, {"message": "Method not allowed"})


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
