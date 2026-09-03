#!/bin/bash
set -e

# Eternal Life Hospice is a static HTML site (website/elh-preview/) served by
# Replit Autoscale. There is no build step and no dependencies to install, so post-merge
# setup is a fast, idempotent check that the published site directory is intact.
# This keeps task merges reconciling cleanly without doing unnecessary work.

test -d website/elh-preview

echo "post-merge OK: website/elh-preview present ($(ls website/elh-preview/*.html 2>/dev/null | wc -l) HTML pages)"
