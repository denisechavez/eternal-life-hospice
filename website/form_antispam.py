"""Intake abuse controls. Persist only keyed digests and short-lived counters."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import Request, urlopen

from form_intake import FORM_RULES, IntakeError, notify_security_failure
from journal_release import connect
from website_phone import public_text

MIN_AGE_SECONDS = 1.8
TOKEN_TTL_SECONDS = 1800
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
SAFE_MESSAGE = "We could not verify this submission. Please retry or call 805.953.7273."
ASSETS = Path(__file__).parent / "elh-preview/assets"
SECURITY_VERSION = hashlib.sha256(public_text((ASSETS / "intake-security.js").read_bytes().decode()).encode()).hexdigest()[:12]
CHAT_VERSION = hashlib.sha256(
    public_text((ASSETS / "chat.js").read_bytes().decode()).encode() + SECURITY_VERSION.encode()
).hexdigest()[:12]


def unavailable(status):
    notify_security_failure(status)
    return IntakeError("security_unavailable", SAFE_MESSAGE, 503)


@contextmanager
def guard_database():
    """Report connection, query and commit failures, but never rejected spam."""
    try:
        with connect() as db:
            yield db
    except IntakeError:
        raise
    except Exception:
        raise unavailable("guard_storage_unavailable") from None


def refresh_assets(document):
    """Retired immutable chat URLs must not keep posting without protection."""
    document = re.sub(r'(["\'])/assets/intake-security\.js(?:\?[^"\']*)?',
                      lambda match: match[1] + "/assets/intake-security.js?v=" + SECURITY_VERSION, document)
    return re.sub(r'(\bsrc=["\'])/assets/chat\.js(?:\?[^"\']*)?',
                  lambda match: match[1] + "/assets/chat.js?v=" + CHAT_VERSION, document)


def initialize():
    with connect() as db:
        # Serialize additive schema setup across concurrent cold starts.
        db.execute("SELECT pg_advisory_xact_lock(630631)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS intake_abuse_guard (
                key text PRIMARY KEY, expires_at timestamptz NOT NULL,
                attempts integer NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS intake_abuse_guard_expiry ON intake_abuse_guard(expires_at);
        """)


def digest(value):
    key = os.environ.get("SESSION_SECRET", "")
    if len(key) < 32:
        raise unavailable("guard_configuration_unavailable")
    return hmac.new(key.encode(), ("elh-intake-v1:" + value).encode(), hashlib.sha256).hexdigest()


def turnstile_configuration():
    site = os.environ.get("TURNSTILE_SITE_KEY", "").strip()
    secret = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()
    if bool(site) != bool(secret):
        raise unavailable("turnstile_unavailable")
    return site, secret


def valid_browser_proof(proof):
    return isinstance(proof, str) and re.fullmatch(r"[a-f0-9]{64}", proof) is not None


