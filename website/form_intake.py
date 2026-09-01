"""Production form intake for the Eternal Life Hospice website.

The public site is served by the Replit Python deployment, so Netlify form
attributes are not a delivery mechanism.  This module validates same-origin
form submissions and delivers them through Brevo without storing them locally.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from typing import Dict, Iterable, Mapping, Optional, Tuple
from urllib.parse import parse_qs


PHONE_DISPLAY = "805.953.7273"
PHONE_TEL = "18059537273"
SITE = "https://eternallifehospice.com"
BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
FROM_EMAIL = os.environ.get("FORM_FROM_EMAIL", "no-reply@eternallifehospice.com")
FROM_NAME = os.environ.get("FORM_FROM_NAME", "Eternal Life Hospice")
REFERRAL_EMAIL = os.environ.get(
    "REFERRAL_DESTINATION", "referral@eternallifehospice.com"
)
CONTACT_EMAIL = os.environ.get(
    "FORM_CONTACT_DESTINATION", "info@eternallifehospice.com"
)
MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FIELD_CHARS = 5000
MAX_REFERRAL_NOTE_CHARS = 1200
RATE_LIMIT_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 10 * 60
GLOBAL_RATE_LIMIT_ATTEMPTS = 30
FORM_ALERT_FAILURE_THRESHOLD = 3
FORM_ALERT_WINDOW_SECONDS = 5 * 60
FORM_ALERT_COOLDOWN_SECONDS = 15 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMBEDDED_EMAIL_RE = re.compile(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b")
PHONE_RE = re.compile(r"\d")
REFERRAL_NOTE_FIELDS = ("message", "situation", "needs")
POSSIBLE_PHI_PATTERNS = (
    re.compile(
        r"\b(?:dob|date of birth|birthdate|ssn|social security|mrn|"
        r"medical record number|member id|policy number|medicare number|"
        r"medi-cal number)\b",
        re.I,
    ),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(
        r"\b(?:0?[1-9]|1[0-2])[/.-](?:0?[1-9]|[12]\d|3[01])"
        r"[/.-](?:19|20)?\d{2}\b"
    ),
    re.compile(
        r"\b(?:patient|resident|client)\s+(?:is|name(?:\s+is)?|:)\s+"
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
    ),
    re.compile(
        r"\b(?:my|our)\s+(?:mother|father|mom|dad|husband|wife|spouse|parent)"
        r"\s+(?:is\s+)?(?:named\s+)?[A-Z][a-z]+"
    ),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    re.compile(
        r"\b\d{1,6}\s+[A-Za-z0-9.' -]{2,40}\s+"
        r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|"
        r"court|ct|way)\b",
        re.I,
    ),
)


class IntakeError(Exception):
    """A safe, user-correctable intake error."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class DeliveryError(Exception):
    """The transactional email provider did not accept a message."""


