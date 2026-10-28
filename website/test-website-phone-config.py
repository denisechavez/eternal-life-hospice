#!/usr/bin/env python3
"""Exercise a number change in an isolated copy, without sends or publication."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import form_antispam
import website_phone

BASE = Path(__file__).resolve().parent

PROBE = r'''
import hashlib, importlib.util, io, json, sys
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import website_phone as phone
import form_antispam, footer_contact, fragments, acknowledgments
from devserver import PrettyURLHandler
root = Path(sys.argv[2])
assert phone.MAIN_DISPLAY == "212.555.0199"
assert phone.MAIN_TEL == "12125550199"

def handler(route):
    obj = object.__new__(PrettyURLHandler)
    obj.path, obj.command = route, "GET"
    obj.directory = str(root / "elh-preview")
    obj.headers = {}
    obj.response_headers = {}
    obj.send_response = lambda status: obj.response_headers.update(status=status)
    obj.send_header = lambda name, value: obj.response_headers.update({name: value})
    obj.end_headers = lambda: None
    return obj

# Every major HTML contact surface, including schema and employee company links.
for route, filename in [
    ("/", "index.html"), ("/refer", "refer.html"),
    ("/hospice-thousand-oaks-ca", "hospice-thousand-oaks-ca.html"),
    ("/card-aleksandra-dubina", "card-aleksandra-dubina.html"),
    ("/card-denise-chavez", "card-denise-chavez.html"),
]:
    source = (root / "elh-preview" / filename).read_text()
    projected = handler(route)._service_preview_chrome(source)
    if route.startswith("/card-"):
        assert "Call Office &nbsp; 805.953.7273" in projected, filename
        assert "tel:+18059537273" in projected, filename
        continue
    assert "212.555.0199" in projected, filename
    assert "tel:12125550199" in projected or "tel:+12125550199" in projected, filename
    assert not phone.OLD_PUBLIC_PHONE.search(projected), filename
    assert "__ELH_MAIN_" not in projected, filename

# Fragments and the independent city-footer generation path.
for source in (fragments.FOOTER_HTML,):
    assert "212.555.0199 · Main" in source
    assert 'class="fc-line fc-direct no-swap" href="tel:12125550199"' in source
spec = importlib.util.spec_from_file_location("city_builder", root / "build-cities.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
for county in ("Ventura County", "Los Angeles County"):
    assert "212.555.0199 · Main" in builder.make_footer(county)

# Runtime-serving of browser sources and metadata, including query-version URLs.
for route in ["/assets/chat.js?v=previous", "/assets/intake-security.js?v=previous",
              "/.well-known/agent-card.json", "/.well-known/openapi.json",
              "/assets/aleksandra-dubina.vcf", "/assets/denise-chavez.vcf"]:
    obj = handler(route)
    response = obj.send_head()
    body = response.read().decode()
    response.close()
    assert obj.response_headers["status"] == 200, route
    assert len(body.encode()) == int(obj.response_headers["Content-Length"])
    assert "212.555.0199" in body or "12125550199" in body, route
    assert "__ELH_MAIN_" not in body and not phone.OLD_PUBLIC_PHONE.search(body), route
    if route.startswith("/assets/intake-security.js"):
        assert hashlib.sha256(body.encode()).hexdigest()[:12] == form_antispam.SECURITY_VERSION
    if route.startswith("/assets/chat.js"):
        assert hashlib.sha256(body.encode() + form_antispam.SECURITY_VERSION.encode()).hexdigest()[:12] == form_antispam.CHAT_VERSION
    if route.endswith(".json"):
        json.loads(body)

# Frozen approved Journal branch: read-only snapshot in, projection out.
article = next(path for path in (root / "elh-preview/blog").glob("*.html")
               if 'id="site-footer"' in path.read_text())
frozen = article.read_bytes()
obj = handler("/blog/" + article.stem)
obj._released_journal = lambda: {article.stem: {"html": frozen.decode(), "revision": "frozen-approved"}}
obj._hide_unreleased_links = lambda document, route: document
response = obj.send_head()
body = response.read().decode()
assert "212.555.0199" in body and not phone.OLD_PUBLIC_PHONE.search(body)
assert obj.response_headers["X-Journal-Revision"] == "frozen-approved"
assert article.read_bytes() == frozen

# Projection is scoped to the existing public API allowlist, never mail/private APIs.
approved = acknowledgments.CTA_HTML
for route in [*phone.PUBLIC_API_ROUTES, "/api/studio/email-review"]:
    obj = handler(route)
    obj.wfile = io.BytesIO()
    obj._send_json(200, {"care_cta_html": approved, "officePhone": "805.953.7273",
                         "referral_phone": "805.953.7273", "email": "referral@eternallifehospice.com"})
    result = json.loads(obj.wfile.getvalue())
    assert result["email"] == "referral@eternallifehospice.com"
    if route in phone.PUBLIC_API_ROUTES:
        assert "212.555.0199" in result["care_cta_html"]
        assert result["officePhone"] == "805.953.7273"
        assert result["referral_phone"] == "212.555.0199"
    else:
        assert result["care_cta_html"] == approved
assert acknowledgments.CTA_HTML == approved
for key in acknowledgments.TEMPLATES:
    _, text, html = acknowledgments.render(key, "Synthetic", "SYNTHETIC", "info@eternallifehospice.com")
    assert "212.555.0199" not in text + html
assert phone.public_text("Fax 805.953.8530; employee 202.555.0190; Medicare 1-800-633-4227") == \
    "Fax 805.953.8530; employee 202.555.0190; Medicare 1-800-633-4227"
formats = ["805.409.9262", "tel:18054099262", "+1-805-953-7273", "(805) 410-1151",
           "__ELH_MAIN_DISPLAY__ __ELH_MAIN_TEL__", "805.953.8530", "202.555.0190"]
print(json.dumps({"formats": [phone.public_text(value) for value in formats],
                  "security": form_antispam.SECURITY_VERSION, "chat": form_antispam.CHAT_VERSION}))
'''


class WebsitePhoneConfigTests(unittest.TestCase):
    def test_synthetic_change_projects_without_editing_protected_sources(self):
        protected = [
            BASE / "acknowledgments.py",
            *BASE.glob("elh-preview/blog/*.html"),
            *BASE.glob("content/**/*"),
            *BASE.glob("*google*"),
            *BASE.glob("*whatconverts*"),
            BASE / "website-contact.json",
            *BASE.glob("elh-preview/assets/*.vcf"),
        ]
        before = {path: hashlib.sha256(path.read_bytes()).digest()
                  for path in protected if path.is_file()}
        with tempfile.TemporaryDirectory(prefix="elh-phone-") as directory:
            temp = Path(directory)
            for filename in ("website_phone.py", "website-phone.cjs", "footer_contact.py",
                             "fragments.py", "form_antispam.py"):
                shutil.copy2(BASE / filename, temp / filename)
            assets = temp / "elh-preview/assets"
            assets.mkdir(parents=True)
            for filename in ("chat.js", "intake-security.js", "build-search-index.js"):
                shutil.copy2(BASE / "elh-preview/assets" / filename, assets / filename)
            config = dict(website_phone.CONFIG, main="2125550199")
            (temp / "website-contact.json").write_text(json.dumps(config))
            result = subprocess.run([sys.executable, "-c", PROBE, str(temp), str(BASE)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            probe = json.loads(result.stdout)
            self.assertNotEqual(probe["security"], form_antispam.SECURITY_VERSION)
            self.assertNotEqual(probe["chat"], form_antispam.CHAT_VERSION)
            node = subprocess.run(["node", "-e", """
