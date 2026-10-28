// Narrow adapter for client acknowledgments, not a general Gmail API proxy.
import {ReplitConnectors} from "@replit/connectors-sdk";
import {pathToFileURL} from "node:url";

class GmailAckError extends Error {
  constructor(code) { super(code); this.code = code; }
}

async function companyMailbox(connectors) {
  const connections = await connectors.listConnections({connector_names:"google-mail"});
  const usable = connections.filter(connection => !connection.disabled);
  if (usable.length !== 1 || usable[0].status !== "healthy")
    throw new GmailAckError("gmail_connection_unavailable_or_ambiguous");
  const response = await connectors.proxy("google-mail", "/gmail/v1/users/me/profile", {method:"GET"});
  if (!response.ok) throw new GmailAckError("gmail_profile_unavailable");
  const profile = await response.json();
  const mailbox = profile?.emailAddress;
  // Never impersonate an unverified alias or send through a personal domain.
  if (typeof mailbox !== "string" || !/^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@eternallifehospice\.com$/i.test(mailbox))
    throw new GmailAckError("gmail_company_mailbox_required");
  return mailbox.toLowerCase();
}

export async function handleAcknowledgment(input, connectors) {
  if (!input || !["profile", "send_acknowledgment"].includes(input.action))
    throw new GmailAckError("gmail_invalid_action");
  if (input.action === "profile")
    return {ok:true, sender:await companyMailbox(connectors)};
  if (typeof input.raw !== "string" || !/^[A-Za-z0-9_-]+$/.test(input.raw))
    throw new GmailAckError("gmail_invalid_message");
  const message = Buffer.from(input.raw, "base64url");
  const separator = message.indexOf("\r\n\r\n");
  if (message.length > 200000 || separator < 0)
    throw new GmailAckError("gmail_invalid_message");
  const headers = message.subarray(0, separator).toString("utf8");
  if (!/^To:/im.test(headers) || !/^X-ELH-Receipt:/im.test(headers)
      || /^(?:From|Sender|Bcc|Cc):/im.test(headers))
    throw new GmailAckError("gmail_invalid_headers");
  const mailbox = await companyMailbox(connectors);
  const raw = Buffer.concat([
    Buffer.from(`From: Eternal Life Hospice <${mailbox}>\r\n`, "utf8"),
    message
  ]).toString("base64url");
  // No network/5xx retry: a lost response may follow an accepted send.
  const response = await connectors.proxy("google-mail", "/gmail/v1/users/me/messages/send", {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({raw})
  });
  if (!response.ok) throw new GmailAckError("gmail_send_unconfirmed");
  const result = await response.json();
  if (typeof result?.id !== "string" || !result.id)
    throw new GmailAckError("gmail_send_unconfirmed");
  return {ok:true, message_id:result.id};
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const chunks = [];
    let size = 0;
    for await (const chunk of process.stdin) {
      size += chunk.length;
      if (size > 300000) throw new GmailAckError("gmail_invalid_message");
      chunks.push(chunk);
    }
    const input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    const result = await handleAcknowledgment(input, new ReplitConnectors());
    process.stdout.write(JSON.stringify(result));
  } catch (error) {
    // Do not emit provider bodies, MIME content, recipients or credentials.
    process.stdout.write(JSON.stringify({ok:false,
      error:error instanceof GmailAckError ? error.code : "gmail_connector_unavailable"}));
    process.exitCode = 1;
  }
}
