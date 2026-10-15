"""Single owner-directed approval; not a login or a general approval bypass.

The project owner explicitly requested approval/publication of the October 15
Journal post while Studio sign-in was unavailable. Do not add other articles
without a separate explicit request. This runs only on an approved publication,
records its actual source and freezes the exact reviewed content and imagery.
The owner's subsequent "post it now" instruction authorizes immediate release
of this one version. Every other article keeps its existing schedule.
"""
import journal_release as journal

REQUEST = {
    "slug": "when-a-parent-refuses-hospice",
    "date": "2026-10-15",
    "revision": "5b39a6afbd08264218de419d3960c9b5cc88cb9fe27db6f989eec765839e5153",
    "reviewer": "Owner request — October 15, 2026 (outside Studio)",
}


def apply():
    if journal.environment() != "production":
        return False
    try:
        applied = journal.decide(
            REQUEST["slug"], REQUEST["revision"], "approve", REQUEST["reviewer"],
            only_if_undecided=True, expected_date=REQUEST["date"], release_immediately=True)
    except ValueError:
        # A later editorial change is not authorized by this request. Keep the
        # site available but never approve different bytes automatically.
        print("Owner-requested October 15 approval not applied: article version changed.")
        return False
    if applied:
        print("Owner-requested October 15 Journal version approved and released immediately.")
    return applied
