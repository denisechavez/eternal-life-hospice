#!/usr/bin/env python3
"""Synthetic transport only; never sends email or creates live leads."""
import contextlib
import html
import io
from pathlib import Path
import re
import unittest
from unittest import mock

import acknowledgments as ack
import form_intake as intake


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
    def test_every_form_and_interest_one_ack_after_internal_record(self):
        cases = [(form, "", key) for form, key in ack.FORM_TEMPLATE.items()]
        cases += [("elh-voice", key, key) for key in ack.INTEREST_LABELS]
        self.assertEqual(len(cases), 14)
        for form, interest, key in cases:
            with self.subTest(form=form, interest=interest):
                files = {"resume": intake.UploadedFile("synthetic.pdf", "application/pdf", b"%PDF-synthetic")} if form == "elh-careers" else {}
                mailer = Mailer()
                result = intake.process_submission(fields_for(form, interest), files, mailer)
                self.assertTrue(result["accepted"])
                self.assertTrue(result["acknowledgement_sent"])
                self.assertEqual(len(mailer.payloads), 2)
                internal, receipt = mailer.payloads
                self.assertEqual(receipt["subject"], ack.TEMPLATES[key][0])
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
                if key in ack.CARE_TEMPLATES:
                    for line in ack.CTA_LINES:
                        self.assertEqual(receipt["textContent"].count(line), 1)
                        self.assertEqual(visible.count(line), 1)
                    self.assertIn('href="tel:18059537273"', receipt["htmlContent"])
                    self.assertEqual(result["care_cta_html"], ack.CTA_HTML)
                else:
                    self.assertNotIn(ack.CTA_LINES[1], receipt["textContent"])
                    self.assertEqual(result["care_cta_html"], "")
                self.assertIn("logo-cream.png", receipt["htmlContent"])

    def test_original_approved_paragraphs_preserved_except_cta_override(self):
        source = Path(__file__).resolve().parents[1] / "attached_assets/Pasted--REPLIT-IMPLEMENTATION-PROMPT-Eternal-Life-Hospice-Onli_1793083166942.txt"
        if not source.exists():
            self.skipTest("Approval attachment not present in this checkout")
        document = source.read_text()
        for key, (_, body) in ack.TEMPLATES.items():
            for paragraph in body.split("\n\n"):
                if paragraph in {"{cta}", "If your inquiry involves care for yourself or someone you love:"}:
                    continue
                with self.subTest(key=key, paragraph=paragraph[:50]):
                    self.assertIn(paragraph, document.replace("**", "").replace("*", ""))

    def test_historical_labels_and_ids_route_identically(self):
        for key, label in ack.INTEREST_LABELS.items():
            self.assertEqual(ack.template_key("elh-voice", {"interest": label}), key)
            self.assertEqual(ack.template_key("elh-voice", {"interest": key}), key)

    def test_all_interests_retains_categories_and_flags_but_one_receipt(self):
        mailer = Mailer()
        intake.process_submission(fields_for("elh-voice", "All of the above"), {}, mailer)
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
            intake.process_submission(fields_for("elh-voice", key), {}, mailer)
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
            result = intake.process_submission(fields, {}, mailer)
            self.assertTrue(result["accepted"])
            self.assertFalse(result["acknowledgement_sent"])
            self.assertEqual(len(mailer.payloads), 1)
            self.assertEqual(result["care_cta_html"], ack.CTA_HTML)

    def test_internal_failure_never_sends_receipt(self):
        mailer = Mailer(fail_at=1)
        with self.assertRaises(intake.DeliveryError):
            intake.process_submission(fields_for("elh-family"), {}, mailer)
        self.assertEqual(len(mailer.payloads), 1)

    def test_ack_failure_keeps_original_internal_record_and_reports_status(self):
        mailer = Mailer(fail_at=2)
        logs = io.StringIO()
        with contextlib.redirect_stderr(logs), mock.patch.object(
            intake, "notify_acknowledgement_failure"
        ) as notify:
            result = intake.process_submission(fields_for("elh-family"), {}, mailer)
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
            intake.process_submission(fields_for("elh-voice", "unknown-id"), {}, mailer)
        self.assertFalse(mailer.payloads)


if __name__ == "__main__":
    unittest.main(verbosity=2)
