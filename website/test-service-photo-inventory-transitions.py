#!/usr/bin/env python3
"""Disposable same-server HTTP checks for changing service-link eligibility.

Run: python3 website/test-service-photo-inventory-transitions.py

Reuse the rebuild/HTTP fixture without discovering its separate stable-inventory
tests. Only disposable service inventory is changed; no Journal release storage,
workspace publication state or public source files are touched.
"""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "service_photo_http_fixture",
    Path(__file__).with_name("test-service-photo-notes-e2e.py"))
fixture_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture_module)


class ServicePhotoInventoryTransitionTests(unittest.TestCase):
    def exercise(self, transition):
        fixture = fixture_module.ServicePhotoNoteTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.exercise(production=True, contextual=True, transition=transition)

    def test_recommendations_disappear_and_return_on_same_server(self):
        self.exercise("destinations")

    def test_entire_inventory_disappears_and_returns_on_same_server(self):
        self.exercise("inventory")


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("SENTINEL: test-service-photo-inventory-transitions.py OK")
    raise SystemExit(not result.result.wasSuccessful())
