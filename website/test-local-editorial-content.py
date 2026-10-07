#!/usr/bin/env python3
"""Regression checks for local content repetition and the published issue archive."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "elh-preview"
spec = importlib.util.spec_from_file_location("city_audit", ROOT / "audit-city-redundancy.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ParagraphMeasurementTests(unittest.TestCase):
    def test_normalizes_geography_and_inline_markup(self):
        corpus = {
            "a": "<main><p>Care in <strong>Acton</strong>, Ventura County.</p></main>",
            "b": "<main><p>Care in Agoura Hills, Los Angeles County.</p></main>",
        }
        pattern = re.compile(r"\b(?:Acton|Agoura Hills)\b", re.I)
        result = audit.paragraph_repetition(corpus, pattern, minimum_pages=2)
        self.assertEqual(result["pages_at_least_half_repeated"], 2)
        self.assertEqual(result["mean_repeated_percent"], 100)

    def test_uses_distinct_pages_not_occurrences(self):
        corpus = {
            "a": "<main><p>One repeated paragraph.</p><p>One repeated paragraph.</p></main>",
            "b": "<main><p>Other useful guidance.</p></main>",
        }
        result = audit.paragraph_repetition(corpus, re.compile("never-match"), 2)
        self.assertEqual(result["mean_repeated_percent"], 0)

    def test_excludes_shared_chrome_and_non_paragraph_text(self):
        markup = ("<header><p>header</p></header><main><nav><p>nav</p></nav>"
                  "<h2>Heading</h2><p>Family &amp; caregiver guidance.</p>"
                  "<script>ignore</script><style>ignore</style></main>"
                  "<footer><p>footer</p></footer>")
        result = audit.paragraph_repetition({"a": markup}, re.compile("never-match"))
        self.assertEqual(result["per_page"]["a"]["paragraph_words"], 4)

    def test_twenty_page_threshold(self):
        corpus = {str(i): "<main><p>Same paragraph.</p></main>" for i in range(19)}
        self.assertEqual(audit.paragraph_repetition(
            corpus, re.compile("never-match"))["mean_repeated_percent"], 0)
        corpus["20"] = corpus["0"]
        self.assertEqual(audit.paragraph_repetition(
            corpus, re.compile("never-match"))["mean_repeated_percent"], 100)


class PublishedContentTests(unittest.TestCase):
    def test_city_cluster_is_not_majority_template_copy(self):
        cities = [c for c in json.loads((ROOT / "city-data.json").read_text())
                  if c.get("publishStatus") == "published"]
        names = sorted({c["city"] for c in cities}, key=len, reverse=True)
        pattern = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, names)) +
                             r")(?!\w)", re.I)
        corpus = {c["slug"]: (PUBLIC / f"hospice-{c['slug']}-ca.html").read_text()
                  for c in cities}
        result = audit.paragraph_repetition(corpus, pattern)
        self.assertEqual(result["page_count"], len(cities))
        self.assertEqual(result["pages_at_least_half_repeated"], 0,
                         "Review source city content; do not edit generated pages.")

    def test_issue_archive_has_no_unpublished_teaser(self):
        page = (PUBLIC / "care-brief/issue-1.html").read_text()
        menu = re.search(r'<div class="cb-archive-menu">(.*?)</div>', page, re.S).group(1)
        self.assertNotIn("cb-arch-soon", menu)
        self.assertNotRegex(menu, r"(?i)coming\s+\w+\s+20\d\d")
        self.assertIn("Issue One", menu)
        self.assertIn('href="/blog/the-caregiver-who-needs-care"', menu)
        self.assertTrue((PUBLIC / "blog/the-caregiver-who-needs-care.html").is_file())


if __name__ == "__main__":
    unittest.main()
