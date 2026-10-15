"""Validate existing Clerk browser sessions and explicit reviewer authority."""
import base64
import json
import logging
import os
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


def reviewer(headers):
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
        if not any(e.get("email_address", "").lower() in REVIEWER_EMAILS
                   and e.get("verification", {}).get("status") == "verified"
                   for e in user.get("email_addresses", [])):
            raise PermissionError("Only authorized Journal reviewers can approve releases. Sign in with Denise's or Aleksandra's verified account.")
        return claims["sub"]
    except PermissionError:
        raise
    except Exception as error:
        # No tokens, addresses, keys or raw exception messages in diagnostics.
        logging.getLogger(__name__).warning(
            "Studio verification failed stage=%s kind=%s status=%s",
            stage, type(error).__name__, getattr(error, "code", "-"))
        raise PermissionError("Studio session could not be verified.") from None