def issue(form_name, browser_proof):
    if form_name not in FORM_RULES:
        raise IntakeError("unknown_form", "This form is not available.", 400)
    if not valid_browser_proof(browser_proof):
        raise IntakeError("verification_required", SAFE_MESSAGE, 403)
    site, _ = turnstile_configuration()
    # A fresh, in-memory browser proof binds this attempt, not the proxy's
    # changing address. The raw proof is never put in URLs, tokens or storage.
    payload = {"v": 2, "form": form_name, "client": digest("browser-proof:" + browser_proof),
               "at": time.time(), "nonce": secrets.token_hex(16)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return {"token": encoded + "." + digest("token:" + encoded),
            "siteKey": site, "waitMs": int(MIN_AGE_SECONDS * 1000)}


def verify_turnstile(token, hostname):
    site, secret = turnstile_configuration()
    if not site:
        return
    if not token or len(token) > 2048:
        raise IntakeError("bot_verification_required", SAFE_MESSAGE, 403)
    request = Request(VERIFY_URL, method="POST",
                      data=json.dumps({"secret": secret, "response": token}).encode(),
                      headers={"Content-Type": "application/json", "User-Agent": "ELH-Intake/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            result = json.loads(response.read(16384))
        # Malformed provider responses are service failures, not evidence of spam.
        if not isinstance(result, dict) or type(result.get("success")) is not bool:
            raise ValueError()
        if result["success"] and (
            not isinstance(result.get("hostname"), str)
            or not isinstance(result.get("action"), str)
        ):
            raise ValueError()
        errors = result.get("error-codes", [])
        if not isinstance(errors, list) or any(not isinstance(code, str) for code in errors):
            raise ValueError()
    except Exception:
        raise unavailable("turnstile_unavailable") from None
    if not result["success"] and set(errors) & {
        "internal-error", "missing-input-secret", "invalid-input-secret", "bad-request",
    }:
        raise unavailable("turnstile_unavailable")
    if result.get("success") is not True or result.get("hostname", "").lower() != hostname.lower() or result.get("action") != "intake":
        raise IntakeError("bot_verification_failed", SAFE_MESSAGE, 403)


def reserve(fields, client, hostname):
    token = fields.get("_elh_security", "")
    proof = fields.get("_elh_browser_proof", "")
    if not token or len(token) > 1500 or not valid_browser_proof(proof):
        raise IntakeError("verification_required", SAFE_MESSAGE, 403)
    try:
        encoded, signature = token.split(".")
        if not hmac.compare_digest(signature, digest("token:" + encoded)):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        age = time.time() - payload["at"]
        if not MIN_AGE_SECONDS <= age <= TOKEN_TTL_SECONDS:
            raise ValueError()
        if (payload.get("v") != 2 or payload["form"] != fields.get("form-name")
                or not hmac.compare_digest(payload["client"], digest("browser-proof:" + proof))):
            raise ValueError()
        nonce = digest("used:" + payload["nonce"])
    except IntakeError:
        raise
    except Exception:
        raise IntakeError("verification_invalid", SAFE_MESSAGE, 403) from None
    verify_turnstile(fields.get("cf-turnstile-response", ""), hostname)
    # Do not retain phone numbers, emails, names, messages or raw IP addresses.
    names = ("form-name", "phone", "email", "first_name", "last_name", "name",
             "referrer_name", "message", "situation", "needs")
    fingerprint = digest("duplicate:" + json.dumps(
        {name: " ".join(fields.get(name, "").lower().split()) for name in names},
        sort_keys=True))
    contact = re.sub(r"\D", "", fields.get("phone", ""))
    if len(contact) == 11 and contact.startswith("1"):
        contact = contact[1:]
    contacts = {contact} if contact else set()
    email = fields.get("email", "").strip().lower()
    if email:
        contacts.add(email)
    window = int(time.time() // 600)
    professional = fields.get("form-name") in {"elh-physician", "elh-casemanager", "elh-coordinator"}
    limits = [(digest(f"ip:{client}:{window}"), 10)]
    for contact in sorted(contacts):
        limits.append((digest(f"contact:{contact}:{window}"), 10 if professional else 3))
    with guard_database() as db:
        # Serialize a client's reservations across every Autoscale instance.
        db.execute("SELECT pg_advisory_xact_lock(%s)", (int(digest("lock:" + client)[:15], 16),))
        db.execute("""DELETE FROM intake_abuse_guard WHERE key IN
                      (SELECT key FROM intake_abuse_guard WHERE expires_at <= now() LIMIT 200)""")
        used = db.execute("""
            INSERT INTO intake_abuse_guard (key,expires_at) VALUES (%s,now()+interval '30 minutes')
            ON CONFLICT DO NOTHING RETURNING key
        """, ("nonce:" + nonce,)).fetchone()
        if not used:
            raise IntakeError("verification_reused", SAFE_MESSAGE, 403)
        for key, maximum in limits:
            counted = db.execute("""
                INSERT INTO intake_abuse_guard (key,expires_at) VALUES (%s,now()+interval '11 minutes')
                ON CONFLICT (key) DO UPDATE SET attempts=intake_abuse_guard.attempts+1
                WHERE intake_abuse_guard.attempts < %s RETURNING key
            """, ("rate:" + key, maximum)).fetchone()
            if not counted:
                raise IntakeError("submission_rate_limited", "Too many requests. Please call 805.953.7273 for help.", 429)
        duplicate = db.execute("""
            INSERT INTO intake_abuse_guard (key,expires_at) VALUES (%s,now()+interval '2 minutes')
            ON CONFLICT (key) DO UPDATE SET expires_at=EXCLUDED.expires_at,attempts=1
            WHERE intake_abuse_guard.expires_at <= now() RETURNING key
        """, ("duplicate:" + fingerprint,)).fetchone()
        if not duplicate:
            raise IntakeError("duplicate_submission", "This request was recently submitted. Please call 805.953.7273 if you need immediate help.", 429)
    return "duplicate:" + fingerprint


def release_failed(reservation):
    """Allow a fresh-token retry after a confirmed delivery failure."""
    if reservation:
        with guard_database() as db:
            db.execute("DELETE FROM intake_abuse_guard WHERE key=%s", (reservation,))