const {publicPhoneText} = require('./website-phone.cjs');
console.log(JSON.stringify(["805.409.9262", "tel:18054099262", "+1-805-953-7273",
  "(805) 410-1151", "__ELH_MAIN_DISPLAY__ __ELH_MAIN_TEL__", "805.953.8530",
  "202.555.0190"].map(publicPhoneText)));
"""], cwd=temp, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(node.stdout), probe["formats"])

            # Real search builder, temporary HTML/index only; preserve its sources.
            html = ('<html><head><title>Call 805.409.9262 | Eternal Life Hospice</title>'
                    '<meta name="description" content="Call 805.953.7273 for guidance.">'
                    '<link rel="canonical" href="https://eternallifehospice.com/"></head></html>')
            (temp / "elh-preview/index.html").write_text(html)
            (assets / "search-index.json").write_text("[]")
            subprocess.run(["node", str(assets / "build-search-index.js")],
                           check=True, text=True, capture_output=True)
            index = (assets / "search-index.json").read_text()
            self.assertIn("212.555.0199", index)
            self.assertNotIn("805.409.9262", index)
            self.assertNotIn("805.953.7273", index)
            self.assertEqual((temp / "elh-preview/index.html").read_text(), html)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).digest() for path in before})


if __name__ == "__main__":
    unittest.main()
