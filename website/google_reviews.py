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
from urllib.parse import quote
from urllib.request import Request, urlopen


GOOGLE_PLACES_BASE = "https://places.googleapis.com/v1"
CANONICAL_MAPS_URL = "https://maps.google.com/?cid=9771388271577679785"
# This is the canonical "Eternal Life Hospice" listing already used by the
# retired Netlify review function.  It is not the lingering "Inc." duplicate.
CANONICAL_PLACE_ID = "ChIJteBBU6vdfEcRqUfOqdzxmoc"
CACHE_TTL_SECONDS = 60 * 60
REQUEST_TIMEOUT_SECONDS = 8
MAX_REVIEW_LENGTH = 360
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


def _clean_review(review):
    text_obj = review.get("text") or review.get("originalText") or {}
    text = (text_obj.get("text") or "").strip()
    if not text:
        return None
    if len(text) > MAX_REVIEW_LENGTH:
        text = text[: MAX_REVIEW_LENGTH - 1].rstrip() + "…"
    author = ((review.get("authorAttribution") or {}).get("displayName") or "").strip()
    return {
        "text": text,
        "author": author[:120] or "Google reviewer",
        "rating": review.get("rating"),
        "published": review.get("relativePublishTimeDescription") or "",
    }


def _fetch_reviews():
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