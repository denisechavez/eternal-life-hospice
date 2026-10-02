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

## Syncing an edited article

Once a page exists, its visible hero `<h1>` and hero summary `<p>` are the
authority for archive titles and descriptions, including legacy posts. Inline
formatting and HTML entities are read as plain text. The article body/lede,
SEO title and meta description are not substituted for the visible summary.
Source JSON still controls dates, categories, read times, images and whether a
story is archived; editing that JSON does not replace existing article copy.

After editing an article in `website/elh-preview/blog/`, run:

```sh
python3 website/build-journal-campaign.py --archive-only
python3 website/test-journal-campaign.py
```

This updates the archive grid, featured card (including the scheduled promotion
payloads) and archive Blog structured data without writing any article, manifest,
sitemap or search-index files. Normal builds and `--images-only` use the same
archive sync. For search-index updates, use the normal build. Article-level SEO,
social metadata and structured data still need to be edited in the article
itself when appropriate; the archive sync does not rewrite them.

Every public source must have an existing page with exactly one hero section,
one non-empty heading and one non-empty summary paragraph. Missing or ambiguous
copy stops the sync before the archive is written, rather than silently
reintroducing stale JSON. Fix the named page and rerun. Archived sources are
excluded and do not need a page. Verify scheduled visibility in local preview
using `ELH_JOURNAL_DATE`; syncing does not change publication dates.