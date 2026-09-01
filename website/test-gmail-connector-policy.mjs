#!/usr/bin/env node

import assert from "node:assert/strict";
import {
  cleanupReceiptMessages,
  validateCleanupInput,
} from "./gmail-connector-policy.mjs";

const receiptId = "ABC123DEF456";
const messageIds = {
  internal_referral: "internal-1",
  forwarded_referral: "forwarded-1",
  requester_acknowledgement: "ack-1",
};

assert.deepEqual(validateCleanupInput(receiptId, messageIds), messageIds);
for (const invalid of [
  { ...messageIds, extra_role: "other-1" },
  { ...messageIds, internal_referral: "../unsafe" },
  { ...messageIds, requester_acknowledgement: "internal-1" },
]) {
  assert.throws(() => validateCleanupInput(receiptId, invalid));
}
assert.throws(() => validateCleanupInput("from:anyone", messageIds));

function makeProxy(messages, requestedPaths, failTrashId = null) {
  return async (path, options) => {
    requestedPaths.push([options.method, path]);
    if (path.includes("threads:search")) {
      return new Response(
        JSON.stringify({
          threads: messages.map((message) => ({
            id: `thread-${message.id}`,
            messages: [message],
          })),
        }),
        { status: 200 },
      );
    }
    const match = path.match(
      /^\/gmail\/v1\/users\/me\/messages\/([A-Za-z0-9_-]+)\/trash$/,
    );
    assert.ok(match, `unexpected proxy path: ${path}`);
    if (match[1] === failTrashId) {
      return new Response("{}", { status: 403 });
    }
    const message = messages.find((item) => item.id === match[1]);
    assert.ok(message, `uncorrelated ID reached proxy: ${match[1]}`);
    message.labelIds = ["TRASH"];
    return new Response("{}", { status: 200 });
  };
}

const messages = Object.values(messageIds).map((id) => ({
  id,
  labelIds: ["INBOX"],
}));
const paths = [];
const success = await cleanupReceiptMessages({
  receiptId,
  messageIds,
  proxy: makeProxy(messages, paths),
});
assert.equal(success.verification.status, "CLOSED");
assert.deepEqual(
  success.deleted.map((item) => item.status),
  ["trashed", "trashed", "trashed"],
);
assert.equal(
  paths.filter(([method]) => method === "POST").length,
  3,
);

const unrelatedPaths = [];
await assert.rejects(
  cleanupReceiptMessages({
    receiptId,
    messageIds,
    proxy: makeProxy(
      [
        ...Object.values(messageIds).map((id) => ({
          id,
          labelIds: ["INBOX"],
        })),
        { id: "unrelated-valid-id", labelIds: ["INBOX"] },
      ],
      unrelatedPaths,
    ),
  }),
  /Unrecorded non-trash IDs/,
);
assert.equal(
  unrelatedPaths.filter(([method]) => method === "POST").length,
  0,
);

const missingPaths = [];
await assert.rejects(
  cleanupReceiptMessages({
    receiptId,
    messageIds,
    proxy: makeProxy(
      [
        { id: "internal-1", labelIds: ["INBOX"] },
        { id: "ack-1", labelIds: ["INBOX"] },
      ],
      missingPaths,
    ),
  }),
  /Recorded IDs not found/,
);
assert.equal(
  missingPaths.filter(([method]) => method === "POST").length,
  0,
);

console.log("Gmail connector policy tests passed");