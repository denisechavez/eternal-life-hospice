#!/usr/bin/env python3
"""
Build-time guard for the Journal archive's Blog JSON-LD.

The archive must expose one BlogPosting object per published article. In
particular, no two objects may share the same URL: duplicate URLs produce
redundant structured-data signals even when the visible archive has one card.

Run from the repository root:
    python3 website/check-blog-schema.py

Exits 0 on success and 1 when the archive is missing, malformed, or contains
duplicate BlogPosting URLs.
"""

import copy
import json
import os
import re
import sys


SITE_ROOT = os.path.join(os.path.dirname(__file__), "elh-preview")
BLOG_PATH = os.path.join(SITE_ROOT, "blog.html")
JSON_LD_RE = re.compile(
    r"<script\b[^>]*\btype\s*=\s*['\"]application/ld\+json['\"][^>]*>"
    r"(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def extract_blog_schema(html):
    """Return Blog JSON-LD objects from the page and any parse errors."""
    schemas = []
    errors = []

    for index, match in enumerate(JSON_LD_RE.finditer(html), start=1):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON-LD block {index} is invalid JSON: {exc}")
            continue

        types = data.get("@type", []) if isinstance(data, dict) else []
        if isinstance(types, str):
            types = [types]
        if "Blog" in types:
            schemas.append(data)

    return schemas, errors


def validate_blog_schemas(schemas):
    """Return validation errors for Blog schema objects."""
    errors = []

    if not schemas:
        return ["no Blog JSON-LD object found"]
    if len(schemas) > 1:
        errors.append(f"found {len(schemas)} Blog JSON-LD objects; expected one")

    for schema_index, schema in enumerate(schemas, start=1):
        posts = schema.get("blogPost")
        if not isinstance(posts, list):
            errors.append(f"Blog JSON-LD object {schema_index} has no blogPost list")
            continue

        seen_urls = {}
        for post_index, post in enumerate(posts, start=1):
            if not isinstance(post, dict):
                errors.append(
                    f"Blog JSON-LD object {schema_index} blogPost {post_index} "
                    "is not an object"
                )
                continue

            post_types = post.get("@type", [])
            if isinstance(post_types, str):
                post_types = [post_types]
            if "BlogPosting" not in post_types:
                errors.append(
                    f"Blog JSON-LD object {schema_index} blogPost {post_index} "
                    "is not a BlogPosting"
                )

            url = post.get("url")
            if not isinstance(url, str) or not url.strip():
                errors.append(
                    f"Blog JSON-LD object {schema_index} blogPost {post_index} "
                    "has no URL"
                )
                continue

            if url in seen_urls:
                errors.append(
                    f"duplicate blogPost URL {url!r} at positions "
                    f"{seen_urls[url]} and {post_index}"
                )
            else:
                seen_urls[url] = post_index

    return errors


def run_self_test():
    """Verify the guard catches a deliberately duplicated article URL."""
    valid = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "blogPost": [
            {"@type": "BlogPosting", "url": "https://example.com/one"},
        ],
    }
    duplicate = copy.deepcopy(valid)
    duplicate["blogPost"].append(copy.deepcopy(duplicate["blogPost"][0]))
    errors = validate_blog_schemas([duplicate])
    if not any("duplicate blogPost URL" in error for error in errors):
        print("ERROR: self-test did not catch a duplicate blogPost URL")
        return False
    return True


def main():
    if not os.path.isfile(BLOG_PATH):
        print(f"ERROR: archive not found: {BLOG_PATH}")
        return 1

    with open(BLOG_PATH, encoding="utf-8") as blog_file:
        schemas, parse_errors = extract_blog_schema(blog_file.read())

    errors = parse_errors + validate_blog_schemas(schemas)
    if errors:
        print("\nJournal Blog JSON-LD check FAILED")
        for error in errors:
            print(f"  ✗  {error}")
        return 1

    posts = sum(len(schema["blogPost"]) for schema in schemas)
    print(f"Journal Blog JSON-LD check — {posts} BlogPosting URL(s) scanned")
    print("  ✓  all blogPost URLs are unique")

    if not run_self_test():
        return 1
    print("SENTINEL: check-blog-schema.py self-test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())