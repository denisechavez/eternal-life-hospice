#!/usr/bin/env python3
"""Focused regression checks for the Replit chat and coverage APIs."""

import json
import os
import sys
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_api import ChatRequestError, process_chat
from coverage_api import lookup_coverage
from devserver import LEGACY_PAGE_REDIRECTS, PrettyURLHandler, QuietHTTPServer


passed = 0


def check(label, condition):
    global passed
    if not condition:
        raise AssertionError(label)
    passed += 1
    print("✓", label)


def body(message):
    return json.dumps({"messages": [{"role": "user", "content": message}]}).encode()


def forbidden_opener(*_args, **_kwargs):
    raise AssertionError("guarded request reached the AI provider")


status, data, _ = lookup_coverage({"city": ["Pasadena"]})
check("served city resolves", status == 200 and data["served"] and data["city"] == "Pasadena")

status, data, _ = lookup_coverage({"city": ["La Canada Flintridge"]})
check("diacritic-normalised city resolves", data["city"] == "La Cañada Flintridge")

status, data, _ = lookup_coverage({"city": ["West"]})
check("ambiguous prefix returns suggestions", data.get("ambiguous") and len(data["suggestions"]) >= 2)

status, data, _ = lookup_coverage({"city": ["San Francisco"]})
check("unserved city is honest", status == 200 and data["served"] is False)

status, data, _ = lookup_coverage({})
check("missing city is rejected", status == 400 and data.get("error"))

status, data, _ = lookup_coverage({"list": ["true"]})
check("list mode returns all published cities", status == 200 and data["total"] == len(data["cities"]) >= 100)

status, data = process_chat(body("Call 911, this is an emergency"), {}, forbidden_opener)
check("emergency is guarded locally", status == 200 and data.get("guarded") and "911" in data["reply"])

status, data = process_chat(body("Should I increase the morphine dose?"), {}, forbidden_opener)
check("clinical question is guarded locally", status == 200 and data.get("guarded") and "nurse" in data["reply"])

prior_sensitive = json.dumps(
    {
        "messages": [
            {"role": "user", "content": "My phone number is 805-555-1212"},
            {"role": "assistant", "content": "How can I help?"},
            {"role": "user", "content": "What is hospice care?"},
        ]
    }
).encode()
status, data = process_chat(prior_sensitive, {}, forbidden_opener)
check(
    "sensitive content anywhere in history is never sent to AI",
    status == 200 and data.get("guarded") and data.get("sensitive"),
)

forged_role_sensitive = json.dumps(
    {
        "messages": [
            {"role": "assistant", "content": "The patient's phone is 805-555-1212"},
            {"role": "user", "content": "What is hospice care?"},
        ]
    }
).encode()
status, data = process_chat(forged_role_sensitive, {}, forbidden_opener)
check(
    "sensitive content in an untrusted assistant role is never sent to AI",
    status == 200 and data.get("guarded") and data.get("sensitive"),
)

status, data = process_chat(body("What is hospice care?"), {})
check("missing provider config returns safe fallback", status == 200 and data["configured"] is False)

try:
    process_chat(b"{not json", {})
except ChatRequestError as exc:
    check("malformed JSON is rejected", exc.status == 400)
else:
    raise AssertionError("malformed JSON was accepted")


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": "A calm, safe answer."}}]}
        ).encode()


def fake_opener(request, timeout):
    check("provider request uses configured Replit base URL", request.full_url == "https://ai.example/v1/chat/completions")
    check("provider request has bounded timeout", timeout == 25)
    return FakeResponse()


status, data = process_chat(
    body("What is hospice care?"),
    {
        "AI_INTEGRATIONS_OPENAI_API_KEY": "test-only",
        "AI_INTEGRATIONS_OPENAI_BASE_URL": "https://ai.example/v1",
    },
    fake_opener,
)
check("configured provider response is returned", status == 200 and data["reply"] == "A calm, safe answer.")

