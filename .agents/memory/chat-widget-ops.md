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

**Intermittent "I'm not certain about that one" dead-ends = fragile reply extraction, NOT missing knowledge:**
- The bot does NOT read/crawl the website. Its knowledge is the curated fact list inside SYSTEM_PROMPT only. It can explain general hospice care/process because that's in the prompt — if it "can't" answer something it normally covers, suspect the extraction/response path, not missing content.
- Root cause of random dead-ends: `callClaude` only read `content[0].text` and returned "" (→ the "not certain" fallback) with NO retry. Newer Claude replies can span multiple content blocks or lead with an empty/non-text block, so a good answer looked empty ~2 of 3 times for some phrasings.
- Fix: `extractClaudeText()` concatenates ALL text-type blocks, and `callClaude` retries up to 3 attempts when the reply is empty. Also bumped max_tokens 320→500 for fuller answers. Keep these — don't revert to single-block extraction.
- **RAG option not built:** if the user wants answers grounded in actual page content (not just the prompt fact list), that requires adding retrieval — it does not happen today.
