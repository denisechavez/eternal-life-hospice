#!/usr/bin/env node

import { ReplitConnectors } from "@replit/connectors-sdk";
import { cleanupReceiptMessages } from "./gmail-connector-policy.mjs";

const GMAIL_CONNECTOR = "google-mail";
const GMAIL_MODIFY_SCOPE =
  "https://www.googleapis.com/auth/gmail.modify";

function fail(status, error) {
  process.stdout.write(JSON.stringify({ status, error }));
  process.exitCode = 1;
}

async function readInput() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function configuredScopes(value, found = new Set()) {
  if (!value || typeof value !== "object") return found;
  for (const [key, item] of Object.entries(value)) {
    if (
      key.toLowerCase() === "scopes" &&
      Array.isArray(item)
    ) {
      for (const scope of item) {
        if (typeof scope === "string") found.add(scope);
      }
    } else if (item && typeof item === "object") {
      configuredScopes(item, found);
    }
  }
  return found;
}

try {
  const input = await readInput();
  if (
    !input ||
    typeof input.connectionId !== "string" ||
    input.action !== "cleanup_receipt" ||
    input.requiredScope !== GMAIL_MODIFY_SCOPE
  ) {
    fail(400, "Invalid Gmail connector request");
  } else {
    const connectors = new ReplitConnectors();
    const connections = await connectors.listConnections({
      connector_names: GMAIL_CONNECTOR,
    });
    const usableConnections = connections.filter(
      (candidate) => !candidate.disabled,
    );
    const connection = connections.find(
      (candidate) => candidate.id === input.connectionId,
    );

    if (!connection) {
      fail(403, "The named Gmail connection is not attached to this project");
    } else if (
      usableConnections.length !== 1 ||
      usableConnections[0].id !== input.connectionId
    ) {
      fail(
        409,
        "Gmail cleanup requires exactly one attached Gmail connection so the " +
          "mailbox target cannot be ambiguous",
      );
    } else if (connection.status !== "healthy") {
      fail(401, "The named Gmail connection is not healthy");
    } else if (
      typeof connection.connector_config_id !== "string" ||
      connection.connector_config_id.includes("_default_")
    ) {
      fail(
        403,
        "The named Gmail connection uses platform credentials, which do not " +
          "grant gmail.modify; authorize a custom-OAuth Gmail connection",
      );
    } else if (
      !configuredScopes(connection.public_settings).has(input.requiredScope)
    ) {
      fail(
        403,
        "The named Gmail connection's configured OAuth scopes do not include " +
          "gmail.modify",
      );
    } else {
      try {
        const result = await cleanupReceiptMessages({
          receiptId: input.receiptId,
          messageIds: input.messageIds,
          proxy: (path, options) =>
            connectors.proxy(GMAIL_CONNECTOR, path, options),
        });
        process.stdout.write(
          JSON.stringify({
            status: result.verification.status === "CLOSED" ? 200 : 409,
            body: result,
          }),
        );
        if (result.verification.status !== "CLOSED") process.exitCode = 1;
      } catch (error) {
        fail(400, error.message);
      }
    }
  }
} catch (error) {
  fail(
    500,
    `Gmail connector request failed: ${error?.name ?? "UnknownError"}`,
  );
}