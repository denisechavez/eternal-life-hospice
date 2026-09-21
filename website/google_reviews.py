#!/usr/bin/env python3
"""Small, server-side Google Places review feed for the public homepage.

The browser never receives the Google API key.  This module resolves the
approved listing once per cache window, then fetches the rating and the
review fields allowed by Google Places API (New).
"""

import json
import os
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen


GOOGLE_PLACES_BASE = "https://places.googleapis.com/v1"
# Verified Eternal Life Hospice profile. Google Places confirms this listing
# uses Eternal's phone, domain, and Suite 325B; Westlake has a distinct profile.
REVIEWS_ENABLED = True
CANONICAL_MAPS_URL = "https://maps.google.com/?cid=9771388271577679785"
CANONICAL_PLACE_ID = "ChIJteBBU6vdfEcRqUfOqdzxmoc"
WESTLAKE_PLACE_ID = "ChIJrRDxvAsl6IARsRyNjEqD2U8"
APPROVED_ETERNAL_IDENTITY = {
    "displayName": "Eternal Life Hospice",
    "nationalPhoneNumber": "(805) 953-7273",
    "websiteDomain": "eternallifehospice.com",
    "formattedAddress": (
        "4165 E Thousand Oaks Blvd Ste 325B, Westlake Village, CA 91362, USA"
    ),
    "googleMapsCid": "9771388271577679785",
}
APPROVED_WESTLAKE_IDENTITY = {
    "displayName": "Westlake Village Hospice Inc",
    "nationalPhoneNumber": "(818) 791-0611",
    "websiteDomain": "westlakevillagehospiceinc.com",
    "formattedAddress": (
        "4165 E Thousand Oaks Blvd Ste 325D, Westlake Village, CA 91362, USA"
    ),
    "googleMapsCid": "5753774355151396017",
}
CACHE_TTL_SECONDS = 60 * 60
REQUEST_TIMEOUT_SECONDS = 8
MAX_REVIEWS = 5

_cache = None
_cache_lock = threading.Lock()


class GoogleReviewsError(RuntimeError):
    """An expected upstream/configuration error safe to expose generically."""


def _api_key():
    key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key or key.lower() in {"replace-me", "your-api-key"}:
        raise GoogleReviewsError("Google Places is not configured.")
    return key


def _request_json(method, url, api_key, body=None, field_mask=""):
    headers = {
        "Accept": "application/json",
        "X-Goog-Api-Key": api_key,
        "User-Agent": "EternalLifeHospice/1.0 live-reviews",
    }
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        status = getattr(exc, "code", "network")
        raise GoogleReviewsError(f"Google Places request failed ({status}).") from exc


def _resolve_place_id(api_key):
    configured = (os.environ.get("GOOGLE_PLACE_ID") or "").strip()
    return configured or CANONICAL_PLACE_ID


def _fetch_place_identity(place_id, api_key):
    """Fetch only the public fields needed to verify an agency's identity."""
    return _request_json(
        "GET",
        f"{GOOGLE_PLACES_BASE}/places/{quote(place_id, safe='')}",
        api_key,
        field_mask=(
            "id,name,displayName,nationalPhoneNumber,websiteUri,"
            "formattedAddress,googleMapsUri"
        ),
    )


def _identity_values(place):
    website = (place.get("websiteUri") or "").strip()
    domain = (urlparse(website).hostname or "").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    maps_uri = (place.get("googleMapsUri") or "").strip()
    maps_cid = (parse_qs(urlparse(maps_uri).query).get("cid") or [""])[0]
    return {
        "id": (place.get("id") or "").strip(),
        "resourceName": (place.get("name") or "").strip(),
        "displayName": ((place.get("displayName") or {}).get("text") or "").strip(),
        "nationalPhoneNumber": (place.get("nationalPhoneNumber") or "").strip(),
        "websiteDomain": domain,
        "formattedAddress": (place.get("formattedAddress") or "").strip(),
        "googleMapsCid": maps_cid,
    }