class DeliveryFailureAlerter:
    """Rate-limited, privacy-safe notification for internal delivery outages.

    The alert endpoint is intentionally generic so it can be hosted by a
    provider that is independent of Brevo (for example, an operations
    webhook relay). No submission data is accepted by this class.
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        environment: Optional[str] = None,
        failure_threshold: int = FORM_ALERT_FAILURE_THRESHOLD,
        window_seconds: int = FORM_ALERT_WINDOW_SECONDS,
        cooldown_seconds: int = FORM_ALERT_COOLDOWN_SECONDS,
    ):
        self.webhook_url = (
            webhook_url
            if webhook_url is not None
            else os.environ.get("FORM_ALERT_WEBHOOK_URL", "")
        ).strip()
        self.environment = (
            environment
            if environment is not None
            else os.environ.get("FORM_ALERT_ENVIRONMENT", "production")
        ).strip() or "production"
        self.failure_threshold = max(1, int(failure_threshold))
        self.window_seconds = max(1, int(window_seconds))
        self.cooldown_seconds = max(1, int(cooldown_seconds))
        self._failures = deque()
        self._last_alert_at = None
        self._lock = threading.Lock()

    def record_failure(self) -> bool:
        """Record one failed internal delivery and send at most one alert.

        Returns True only when an alert request was attempted. The request is
        deliberately best-effort: an alert outage must not turn a clear public
        delivery error into a server traceback or a different user response.
        """
        now = time.monotonic()
        should_alert = False
        failure_count = 0
        with self._lock:
            cutoff = now - self.window_seconds
            while self._failures and self._failures[0] <= cutoff:
                self._failures.popleft()
            self._failures.append(now)
            failure_count = len(self._failures)
            if (
                self.webhook_url
                and failure_count >= self.failure_threshold
                and (
                    self._last_alert_at is None
                    or now - self._last_alert_at >= self.cooldown_seconds
                )
            ):
                self._last_alert_at = now
                should_alert = True

        if not should_alert:
            return False

        payload = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "environment": self.environment,
            "processor_status": "delivery_unavailable",
            "failure_count": failure_count,
        }
        try:
            self._send(payload)
        except Exception as exc:
            # Keep this event safe even if the configured alert service
            # returns an error. Do not print its URL or response body.
            print(
                f"FORM_ALERT_FAILED channel=webhook error={type(exc).__name__}",
                file=sys.stderr,
            )
        return True

    def _send(self, payload: Mapping[str, object]) -> None:
        request = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "user-agent": "ELH-Replit-Form-Alert/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            if not 200 <= response.status < 300:
                raise OSError("alert endpoint rejected the notification")


class SlidingWindowRateLimiter:
    """Thread-safe, bounded in-memory limiter for the single-process server."""

    def __init__(self, attempts: int, window_seconds: int):
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.attempts:
                return False
            events.append(now)
            # Prevent an unbounded key map during broad bot scans.
            if len(self._events) > 5000:
                stale = [
                    item_key
                    for item_key, item_events in self._events.items()
                    if not item_events or item_events[-1] <= cutoff
                ]
                for item_key in stale[:1000]:
                    self._events.pop(item_key, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


FORM_CLIENT_RATE_LIMITER = SlidingWindowRateLimiter(
    RATE_LIMIT_ATTEMPTS, RATE_LIMIT_WINDOW_SECONDS
)
FORM_GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter(
    GLOBAL_RATE_LIMIT_ATTEMPTS, RATE_LIMIT_WINDOW_SECONDS
)
FORM_DELIVERY_ALERTER = DeliveryFailureAlerter()


def notify_delivery_failure() -> bool:
    """Notify the configured independent alert channel after a Brevo failure."""
    return FORM_DELIVERY_ALERTER.record_failure()


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class FormRule:
    label: str
    destination: str
    required: Tuple[str, ...]
    acknowledge: bool = False
    referral: bool = False
    attachment_required: bool = False


FORM_RULES: Dict[str, FormRule] = {
    "elh-family": FormRule(
        "Family care request",
        REFERRAL_EMAIL,
        ("first_name", "last_name", "phone"),
        acknowledge=True,
        referral=True,
    ),
    "elh-physician": FormRule(
        "Professional referral",
        REFERRAL_EMAIL,
        ("phone",),
        acknowledge=True,
        referral=True,
    ),
    "elh-casemanager": FormRule(
        "Case manager referral",
        REFERRAL_EMAIL,
        ("first_name", "last_name", "phone"),
        acknowledge=True,
        referral=True,
    ),
    "elh-coordinator": FormRule(
        "Care coordinator inquiry",
        REFERRAL_EMAIL,
        ("first_name", "last_name", "phone"),
        referral=True,
    ),
    "elh-chat-callback": FormRule(
        "Website chat callback",
        REFERRAL_EMAIL,
        ("name", "phone"),
        referral=True,
    ),
    "elh-voice": FormRule(
        "Care Brief contributor inquiry",
        CONTACT_EMAIL,
        ("first_name", "last_name", "email"),
        acknowledge=True,
    ),
    "elh-careers": FormRule(
        "Career application",
        CONTACT_EMAIL,
        ("first_name", "last_name", "email", "phone", "role"),
        acknowledge=True,
        attachment_required=True,
    ),
    "elh-care-brief-signup": FormRule(
        "Care Brief signup",
        CONTACT_EMAIL,
        ("email",),
        acknowledge=True,
    ),
}

# Only these fields are included in the internal email.  Unknown fields are
# ignored rather than reflected into a message.
FIELD_LABELS = {
    "audience": "Audience",
    "source": "Source",
    "first_name": "First name",
    "last_name": "Last name",
    "name": "Name",
    "referrer_name": "Referrer name",
    "provider_first_name": "Provider first name",
    "provider_last_name": "Provider last name",
    "phone": "Phone",
    "email": "Email",
    "relationship": "Relationship",
    "practice": "Practice / facility",
    "facility": "Facility",
    "organization": "Organization",
    "referrer_role": "Referrer role",
    "role": "Role",
    "npi": "NPI",
    "county": "County",
    "timeframe": "Timeframe",
    "urgency": "Urgency",
    "preferred_time": "Preferred contact time",
    "interest": "Interest",
    "message": "Message",
    "situation": "General situation (no PHI requested)",
    "needs": "General discharge needs (no PHI requested)",
}


def parse_form_body(
    content_type: str, body: bytes
) -> Tuple[Dict[str, str], Dict[str, UploadedFile]]:
    """Parse URL-encoded or multipart form data with explicit size limits."""
    if len(body) > MAX_BODY_BYTES:
        raise IntakeError(
            "payload_too_large",
            "The submission is too large. Please reduce the file size and try again.",
            413,
        )

    fields: Dict[str, str] = {}
    files: Dict[str, UploadedFile] = {}
    media_type = (content_type or "").split(";", 1)[0].strip().lower()

    if media_type == "application/x-www-form-urlencoded":
        parsed = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
        fields = {key: values[-1] for key, values in parsed.items() if values}
    elif media_type == "multipart/form-data":
        header = (
            "Content-Type: "
            + content_type
            + "\r\nMIME-Version: 1.0\r\n\r\n"
        ).encode("utf-8")
        message = BytesParser(policy=default).parsebytes(header + body)
        if not message.is_multipart():
            raise IntakeError("invalid_form", "The submitted form could not be read.")
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                files[name] = UploadedFile(
                    filename=_safe_filename(filename),
                    content_type=part.get_content_type(),
                    content=payload,
                )
            else:
                charset = part.get_content_charset() or "utf-8"
                fields[name] = payload.decode(charset, "replace")
    else:
        raise IntakeError(
            "unsupported_content_type",
            "The submitted form format is not supported.",
            415,
        )

    cleaned = {}
    for key, value in fields.items():
        if len(value) > MAX_FIELD_CHARS:
            raise IntakeError(
                "field_too_long",
                "One of the fields is too long. Please shorten it and try again.",
            )
        cleaned[key] = _clean_text(value)
    return cleaned, files


def validate_submission(
    fields: Mapping[str, str], files: Mapping[str, UploadedFile]
) -> Tuple[str, FormRule]:
    form_name = fields.get("form-name", "").strip()
    rule = FORM_RULES.get(form_name)
    if not rule:
        raise IntakeError("unknown_form", "This form is not recognized.")

    if fields.get("bot-field", "").strip():
        return form_name, rule

    missing = [name for name in rule.required if not fields.get(name, "").strip()]
    if form_name == "elh-physician":
        has_referrer = bool(fields.get("referrer_name", "").strip())
        has_provider = bool(
            fields.get("provider_first_name", "").strip()
            and fields.get("provider_last_name", "").strip()
        )
        if not has_referrer and not has_provider:
            missing.append("name")

    if missing:
        raise IntakeError(
            "missing_required",
            "Please complete all required fields and try again.",
        )

    phone = fields.get("phone", "")
    if phone and len(PHONE_RE.findall(phone)) < 10:
        raise IntakeError("invalid_phone", "Please enter a valid callback phone number.")

    email = fields.get("email", "")
    if email and not EMAIL_RE.match(email):
        raise IntakeError("invalid_email", "Please enter a valid email address.")

    if rule.attachment_required:
        resume = files.get("resume")
        if not resume or not resume.content:
            raise IntakeError("missing_resume", "Please attach your résumé and try again.")
        if len(resume.content) > MAX_FILE_BYTES:
            raise IntakeError(
                "file_too_large",
                "The résumé must be 5 MB or smaller.",
                413,
            )
        extension = os.path.splitext(resume.filename)[1].lower()
        if extension not in {".pdf", ".doc", ".docx"}:
            raise IntakeError(
                "invalid_file_type",
                "Please attach a PDF or Word document.",
            )

    if rule.referral:
        _validate_referral_notes(fields)

    return form_name, rule


def _validate_referral_notes(fields: Mapping[str, str]) -> None:
    """Reject common identifiers before a referral note reaches Brevo.

    This is intentionally conservative and complements, rather than replaces,
    the form's instruction to share only a general non-identifying situation.
    """
    for field_name in REFERRAL_NOTE_FIELDS:
        value = fields.get(field_name, "").strip()
        if not value:
            continue
        if len(value) > MAX_REFERRAL_NOTE_CHARS:
            raise IntakeError(
                "referral_note_too_long",
                "Please shorten the note to a general, non-identifying summary.",
            )
        if EMBEDDED_EMAIL_RE.search(value) or any(
            pattern.search(value) for pattern in POSSIBLE_PHI_PATTERNS
        ):
            raise IntakeError(
                "possible_phi",
                (
                    "For privacy, remove patient names, dates of birth, "
                    "addresses, and record or insurance numbers. Share only a "
                    f"general situation, or call {PHONE_DISPLAY}."
                ),
            )


class BrevoMailer:
    """Small Brevo transactional-email client using the Python standard library."""

    def __init__(self, api_key: Optional[str] = None, endpoint: str = BREVO_ENDPOINT):
        self.api_key = api_key if api_key is not None else os.environ.get("BREVO_API", "")
        self.endpoint = endpoint

    def send(self, payload: Mapping[str, object]) -> str:
        if not self.api_key:
            raise DeliveryError("BREVO_API is not configured")
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "api-key": self.api_key,
                "accept": "application/json",
                "content-type": "application/json",
                "user-agent": "ELH-Replit-Form-Intake/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                raw = response.read(16_384)
                if response.status not in (200, 201, 202):
                    raise DeliveryError("Brevo rejected the message")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DeliveryError("Brevo delivery request failed") from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = {}
        return str(data.get("messageId") or "")


def process_submission(
    fields: Mapping[str, str],
    files: Mapping[str, UploadedFile],
    mailer: Optional[BrevoMailer] = None,
) -> Dict[str, object]:
    """Validate, deliver internally, then optionally send a static acknowledgement."""
    form_name, rule = validate_submission(fields, files)

    # Honeypot requests are accepted without sending or storing anything. This
    # avoids teaching bots whether they were detected.
    if fields.get("bot-field", "").strip():
        return {"ok": True, "accepted": True, "acknowledgement_sent": False}

    receipt_id = secrets.token_hex(6).upper()
    sender_name = _sender_name(fields) or "Website visitor"
    subject = f"{rule.label} — {sender_name} [{receipt_id}]"
    text, html_body = _internal_message(rule, fields, receipt_id)
    payload: Dict[str, object] = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": rule.destination, "name": "Eternal Life Hospice Intake"}],
        "replyTo": {"email": CONTACT_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "textContent": text,
        "htmlContent": html_body,
        "headers": {
            "X-ELH-Form": form_name,
            "X-ELH-Receipt": receipt_id,
        },
        "tags": ["website-intake", form_name],
    }

    email = fields.get("email", "").strip().lower()
    if email and EMAIL_RE.match(email):
        payload["replyTo"] = {"email": email, "name": sender_name}

    resume = files.get("resume")
    if resume:
        payload["attachment"] = [
            {
                "name": resume.filename,
                "content": base64.b64encode(resume.content).decode("ascii"),
            }
        ]

    active_mailer = mailer or BrevoMailer()
    provider_id = active_mailer.send(payload)
    acknowledged = False
    acknowledgement_error = False

    if rule.acknowledge and email and EMAIL_RE.match(email):
        ack_payload = _acknowledgement_payload(
            form_name, rule, fields, receipt_id, email
        )
        try:
            active_mailer.send(ack_payload)
            acknowledged = True
        except DeliveryError:
            # The internal intake message was already accepted. Returning a
            # failure here would invite a duplicate referral, so report success
            # and retain an auditable acknowledgement flag.
            acknowledgement_error = True

    return {
        "ok": True,
        "accepted": True,
        "receipt_id": receipt_id,
        "provider_message_id": provider_id,
        "acknowledgement_sent": acknowledged,
        "acknowledgement_error": acknowledgement_error,
    }


def _internal_message(
    rule: FormRule, fields: Mapping[str, str], receipt_id: str
) -> Tuple[str, str]:
    rows = []
    text_rows = []
    for key, label in FIELD_LABELS.items():
        value = fields.get(key, "").strip()
        if not value:
            continue
        text_rows.append(f"{label}: {value}")
        rows.append(
            "<tr><th align=\"left\" valign=\"top\" "
            "style=\"padding:6px 16px 6px 0;color:#6b5f57;"
            "font:600 13px Arial,sans-serif;white-space:nowrap\">"
            + html.escape(label)
            + "</th><td style=\"padding:6px 0;color:#3C1C3B;"
            "font:14px/1.5 Arial,sans-serif;white-space:pre-wrap\">"
            + html.escape(value)
            + "</td></tr>"
        )

    safety = (
        "This public form asks for no patient name or other identifying details. "
        "Complete any clinical intake securely by phone."
        if rule.referral
        else "Submitted through the public Eternal Life Hospice website."
    )
    text = "\n".join(
        [
            rule.label,
            f"Receipt: {receipt_id}",
            "",
            *text_rows,
            "",
            safety,
            f"24/7 line: {PHONE_DISPLAY}",
        ]
    )
    html_body = "".join(
        [
            "<!doctype html><html><body style=\"margin:0;background:#F5F0EB\">",
            "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" "
            "cellspacing=\"0\" style=\"padding:28px;background:#F5F0EB\"><tr><td align=\"center\">",
            "<table role=\"presentation\" width=\"560\" cellpadding=\"0\" cellspacing=\"0\" "
            "style=\"max-width:560px;width:100%;background:#fff;border:1px solid #D8CDBF;"
            "border-radius:14px;overflow:hidden\">",
            "<tr><td style=\"background:#5B2E59;padding:22px 28px;color:#F5F0EB;"
            "font:20px Georgia,serif\">",
            html.escape(rule.label),
            "</td></tr><tr><td style=\"padding:26px 28px\">",
            "<p style=\"margin:0 0 18px;color:#6b5f57;font:13px Arial,sans-serif\">Receipt ",
            html.escape(receipt_id),
            "</p><table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\">",
            "".join(rows),
            "</table><p style=\"margin:22px 0 0;padding-top:18px;border-top:1px solid #EDE6DE;"
            "color:#6b5f57;font:13px/1.6 Arial,sans-serif\">",
            html.escape(safety),
            " For urgent needs, call ",
            html.escape(PHONE_DISPLAY),
            ".</p></td></tr></table></td></tr></table></body></html>",
        ]
    )
    return text, html_body


def _acknowledgement_payload(
    form_name: str,
    rule: FormRule,
    fields: Mapping[str, str],
    receipt_id: str,
    email: str,
) -> Dict[str, object]:
    first_name = _sender_name(fields).split(" ", 1)[0]
    greeting = f"Hi {first_name}," if first_name else "Hello,"
    if rule.referral:
        subject = "We received your request — Eternal Life Hospice"
        lead = (
            "Our intake team received your request and will follow up by phone. "
            "No patient or clinical details are included in this email."
        )
    elif form_name == "elh-careers":
        subject = "We received your application — Eternal Life Hospice"
        lead = "We received your application and résumé. A member of our team will review it and be in touch."
    elif form_name == "elh-care-brief-signup":
        subject = "You're on the list — The Eternal Care Brief"
        lead = "Thank you for signing up for The Eternal Care Brief. We will share each new issue with you."
    elif form_name == "elh-voice":
        subject = "Thank you for raising your hand — The Eternal Care Brief"
        lead = "Thank you for offering your voice. A member of our team will reach out shortly."
    else:
        subject = "We received your message — Eternal Life Hospice"
        lead = "We received your message and a member of our team will be in touch."

    text = "\n".join(
        [
            greeting,
            "",
            lead,
            "",
            f"Confirmation: {receipt_id}",
            f"If you need us right away, call {PHONE_DISPLAY}. We are here 24/7.",
            "",
            "With care,",
            "Eternal Life Hospice",
            PHONE_DISPLAY,
            CONTACT_EMAIL,
        ]
    )
    html_body = (
        "<!doctype html><html><body style=\"margin:0;background:#F5F0EB\">"
        "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"padding:32px;background:#F5F0EB\"><tr><td align=\"center\">"
        "<table role=\"presentation\" width=\"520\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"max-width:520px;width:100%;background:#fff;border:1px solid #D8CDBF;"
        "border-radius:14px;overflow:hidden\"><tr><td style=\"background:#5B2E59;"
        "padding:22px 30px;color:#F5F0EB;font:20px Georgia,serif\">Eternal Life Hospice"
        "</td></tr><tr><td style=\"padding:30px;color:#3C1C3B;font:16px/1.7 Georgia,serif\">"
        f"<p style=\"margin:0 0 16px\">{html.escape(greeting)}</p>"
        f"<p style=\"margin:0 0 18px\">{html.escape(lead)}</p>"
        f"<p style=\"margin:0 0 18px;color:#6b5f57;font-size:13px\">Confirmation: {html.escape(receipt_id)}</p>"
        f"<p style=\"margin:0\">If you need us right away, call <a href=\"tel:{PHONE_TEL}\" "
        f"style=\"color:#5B2E59;font-weight:bold\">{PHONE_DISPLAY}</a>. We are here 24/7.</p>"
        "</td></tr></table></td></tr></table></body></html>"
    )
    return {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": email}],
        "replyTo": {"email": CONTACT_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "textContent": text,
        "htmlContent": html_body,
        "headers": {
            "X-ELH-Form": form_name,
            "X-ELH-Receipt": receipt_id,
        },
        "tags": ["website-acknowledgement", form_name],
    }


def _sender_name(fields: Mapping[str, str]) -> str:
    direct = fields.get("referrer_name", "") or fields.get("name", "")
    if direct:
        return _clean_text(direct)[:120]
    first = fields.get("provider_first_name", "") or fields.get("first_name", "")
    last = fields.get("provider_last_name", "") or fields.get("last_name", "")
    return _clean_text(f"{first} {last}".strip())[:120]


def _clean_text(value: object) -> str:
    return (
        str(value)
        .replace("\x00", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename.replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "attachment")[:160]


def json_response_payload(
    ok: bool,
    *,
    error: Optional[str] = None,
    message: Optional[str] = None,
    **extra: object,
) -> bytes:
    payload: Dict[str, object] = {
        "ok": ok,
        "phone": PHONE_DISPLAY,
    }
    if error:
        payload["error"] = error
    if message:
        payload["message"] = message
    payload.update(extra)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")
