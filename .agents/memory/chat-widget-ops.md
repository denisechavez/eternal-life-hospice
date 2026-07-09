---
name: Chat widget operations (Netlify Function)
description: How the AI chat widget is deployed/configured on Netlify, and the non-obvious gotchas that caused a long go-live debug.
---

The chat widget is a serverless **Netlify Function** (`website/elh-preview/netlify/functions/chat.js`); the browser side lives in `website/elh-preview/assets/chat.js`. It calls Anthropic (primary) and falls back to OpenAI only if `OPENAI_API_KEY` is set.

**Go-live gotchas (each cost a debug cycle):**
- The function returns its replies in **4–5 ms with no error line** when it can't see an API key — that fast duration is the tell that `ANTHROPIC_API_KEY` is missing, not that Anthropic failed.
- On Netlify, the key must be set on the **project that actually serves the domain** (there can be duplicate/leftover projects), scoped to **All scopes** (Functions scope specifically), and a **fresh deploy** must run after adding it — env vars only bake into new builds.
- A `404 not_found_error` from Anthropic means the **model name is retired/renamed**, NOT a credit problem (credits show as 400/403). Hardcoded model defaults *will* eventually 404 as Anthropic rotates names.

**Why the function self-heals:** to avoid chasing model renames forever, `callClaude` retries via `pickAvailableClaudeModel()` which calls `GET /v1/models` and picks newest Sonnet → newest Haiku → anything. `ANTHROPIC_MODEL` env var can still pin a specific model.
**How to apply:** if chat falls back to the "having trouble" message, check function-log Duration first (fast = no key), then the `Anthropic <code>` line (404 = model, 401 = bad key, 400/403 = credits).

**Anthropic param deprecation = 400, NOT 404 (so self-heal does NOT catch it):**
- Symptom: live function returns HTTP 502 + generic fallback, but timing is ~1–1.8s (a real upstream call happened), NOT the 4–5ms "no key" tell. Confirmed via the gated diag flag: `Anthropic 400: "temperature is deprecated for this model."`
- Cause: newer Claude models reject the `temperature` param that `postClaude` was sending. `pickAvailableClaudeModel()` only retries on **404** (model name), so a 400 param error is never self-healed — it throws straight to the 502 fallback.
- Fix applied: removed `temperature` from the Claude request body entirely (tone is carried by SYSTEM_PROMPT; default sampling is fine). Do NOT re-add `temperature` to the Claude call. OpenAI (gpt-4o) still accepts temperature — leave callOpenAI as-is.
- **Debugging pattern that worked:** Netlify function logs aren't reachable from Replit and secret VALUES can't be read (viewEnvVars = existence only). To see the real provider error, temporarily surface `lastErr.message` in the 502 JSON gated behind `?diag=elh` (query param), Git→Sync to deploy, curl `POST /.netlify/functions/chat?diag=elh`, read it, then REMOVE the diag block. The detail string carries no secret (it's the API error body, truncated 300 chars).
