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

    def test_fetch_normalizes_and_limits_public_fields(self):
        upstream = {
            "rating": 4.9,
            "userRatingCount": 27,
            "googleMapsUri": "https://maps.google.com/example",
            "reviews": [
                {
                    "rating": 5,
                    "text": {"text": "A steady and responsive team."},
                    "authorAttribution": {"displayName": "A. Reviewer"},
                    "relativePublishTimeDescription": "a month ago",
                }
            ],
        }
        with mock.patch.object(
            google_reviews, "_request_json", return_value=upstream
        ) as request_json:
            result = google_reviews._fetch_reviews()

        self.assertEqual(result["rating"], 4.9)
        self.assertEqual(result["reviewCount"], 27)
        self.assertEqual(result["reviews"][0]["author"], "A. Reviewer")
        self.assertNotIn("GOOGLE_API_KEY", json.dumps(result))
        self.assertEqual(
            request_json.call_args.kwargs["field_mask"],
            "id,displayName,rating,userRatingCount,reviews,googleMapsUri",
        )

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


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2)
    if result.result.wasSuccessful():
        print("SENTINEL: test-google-reviews.py OK")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)