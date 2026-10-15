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
            ALTER TABLE journal_review_audit ADD COLUMN IF NOT EXISTS reviewer_name text;
            ALTER TABLE journal_decisions ADD COLUMN IF NOT EXISTS reviewer_name text;
            CREATE INDEX IF NOT EXISTS journal_audit_article_page
                ON journal_review_audit (slug, occurred_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS journal_audit_saved_decision
                ON journal_review_audit (slug, revision, reviewer, occurred_at);
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
            WHERE journal_releases.revision <> EXCLUDED.revision
                AND journal_releases.released_at < EXCLUDED.released_at
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


def decide(slug, expected_revision, action, reviewer, *, reviewer_name=None, only_if_undecided=False, expected_date=None, release_immediately=False):
    if action not in {"approve", "hold"}:
        raise ValueError("Choose approve or hold")
    if release_immediately and (action != "approve" or not only_if_undecided):
        raise ValueError("Immediate publication requires a single-use owner instruction")
    instant = now()
    with connect() as db:
        materialize(db, instant)
        # Startup owner instructions must never replay over a later Studio
        # approval or hold. Share the decision lock, including across instances.
        if only_if_undecided and db.execute("""
            SELECT 1 FROM journal_decisions WHERE slug=%s
            UNION ALL SELECT 1 FROM journal_review_audit WHERE slug=%s LIMIT 1
        """, (slug, slug)).fetchone():
            return False
        record = candidates().get(slug)
        if not record or record["revision"] != expected_revision or (expected_date and record["date"] != expected_date):
            raise ValueError("Article changed. Reload and review the complete current version.")
        frozen = freeze_photos(db, record["html"]) if action == "approve" else record["html"]
        db.execute("""
            INSERT INTO journal_decisions (slug,revision,release_date,document,state,reviewer,decided_at,reviewer_name)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (slug,revision) DO UPDATE SET state=EXCLUDED.state,
                reviewer=EXCLUDED.reviewer, decided_at=EXCLUDED.decided_at,
                reviewer_name=EXCLUDED.reviewer_name
        """, (slug, record["revision"], record["date"], frozen,
              "approved" if action == "approve" else "held", reviewer, instant, reviewer_name))
        db.execute("INSERT INTO journal_review_audit (slug,revision,action,reviewer,occurred_at,environment,reviewer_name) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                   (slug, record["revision"], action, reviewer, instant, environment(), reviewer_name))
        if release_immediately:
            db.execute("""
                INSERT INTO journal_releases (slug,revision,document,release_date,released_at)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (slug, record["revision"], frozen, record["date"], instant))
        materialize(db, instant)
    return True

def publication_metadata(db, slug, instant, original=None):
    """Project materialize's version choice without writes, locks or document IO.

    Due approvals count even before the next public request persists them.
    Existing releases win equal timestamps (including early owner releases).
    The caller supplies a consistent snapshot of releases and decisions.
    """
    saved = db.execute("""
        SELECT revision,release_date,released_at FROM journal_releases WHERE slug=%s
    """, (slug,)).fetchone()
    rows = db.execute("""
        SELECT revision,release_date,decided_at FROM journal_decisions
        WHERE slug=%s AND state='approved' ORDER BY decided_at
    """, (slug,)).fetchall()
    for row in rows:
        due = release_at(row["release_date"].isoformat())
        if due > instant:
            continue
        effective = max(row["decided_at"], due)
        if saved is None or (saved["revision"] != row["revision"] and saved["released_at"] < effective):
            saved = {**row, "released_at": effective}
    if saved:
        return {"revision": saved["revision"], "date": saved["release_date"].isoformat()}
    return {"revision": original["revision"], "date": original["date"]} if original else None
def article_history(slug, limit=25, cursor=None):
    """Private, bounded keyset pages. Saved legacy states are not audit events."""
    from studio_auth import reviewer_label
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Invalid article")
    try:
        limit = int(limit)
        if not 1 <= limit <= 100:
            raise ValueError()
        boundary = None
        if cursor:
            if len(cursor) > 2048:
                raise ValueError()
            saved = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            if saved["slug"] != slug or not re.fullmatch(r"\d+", saved["id"]):
                raise ValueError()
            stamp = datetime.fromisoformat(saved["at"])
            if stamp.tzinfo is None or not isinstance(saved["revision"], str):
                raise ValueError()
            boundary = (stamp, int(saved["id"]), saved["revision"])
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError) as exc:
        raise ValueError("Invalid history page") from exc
    original = history().get(slug)
    if slug not in candidates() and original is None:
        raise LookupError("Article not found")
    with connect() as db:
        # One committed view while publication/decisions continue independently.
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        live = publication_metadata(db, slug, now(), original)
        # Bound both branches before merging: no full audit history in Python.
        audit_where = "AND (occurred_at,id) < (%s,%s)" if boundary else ""
        audits = db.execute(f"""
            SELECT id,revision,action,reviewer,reviewer_name,occurred_at,environment,'audit' AS source
            FROM journal_review_audit WHERE slug=%s {audit_where}
            ORDER BY occurred_at DESC,id DESC LIMIT %s
        """, (slug, *(boundary[:2] if boundary else ()), limit + 1)).fetchall()
        decision_where = 'AND (d.decided_at,0::bigint,d.revision COLLATE "C") < (%s,%s,%s)' if boundary else ""
        legacy = db.execute(f"""
            SELECT 0::bigint AS id,d.revision,
                CASE WHEN d.state='approved' THEN 'approve' ELSE 'hold' END AS action,
                d.reviewer,d.reviewer_name,d.decided_at AS occurred_at,NULL::text AS environment,
                'saved-decision' AS source
            FROM journal_decisions d WHERE d.slug=%s {decision_where}
                AND NOT EXISTS (
                    SELECT 1 FROM journal_review_audit a WHERE a.slug=d.slug
                    AND a.revision=d.revision AND a.reviewer=d.reviewer
                    AND a.occurred_at=d.decided_at)
            ORDER BY d.decided_at DESC,d.revision COLLATE "C" DESC LIMIT %s
        """, (slug, *(boundary if boundary else ()), limit + 1)).fetchall()
        original_recorded = original and db.execute("""
            SELECT EXISTS(SELECT 1 FROM journal_review_audit WHERE slug=%s AND revision=%s)
                OR EXISTS(SELECT 1 FROM journal_decisions WHERE slug=%s AND revision=%s) AS recorded
        """, (slug, original["revision"], slug, original["revision"])).fetchone()["recorded"]
    rows = sorted(audits + legacy,
                  key=lambda row: (row["occurred_at"], row["id"], row["revision"]), reverse=True)
    more = len(rows) > limit
    rows = rows[:limit]
    labels = {identity: reviewer_label(identity) for identity in {row["reviewer"] for row in rows}}
    events = []
    for row in rows:
        events.append({
            "id": str(row["id"]) if row["source"] == "audit" else "saved:" + row["revision"],
            "revision": row["revision"], "action": row["action"],
            "reviewerId": row["reviewer"], "reviewerLabel": labels[row["reviewer"]],
            "reviewerNameSnapshot": row["reviewer_name"],
            "occurredAt": row["occurred_at"].isoformat(),
            "environment": row["environment"], "source": row["source"],
        })
    next_cursor = None
    if more:
        last = rows[-1]
        next_cursor = base64.urlsafe_b64encode(json.dumps({
            "slug": slug, "at": last["occurred_at"].isoformat(),
            "id": str(last["id"]), "revision": last["revision"],
        }).encode()).decode().rstrip("=")
    return {
        "recordEnvironment": environment(),
        "publishedVersion": live,
        "preStudioVersion": {"revision": original["revision"], "date": original["date"]}
            if original and not original_recorded else None,
        "events": events, "nextCursor": next_cursor,
    }


def review_items():
    published, healthy = released()
    if not healthy:
        raise RuntimeError("Journal approval storage unavailable")
    with connect() as db:
        decisions = {(r["slug"], r["revision"]): r for r in db.execute(
            "SELECT slug,revision,state FROM journal_decisions").fetchall()}
    results = []
    for slug, record in candidates().items():
        decision = decisions.get((slug, record["revision"]))
        live = published.get(slug)
        status = "Published" if live and live["revision"] == record["revision"] else (
            "Approved" if decision and decision["state"] == "approved" else "Needs review")
        results.append({**record, "status": status, "held": bool(decision and decision["state"] == "held"),
                        "releaseAt": release_at(record["date"]).isoformat(),
                        "hasPublishedVersion": bool(live)})
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
