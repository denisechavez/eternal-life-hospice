# GoDaddy Wildcard Redirect Setup — Step-by-Step
**Business:** Eternal Life Hospice, Inc.
**Date:** July 15, 2026
**Goal:** Make every path on `eternalhospice.com` and `eternallifehospiceinc.com`
forward to the matching page on `https://eternallifehospice.com/` — not just the homepage.

---

## Why this matters

Right now, if someone clicks an old link to, say, `eternalhospice.com/resources`, they
get a "Page Not Found" error instead of landing on `eternallifehospice.com/resources`.
This fix turns on "forward with path" — a single checkbox — so **any** page on either
old domain lands on the same page at the official site.

---

## What you need

- GoDaddy login for the account that owns `eternalhospice.com` and `eternallifehospiceinc.com`
- About 5 minutes per domain (2 domains = ~10 minutes total)
- Changes take effect within a few minutes to a few hours (usually fast)

---

## Step-by-step: for each domain

Repeat these steps for **both** `eternalhospice.com` **and** `eternallifehospiceinc.com`.

### 1 — Log in and open the domain

1. Go to [godaddy.com](https://godaddy.com) and sign in.
2. Click your name (top right) → **My Products**.
3. Under "Domains", find the domain you're working on → click **DNS** (or **Manage**).

### 2 — Open Forwarding settings

1. Scroll down to the **Forwarding** section.
2. You'll see an existing forward for the domain — something like:
   - **Forward to:** `https://eternallifehospice.com/`
   - **Redirect type:** Permanent (301)
3. Click the **pencil / Edit** icon on that forward.

### 3 — Enable "Forward with Path"

In the edit panel you'll see a checkbox or toggle labelled one of:
- **"Forward with Path"**, or
- **"Forward all paths"**, or
- **"Include path and query string"**

**Check (turn on) that option.**

> This is the key change. It tells GoDaddy: "when someone visits any page on this
> old domain, include the page path in the forward." So `/resources` → `/resources`,
> `/blog` → `/blog`, `/media-kit` → `/media-kit`, etc.

Confirm the other settings look like this:

| Setting | Value |
|---|---|
| Forward to | `https://eternallifehospice.com/` |
| Redirect type | **Permanent (301)** |
| Forward with Path | **✅ Checked / ON** |
| Forward with Masking | ❌ Off (leave this off — masking hides the real URL and hurts SEO) |

### 4 — Save

Click **Save** (or **Update**). GoDaddy will confirm the change.

### 5 — Repeat for the second domain

Go back to **My Products → Domains** and do the same for the other domain.

---

## Optional polish: fix the extra hop on eternalhospice.com

`eternalhospice.com` currently bounces through `www.eternallifehospice.com` before
reaching the final destination (two hops instead of one). `eternallifehospiceinc.com`
already forwards in a single clean hop.

While you're editing the `eternalhospice.com` forward, confirm the "Forward to" field
reads exactly:

```
https://eternallifehospice.com/
```

(no `www` prefix). If it says `https://www.eternallifehospice.com/`, change it to
the non-www version. That eliminates the extra hop.

---

## Current state (verified July 15, 2026)

Before the fix, here is what each URL returns:

| URL | HTTP code | Result |
|---|---|---|
| `eternalhospice.com/` | **301** → `www.eternallifehospice.com/` | ✅ Works (extra hop) |
| `eternalhospice.com/resources` | **404** | ❌ Page Not Found |
| `eternallifehospiceinc.com/` | **301** → `eternallifehospice.com/` | ✅ Works (clean) |
| `eternallifehospiceinc.com/resources` | **404** | ❌ Page Not Found |

---

## How to verify after the fix

Wait 10–15 minutes after saving in GoDaddy, then test these URLs in your browser
(or paste them here and I can check for you):

| Test URL | Should land at |
|---|---|
| `https://eternalhospice.com/resources` | `https://eternallifehospice.com/resources` |
| `https://eternalhospice.com/blog` | `https://eternallifehospice.com/blog` |
| `https://eternalhospice.com/media-kit` | `https://eternallifehospice.com/media-kit` |
| `https://eternallifehospiceinc.com/resources` | `https://eternallifehospice.com/resources` |
| `https://eternallifehospiceinc.com/blog` | `https://eternallifehospice.com/blog` |

Each URL should redirect automatically and show the correct page — no "Page Not Found."

**Bonus check — single hop for eternalhospice.com:**
After fixing the "Forward to" field to point directly at `https://eternallifehospice.com/`
(no `www`), the first row above should show a clean 301 directly to the final address,
not two hops via `www`.

---

## If "Forward with Path" is not available

GoDaddy occasionally changes its interface. If you don't see the "Forward with Path"
checkbox:

1. **Delete** the existing forward entry.
2. Click **Add Forwarding**.
3. Set up the forward fresh — the newer "Add" flow almost always shows all options
   including the path toggle.

If GoDaddy's forwarding still won't do it, the next best option is to move the domain's
DNS to **Cloudflare** (free), where wildcard redirect rules are a standard feature.
Let me know if you hit that wall and I'll write the Cloudflare instructions.

---

*This guide produced by the ELH project AI. Changes happen entirely in GoDaddy —
nothing in this repository needs to change.*
