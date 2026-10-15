"""Authoritative Journal versions. No browser state or date-only approvals."""
import base64
import hashlib
import json
import os
import re
import zlib
import mimetypes
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from journal_image_revisions import apply_image_revision

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / "elh-preview"
PACIFIC = ZoneInfo("America/Los_Angeles")
HISTORY = BASE / "content/journal-published-history.json"


def now():
    return datetime.now(timezone.utc)


def environment():
    return "production" if os.environ.get("REPLIT_DEPLOYMENT") == "1" else "workspace"


def release_at(day):
    return datetime.combine(datetime.fromisoformat(day).date(), time(6, 30), PACIFIC)


def unpack(record):
    return zlib.decompress(base64.b64decode(record["document"])).decode()


def history():
    return json.loads(HISTORY.read_text())["articles"]


def revision(document):
    """Include local photographs so replacing a photo needs fresh approval."""
    digest = hashlib.sha256(document.encode())
    assets = sorted(set(re.findall(r'(?:src=["\']|url\(["\']?)([^"\')\s]+)', document)))
    for asset in assets:
        if asset.startswith(("https:", "http:", "data:")):
            continue
        target = (PUBLIC / "blog" / asset.split("?")[0]).resolve() if not asset.startswith("/") else (PUBLIC / asset.lstrip("/").split("?")[0]).resolve()
        if target.is_relative_to(PUBLIC) and target.is_file() and target.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            digest.update(asset.encode())
            digest.update(target.read_bytes())
    return digest.hexdigest()


def freeze_photos(db, document):
    """Keep the reviewed photo bytes even if a source file later changes."""
    assets = sorted(set(re.findall(r'(?:src=["\']|url\(["\']?)([^"\')\s]+)', document)))
    for asset in assets:
        if asset.startswith(("https:", "http:", "data:")):
            continue
        target = (PUBLIC / "blog" / asset.split("?")[0]).resolve() if not asset.startswith("/") else (PUBLIC / asset.lstrip("/").split("?")[0]).resolve()
        if not target.is_relative_to(PUBLIC) or not target.is_file() or target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            continue
        body = target.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        url = "/api/journal-photo/" + digest
        db.execute("INSERT INTO journal_photos (digest,body,media_type) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                   (digest, body, mimetypes.guess_type(str(target))[0] or "application/octet-stream"))
        document = document.replace(asset, url)
    return document


def photo(digest):
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        return None
    with connect() as db:
        # Only released documents authorize public access, never held drafts.
        materialize(db, now())
        return db.execute("""
            SELECT body,media_type FROM journal_photos
            WHERE digest=%s AND EXISTS (
                SELECT 1 FROM journal_releases WHERE
                position(%s in document) > 0
            )
        """, (digest, "/api/journal-photo/" + digest)).fetchone()


def candidates():
    manifest = json.loads((BASE / "content/30-day-journal-manifest.json").read_text())
    drafts = json.loads((BASE / "content/seo-journal-review.json").read_text())["articles"]
    dates = {a["slug"]: a["date"] for a in manifest["articles"]}
    records = {}
    for path in sorted((PUBLIC / "blog").glob("*.html")):
        slug = path.stem
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            continue
        document = apply_image_revision(
            slug, drafts.get(slug, {}).get("reviewHtml") or path.read_text())
        if 'http-equiv="refresh"' in document or re.search(r'name="robots"[^>]*content="[^"]*noindex', document):
            continue
        match = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', document)
        day = dates.get(slug) or (match.group(1) if match else None)
        if not day:
            continue
        # Never accept dates or document bytes from the approval caller.
        release_at(day)
        title = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", document)
        records[slug] = {
            "slug": slug, "date": day, "revision": revision(document),
            "title": re.sub("<[^>]+>", "", title.group(1)) if title else slug,
            "html": document,
        }
    return records


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5, row_factory=dict_row)


