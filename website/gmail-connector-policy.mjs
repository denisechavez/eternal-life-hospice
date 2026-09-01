const RECEIPT_PATTERN = /^[A-Z0-9]{6,40}$/;
const MESSAGE_ID_PATTERN = /^[A-Za-z0-9_-]{5,200}$/;
const PAGE_TOKEN_PATTERN = /^[A-Za-z0-9._~+/=-]{1,500}$/;
const MESSAGE_ROLES = [
  "internal_referral",
  "forwarded_referral",
  "requester_acknowledgement",
];

export function validateCleanupInput(receiptId, messageIds) {
  if (!RECEIPT_PATTERN.test(receiptId ?? "")) {
    throw new Error("Invalid processor receipt ID");
  }
  if (!messageIds || typeof messageIds !== "object" || Array.isArray(messageIds)) {
    throw new Error("Cleanup message IDs must be an object");
  }
  const unknownRoles = Object.keys(messageIds).filter(
    (role) => !MESSAGE_ROLES.includes(role),
  );
  if (unknownRoles.length) {
    throw new Error(`Unsupported cleanup roles: ${unknownRoles.join(", ")}`);
  }
  const normalized = {};
  for (const role of MESSAGE_ROLES) {
    const messageId = messageIds[role];
    if (
      role === "forwarded_referral" &&
      (messageId === null || messageId === "" || messageId === "NONE")
    ) {
      continue;
    }
    if (typeof messageId !== "string" || !MESSAGE_ID_PATTERN.test(messageId)) {
      throw new Error(`Invalid Gmail message ID for ${role}`);
    }
    normalized[role] = messageId;
  }
  if (!normalized.internal_referral || !normalized.requester_acknowledgement) {
    throw new Error("Internal referral and acknowledgement IDs are required");
  }
  if (new Set(Object.values(normalized)).size !== Object.keys(normalized).length) {
    throw new Error("Cleanup Gmail message IDs must be unique");
  }
  return normalized;
}

function messagesFromSearch(result) {
  if (!result || !Array.isArray(result.threads)) {
    throw new Error("Gmail search returned no thread list");
  }
  return result.threads.flatMap((thread) =>
    Array.isArray(thread?.messages)
      ? thread.messages.filter((message) => typeof message?.id === "string")
      : [],
  );
}

async function responseJson(response) {
  const text = await response.text();
  let body = {};
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = {};
    }
  }
  if (!response.ok) {
    throw new Error(`Gmail returned HTTP ${response.status}`);
  }
  return body;
}

async function searchReceipt(proxy, receiptId) {
  const messages = [];
  let pageToken = null;
  for (let page = 0; page < 10; page += 1) {
    const query = new URLSearchParams({
      q: receiptId,
      pageSize: "50",
      view: "THREAD_VIEW_MINIMAL",
      includeTrash: "true",
    });
    if (pageToken) query.set("pageToken", pageToken);
    const response = await proxy(
      `/gmail/v1/users/me/threads:search?${query.toString()}`,
      { method: "GET" },
    );
    const result = await responseJson(response);
    messages.push(...messagesFromSearch(result));
    if (!result.nextPageToken) return messages;
    if (
      typeof result.nextPageToken !== "string" ||
      !PAGE_TOKEN_PATTERN.test(result.nextPageToken) ||
      result.nextPageToken === pageToken
    ) {
      throw new Error("Gmail returned an invalid continuation token");
    }
    pageToken = result.nextPageToken;
  }
  throw new Error("Receipt search exceeded the 500-thread safety limit");
}

function isInTrash(message) {
  return Array.isArray(message?.labelIds) && message.labelIds.includes("TRASH");
}

export async function cleanupReceiptMessages({
  receiptId,
  messageIds,
  proxy,
}) {
  const normalizedIds = validateCleanupInput(receiptId, messageIds);
  const initialMessages = await searchReceipt(proxy, receiptId);
  const initialById = new Map(
    initialMessages.map((message) => [message.id, message]),
  );
  const missingIds = Object.values(normalizedIds).filter(
    (messageId) => !initialById.has(messageId),
  );
  if (missingIds.length) {
    throw new Error(
      `Recorded IDs not found for receipt ${receiptId}: ${missingIds.join(", ")}`,
    );
  }
  const targetIds = new Set(Object.values(normalizedIds));
  const unexpectedNonTrash = initialMessages
    .filter((message) => !targetIds.has(message.id) && !isInTrash(message))
    .map((message) => message.id)
    .sort();
  if (unexpectedNonTrash.length) {
    throw new Error(
      `Unrecorded non-trash IDs match receipt ${receiptId}: ` +
        unexpectedNonTrash.join(", "),
    );
  }

  const deleted = [];
  const entries = Object.entries(normalizedIds);
  for (let index = 0; index < entries.length; index += 1) {
    const [role, messageId] = entries[index];
    if (isInTrash(initialById.get(messageId))) {
      deleted.push({ role, message_id: messageId, status: "already_in_trash" });
      continue;
    }
    try {
      const response = await proxy(
        `/gmail/v1/users/me/messages/${messageId}/trash`,
        { method: "POST" },
      );
      await responseJson(response);
      deleted.push({ role, message_id: messageId, status: "trashed" });
    } catch (error) {
      deleted.push({
        role,
        message_id: messageId,
        status: "failed",
        error: error.message,
      });
      for (const [remainingRole, remainingId] of entries.slice(index + 1)) {
        deleted.push({
          role: remainingRole,
          message_id: remainingId,
          status: "not_attempted_after_failure",
        });
      }
      break;
    }
  }

  let remainingNonTrash = [];
  let verificationError = "";
  try {
    const finalMessages = await searchReceipt(proxy, receiptId);
    remainingNonTrash = finalMessages
      .filter((message) => !isInTrash(message))
      .map((message) => message.id)
      .sort();
  } catch (error) {
    verificationError = error.message;
  }
  const failed = deleted.some((item) => item.status === "failed");
  const status =
    failed || remainingNonTrash.length || verificationError ? "OPEN" : "CLOSED";
  return {
    receipt_id: receiptId,
    scope_verified: true,
    deleted,
    verification: {
      searched_by_receipt: true,
      remaining_non_trash_ids: remainingNonTrash,
      status,
      ...(verificationError ? { error: verificationError } : {}),
    },
  };
}