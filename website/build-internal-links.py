#!/usr/bin/env python3
"""Refresh authored link slots and complete the published county directory."""
import argparse
import html
import json
import re
from internal_links import BASE, PUBLIC, inventory, refresh, today

def build(as_of):
    hub = PUBLIC / "hospice-ventura-and-los-angeles-county-ca.html"
    text = hub.read_text()
    pages = inventory(as_of)
    cities = json.loads((BASE / "city-data.json").read_text())
    missing = []
    for city in cities:
        route = "/hospice-" + city["slug"] + "-ca"
        if city.get("publishStatus") == "published" and route in pages and not re.search(r'href=["\']/?' + re.escape(route[1:]) + r'(?:\.html)?["\']', text):
            missing.append((city, route))
    start, end = "<!-- CITY_DIRECTORY_LINKS_START -->", "<!-- CITY_DIRECTORY_LINKS_END -->"
    # Use all inventory cities in a stable list; do not rewrite county messaging.
    cities = [(c, "/hospice-" + c["slug"] + "-ca") for c in cities
              if c.get("publishStatus") == "published" and "/hospice-" + c["slug"] + "-ca" in pages]
    if missing or start in text:
        block = start + '\n<section class="elh-related" aria-labelledby="city-directory-title"><h2 id="city-directory-title">Published community guides</h2><ul>'
        block += "".join(f'<li><a href="{route}">{html.escape(c["city"])}</a></li>'
                         for c, route in sorted(cities, key=lambda x: x[0]["city"]))
        block += "</ul></section>\n" + end
        if start in text:
            text = re.sub(re.escape(start) + r"[\s\S]*?" + re.escape(end), lambda _: block, text)
        else:
            text = text.replace("</main>", block + "\n</main>", 1)
        hub.write_text(text)
    refresh(as_of)

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--date", default=today())
    build(cli.parse_args().date)