def initialize():
    """Additive migration, explicitly run in development / at approved publish."""
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS journal_decisions (
                slug text NOT NULL, revision text NOT NULL, release_date date NOT NULL,
                document text NOT NULL, state text NOT NULL CHECK (state IN ('approved','held')),
                reviewer text NOT NULL, decided_at timestamptz NOT NULL,
                PRIMARY KEY (slug, revision)
            );
            CREATE TABLE IF NOT EXISTS journal_releases (
                slug text PRIMARY KEY, revision text NOT NULL, document text NOT NULL,
                release_date date NOT NULL, released_at timestamptz NOT NULL
            );
            CREATE TABLE IF NOT EXISTS journal_review_audit (
                id bigserial PRIMARY KEY, slug text NOT NULL, revision text NOT NULL,
                action text NOT NULL, reviewer text NOT NULL, occurred_at timestamptz NOT NULL
            );
            ALTER TABLE journal_review_audit ADD COLUMN IF NOT EXISTS environment text;
            CREATE TABLE IF NOT EXISTS journal_photos (
                digest text PRIMARY KEY, body bytea NOT NULL, media_type text NOT NULL
            );
        """)


def materialize(db, instant):
    """Transactionally retain every due approved version before a hold/edit."""
    db.execute("SELECT pg_advisory_xact_lock(630630)")
    rows = db.execute("SELECT * FROM journal_decisions WHERE state='approved' ORDER BY decided_at").fetchall()
    for row in rows:
        if release_at(row["release_date"].isoformat()) > instant:
            continue
        db.execute("""
            INSERT INTO journal_releases (slug,revision,document,release_date,released_at)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (slug) DO UPDATE SET revision=EXCLUDED.revision,
                document=EXCLUDED.document, release_date=EXCLUDED.release_date,
                released_at=EXCLUDED.released_at
            WHERE journal_releases.released_at < EXCLUDED.released_at
        """, (row["slug"], row["revision"], row["document"], row["release_date"],
              max(row["decided_at"], release_at(row["release_date"].isoformat()))))


def released(instant=None):
    instant = instant or now()
    records = {slug: {"revision": row["revision"], "html": unpack(row), "date": row["date"]}
               for slug, row in history().items()}
    try:
        with connect() as db:
            materialize(db, instant)
            rows = db.execute("SELECT * FROM journal_releases").fetchall()
        for row in rows:
            records[row["slug"]] = {"revision": row["revision"], "html": row["document"],
                                   "date": row["release_date"].isoformat()}
        return records, True
    except Exception:
        # Frozen published originals remain public during a storage outage.
        # New versions fail closed; monitoring reports storage unavailability.
        return records, False


def decide(slug, expected_revision, action, reviewer):
    if action not in {"approve", "hold"}:
        raise ValueError("Choose approve or hold")
    record = candidates().get(slug)
    if not record or record["revision"] != expected_revision:
        raise ValueError("Article changed. Reload and review the complete current version.")
    instant = now()
    with connect() as db:
        materialize(db, instant)
        frozen = freeze_photos(db, record["html"]) if action == "approve" else record["html"]
        db.execute("""
            INSERT INTO journal_decisions (slug,revision,release_date,document,state,reviewer,decided_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (slug,revision) DO UPDATE SET state=EXCLUDED.state,
                reviewer=EXCLUDED.reviewer, decided_at=EXCLUDED.decided_at
        """, (slug, record["revision"], record["date"], frozen,
              "approved" if action == "approve" else "held", reviewer, instant))
        db.execute("INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at,environment) VALUES (%s,%s,%s,%s,%s,%s)",
                   (slug, record["revision"], action, reviewer, instant, environment()))
        materialize(db, instant)


def approval_histories(decisions, audits, published):
    """Private metadata only. Never infer an event from a publication date."""
    from studio_auth import reviewer_label
    grouped = {}
    identities = {row["reviewer"] for row in audits} | {row["reviewer"] for row in decisions.values()}
    labels = {identity: reviewer_label(identity) for identity in identities}
    # The append-only audit preserves repeated actions on the same revision.
    for row in audits:
        grouped.setdefault(row["slug"], []).append({
            "revision": row["revision"], "action": row["action"],
            "reviewerId": row["reviewer"], "reviewerLabel": labels[row["reviewer"]],
            "occurredAt": row["occurred_at"].isoformat(),
            "environment": row.get("environment"), "source": "audit",
        })
    # Older decision rows may predate auditing. Show their saved state, not a
    # fabricated audit event, and do not duplicate an existing audit entry.
    for row in decisions.values():
        events = grouped.setdefault(row["slug"], [])
        if not any(e["revision"] == row["revision"] and e["reviewerId"] == row["reviewer"]
                   and e["occurredAt"] == row["decided_at"].isoformat() for e in events):
            events.append({
                "revision": row["revision"], "action": "approve" if row["state"] == "approved" else "hold",
                "reviewerId": row["reviewer"], "reviewerLabel": labels[row["reviewer"]],
                "occurredAt": row["decided_at"].isoformat(),
                "environment": None, "source": "saved-decision",
            })
    originals = history()
    result = {}
    for slug in set(grouped) | set(published) | set(originals):
        events = sorted(grouped.get(slug, []), key=lambda e: e["occurredAt"], reverse=True)
        original = originals.get(slug)
        pre_studio = original and not any(e["revision"] == original["revision"] for e in events)
        live = published.get(slug)
        result[slug] = {
            "recordEnvironment": environment(),
            "publishedVersion": {"revision": live["revision"], "date": live["date"]} if live else None,
            "preStudioVersion": {"revision": original["revision"], "date": original["date"]} if pre_studio else None,
            "events": events,
        }
    return result


def review_items():
    published, healthy = released()
    if not healthy:
        raise RuntimeError("Journal approval storage unavailable")
    with connect() as db:
        decisions = {(r["slug"], r["revision"]): r for r in db.execute("SELECT * FROM journal_decisions").fetchall()}
        audits = db.execute("SELECT * FROM journal_review_audit ORDER BY occurred_at DESC,id DESC").fetchall()
    histories = approval_histories(decisions, audits, published)
    results = []
    for slug, record in candidates().items():
        decision = decisions.get((slug, record["revision"]))
        live = published.get(slug)
        status = "Published" if live and live["revision"] == record["revision"] else (
            "Approved" if decision and decision["state"] == "approved" else "Needs review")
        results.append({**record, "status": status, "held": bool(decision and decision["state"] == "held"),
                        "releaseAt": release_at(record["date"]).isoformat(),
                        "hasPublishedVersion": bool(live),
                        "approvalHistory": histories.get(slug, {
                            "recordEnvironment": environment(), "publishedVersion": None,
                            "preStudioVersion": None, "events": []})})
    return results


def release_status():
    instant = now()
    published, healthy = released(instant)
    if not healthy:
        raise RuntimeError("Journal approval storage unavailable")
    with connect() as db:
        rows = db.execute("SELECT slug,revision,release_date,decided_at FROM journal_decisions WHERE state='approved'").fetchall()
    # Latest approved version per URL. Held drafts never enter the expected set.
    latest = {}
    for row in sorted(rows, key=lambda r: r["decided_at"]):
        if release_at(row["release_date"].isoformat()) <= instant:
            latest[row["slug"]] = row
    return {"checkedAt": instant.isoformat(), "timezone": "America/Los_Angeles",
            "releaseTime": "06:30",
            "expected": [{"slug": slug, "revision": row["revision"],
                          "date": row["release_date"].isoformat(),
                          "available": published.get(slug, {}).get("revision") == row["revision"]}
                         for slug, row in latest.items()]}