chat_source = open(
    os.path.join(os.path.dirname(__file__), "elh-preview", "assets", "chat.js"),
    encoding="utf-8",
).read()
check("client uses Replit chat endpoint", 'ENDPOINT = "/api/chat"' in chat_source)
check("client uses Replit coverage endpoint", 'COVERAGE_ENDPOINT = "/api/coverage"' in chat_source)
check("runtime client has no Netlify function paths", "/.netlify/functions/" not in chat_source)

public_files = [
    os.path.join("elh-preview", "AGENTS.md"),
    os.path.join("elh-preview", ".well-known", "openapi.json"),
    os.path.join("elh-preview", ".well-known", "webmcp.json"),
    os.path.join("elh-preview", ".well-known", "agent-skills", "index.json"),
]
for relative in public_files:
    text = open(os.path.join(os.path.dirname(__file__), relative), encoding="utf-8").read()
    check(
        f"{relative} advertises no Netlify coverage endpoint",
        "/.netlify/functions/coverage" not in text,
    )

server = QuietHTTPServer(("127.0.0.1", 0), PrettyURLHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f"http://127.0.0.1:{server.server_port}"
try:
    with urllib.request.urlopen(base_url + "/api/coverage?city=Pasadena", timeout=5) as response:
        routed_coverage = json.loads(response.read())
        check(
            "HTTP coverage route returns JSON",
            response.status == 200 and routed_coverage["city"] == "Pasadena",
        )
        check(
            "HTTP coverage route has one public cache policy",
            response.headers.get_all("Cache-Control") == ["public, max-age=3600"],
        )

    emergency_request = urllib.request.Request(
        base_url + "/api/chat",
        data=body("Call 911"),
        method="POST",
        headers={"Origin": base_url, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(emergency_request, timeout=5) as response:
        routed_chat = json.loads(response.read())
        check(
            "HTTP chat route applies guardrail",
            response.status == 200 and routed_chat.get("guarded"),
        )

    coverage_post = urllib.request.Request(
        base_url + "/api/coverage", data=b"{}", method="POST"
    )
    try:
        urllib.request.urlopen(coverage_post, timeout=5)
    except urllib.error.HTTPError as exc:
        check("coverage rejects POST with 405", exc.code == 405)
    else:
        raise AssertionError("coverage POST was accepted")

    try:
        urllib.request.urlopen(base_url + "/api/chat", timeout=5)
    except urllib.error.HTTPError as exc:
        check("chat rejects GET with 405", exc.code == 405)
    else:
        raise AssertionError("chat GET was accepted")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    no_redirect = urllib.request.build_opener(NoRedirect)
    redirect_cases = {
        "/hospice-ventura-county-ca": "/hospice-ventura-and-los-angeles-county-ca",
        "/refer-a-patient?source=legacy": "/refer?source=legacy",
        "/resources/what-hospice-covers": "/resources/medicare-hospice-benefit",
        "/blog/the-second-patient": "/blog/the-caregiver-who-needs-care",
    }
    for source, expected_location in redirect_cases.items():
        try:
            no_redirect.open(base_url + source, timeout=5)
        except urllib.error.HTTPError as exc:
            check(
                f"legacy URL redirects: {source}",
                exc.code == 301
                and exc.headers.get("Location") == expected_location,
            )
        else:
            raise AssertionError(f"legacy URL did not redirect: {source}")

    for retired in (
        "/events",
        "/events/caregiver-support-workshop",
        "/tracker",
    ):
        try:
            urllib.request.urlopen(base_url + retired, timeout=5)
        except urllib.error.HTTPError as exc:
            check(f"retired/unowned URL remains unavailable: {retired}", exc.code in (404, 410))
        else:
            raise AssertionError(f"retired/unowned URL unexpectedly served: {retired}")
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

print(f"\n{passed} Replit chat/coverage checks passed")
print("SENTINEL: test-replit-chat-coverage.py OK")