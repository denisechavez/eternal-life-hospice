#!/usr/bin/env python3
"""Scheduled live guard against Google Place profile cross-linking."""

import argparse

from google_reviews import GoogleReviewsError, check_agency_identities


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-failure",
        action="store_true",
        help="emit a credential-free synthetic failure for alert-path testing",
    )
    args = parser.parse_args(argv)

    if args.test_failure:
        print("ALERT: Synthetic Google Place identity failure test.")
        print("No Google request was made; verify the designated owner received this alert.")
        return 1

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