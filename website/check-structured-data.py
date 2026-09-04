#!/usr/bin/env python3
"""Regression checks for the site's JSON-LD entity and FAQ rules."""

import json
import re
import sys
from html import unescape
from pathlib import Path


ROOT = Path(__file__).parent / "elh-preview"
CITY_DATA = Path(__file__).parent / "city-data.json"
ORG_ID = "https://eternallifehospice.com/#organization"
JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)
FAQ_FORBIDDEN = (
    "resources/comfort-therapies.html",
    "resources/first-48-hours.html",
    "resources/how-to-choose-a-hospice.html",
    "resources/medicare-hospice-benefit.html",
    "resources/pain-symptom-management.html",
    "resources/the-circle-around-you.html",
    "resources/volunteer.html",
    "resources/when-is-it-time.html",
    "services/medical-aid-in-dying-california.html",
    "hospice-ventura-and-los-angeles-county-ca.html",
    "careers.html",
    "volunteer.html",
)


def schemas(path: Path) -> list[dict]:
    payloads = []
    for index, match in enumerate(
        JSON_LD_RE.finditer(path.read_text(encoding="utf-8")), start=1
    ):
        try:
            payloads.append(json.loads(match.group(1)))
        except json.JSONDecodeError as error:
            raise AssertionError(
                f"{path}: JSON-LD block {index} does not parse: {error}"
            ) from error
    return payloads


def has_type(schema: dict, expected: str) -> bool:
    schema_type = schema.get("@type")
    return schema_type == expected or (
        isinstance(schema_type, list) and expected in schema_type
    )


