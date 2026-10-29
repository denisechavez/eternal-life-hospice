"""Check actual response permissions for the active call tracker; no network."""
import io
import unittest

from devserver import PrettyURLHandler
from analytics_assets import ANALYTICS_FILE


class TrackerPolicyTests(unittest.TestCase):
    def policy(self):
        handler = object.__new__(PrettyURLHandler)
        handler.path = "/"
        handler.request_version = "HTTP/1.1"
        handler._headers_buffer = []
        handler.wfile = io.BytesIO()
        handler.end_headers()
        headers = handler.wfile.getvalue().decode()
        line = next(line for line in headers.splitlines()
                    if line.startswith("Content-Security-Policy:"))
        return {part.strip().split()[0]: part.strip().split()[1:]
                for part in line.split(":", 1)[1].split(";") if part.strip()}

    def test_active_nimbata_script_is_allowed(self):
        self.assertIn("https://cdn.dni.nimbata.com", self.policy()["script-src"])

    def test_nimbata_generated_attribution_rules_are_allowed(self):
        # The configured vendor tag uses new Function before opening a session.
        # A successful CDN download alone does not establish runtime access.
        self.assertIn("'unsafe-eval'", self.policy()["script-src"])

    def test_runtime_permission_does_not_expand_external_host_access(self):
        policy = self.policy()
        self.assertEqual(policy["default-src"], ["'self'"])
        for directive in ("script-src", "connect-src"):
            self.assertNotIn("*", policy[directive])
            self.assertNotIn("https:", policy[directive])
            self.assertNotIn("data:", policy[directive])

    def test_nimbata_configured_session_endpoint_is_allowed(self):
        self.assertIn("https://dakvo8z10w4va.cloudfront.net", self.policy()["connect-src"])

    def test_removed_whatconverts_hosts_are_not_allowed(self):
        policy = str(self.policy())
        self.assertNotIn("ksrndkehqnwntyxlhgto", policy)
        self.assertNotIn("whatconverts", policy.lower())

    def test_removed_browser_tag_and_metadata_collection_do_not_return(self):
        source = ANALYTICS_FILE.read_text()
        self.assertNotIn("ksrndkehqnwntyxlhgto", source)
        self.assertNotIn("$wc_leads", source)

    def test_google_ads_permissions_are_preserved(self):
        policy = self.policy()
        self.assertIn("https://www.googletagmanager.com", policy["script-src"])
        self.assertIn("https://www.googleadservices.com", policy["connect-src"])
        self.assertIn("https://googleads.g.doubleclick.net", policy["connect-src"])


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    if not result.wasSuccessful() or result.testsRun < 5:
        raise SystemExit(1)
    print("SENTINEL: test-tracker-policy.py OK")
