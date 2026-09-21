#!/usr/bin/env python3
"""Regression checks for the server-mediated Google reviews feed."""

import json
import os
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import devserver
import google_reviews


class GoogleReviewsTests(unittest.TestCase):
    def setUp(self):
        google_reviews._cache = None
        self.key_patch = mock.patch.dict(
            os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False
        )
        self.key_patch.start()

    def tearDown(self):
        self.key_patch.stop()
        google_reviews._cache = None

    def test_verified_eternal_profile_is_canonical(self):
        self.assertTrue(google_reviews.REVIEWS_ENABLED)
        self.assertEqual(
            google_reviews.CANONICAL_PLACE_ID,
            "ChIJteBBU6vdfEcRqUfOqdzxmoc",
        )
        self.assertEqual(
            google_reviews.CANONICAL_MAPS_URL,
            "https://maps.google.com/?cid=9771388271577679785",
        )
        self.assertEqual(
            google_reviews.WESTLAKE_PLACE_ID,
            "ChIJrRDxvAsl6IARsRyNjEqD2U8",
        )

    def _identity(self, place_id, name="Eternal Life Hospice"):
        is_westlake = place_id == google_reviews.WESTLAKE_PLACE_ID
        maps_cid = "5753774355151396017" if is_westlake else "9771388271577679785"
        return {
            "id": place_id,
            "name": f"places/{place_id}",
            "displayName": {"text": name},
            "nationalPhoneNumber": (
                "(818) 791-0611" if is_westlake else "(805) 953-7273"
            ),
            "websiteUri": (
                "https://westlakevillagehospiceinc.com/"
                if is_westlake
                else "https://eternallifehospice.com/"
            ),
            "formattedAddress": (
                f"4165 E Thousand Oaks Blvd Ste {'325D' if is_westlake else '325B'}, "
                "Westlake Village, CA 91362, USA"
            ),
            "googleMapsUri": f"https://maps.google.com/?cid={maps_cid}&g_mp=test",
        }

    def test_live_identity_check_accepts_distinct_approved_profiles(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        westlake = self._identity(
            google_reviews.WESTLAKE_PLACE_ID, "Westlake Village Hospice Inc"
        )
        westlake.update(
            {
                "nationalPhoneNumber": "(818) 791-0611",
                "websiteUri": "https://westlakevillagehospiceinc.com/",
                "formattedAddress": (
                    "4165 E Thousand Oaks Blvd Ste 325D, "
                    "Westlake Village, CA 91362, USA"
                ),
            }
        )
        self.assertEqual(
            google_reviews.validate_agency_identities(eternal, westlake), []
        )

    def test_live_identity_check_rejects_shared_identifier(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        westlake = self._identity(
            google_reviews.CANONICAL_PLACE_ID, "Westlake Village Hospice Inc"
        )
        violations = google_reviews.validate_agency_identities(eternal, westlake)
        self.assertTrue(any("share the same id" in item for item in violations))
        self.assertTrue(
            any("unexpected Place ID" in item for item in violations)
        )

    def test_live_identity_check_rejects_changed_eternal_contact_fields(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        eternal.update(
            {
                "nationalPhoneNumber": "(818) 791-0611",
                "websiteUri": "https://example.com/",
                "formattedAddress": "Different address",
            }
        )
        westlake = self._identity(
            google_reviews.WESTLAKE_PLACE_ID, "Westlake Village Hospice Inc"
        )
        violations = google_reviews.validate_agency_identities(eternal, westlake)
        self.assertTrue(any("nationalPhoneNumber changed" in item for item in violations))
        self.assertTrue(any("websiteDomain changed" in item for item in violations))
        self.assertTrue(any("formattedAddress changed" in item for item in violations))

    def test_live_identity_check_rejects_westlake_with_eternal_fields(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        westlake = dict(eternal)
        westlake.update(
            {
                "id": google_reviews.WESTLAKE_PLACE_ID,
                "name": f"places/{google_reviews.WESTLAKE_PLACE_ID}",
            }
        )
        violations = google_reviews.validate_agency_identities(eternal, westlake)
        for field in (
            "displayName",
            "nationalPhoneNumber",
            "websiteDomain",
            "formattedAddress",
            "googleMapsCid",
        ):
            self.assertTrue(
                any(f"share the same {field}" in item for item in violations),
                f"missing shared-field violation for {field}",
            )

    def test_live_identity_check_rejects_changed_public_maps_cid(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        eternal["googleMapsUri"] = "https://maps.google.com/?cid=123456789"
        westlake = self._identity(
            google_reviews.WESTLAKE_PLACE_ID, "Westlake Village Hospice Inc"
        )
        westlake.update(
            {
                "nationalPhoneNumber": "(818) 791-0611",
                "websiteUri": "https://westlakevillagehospiceinc.com/",
                "formattedAddress": (
                    "4165 E Thousand Oaks Blvd Ste 325D, "
                    "Westlake Village, CA 91362, USA"
                ),
            }
        )
        violations = google_reviews.validate_agency_identities(eternal, westlake)
        self.assertTrue(any("Eternal googleMapsCid changed" in item for item in violations))

    def test_live_identity_check_never_passes_api_key_to_validation(self):
        eternal = self._identity(google_reviews.CANONICAL_PLACE_ID)
        westlake = self._identity(
            google_reviews.WESTLAKE_PLACE_ID, "Westlake Village Hospice Inc"
        )
        with mock.patch.object(
            google_reviews,
            "_fetch_place_identity",
            side_effect=[eternal, westlake],
        ) as fetch:
            violations = google_reviews.check_agency_identities()
        self.assertEqual(violations, [])
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args_list[0].args[1], "test-key")

    def test_hourly_cache_prevents_repeat_google_calls(self):
        live = {
            "ok": True,
            "source": "Google Business Profile",
            "live": True,
            "stale": False,
            "rating": 5,
            "reviewCount": 11,
            "googleMapsUrl": google_reviews.CANONICAL_MAPS_URL,
            "reviews": [],
            "fetchedAt": "2026-09-01T00:00:00+00:00",
        }
        with mock.patch.object(
            google_reviews, "_fetch_reviews", return_value=live
        ) as fetch:
            first = google_reviews.get_reviews()
            second = google_reviews.get_reviews()
        self.assertEqual(first["rating"], 5)
        self.assertEqual(second["rating"], 5)
        self.assertEqual(fetch.call_count, 1)

    def test_stale_cache_is_returned_during_google_outage(self):
        cached = {
            "ok": True,
            "source": "Google Business Profile",
            "live": True,
            "stale": False,
            "rating": 4.8,
            "reviewCount": 25,
            "googleMapsUrl": google_reviews.CANONICAL_MAPS_URL,
            "reviews": [],
            "fetchedAt": "2026-08-31T00:00:00+00:00",
        }
        google_reviews._cache = {
            "_storedAt": time.monotonic() - google_reviews.CACHE_TTL_SECONDS - 1,
            "data": cached,
        }
        with mock.patch.object(
            google_reviews,
            "_fetch_reviews",
            side_effect=google_reviews.GoogleReviewsError("upstream"),
        ):
            result = google_reviews.get_reviews()
        self.assertTrue(result["stale"])
        self.assertFalse(result["live"])
        self.assertEqual(result["reviewCount"], 25)

    def test_endpoint_returns_json_without_exposing_configuration_error(self):
        app = ThreadingHTTPServer(("127.0.0.1", 0), devserver.PrettyURLHandler)
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        with mock.patch.object(
            devserver,
            "get_reviews",
            side_effect=google_reviews.GoogleReviewsError("private detail"),
        ):
            thread.start()
            url = (
                f"http://127.0.0.1:{app.server_address[1]}"
                "/api/google-reviews"
            )
            try:
                urlopen(url)
                self.fail("Expected HTTP 503")
            except HTTPError as exc:
                self.assertEqual(exc.code, 503)
                payload = json.loads(exc.read().decode("utf-8"))
            finally:
                app.shutdown()
                thread.join(timeout=2)
                app.server_close()
        self.assertEqual(payload["error"], "reviews_unavailable")
        self.assertNotIn("private detail", json.dumps(payload))
        self.assertNotIn("googleMapsUrl", payload)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    if result.result.wasSuccessful():
        print("SENTINEL: test-google-reviews.py OK")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)