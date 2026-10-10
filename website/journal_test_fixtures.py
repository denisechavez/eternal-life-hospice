"""Explicitly approved fixtures for the older archive-generation tests only.

These tests exercise generated layout across dates, not live authorization.
The authoritative release suite tests unapproved/held versions and clock times.
"""
from pathlib import Path
import re
import devserver
import journal_release


def approved_fixture_releases():
    today = devserver.PrettyURLHandler._journal_today()
    records = {slug: {"date": row["date"], "revision": row["revision"], "html": journal_release.unpack(row)}
               for slug, row in journal_release.history().items() if row["date"] <= (today or "")}
    for row in devserver.PrettyURLHandler._journal_manifest() or []:
        if row["date"] > (today or ""):
            continue
        path = Path(devserver.ROOT) / "blog" / (row["slug"] + ".html")
        records[row["slug"]] = {"date":row["date"],"revision":"explicitly-approved-test-fixture",
                               "html":path.read_text() if path.is_file() else ""}
    # Explicitly approve legacy/new fixture pages outside the campaign manifest.
    for path in (Path(devserver.ROOT) / "blog").glob("*.html"):
        document = path.read_text()
        day = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', document)
        if day and day.group(1) <= (today or "") and 'http-equiv="refresh"' not in document:
            records[path.stem] = {"date":day.group(1),"revision":"explicitly-approved-test-fixture","html":document}
    return records, True