def nodes(value):
    """Yield every JSON-LD object, including nodes nested in @graph."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def visible_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    content = re.sub(
        r"<(?:script|style)\b.*?</(?:script|style)>",
        " ",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    content = re.sub(
        r"</?(?:address|article|aside|blockquote|br|details|div|footer|"
        r"h[1-6]|header|li|main|nav|ol|p|section|summary|table|td|th|tr|ul)\b[^>]*>",
        " ",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"<[^>]+>", "", content)
    return " ".join(unescape(content).split())


def check_homepage(errors: list[str]) -> None:
    homepage_schemas = schemas(ROOT / "index.html")
    organizations = [
        node
        for schema in homepage_schemas
        for node in nodes(schema)
        if node.get("@id") == ORG_ID
        and (
            has_type(node, "MedicalOrganization")
            or has_type(node, "LocalBusiness")
        )
    ]
    if len(organizations) != 1:
        errors.append(
            "index.html must contain exactly one canonical organization graph node"
        )
        return

    organization = organizations[0]
    address = organization.get("address", {})
    geo = organization.get("geo", {})
    if address.get("streetAddress") != "4165 E Thousand Oaks Blvd, Ste 325B":
        errors.append("index.html canonical organization address changed")
    if (
        geo.get("latitude") != 34.1386
        or geo.get("longitude") != -118.8198
    ):
        errors.append("index.html canonical organization coordinates changed")


def check_city_pages(errors: list[str]) -> None:
    city_data = json.loads(CITY_DATA.read_text(encoding="utf-8"))
    expected_paths = {
        ROOT / f"hospice-{city['slug']}-ca.html"
        for city in city_data
        if city.get("publishStatus") == "published"
    }
    actual_paths = set(ROOT.glob("hospice-*-ca.html"))
    county_hub = ROOT / "hospice-ventura-and-los-angeles-county-ca.html"
    actual_paths.discard(county_hub)
    missing = expected_paths - actual_paths
    unexpected = actual_paths - expected_paths
    for path in sorted(missing):
        errors.append(f"{path.name}: published city page is missing")
    for path in sorted(unexpected):
        errors.append(f"{path.name}: city page is not present in canonical city data")

    city_by_path = {
        ROOT / f"hospice-{city['slug']}-ca.html": city
        for city in city_data
        if city.get("publishStatus") == "published"
    }
    for path in sorted(expected_paths & actual_paths):
        city = city_by_path[path]
        page_schemas = schemas(path)
        organizations = [
            node
            for schema in page_schemas
            for node in nodes(schema)
            if node.get("@id") == ORG_ID
            and (
                has_type(node, "MedicalOrganization")
                or has_type(node, "LocalBusiness")
            )
        ]
        if organizations:
            errors.append(f"{path.name}: redefines the canonical organization")

        geo_nodes = [
            node
            for schema in page_schemas
            for node in nodes(schema)
            if has_type(node, "GeoCoordinates") or "geo" in node
        ]
        if geo_nodes:
            errors.append(f"{path.name}: publishes city coordinates as entity geo")

        services = [
            node
            for schema in page_schemas
            for node in nodes(schema)
            if has_type(node, "Service")
        ]
        if len(services) != 1:
            errors.append(f"{path.name}: expected exactly one Service node")
            continue
        service = services[0]
        if service.get("provider") != {"@id": ORG_ID}:
            errors.append(f"{path.name}: Service must reference the canonical provider")
        expected_areas = [
            {"@type": "City", "name": f"{city['city']}, California"},
            {"@type": "AdministrativeArea", "name": f"{city['county']}, California"},
        ]
        if service.get("areaServed") != expected_areas:
            errors.append(f"{path.name}: Service areaServed differs from city data")

    hub_services = [
        schema for schema in schemas(county_hub) if has_type(schema, "Service")
    ]
    if (
        len(hub_services) != 1
        or hub_services[0].get("provider") != {"@id": ORG_ID}
        or len(hub_services[0].get("areaServed", [])) != 2
    ):
        errors.append(
            f"{county_hub.name}: expected one provider-linked, two-county Service"
        )


def check_forbidden_faqs(errors: list[str]) -> None:
    for relative_path in FAQ_FORBIDDEN:
        path = ROOT / relative_path
        if any(
            has_type(node, "FAQPage")
            for schema in schemas(path)
            for node in nodes(schema)
        ):
            errors.append(f"{relative_path}: FAQPage requires matching visible Q&A")


def check_visible_faqs(errors: list[str]) -> None:
    for path in ROOT.rglob("*.html"):
        text = visible_text(path)
        for schema in schemas(path):
            for faq in (node for node in nodes(schema) if has_type(node, "FAQPage")):
                for question in faq.get("mainEntity", []):
                    question_text = " ".join(question.get("name", "").split())
                    answer_text = " ".join(
                        question.get("acceptedAnswer", {}).get("text", "").split()
                    )
                    if not question_text or question_text not in text:
                        errors.append(
                            f"{path.relative_to(ROOT)}: FAQ question is not visible: "
                            f"{question_text!r}"
                        )
                    if not answer_text or answer_text not in text:
                        errors.append(
                            f"{path.relative_to(ROOT)}: FAQ answer is not visible for "
                            f"{question_text!r}"
                        )


def self_test() -> None:
    nested = {"@graph": [{"@type": "GeoCoordinates"}, {"@type": "FAQPage"}]}
    if not any(has_type(node, "GeoCoordinates") for node in nodes(nested)):
        raise AssertionError("recursive JSON-LD node traversal self-test failed")
    if not any(has_type(node, "FAQPage") for node in nodes(nested)):
        raise AssertionError("nested FAQPage traversal self-test failed")


def main() -> int:
    errors: list[str] = []
    for path in ROOT.rglob("*.html"):
        try:
            schemas(path)
        except AssertionError as error:
            errors.append(str(error))

    check_homepage(errors)
    check_city_pages(errors)
    check_forbidden_faqs(errors)
    check_visible_faqs(errors)

    if errors:
        print("Structured-data regression check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    self_test()
    print("Structured-data regression check passed.")
    print("SENTINEL: check-structured-data.py self-test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())