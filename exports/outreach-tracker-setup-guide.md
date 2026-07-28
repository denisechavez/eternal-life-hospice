# Eternal Field Log — Standalone Replit Setup Guide

**Prepared:** 2026-07-28  
**Source package:** `exports/outreach-tracker-standalone.zip`

---

## Pre-generated secrets (copy these now — store them somewhere safe too)

| Secret | Value |
|---|---|
| `SESSION_SECRET` | `Jm9NeuC1iBk6UV+vOkWgRDYF1JhdlSfsjHSveQDq71bUFgoeVVrPIS16BjK4G2fr` |
| `REGISTRATION_CODE` | `D39642477C85677E705122C8` |

> The REGISTRATION_CODE is what field staff enter when creating their account on first launch. Share it only with the two authorised users.

---

## Step-by-step setup (~10 minutes)

### Step 1 — Create the new Replit

1. Go to [replit.com](https://replit.com) → **+ Create Repl**
2. Choose **Node.js** as the template
3. Name it something like `elh-outreach-tracker` (private / team visibility)
4. Click **Create Repl**

### Step 2 — Upload the app files

Option A — Shell upload:
```bash
# In the new Repl's Shell, download the zip from the main project's
# GitHub/Netlify exports, then:
unzip outreach-tracker-standalone.zip
mv outreach-tracker/* .
rm -rf outreach-tracker
```

Option B — Manual upload:
- Download `exports/outreach-tracker-standalone.zip` from this project
- Unzip it locally
- Drag-and-drop all files into the new Repl's file tree

Files needed (from the zip):
```
package.json
server.js
db.js
ai.js
schema.sql
public/
  index.html
  app.js
  styles.css
_setup/
  dot-replit.toml   → rename to .replit
  replit-nix.txt    → rename to replit.nix
```

### Step 3 — Rename the setup config files

In the Shell:
```bash
mv _setup/dot-replit.toml .replit
mv _setup/replit-nix.txt replit.nix
rm -rf _setup
```

### Step 4 — Install dependencies

```bash
npm install
```

### Step 5 — Enable PostgreSQL

1. In the Repl sidebar → **Tools → Database**
2. Click **Enable PostgreSQL** — this automatically sets `DATABASE_URL`
3. Wait for it to provision (takes ~30 seconds)

### Step 6 — Apply the schema

```bash
psql $DATABASE_URL < schema.sql
```

Expected output: a series of `CREATE TABLE` / `CREATE INDEX` lines, no errors.

### Step 7 — Set secrets

1. Sidebar → **Tools → Secrets**
2. Add these two secrets exactly:

| Key | Value |
|---|---|
| `SESSION_SECRET` | `Jm9NeuC1iBk6UV+vOkWgRDYF1JhdlSfsjHSveQDq71bUFgoeVVrPIS16BjK4G2fr` |
| `REGISTRATION_CODE` | `D39642477C85677E705122C8` |

3. **Optional — for AI card scanning & voice notes:**  
   Sidebar → **Tools → Integrations** → search **OpenAI** → Connect.  
   This sets `AI_INTEGRATIONS_OPENAI_API_KEY` and `AI_INTEGRATIONS_OPENAI_BASE_URL` automatically.

### Step 8 — Start the app

Click **Run**, or in the Shell:
```bash
npm start
```

The app should print:
```
ELH Outreach Tracker listening on port 5000
```

Open the preview URL to confirm the login page loads.

### Step 9 — Create the first account

1. Click **Register** on the login page
2. Enter the `REGISTRATION_CODE` from Step 7
3. Create a name, phone number, and password
4. Log in

### Step 10 — Log a test visit

1. Click **+ New Visit**
2. Fill in:  
   - Company: `TEST – Setup Verification`  
   - Visit date: today  
   - Status: `Not started`
3. Save
4. Confirm the visit appears in the visit list and the Follow-up tab
5. Download the CSV export and confirm the row appears

### Step 11 — Deploy

1. Sidebar → **Deploy**
2. Choose **Autoscale** (or Static → Scheduled, whichever is available)
3. Click **Deploy** — Replit will build and serve at a stable `*.replit.app` URL
4. Share that URL with field staff

---

## Post-setup checklist

- [ ] Schema applied (no errors)
- [ ] Two secrets set (`SESSION_SECRET`, `REGISTRATION_CODE`)
- [ ] App boots and login page loads
- [ ] First account registered with `REGISTRATION_CODE`
- [ ] Test visit saved and visible
- [ ] CSV export contains the test visit row
- [ ] App deployed at stable `*.replit.app` URL
- [ ] Deployed URL shared with field staff
- [ ] Test visit deleted (or left as-is — it won't affect real data)

---

## Data migration (future use)

If visits are added to the old main-site Replit before this setup is live, run the export query documented in `exports/outreach-data-export/visits-export.sql`, paste the generated `INSERT` block into that file, and then run:

```bash
psql $DATABASE_URL < exports/outreach-data-export/visits-export.sql
```

As of 2026-07-28 there were **0 visit records** — no migration needed right now.
