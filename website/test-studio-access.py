#!/usr/bin/env python3
"""Offline Studio security regressions: synthetic RSA tokens, no live sessions.

No database is needed. All provider I/O is intercepted; production authorization
and asset/API handlers themselves remain unchanged.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from devserver import PrettyURLHandler
import journal_release
import studio_auth
import studio_site

ORIGINS = ("https://eternallifehospice.com", "https://eternal-life-hospice.replit.app")


class ProductionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        public.update(kid="isolated-reviewer", use="sig", alg="RS256")
        self.jwks = json.dumps({"keys": [public]}).encode()
        self.key_transport = Mock()
        self.key_transport.open.side_effect = lambda *a, **k: io.BytesIO(self.jwks)
        self.user = {"id": "user_fixture", "first_name": "Fixture",
                     "email_addresses": [{"email_address": "denise@eternallifehospice.com",
                                          "verification": {"status": "verified"}}]}
        self.session = {"user_id": "user_fixture", "status": "active"}
        self.env = patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1",
                                          "CLERK_PUBLISHABLE_KEY": "unused-fixture-key",
                                          "CLERK_SECRET_KEY": "isolated-not-a-secret"})
        self.env.start()
        studio_auth.verifier.cache_clear()
        self.addCleanup(self.env.stop)
        self.addCleanup(studio_auth.verifier.cache_clear)
        network = patch("socket.create_connection", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def token(self, origin, **overrides):
        now = datetime.now(timezone.utc)
        claims = {"iss": "https://clerk." + origin.removeprefix("https://"),
                  "azp": origin, "sub": "user_fixture", "sid": "sess_fixture",
                  "iat": now, "nbf": now, "exp": now + timedelta(minutes=5)}
        claims.update(overrides)
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "isolated-reviewer"})

    def identity(self, origin, token=None, host=None):
        return studio_auth.reviewer_identity({
            "Cookie": "__session=" + (token or self.token(origin)),
            # Reverse proxy identity must win over an internal Host.
            "Host": "internal.invalid", "X-Forwarded-Host": host or origin.removeprefix("https://"),
        })

    def provider(self, request, **kwargs):
        self.assertEqual(request.get_header("User-agent"), "Eternal-Studio/1.0")
        self.assertEqual(request.get_header("Accept"), "application/json")
        path = request.full_url
        if path == "https://api.clerk.com/v1/sessions/sess_fixture":
            return io.BytesIO(json.dumps(self.session).encode())
        if path == "https://api.clerk.com/v1/users/user_fixture":
            return io.BytesIO(json.dumps(self.user).encode())
        self.fail("Unexpected provider URL: " + path)

    def test_both_domains_verify_real_signatures_through_matching_proxy_identity(self):
        for origin in ORIGINS:
            for address in studio_auth.REVIEWER_EMAILS:
                with self.subTest(origin=origin, reviewer=address):
                    studio_auth.verifier.cache_clear()
                    self.user["email_addresses"][0]["email_address"] = address
                    self.key_transport.reset_mock()
                    with patch("jwt.jwks_client.urllib.request.build_opener", return_value=self.key_transport), \
                         patch.object(studio_auth, "urlopen", side_effect=self.provider) as provider:
                        identity = self.identity(origin)
                        self.assertEqual(identity, studio_auth.ReviewerIdentity("user_fixture", "Fixture"))
                        self.assertEqual(self.key_transport.open.call_count, 1)
                        request = self.key_transport.open.call_args.args[0]
                        self.assertEqual(request.full_url, origin + "/api/__clerk/.well-known/jwks.json")
                        self.assertEqual(request.get_header("User-agent"), "Eternal-Studio/1.0")
                        self.assertEqual(provider.call_count, 2)

    def test_host_issuer_origin_signature_and_session_checks_are_not_bypassed(self):
        origin = ORIGINS[0]
        now = datetime.now(timezone.utc)
        for changes in ({"iss": "https://clerk.evil.invalid"}, {"azp": "https://evil.invalid"},
                        {"iss": "https://clerk.eternal-life-hospice.replit.app"},
                        {"exp": now - timedelta(minutes=1)}, {"sid": None}):
            with self.subTest(changes=changes), \
                 patch("jwt.jwks_client.urllib.request.build_opener", return_value=self.key_transport), \
                 patch.object(studio_auth, "urlopen", side_effect=self.provider):
                with self.assertRaises(PermissionError):
                    self.identity(origin, self.token(origin, **changes))
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        forged = jwt.encode(jwt.decode(self.token(origin), options={"verify_signature": False}),
                            other_key, algorithm="RS256", headers={"kid": "isolated-reviewer"})
        with patch("jwt.jwks_client.urllib.request.build_opener", return_value=self.key_transport), \
             patch.object(studio_auth, "urlopen", side_effect=self.provider):
            with self.assertRaises(PermissionError):
                self.identity(origin, forged)
            for status in ("revoked", "ended"):
                self.session["status"] = status
                with self.assertRaises(PermissionError):
                    self.identity(origin)
            self.session["status"] = "active"
            self.user["email_addresses"][0]["verification"]["status"] = "unverified"
            with self.assertRaises(PermissionError):
                self.identity(origin)
            self.user["email_addresses"][0] = {"email_address": "outsider@example.invalid",
                                               "verification": {"status": "verified"}}
            with self.assertRaises(PermissionError):
                self.identity(origin)
        with patch.object(jwt, "PyJWKClient") as client, patch.object(studio_auth, "urlopen") as remote:
            with self.assertRaises(PermissionError):
                self.identity(origin, host="evil.invalid")
            client.assert_not_called()
            remote.assert_not_called()


class ProtectedDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the real request handlers; no release DB should be touched.
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), PrettyURLHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET", cookie=None, headers=None):
        headers = dict(headers or {})
        if cookie:
            headers["Cookie"] = cookie
        request = Request(self.origin + path, method=method, headers=headers,
                          data=b"{}" if method == "POST" else None)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read().decode(), response.headers

    def test_public_jwks_proxy_keeps_each_allowlisted_host_identity(self):
        for origin in ORIGINS:
            with self.subTest(origin=origin):
                response = io.BytesIO(b'{"keys":[]}')
                response.status = 200
                response.headers = Message()
                response.headers["Content-Type"] = "application/json"
                opener = Mock()
                opener.open.return_value = response
                with patch.dict(os.environ, {"REPLIT_DEPLOYMENT": "1", "CLERK_SECRET_KEY": "fixture-only"}), \
                     patch.object(studio_site, "build_opener", return_value=opener):
                    status, body, _ = self.request("/api/__clerk/.well-known/jwks.json",
                                                  headers={"X-Forwarded-Host": origin.removeprefix("https://")})
                    self.assertEqual(status, 200)
                    self.assertEqual(json.loads(body), {"keys": []})
                    upstream = opener.open.call_args.args[0]
                    self.assertEqual(upstream.full_url, "https://frontend-api.clerk.dev/.well-known/jwks.json")
                    self.assertEqual(upstream.get_header("Clerk-proxy-url"), origin + "/api/__clerk")
                    self.assertEqual(upstream.get_header("Clerk-secret-key"), "fixture-only")
                    opener.reset_mock()
                    status, _, _ = self.request("/api/__clerk/.well-known/jwks.json",
                                                headers={"X-Forwarded-Host": "evil.invalid"})
                    self.assertEqual(status, 403)
                    opener.open.assert_not_called()

    def test_public_presentation_does_not_expose_dynamic_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            (build / "assets").mkdir()
            (build / ".vite").mkdir()
            (build / "index.html").write_text("<h1>Fixture login</h1>")
            for name, text in {"login.js": "public login", "shared.js": "public runtime",
                               "review.js": "PRIVATE_FIXTURE", "nested.js": "PRIVATE_FIXTURE",
                               "review.css": ".review{color:plum}"}.items():
                (build / "assets" / name).write_text(text)
            (build / ".vite/manifest.json").write_text(json.dumps({
                "index.html": {"file": "assets/login.js", "imports": ["shared"], "dynamicImports": ["review"]},
                "shared": {"file": "assets/shared.js"},
                "review": {"file": "assets/review.js", "imports": ["nested"], "css": ["assets/review.css"]},
                "nested": {"file": "assets/nested.js"},
            }))
            with patch.object(studio_site, "BUILD", build):
                for path in ("/studio/", "/studio/sign-in", "/studio/preview/elh-marketing-hub/Hub",
                             "/studio/assets/login.js", "/studio/assets/shared.js", "/studio/assets/review.css"):
                    self.assertEqual(self.request(path)[0], 200, path)
                for cookie in (None, "__session=unapproved-fixture"):
                    with patch.object(studio_auth, "reviewer", side_effect=PermissionError("Denied")):
                        for path in ("/studio/assets/review.js", "/studio/assets/%72eview.js",
                                     "/studio/assets/../assets/review.js", "/studio/assets/nested.js"):
                            for method in ("GET", "HEAD"):
                                status, body, _ = self.request(path, method, cookie)
                                self.assertEqual(status, 401, path)
                                self.assertNotIn("PRIVATE_FIXTURE", body)
                with patch.object(studio_auth, "reviewer", return_value="fixture"):
                    status, body, headers = self.request("/studio/assets/review.js")
                    self.assertEqual(status, 200)
                    self.assertEqual(body, "PRIVATE_FIXTURE")
                    self.assertEqual(headers["Cache-Control"], "no-store")

    def test_private_apis_reject_anonymous_and_unauthorized_accounts_before_database_access(self):
        with patch.object(journal_release, "connect", side_effect=AssertionError("Private database accessed")) as db:
            for cookie in (None, "__session=unapproved-fixture"):
                with patch.object(studio_auth, "reviewer_identity", side_effect=PermissionError("Denied")):
                    for route in ("/api/studio/session", "/api/studio/journal",
                                  "/api/studio/journal/history?slug=fixture"):
                        for method in ("GET", "HEAD", "POST"):
                            status, _, _ = self.request(route, method, cookie)
                            self.assertEqual(status, 403 if cookie else 401, (route, method))
            db.assert_not_called()
        with patch.object(studio_auth, "reviewer_identity", return_value=studio_auth.ReviewerIdentity("fixture")):
            status, body, headers = self.request("/api/studio/session")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"verified": True})
            self.assertEqual(headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    if not program.result.wasSuccessful():
        sys.exit(1)
    print("SENTINEL: test-studio-access.py protected access checks OK")
