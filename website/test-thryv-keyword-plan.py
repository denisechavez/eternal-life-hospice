#!/usr/bin/env python3
"""Validate audit preservation and private Thryv review, without publishing."""
import csv
import hashlib
import json
import re
import importlib.util
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "exports/site-audits/seo-keyword-stage-one-2026-10-08"
CURRENT = ROOT / "exports/site-audits/seo-keyword-101-2026-10-08"


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    master = json.loads((ROOT / "website/content/seo-keyword-master.json").read_text())
    drafts = json.loads((ROOT / "website/content/seo-private-review.json").read_text())
    provenance = json.loads((CURRENT / "provenance.json").read_text())
    assert master["termCount"] == 101
    assert [k["id"] for k in master["keywords"]] == list(range(1, 102))
    for old_name, new_name in [
        ("keyword-coverage-96.csv", "keyword-coverage-101.csv"),
        ("three-cycle-proposed-mapping.csv", "three-cycle-proposed-mapping-101.csv"),
    ]:
        old, new = rows(BASE / old_name), rows(CURRENT / new_name)
        assert len(old) == 288 and len(new) == 303
        for cycle in ("C1", "C2", "C3"):
            assert sorted(int(r["Keyword ID"]) for r in new if r["Cycle"] == cycle) == list(range(1, 102))
        for original in old:
            current = next(r for r in new if r["Cycle"] == original["Cycle"] and r["Keyword ID"] == original["Keyword ID"])
            assert all(current[key] == value for key, value in original.items())
    for name, expected in provenance["originalAuditHashes"].items():
        assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == expected
    assert len(drafts["articles"]) == 5
    for slug, draft in drafts["articles"].items():
        public = (ROOT / "website/elh-preview/blog" / (slug + ".html")).read_text()
        assert hashlib.sha256(public.encode()).hexdigest() == provenance["publicArticleHashes"][slug]
        # Removing the inserted paragraphs restores the original byte-for-byte.
        content = draft["reviewHtml"]
        heading = '<h2>' + draft["sections"][0]["heading"] + '</h2>'
        begin = content.index(heading)
        end = content.index("<h2", begin + len(heading))
        assert content[:begin] + content[end:] == public
        assert 2 <= len(re.findall(r'<a[^>]+class="elh-inline-link"', content)) <= 7
        assert draft["revision"] == hashlib.sha256(content.encode()).hexdigest()[:12]
        assert len(re.findall(r"<h1\b", content)) == len(re.findall(r"<h1\b", public)) == 1
        assert re.findall(r'<img[^>]+src="([^"]+)"', content) == re.findall(r'<img[^>]+src="([^"]+)"', public)
    rolling = rows(CURRENT / "rolling-new-terms.csv")
    assert len(rolling) == 56 and all(r["Draft placements"] for r in rolling)
    for channel in ["social", "pinterest", "shortVideo"]:
        items = drafts[channel]
        assert len(items) == 15 and len({item["title"] for item in items}) == 15
        for cycle in ["C1", "C2", "C3"]:
            assert {i for item in items if item["cycle"] == cycle for i in item["keywordIds"]} == set(range(97, 102))
        assert all(len(item["title"]) <= 100 for item in items)
    emails = drafts["weeklyEmail"]
    assert len(emails) == 12 and len({email["sendDate"] for email in emails}) == 12
    assert all("{{ unsubscribe }}" in email["html"] for email in emails)
    rankings = rows(CURRENT / "thryv-ranking-observations.csv")
    assert len(rankings) == 5 and all(not r["Rank"] and not r["Observed date"] for r in rankings)
    assert not list((ROOT / "website/elh-preview").rglob("seo-private-review.json"))
    print("PASS: 101 IDs, preserved audit, 303 coverage/mapping rows, private drafts, unchanged images/URLs/dates, 56 planned windows and separate empty rankings.")


def browser_check():
    spec = importlib.util.spec_from_file_location("studio_tools", ROOT / "website/test-header-mobile.py")
    tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="elh-thryv-browser-") as profile:
        process = subprocess.Popen([tools.browser_binary(), "--headless=new", "--no-sandbox",
            "--disable-gpu", "--remote-allow-origins=*", f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            client = tools.DevTools(tools.wait_for_page_debugger(port))
            client.call("Page.enable")
            client.call("Emulation.setDeviceMetricsOverride", {"width":1728,"height":980,"deviceScaleFactor":1,"mobile":False})
            url = "http://127.0.0.1:21921/__reviews-mockup/preview/elh-marketing-hub/Hub?view="
            def evaluate(expression):
                return client.call("Runtime.evaluate", {"expression":expression,"returnByValue":True})["result"].get("value")
            def wait(expression):
                for _ in range(200):
                    if evaluate(expression):
                        return
                    time.sleep(.1)
                raise AssertionError(expression)
            client.call("Page.navigate", {"url":url+"Journal"})
            wait("document.querySelectorAll('.studio-row').length===107")
            assert evaluate("[...document.querySelectorAll('summary')].some(e=>e.textContent.includes('101 keyword IDs'))")
            assert evaluate("document.querySelector('details table tbody').children.length===101")
            # An older saved approval must not approve a new revision.
            evaluate("""localStorage.setItem('egi-publication-statuses-v4',JSON.stringify({
                'j-thousand-oaks-families-coordinating-care-when-relatives-live-far-away':'Approved'
            }))""")
            previous_document = evaluate("performance.timeOrigin")
            client.call("Page.reload")
            wait(f"performance.timeOrigin!=={previous_document} && document.querySelectorAll('.studio-row').length===107")
            selector = "[...document.querySelectorAll('.studio-row')].find(e=>e.textContent.includes('Thousand Oaks Families: Coordinating'))"
            assert evaluate(f"{selector}.textContent.includes('Private SEO draft') && {selector}.textContent.includes('Needs review')"), evaluate(f"{selector}.textContent")
            evaluate(f"{selector}.click()")
            wait("document.querySelector('.article-review iframe')?.contentDocument?.body.innerText.includes('Keep nursing updates useful')")
            assert evaluate("document.querySelector('.detail-body').innerText.includes('previous approvals do not carry over')")
            assert evaluate("document.querySelector('.article-review iframe').contentDocument.querySelectorAll('h1').length===1")
            client.call("Page.navigate", {"url":url+"Emails"})
            wait("document.querySelectorAll('.studio-row').length===18")
            assert evaluate("[...document.querySelectorAll('.studio-row')].filter(e=>e.textContent.includes('Private SEO draft')).length===12")
            evaluate("[...document.querySelectorAll('.studio-row')].find(e=>e.textContent.includes('Private SEO draft')).click()")
            wait("document.querySelector('.email-review iframe')?.contentDocument?.body.innerText.includes('not a queued or scheduled campaign')")
            print("PASS: Studio shows 101 terms, fresh article review, old approval isolation and 12 readable private email drafts.")
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
    if "--browser" in sys.argv:
        browser_check()
