#!/usr/bin/env python3
"""Synthetic transport only; never sends email or creates live leads."""
import contextlib
import html
import io
import json
from pathlib import Path
import re
import unittest
from unittest import mock
from unittest.mock import patch

import acknowledgments as ack
import form_intake as intake


def synthetic_submission(fields, files, mailer):
    return intake.process_submission(fields, files, mailer,
        acknowledgement_mailer=mailer)


APPROVED = json.loads(
    (Path(__file__).resolve().parent / "test-fixtures/acknowledgments-approved.json")
    .read_text(encoding="utf-8")
)


class Mailer:
    def __init__(self, fail_at=0):
        self.payloads = []
        self.fail_at = fail_at

    def send(self, payload):
        self.payloads.append(payload)
        if len(self.payloads) == self.fail_at:
            raise intake.DeliveryError("synthetic failure")
        return "synthetic-record-" + str(len(self.payloads))


def fields_for(form, interest=""):
    fields = {
        "form-name": form, "first_name": "Synthetic", "last_name": "Visitor",
        "name": "Synthetic Visitor", "provider_first_name": "Synthetic",
        "provider_last_name": "Professional", "phone": "2025550190",
        "email": "synthetic@example.com", "role": "Synthetic role",
        "organization": "Synthetic Organization", "interest": interest,
        "message": "SYNTHETIC-PRIVATE-MESSAGE", "preferred_time": "Afternoons",
    }
    return fields


