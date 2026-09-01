"""Public, read-only service-area lookup for the Replit deployment."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Mapping, Sequence


PHONE = "805.953.7273"
BASE = os.path.dirname(os.path.abspath(__file__))


def _load_json(name):
    with open(os.path.join(BASE, name), encoding="utf-8") as handle:
        return json.load(handle)


def normalise(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


_cities = _load_json("city-data.json")
_aliases = {
    normalise(key): value
    for key, value in _load_json("city-aliases.json").get("aliases", {}).items()
}
_index = [
    {
        "city": city["city"],
        "county": city.get("county"),
        "subregion": city.get("subregion"),
        "canonicalUrl": city.get("canonicalUrl"),
        "_normCity": normalise(city["city"]),
        "_normSlug": str(city.get("slug", "")).replace("-", " "),
    }
    for city in _cities
    if city.get("publishStatus") == "published"
]


def _param(params: Mapping[str, Sequence[str]], name: str) -> str:
    value = params.get(name, "")
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else ""
    return str(value)


def lookup_coverage(params):
    """Return ``(status, payload, cache_seconds)`` for a query-string mapping."""
    if _param(params, "list") == "true":
        return (
            200,
            {
                "cities": [
                    {
                        "city": city["city"],
                        "county": city["county"],
                        "subregion": city["subregion"],
                        "pageUrl": city["canonicalUrl"],
                    }
                    for city in _index
                ],
                "total": len(_index),
                "counties": sorted({city["county"] for city in _index}),
                "phone": PHONE,
            },
            86400,
        )

    trimmed = _param(params, "city").strip()
    if not trimmed:
        return (
            400,
            {
                "error": "Missing required query parameter: city",
                "example": "/api/coverage?city=Pasadena",
                "tip": "To fetch all published cities use /api/coverage?list=true",
            },
            3600,
        )

    query = normalise(trimmed)
    match = next(
        (
            city
            for city in _index
            if city["_normCity"] == query or city["_normSlug"] == query
        ),
        None,
    )

    if match is None and query in _aliases:
        canonical = normalise(_aliases[query])
        match = next(
            (city for city in _index if city["_normCity"] == canonical), None
        )

    if match is None and len(query) >= 4:
        matches = [
            city
            for city in _index
            if city["_normCity"].startswith(query)
            or query.startswith(city["_normCity"])
        ]
        if len(matches) == 1:
            match = matches[0]
        elif len(matches) > 1:
            return (
                200,
                {
                    "served": False,
                    "city": trimmed,
                    "ambiguous": True,
                    "message": (
                        f"“{trimmed}” matches multiple cities. Please use the full "
                        "city name so we can give you an accurate answer."
                    ),
                    "suggestions": [city["city"] for city in matches],
                },
                3600,
            )

    if match is not None:
        return (
            200,
            {
                "served": True,
                "city": match["city"],
                "county": match["county"],
                "subregion": match["subregion"],
                "pageUrl": match["canonicalUrl"],
                "phone": PHONE,
            },
            3600,
        )

    return (
        200,
        {
            "served": False,
            "city": trimmed,
            "message": (
                "Eternal Life Hospice does not have a published service-area page "
                f"for “{trimmed}”. Please call {PHONE} to confirm coverage — our "
                "service area across Ventura and Los Angeles counties may extend "
                "beyond our published city pages."
            ),
        },
        3600,
    )