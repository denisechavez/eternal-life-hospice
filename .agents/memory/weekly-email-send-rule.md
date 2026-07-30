---
name: Weekly email send rule
description: Standing rule for all weekly ELH email campaigns — send to aggregate of ALL active Brevo lists unless told otherwise.
---

## Rule
Every weekly email campaign sends to the **aggregate of ALL active Brevo lists** (lists with contacts > 0), not just List 8.

**Why:** User instructed on 2026-07-30: "This next email and all weekly emails should go out to aggregate sum of total email in brevo until otherwise notified."

## How to apply
Before scheduling any weekly campaign, pull all lists via `GET /v3/contacts/lists`, filter to those with count > 0, and exclude system/test lists (IDs 3, 6, 11, 12). Set `recipients.listIds` to all remaining list IDs.

## Lists as of 2026-07-30
- List 8: Master Verified (778)
- List 10: SYMPLR Network (1,123)
- List 9: Catch-All — send with caution (148)
- List 13: Hospice Owners — Prospecting (8)
- List 2: Your first list (2)
- **Total: ~2,059 unique recipients**

## Excluded always
- List 3: identified_contacts (system)
- List 6: Contacts involved in conversations (system)
- List 11: Issue 1 Preview (Denise) (test)
- List 12: Issue 1 Preview — containerchiq (test)
