"""Validate existing Clerk browser sessions and explicit reviewer authority."""
import base64
import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from http.cookies import SimpleCookie
from urllib.request import Request, urlopen

REVIEWER_EMAILS = frozenset({
    "aleksandra@eternallifehospice.com",
    "denise@eternallifehospice.com",
})


def allowed_origins():
    origins = {"https://eternallifehospice.com", "https://eternal-life-hospice.replit.app"}
    domain = os.environ.get("REPLIT_DEV_DOMAIN")
    if domain and os.environ.get("REPLIT_DEPLOYMENT") != "1":
        origins.add("https://" + domain)
    return origins


@lru_cache(maxsize=2)
def verifier(key):
    import jwt
    # The configured key, not untrusted token claims, supplies the issuer.
    encoded = key.split("_", 2)[2]
    host = base64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode().rstrip("$")
    issuer = "https://" + host
    return issuer, jwt.PyJWKClient(issuer + "/.well-known/jwks.json", timeout=5)


@dataclass(frozen=True)
class ReviewerIdentity:
    user_id: str
    display_name: str | None = None


def reviewer(headers):
    return reviewer_identity(headers).user_id


def reviewer_identity(headers):
    """Authorize and snapshot identity from the same verified Clerk response."""
    import jwt
    cookies = SimpleCookie()
    cookies.load(headers.get("Cookie", ""))
    token = cookies.get("__session")
    if not token:
        raise PermissionError("Sign in to Studio to review Journal releases.")
    stage = "verify_token"
    try:
        issuer, client = verifier(os.environ["CLERK_PUBLISHABLE_KEY"])
        claims = jwt.decode(token.value, client.get_signing_key_from_jwt(token.value).key,
                            algorithms=["RS256"], issuer=issuer,
                            options={"require": ["exp", "iat", "nbf", "sub", "sid", "azp"],
                                     "verify_aud": False}, leeway=5)
        if claims["azp"] not in allowed_origins():
            raise PermissionError("Studio session origin is not authorized")
        secret = os.environ["CLERK_SECRET_KEY"]
        # Check revocation and reviewer email against Clerk, never UI claims.
        def clerk(path):
            request = Request("https://api.clerk.com/v1/" + path,
                              headers={"Authorization": "Bearer " + secret,
                                       "Accept": "application/json",
                                       "User-Agent": "Eternal-Studio/1.0"})
            with urlopen(request, timeout=5) as response:
                return json.load(response)
        stage = "lookup_session"
        session = clerk("sessions/" + claims["sid"])
        if session.get("status") != "active" or session.get("user_id") != claims["sub"]:
            raise PermissionError("Studio session is no longer active")
        stage = "lookup_user"
        user = clerk("users/" + claims["sub"])
        if user.get("id") != claims["sub"]:
            raise PermissionError("Studio account identity does not match the session")
        if not any(e.get("email_address", "").lower() in REVIEWER_EMAILS
                   and e.get("verification", {}).get("status") == "verified"
                   for e in user.get("email_addresses", [])):
            raise PermissionError("Only authorized Journal reviewers can approve releases. Sign in with Denise's or Aleksandra's verified account.")
        return ReviewerIdentity(claims["sub"], display_name(user))
    except PermissionError:
        raise
    except Exception as error:
        # No tokens, addresses, keys or raw exception messages in diagnostics.
        logging.getLogger(__name__).warning(
            "Studio verification failed stage=%s kind=%s status=%s",
            stage, type(error).__name__, getattr(error, "code", "-"))
        raise PermissionError("Studio session could not be verified.") from None


def display_name(user):
    """Names only, never substitute an email address or account ID."""
    name = " ".join(part.strip() for part in (user.get("first_name"), user.get("last_name"))
                    if isinstance(part, str) and part.strip())
    return name or None

@lru_cache(maxsize=128)
def _reviewer_label(user_id, window):
    """Resolve a recorded identity, never guess a signer from the allowlist."""
    request = Request("https://api.clerk.com/v1/users/" + user_id,
                      headers={"Authorization": "Bearer " + os.environ["CLERK_SECRET_KEY"],
                               "Accept": "application/json", "User-Agent": "Eternal-Studio/1.0"})
    with urlopen(request, timeout=5) as response:
        user = json.load(response)
    if user.get("id") != user_id:
        raise ValueError("Account identity mismatch")
    return display_name(user) or user_id

def reviewer_label(user_id):
    """A current directory label is optional; the stored ID is authoritative."""
    import re
    import time
    if not re.fullmatch(r"user_[A-Za-z0-9]+", user_id):
        return user_id
    try:
        return _reviewer_label(user_id, int(time.monotonic() // 300))
    except Exception:
        return user_id
