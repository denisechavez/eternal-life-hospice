"""Private, bounded Gmail SMTP worker. Never exposes credentials or mail bodies."""
import base64
import json
import os
import re
import smtplib
import ssl
import sys
from email.parser import BytesParser
from email.policy import SMTP


ACCOUNTS = {
    "info": ("info@eternallifehospice.com", "GMAIL_ACK_APP_PASSWORD"),
    "referral": ("referral@eternallifehospice.com", "GMAIL_REFERRAL_APP_PASSWORD"),
}
FORM_ACCOUNTS = {
    "elh-family": "info",
    "elh-chat-callback": "info",
    "elh-voice": "info",
    "elh-careers": "info",
    "elh-care-brief-signup": "info",
    "elh-physician": "referral",
    "elh-casemanager": "referral",
    "elh-coordinator": "referral",
}


class GmailTransportError(Exception):
    pass


def mailbox_for_form(form_name):
    return ACCOUNTS[FORM_ACCOUNTS[form_name]][0]


def login(account):
    mailbox, secret_key = ACCOUNTS[account]
    password = "".join(os.environ.get(secret_key, "").split())
    if not password:
        raise GmailTransportError("gmail_credential_missing")
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    smtp = None
    stage = "connect"
    try:
        smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=8)
        stage = "greeting"
        code, _ = smtp.ehlo()
        if code != 250:
            raise GmailTransportError("gmail_greeting_rejected")
        stage = "tls"
        smtp.starttls(context=context)
        code, _ = smtp.ehlo()
        if code != 250:
            raise GmailTransportError("gmail_secure_greeting_rejected")
        stage = "authentication"
        smtp.login(mailbox, password, initial_response_ok=False)
        return smtp
    except smtplib.SMTPServerDisconnected:
        if smtp is not None:
            smtp.close()
        raise GmailTransportError("gmail_connection_closed_during_" + stage) from None
    except Exception:
        if smtp is not None:
            smtp.close()
        raise


def check_login(account):
    smtp = login(account)
    smtp.close()
    return {"ok": True, "account": account, "authenticated": True}


def send_acknowledgment(raw):
    if len(raw) > 200000:
        raise GmailTransportError("gmail_invalid_message")
    message = BytesParser(policy=SMTP).parsebytes(raw)
    for header in ("From", "To", "Reply-To", "Message-ID", "X-ELH-Form", "X-ELH-Receipt"):
        if len(message.get_all(header, [])) != 1:
            raise GmailTransportError("gmail_invalid_headers")
    if any(message.get_all(header) for header in ("Cc", "Bcc", "Sender", "Resent-To", "Resent-From")):
        raise GmailTransportError("gmail_invalid_headers")
    account = FORM_ACCOUNTS[message["X-ELH-Form"]]
    mailbox = ACCOUNTS[account][0]
    for header in ("From", "Reply-To"):
        addresses = message[header].addresses
        if len(addresses) != 1 or addresses[0].addr_spec.lower() != mailbox:
            raise GmailTransportError("gmail_sender_mismatch")
    recipients = message["To"].addresses
    if len(recipients) != 1 or not recipients[0].domain:
        raise GmailTransportError("gmail_invalid_recipient")
    if message.get_content_type() != "multipart/alternative" or any(
            part.get_content_disposition() == "attachment" for part in message.walk()):
        raise GmailTransportError("gmail_invalid_message")
    smtp = login(account)
    try:
        refused = smtp.send_message(message, from_addr=mailbox,
                                    to_addrs=[recipients[0].addr_spec])
        if refused:
            raise GmailTransportError("gmail_delivery_unconfirmed")
        # Success means Gmail accepted DATA, not that an inbox delivered it.
        return {"ok": True, "message_id": str(message["Message-ID"])}
    finally:
        # A cleanup error after acceptance must not create a false send failure.
        try:
            smtp.close()
        except Exception:
            pass


def main():
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--check":
            result = check_login(sys.argv[2])
        else:
            data = sys.stdin.buffer.read(300001)
            if len(data) > 300000:
                raise GmailTransportError("gmail_invalid_message")
            request = json.loads(data)
            raw = request.get("raw", "")
            if (request.get("action") != "send_acknowledgment"
                    or not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", raw)):
                raise GmailTransportError("gmail_invalid_message")
            result = send_acknowledgment(base64.urlsafe_b64decode(
                raw + "=" * (-len(raw) % 4)))
        print(json.dumps(result))
        return 0
    except Exception as error:
        code = ("gmail_authentication_rejected" if isinstance(error, smtplib.SMTPAuthenticationError)
                else str(error) if isinstance(error, GmailTransportError)
                else "gmail_delivery_unconfirmed")
        # Never print provider replies, passwords, recipients, or the message.
        print(json.dumps({"ok": False, "error": code, "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
