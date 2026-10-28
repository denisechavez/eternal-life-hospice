"""Approved client letters delivered only through the managed Gmail connector."""
import base64
import json
import subprocess
from email.headerregistry import Address
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate, make_msgid
from pathlib import Path


class GmailDeliveryError(Exception):
    """Safe delivery failure; never fall back to a marketing transport."""


class GmailAcknowledgmentMailer:
    def send(self, payload):
        try:
            if ("website-acknowledgement" not in payload.get("tags", [])
                    or payload.get("attachment") or len(payload["to"]) != 1):
                raise ValueError("Not a client acknowledgment")
            message = EmailMessage(policy=SMTP)
            # The Node adapter sets From using the verified connected mailbox.
            message["To"] = str(Address(addr_spec=payload["to"][0]["email"]))
            reply = payload["replyTo"]
            message["Reply-To"] = Address(display_name=reply.get("name", ""),
                                          addr_spec=reply["email"])
            message["Subject"] = payload["subject"]
            message["Date"] = formatdate(localtime=False, usegmt=True)
            message["Message-ID"] = make_msgid(domain="eternallifehospice.com")
            for key in ("X-ELH-Form", "X-ELH-Receipt"):
                message[key] = payload["headers"][key]
            message.set_content(payload["textContent"])
            message.add_alternative(payload["htmlContent"], subtype="html")
            raw = message.as_bytes()
            if len(raw) > 200000:
                raise ValueError("Acknowledgment too large")
            completed = subprocess.run(
                ["node", str(Path(__file__).with_name("gmail-acknowledgment-transport.mjs"))],
                input=json.dumps({"action": "send_acknowledgment",
                    "raw": base64.urlsafe_b64encode(raw).decode().rstrip("=")}),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=25, check=False,
            )
            result = json.loads(completed.stdout)
            if (completed.returncode or result.get("ok") is not True
                    or not isinstance(result.get("message_id"), str)
                    or not result["message_id"]):
                raise ValueError("Send not confirmed")
            return result["message_id"]
        except Exception:
            # A timeout may follow acceptance. Do not retry or switch provider.
            raise GmailDeliveryError("Gmail acknowledgment could not be confirmed") from None
