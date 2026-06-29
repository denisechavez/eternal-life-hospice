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