class AcknowledgmentTests(unittest.TestCase):
    def setUp(self):
        # Fail closed if a regression reaches a real email/alert transport.
        for target in ("socket.socket.connect", "socket.create_connection",
                       "urllib.request.urlopen"):
            blocker = patch(target, side_effect=AssertionError("External transport forbidden"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def test_every_form_and_interest_one_ack_after_internal_record(self):
        cases = [(form, "", key) for form, key in APPROVED["form_templates"].items()]
        cases += [("elh-voice", key, key) for key in APPROVED["interest_labels"]]
        self.assertEqual(len(cases), 14)
        for form, interest, key in cases:
            with self.subTest(form=form, interest=interest):
                files = {"resume": intake.UploadedFile("synthetic.pdf", "application/pdf", b"%PDF-synthetic")} if form == "elh-careers" else {}
                mailer = Mailer()
                result = synthetic_submission(fields_for(form, interest), files, mailer)
                self.assertTrue(result["accepted"])
                self.assertTrue(result["acknowledgement_sent"])
                self.assertEqual(len(mailer.payloads), 2)
                internal, receipt = mailer.payloads
                self.assertEqual(receipt["subject"], APPROVED["templates"][key]["subject"])
                self.assertIn("Synthetic", receipt["textContent"])
                self.assertIn(result["receipt_id"], receipt["textContent"])
                self.assertIn(result["receipt_id"], internal["textContent"])
                self.assertNotIn("SYNTHETIC-PRIVATE-MESSAGE", receipt["textContent"] + receipt["htmlContent"])
                self.assertNotIn("Synthetic Organization", receipt["textContent"])
                self.assertIn("Submission timestamp:", internal["textContent"])
                self.assertIn("Follow-up status: New", internal["textContent"])
                destination = intake.REFERRAL_EMAIL if intake.FORM_RULES[form].referral else intake.CONTACT_EMAIL
                self.assertEqual(internal["to"][0]["email"], destination)
                visible = html.unescape(re.sub("<[^>]+>", " ", receipt["htmlContent"]))
                if key in APPROVED["care_templates"]:
                    for line in APPROVED["care_cta"]:
                        self.assertEqual(receipt["textContent"].count(line), 1)
                        self.assertEqual(visible.count(line), 1)
                    self.assertIn('href="tel:18059537273"', receipt["htmlContent"])
                    self.assertEqual(result["care_cta_html"], ack.CTA_HTML)
                else:
                    self.assertNotIn(ack.CTA_LINES[1], receipt["textContent"])
                    self.assertEqual(result["care_cta_html"], "")
                self.assertIn("logo-plum.png", receipt["htmlContent"])
                self.assertIn("Correspondence", receipt["htmlContent"])
                self.assertIn("4165 E Thousand Oaks Blvd, Suite 325B", receipt["htmlContent"])
                self.assertIn("Westlake Village, CA 91362", receipt["htmlContent"])
                self.assertNotIn("text-decoration:underline", receipt["htmlContent"])
                self.assertNotIn("color:#3C1C3B", receipt["htmlContent"])

    def test_original_approved_paragraphs_preserved_except_cta_override(self):
        self.assertEqual(len(APPROVED["templates"]), 14)
        self.assertEqual(set(ack.TEMPLATES), set(APPROVED["templates"]))
        self.assertEqual(list(ack.CTA_LINES), APPROVED["care_cta"])
        self.assertEqual(ack.CTA_TEXT, "\n".join(APPROVED["care_cta"]))
        self.assertEqual(sorted(ack.CARE_TEMPLATES), APPROVED["care_templates"])
        self.assertEqual(ack.FORM_TEMPLATE, APPROVED["form_templates"])
        self.assertEqual(ack.INTEREST_LABELS, APPROVED["interest_labels"])
        for key, expected in APPROVED["templates"].items():
            with self.subTest(key=key):
                subject, body = ack.TEMPLATES[key]
                self.assertEqual(subject, expected["subject"])
                self.assertEqual(body.split("\n\n"), expected["paragraphs"])
                _, text, markup = ack.render(key, "Synthetic", "SYNTHETIC", "synthetic@example.com")
                rendered = [p.replace("{cta}", "\n".join(APPROVED["care_cta"]))
                            for p in expected["paragraphs"]]
                self.assertIn("\n\n".join(rendered), text)
                visible = html.unescape(re.sub("<[^>]+>", " ", markup))
                positions = [visible.index(p) for paragraph in rendered
                             for p in paragraph.split("\n")]
                self.assertEqual(positions, sorted(positions))

    def test_historical_labels_and_ids_route_identically(self):
        for key, label in APPROVED["interest_labels"].items():
            for value in (key, label):
                with self.subTest(key=key, value=value):
                    self.assertEqual(ack.template_key("elh-voice", {"interest": value}), key)
                    mailer = Mailer()
                    result = synthetic_submission(fields_for("elh-voice", value), {}, mailer)
                    self.assertTrue(result["accepted"])
                    self.assertEqual(len(mailer.payloads), 2)
                    self.assertEqual(mailer.payloads[1]["subject"],
                                     APPROVED["templates"][key]["subject"])

    def test_all_interests_retains_categories_and_flags_but_one_receipt(self):
        mailer = Mailer()
        synthetic_submission(fields_for("elh-voice", "All of the above"), {}, mailer)
        self.assertEqual(len(mailer.payloads), 2)
        internal, receipt = mailer.payloads
        self.assertEqual(receipt["subject"], ack.TEMPLATES["all-interests"][0])
        for category in ack.request_categories("all-interests"):
            self.assertIn(category, internal["textContent"])
        for flag in set(ack.FLAGS.values()):
            self.assertIn(flag, internal["subject"])

    def test_meeting_is_not_a_speaking_engagement(self):
        for key in ("aleksandra-meeting", "speaking-engagement"):
            mailer = Mailer()
            synthetic_submission(fields_for("elh-voice", key), {}, mailer)
            self.assertEqual(mailer.payloads[1]["subject"], ack.TEMPLATES[key][0])
            self.assertIn("ALEKSANDRA — SCHEDULING REQUEST", mailer.payloads[0]["subject"])
        self.assertNotEqual(ack.TEMPLATES["aleksandra-meeting"][0], ack.TEMPLATES["speaking-engagement"][0])

    def test_fallback_escaping_and_no_personal_details(self):
        for key in ack.TEMPLATES:
            subject, text, markup = ack.render(key, "", "SYNTHETIC-RECEIPT", "info@example.com")
            self.assertTrue(text.startswith("Hello,"))
            self.assertNotIn("[First name]", text)
            _, _, escaped = ack.render(key, '<script>alert("x")</script>', "SAFE", "info@example.com")
            self.assertNotIn("<script>", escaped)
        for form in ("elh-family", "elh-coordinator", "elh-chat-callback"):
            fields = fields_for(form)
            fields.pop("email")
            mailer = Mailer()
            result = synthetic_submission(fields, {}, mailer)
            self.assertTrue(result["accepted"])
            self.assertFalse(result["acknowledgement_sent"])
            self.assertEqual(len(mailer.payloads), 1)
            self.assertEqual(result["care_cta_html"], ack.CTA_HTML)

    def test_internal_failure_never_sends_receipt(self):
        mailer = Mailer(fail_at=1)
        with self.assertRaises(intake.DeliveryError):
            synthetic_submission(fields_for("elh-family"), {}, mailer)
        self.assertEqual(len(mailer.payloads), 1)

    def test_ack_failure_keeps_original_internal_record_and_reports_status(self):
        mailer = Mailer(fail_at=2)
        logs = io.StringIO()
        with contextlib.redirect_stderr(logs), mock.patch.object(
            intake, "notify_acknowledgement_failure"
        ) as notify:
            result = synthetic_submission(fields_for("elh-family"), {}, mailer)
        notify.assert_called_once_with()
        self.assertTrue(result["accepted"])
        self.assertTrue(result["acknowledgement_error"])
        self.assertFalse(result["acknowledgement_sent"])
        self.assertEqual(result["provider_message_id"], "synthetic-record-1")
        self.assertIn("SYNTHETIC-PRIVATE-MESSAGE", mailer.payloads[0]["textContent"])
        self.assertIn("FORM_ACK_FAILED", logs.getvalue())
        self.assertNotIn("synthetic@example.com", logs.getvalue())
        self.assertNotIn("SYNTHETIC-PRIVATE-MESSAGE", logs.getvalue())

    def test_invalid_interest_rejected_before_delivery(self):
        mailer = Mailer()
        with self.assertRaises(intake.IntakeError):
            synthetic_submission(fields_for("elh-voice", "unknown-id"), {}, mailer)
        self.assertFalse(mailer.payloads)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    passed = result.wasSuccessful() and not result.skipped and result.testsRun > 0
    if passed:
        print("SENTINEL: test-acknowledgments.py OK")
    raise SystemExit(0 if passed else 1)
