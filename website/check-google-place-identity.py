#!/usr/bin/env python3
"""Scheduled live guard against Google Place profile cross-linking."""

from google_reviews import GoogleReviewsError, check_agency_identities


def main():
    try:
        violations = check_agency_identities()
    except GoogleReviewsError as exc:
        print(f"ALERT: Google Place identity check could not run: {exc}")
        return 1

    if violations:
        print("ALERT: Google Place agency identity check failed:")
        for violation in violations:
            print(f"  - {violation}")
        print("Review both Google Business Profiles before changing website links.")
        return 1

    print("SENTINEL: check-google-place-identity.py OK")
    print("Eternal and Westlake remain distinct; Eternal's approved identity is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())