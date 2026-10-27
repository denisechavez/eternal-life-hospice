"""Workspace-only display of verified, already-public Journal releases.

Never imports a decision, writes approval records or runs network requests at
server startup. The explicitly refreshed cache is excluded from publishing.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

CACHE = Path(__file__).resolve().parent.parent / ".local/journal-preview/published.json"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
REVISION = re.compile(r"[a-f0-9]{64}")


def validate_row(slug, row):
    if (not isinstance(slug, str) or not SLUG.fullmatch(slug)
            or not isinstance(row, dict)
            or not REVISION.fullmatch(row.get("revision", ""))
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("date", ""))
            or not isinstance(row.get("html"), str)
            or row.get("displayDigest") != hashlib.sha256(row["html"].encode()).hexdigest()):
        raise ValueError("Invalid published Journal preview record")


def overlay(records):
    """Display public snapshots only in workspace; no production fallback."""
    if os.environ.get("REPLIT_DEPLOYMENT") == "1" or not CACHE.exists():
        return records
    data = json.loads(CACHE.read_text())
    if data.get("kind") != "published-journal-display-only":
        raise ValueError("Invalid Journal preview cache")
    public = data["articles"]
    for slug, row in public.items():
        validate_row(slug, row)
    return {**records, **{
        slug: {key: row[key] for key in ("revision", "date", "html")}
        for slug, row in public.items()
    }}


def fetch(origin, path):
    with urlopen(Request(origin + path, headers={
        "User-Agent": "ELH-Workspace-Published-Preview/1.0",
        "Accept": "application/json" if path.startswith("/api/") else "text/html",
    }), timeout=30) as response:
        if urlsplit(response.url).netloc != urlsplit(origin).netloc:
            raise ValueError("Published preview request left the verified origin")
        return response.read().decode(), response.headers.get("X-Journal-Revision")


def synchronize(origin):
    if os.environ.get("REPLIT_DEPLOYMENT") == "1":
        raise RuntimeError("Journal preview refresh is workspace-only")
    url = urlsplit(origin)
    if url.scheme != "https" or not url.netloc or url.path not in ("", "/") or url.query or url.fragment:
        raise ValueError("Provide the verified HTTPS published origin")
    origin = origin.rstrip("/")
    status = json.loads(fetch(origin, "/api/journal-release-status")[0])
    rows = [row for row in status["expected"] if row.get("available") is True]

    def download(row):
        slug = row["slug"]
        if not SLUG.fullmatch(slug) or not REVISION.fullmatch(row["revision"]):
            raise ValueError("Invalid public release metadata")
        # Explicit file routes avoid stale negative caches on pretty URLs.
        # The response still has to prove its exact public release revision.
        document, revision = fetch(origin, "/blog/" + slug + ".html")
        if revision != row["revision"]:
            raise ValueError("Published article changed during preview refresh: " + slug)
        # Frozen photographs are publicly served from the live release store.
        # The workspace must not substitute an unapproved local photo or depend
        # on copies of the production database.
        document = re.sub(
            r'(?<![A-Za-z0-9:/.-])(/api/journal-photo/[a-f0-9]{64})',
            lambda match: origin + match.group(1), document,
        )
        record = {"revision": revision, "date": row["date"], "html": document,
                  "displayDigest": hashlib.sha256(document.encode()).hexdigest()}
        validate_row(slug, record)
        return slug, record

    with ThreadPoolExecutor(max_workers=4) as workers:
        articles = dict(workers.map(download, rows))
    if not articles:
        raise ValueError("No verified public releases available; existing preview retained")
    data = {"kind": "published-journal-display-only", "sourceOrigin": origin,
            "fetchedAt": datetime.now(timezone.utc).isoformat(), "articles": articles}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    temporary.replace(CACHE)
    return len(articles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Verified published origin from deployment metadata")
    args = parser.parse_args()
    print(f"Refreshed {synchronize(args.origin)} public releases for workspace display only.")
