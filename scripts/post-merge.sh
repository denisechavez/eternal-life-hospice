#!/bin/bash
set -e

# Eternal Life Hospice is a static HTML site (website/elh-preview/) served by
# Replit Autoscale. Preserve installed internal tools while ensuring the live
# Journal's JWT/database dependencies are present in Replit's managed environment.

test -d website/elh-preview
python3 scripts/setup-python-environment.py
uv sync --locked --inexact
python3 website/migrate-journal.py

echo "post-merge OK: website/elh-preview present ($(ls website/elh-preview/*.html 2>/dev/null | wc -l) HTML pages)"
