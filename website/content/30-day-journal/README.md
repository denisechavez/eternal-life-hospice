# Continuing the Eternal Journal

The five `batch-*.json` files are the original September 21–October 20, 2026
editorial schedule. Do not change their order or dates. Add new stories to an
`additional-*.json` array in this directory (see `additional-2026-10.json`).
Each new story needs a unique slug, a unique date **after October 20, 2026**
and its own existing image under `/assets/img/`. Dates may have gaps; sort
within a file for readability. Use `publicationStatus: "archived"` to retain
an editorial source without publishing it.

From the repository root, run `python3 website/build-journal-campaign.py`,
then `python3 website/test-journal-campaign.py`. The build creates **missing**
article pages and regenerates the archive, manifest, search index and sitemap.
It does not replace an existing article's HTML: edit that page directly for
post-publication copy or metadata changes. If an existing story's image must
change, update its editorial source and run the builder with `--images-only`
instead. A newly added story is staged in those files but the server hides its
page, archive card, structured data, search result and sitemap entry until
its America/Los_Angeles publication date. `ELH_JOURNAL_DATE=YYYY-MM-DD` is
available for local preview and tests.