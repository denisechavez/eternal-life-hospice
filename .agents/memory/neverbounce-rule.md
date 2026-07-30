---
name: NeverBounce verification rule
description: Standing rule — every contact email must be verified through NeverBounce before being added to any Brevo list or included in any campaign send.
---

## Rule
**ALL contact emails must pass NeverBounce verification before being added to Brevo or any send list. No exceptions.**

**Why:** User mandated on 2026-07-30: "check all through bounce lock this in as a rule we need to be careful - all contacts get checked." High bounce rates damage sender reputation and deliverability.

## How to apply
1. Before adding any contact to Brevo, run their email through `GET https://api.neverbounce.com/v4/single/check?key=KEY&email=EMAIL`
2. Results handling:
   - `valid` → add to Brevo ✅
   - `catchall` → add to Brevo with caution (domain accepts all, can't verify individual address) ⚠️
   - `unknown` → add to Brevo with caution (server unreachable/firewall, e.g. UCLA mednet.ucla.edu) ⚠️
   - `invalid` → do NOT add to Brevo, mark in CSV as "Invalid (NeverBounce)" ❌
3. Update the CSV Email Status field with the NeverBounce result
4. Remove any invalids from ALL Brevo lists via `POST /v3/contacts/lists/{id}/contacts/remove`

## Applies to
- Business card imports
- Scraped contact lists
- Manual entries
- Any source — no exceptions