def validate_agency_identities(eternal, westlake):
    """Return human-readable identity violations without including credentials."""
    eternal_values = _identity_values(eternal)
    westlake_values = _identity_values(westlake)
    violations = []

    if eternal_values["id"] != CANONICAL_PLACE_ID:
        violations.append(
            "Eternal returned an unexpected Place ID "
            f"({eternal_values['id'] or 'missing'})."
        )
    if westlake_values["id"] != WESTLAKE_PLACE_ID:
        violations.append(
            "Westlake returned an unexpected Place ID "
            f"({westlake_values['id'] or 'missing'})."
        )

    for field in (
        "id",
        "resourceName",
        "displayName",
        "nationalPhoneNumber",
        "websiteDomain",
        "formattedAddress",
        "googleMapsCid",
    ):
        value = eternal_values[field]
        if value and value == westlake_values[field]:
            violations.append(f"Eternal and Westlake share the same {field}.")

    approved_profiles = (
        ("Eternal", eternal_values, APPROVED_ETERNAL_IDENTITY),
        ("Westlake", westlake_values, APPROVED_WESTLAKE_IDENTITY),
    )
    for agency, actual_values, approved_values in approved_profiles:
        for field, approved in approved_values.items():
            actual = actual_values[field]
            if actual != approved:
                violations.append(
                    f"{agency} {field} changed: expected {approved!r}, "
                    f"received {actual or 'missing'!r}."
                )
    return violations


def check_agency_identities():
    """Fetch both agencies and return any live Google Places identity violations."""
    api_key = _api_key()
    eternal = _fetch_place_identity(CANONICAL_PLACE_ID, api_key)
    westlake = _fetch_place_identity(WESTLAKE_PLACE_ID, api_key)
    return validate_agency_identities(eternal, westlake)


def _clean_review(review):
    text_obj = review.get("text") or review.get("originalText") or {}
    text = (text_obj.get("text") or "").strip()
    if not text:
        return None
    author = ((review.get("authorAttribution") or {}).get("displayName") or "").strip()
    return {
        "text": text,
        "author": author[:120] or "Google reviewer",
        "rating": review.get("rating"),
        "published": review.get("relativePublishTimeDescription") or "",
    }


def _fetch_reviews():
    if not REVIEWS_ENABLED:
        raise GoogleReviewsError(
            "Google reviews are disabled pending a verified Eternal Life Hospice profile."
        )
    api_key = _api_key()
    place_id = _resolve_place_id(api_key)
    result = _request_json(
        "GET",
        f"{GOOGLE_PLACES_BASE}/places/{quote(place_id, safe='')}",
        api_key,
        field_mask=(
            "id,displayName,rating,userRatingCount,reviews,"
            "googleMapsUri"
        ),
    )
    reviews = []
    for review in result.get("reviews") or []:
        cleaned = _clean_review(review)
        if cleaned:
            reviews.append(cleaned)
        if len(reviews) >= MAX_REVIEWS:
            break
    now = datetime.now(timezone.utc).isoformat()
    return {
        "ok": True,
        "source": "Google Business Profile",
        "live": True,
        "stale": False,
        "rating": result.get("rating"),
        "reviewCount": result.get("userRatingCount"),
        "googleMapsUrl": result.get("googleMapsUri") or CANONICAL_MAPS_URL,
        "reviews": reviews,
        "fetchedAt": now,
    }


def get_reviews():
    """Return live data, or stale in-process data if Google is temporarily down."""
    global _cache
    now = time.monotonic()
    with _cache_lock:
        if _cache and now - _cache["_storedAt"] < CACHE_TTL_SECONDS:
            result = dict(_cache["data"])
            result["stale"] = False
            return result

    try:
        fresh = _fetch_reviews()
    except GoogleReviewsError:
        with _cache_lock:
            if _cache:
                result = dict(_cache["data"])
                result["stale"] = True
                result["live"] = False
                return result
        raise

    with _cache_lock:
        _cache = {"_storedAt": time.monotonic(), "data": fresh}
    return dict(fresh)