#!/usr/bin/env node
/**
 * engagement-review.js
 *
 * Pulls open/click stats across all sent ELH campaigns from Brevo, identifies
 * contacts who have never engaged, and segments the list into tiers for future
 * targeting.
 *
 * Usage:
 *   BREVO_API=<key> node engagement-review.js [options]
 *
 * Options:
 *   --campaigns N       Number of most-recent sent campaigns to analyze (default: all)
 *   --min-sends N       Minimum campaigns required before suppression is allowed (default: 6)
 *   --suppress          Actually suppress never-engaged contacts (adds to Brevo blacklist)
 *                       Suppression is blocked unless --min-sends threshold is met.
 *   --move-to-list      Instead of blacklisting, move unengaged to a re-engagement list
 *   --output PATH       Write the HTML report to this path
 *                       (default: exports/campaign-reports/engagement-report-YYYY-MM-DD.html)
 *   --dry-run           Print actions that WOULD be taken; do not call any mutating APIs
 *                       (implied when --suppress is absent)
 *
 * Lists excluded from analysis (system/test):
 *   3  identified_contacts
 *   6  Contacts involved in conversations
 *   11 Issue 1 Preview (Denise)
 *   12 Issue 1 Preview — containerchiq
 *
 * Tier definitions:
 *   Tier 1 — Clickers:           clicked at least once across any campaign
 *   Tier 2 — Active Openers:     opened 2+ times across campaigns (never clicked)
 *   Tier 3 — Occasional Openers: opened exactly once (never clicked)
 *   Tier 4 — Never Engaged:      zero opens, zero clicks across all analyzed campaigns
 *
 * Suppression policy:
 *   Never-engaged contacts are blacklisted in Brevo (emailBlacklisted=true), which
 *   prevents them from receiving any future campaign from this account. They remain
 *   in their current lists for record-keeping. To undo, manually set emailBlacklisted
 *   back to false in the Brevo UI or via the API.
 *
 * Re-engagement policy (--move-to-list):
 *   Instead of blacklisting, never-engaged contacts are added to list 14
 *   "Re-engagement Sequence" (created if it doesn't exist), and removed from
 *   the active lists. A separate re-engagement drip sequence can then target them
 *   with a different angle before a final suppression sweep.
 */

"use strict";

const https = require("https");
const fs    = require("fs");
const path  = require("path");

// ─── CLI ────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const opt  = (name, def) => {
  const i = args.indexOf(name);
  return i !== -1 && args[i + 1] ? args[i + 1] : def;
};

const MAX_CAMPAIGNS  = opt("--campaigns",  null);   // null = all
const MIN_SENDS      = parseInt(opt("--min-sends", "6"), 10);
const DO_SUPPRESS    = flag("--suppress");
const DO_MOVE        = flag("--move-to-list");
const DRY_RUN        = flag("--dry-run") || (!DO_SUPPRESS && !DO_MOVE);
const OUTPUT_PATH    = opt("--output", null);

const BREVO_KEY = process.env.BREVO_API;
if (!BREVO_KEY) {
  console.error("ERROR: BREVO_API environment variable is not set.");
  process.exit(1);
}

// Lists to exclude (system / test)
const EXCLUDED_LIST_IDS = new Set([3, 6, 11, 12]);

// Re-engagement list name (created if --move-to-list and list doesn't exist)
const REENGAGEMENT_LIST_NAME = "Re-engagement Sequence";
const REENGAGEMENT_FOLDER_ID = 1;  // "My contacts" folder

const TIMEOUT_MS = 30_000;

// ─── API helpers ────────────────────────────────────────────────────────────

function brevoGet(urlPath) {
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: "api.brevo.com",
        path: urlPath,
        method: "GET",
        headers: { "api-key": BREVO_KEY, "Accept": "application/json" },
      },
      (res) => {
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try { resolve(JSON.parse(body)); }
            catch (e) { reject(new Error(`JSON parse error on ${urlPath}: ${e.message}`)); }
          } else {
            reject(new Error(`Brevo GET ${urlPath} → ${res.statusCode}: ${body.slice(0, 300)}`));
          }
        });
      }
    );
    req.setTimeout(TIMEOUT_MS, () => req.destroy(new Error(`Timeout: GET ${urlPath}`)));
    req.on("error", reject);
    req.end();
  });
}

function brevoPut(urlPath, payload) {
  const body = JSON.stringify(payload);
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: "api.brevo.com",
        path: urlPath,
        method: "PUT",
        headers: {
          "api-key": BREVO_KEY,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let rb = "";
        res.on("data", (c) => (rb += c));
        res.on("end", () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(rb ? JSON.parse(rb) : {});
          } else {
            reject(new Error(`Brevo PUT ${urlPath} → ${res.statusCode}: ${rb.slice(0, 300)}`));
          }
        });
      }
    );
    req.setTimeout(TIMEOUT_MS, () => req.destroy(new Error(`Timeout: PUT ${urlPath}`)));
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

function brevoPost(urlPath, payload) {
  const body = JSON.stringify(payload);
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: "api.brevo.com",
        path: urlPath,
        method: "POST",
        headers: {
          "api-key": BREVO_KEY,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let rb = "";
        res.on("data", (c) => (rb += c));
        res.on("end", () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(rb ? JSON.parse(rb) : {});
          } else {
            reject(new Error(`Brevo POST ${urlPath} → ${res.statusCode}: ${rb.slice(0, 300)}`));
          }
        });
      }
    );
    req.setTimeout(TIMEOUT_MS, () => req.destroy(new Error(`Timeout: POST ${urlPath}`)));
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

/** Fetch all pages of a Brevo list endpoint, returns flat array of items. */
async function fetchAllPages(basePath, itemKey, pageSize = 500) {
  const items = [];
  let offset = 0;
  while (true) {
    const sep = basePath.includes("?") ? "&" : "?";
    const data = await brevoGet(`${basePath}${sep}limit=${pageSize}&offset=${offset}`);
    const page = data[itemKey] || [];
    items.push(...page);
    if (page.length < pageSize) break;
    offset += pageSize;
  }
  return items;
}

// ─── Data fetching ───────────────────────────────────────────────────────────

async function fetchSentCampaigns() {
  log("Fetching sent campaigns…");
  const data = await brevoGet("/v3/emailCampaigns?type=classic&status=sent&limit=50&sort=desc");
  let campaigns = data.campaigns || [];
  if (MAX_CAMPAIGNS) campaigns = campaigns.slice(0, parseInt(MAX_CAMPAIGNS, 10));
  log(`  → ${campaigns.length} campaign(s) found`);
  return campaigns;
}

async function fetchActiveLists() {
  log("Fetching contact lists…");
  const data = await brevoGet("/v3/contacts/lists?limit=50");
  const lists = (data.lists || []).filter(
    (l) => !EXCLUDED_LIST_IDS.has(l.id) && (l.totalSubscribers || 0) > 0
  );
  log(`  → ${lists.length} active list(s): ${lists.map(l => `#${l.id} ${l.name}`).join(", ")}`);
  return lists;
}

async function fetchListContacts(listId) {
  log(`  Fetching contacts from list #${listId}…`);
  const contacts = await fetchAllPages(
    `/v3/contacts/lists/${listId}/contacts`,
    "contacts"
  );
  log(`    → ${contacts.length} contact(s)`);
  return contacts;
}

async function fetchCampaignOpeners(campaignId) {
  try {
    const contacts = await fetchAllPages(
      `/v3/emailCampaigns/${campaignId}/contacts/opened`,
      "contacts"
    );
    return contacts.map(c => (c.email || "").toLowerCase()).filter(Boolean);
  } catch (e) {
    // Endpoint returns 404 if campaign has no engagement data at all
    if (e.message.includes("404")) return [];
    throw e;
  }
}

async function fetchCampaignClickers(campaignId) {
  try {
    const contacts = await fetchAllPages(
      `/v3/emailCampaigns/${campaignId}/contacts/clickers`,
      "contacts"
    );
    return contacts.map(c => (c.email || "").toLowerCase()).filter(Boolean);
  } catch (e) {
    if (e.message.includes("404")) return [];
    throw e;
  }
}

// ─── Suppress / move helpers ─────────────────────────────────────────────────

async function findOrCreateReengagementList(activeLists) {
  const existing = activeLists.find(l => l.name === REENGAGEMENT_LIST_NAME);
  if (existing) {
    log(`  Re-engagement list already exists: #${existing.id}`);
    return existing.id;
  }
  log(`  Creating re-engagement list "${REENGAGEMENT_LIST_NAME}"…`);
  const result = await brevoPost("/v3/contacts/lists", {
    name: REENGAGEMENT_LIST_NAME,
    folderId: REENGAGEMENT_FOLDER_ID,
  });
  log(`  → Created list #${result.id}`);
  return result.id;
}

async function blacklistContact(email) {
  await brevoPut(`/v3/contacts/${encodeURIComponent(email)}`, { emailBlacklisted: true });
}

async function moveContactToList(email, targetListId, removeFromListIds) {
  // Add to re-engagement list
  await brevoPost(`/v3/contacts/lists/${targetListId}/contacts/add`, {
    emails: [email],
  });
  // Remove from each active list
  for (const listId of removeFromListIds) {
    try {
      await brevoPost(`/v3/contacts/lists/${listId}/contacts/remove`, {
        emails: [email],
      });
    } catch (e) {
      // Contact might not be on this list — not a fatal error
      log(`    ⚠ Could not remove ${email} from list #${listId}: ${e.message}`);
    }
  }
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function log(msg) { process.stdout.write(msg + "\n"); }

function pct(n, d) {
  if (!d) return "—";
  return Math.round((n / d) * 100) + "%";
}

// ─── Report generator ─────────────────────────────────────────────────────────

function buildHtmlReport({
  generatedAt,
  campaigns,
  activeLists,
  tiers,
  suppressionBlocked,
  suppressionMode,
  suppressionDone,
  suppressedCount,
  movedCount,
}) {
  const totalContacts = tiers.reduce((s, t) => s + t.contacts.length, 0);
  const tier1 = tiers[0]; // Clickers
  const tier2 = tiers[1]; // Active Openers
  const tier3 = tiers[2]; // Occasional Openers
  const tier4 = tiers[3]; // Never Engaged

  const engagedCount = tier1.contacts.length + tier2.contacts.length + tier3.contacts.length;
  const neverCount   = tier4.contacts.length;
  const engPct       = pct(engagedCount, totalContacts);
  const neverPct     = pct(neverCount, totalContacts);

  // Suppression status banner
  let suppressionBanner = "";
  if (suppressionBlocked) {
    suppressionBanner = `
    <div class="alert">
      <span class="icon">🔒</span>
      <div>
        <strong>Suppression locked — not enough sends yet</strong>
        <p>Only ${campaigns.length} campaign(s) have been sent. The minimum is ${MIN_SENDS} sends before
        unengaged contacts are suppressed. Run this script again after send #${MIN_SENDS} to unlock suppression.
        Suppression candidates are listed below for reference only.</p>
      </div>
    </div>`;
  } else if (DRY_RUN && !suppressionDone) {
    suppressionBanner = `
    <div class="alert" style="background:#e8f5e9;border-color:#4caf50">
      <span class="icon">ℹ️</span>
      <div>
        <strong>Dry-run mode — no changes made</strong>
        <p>Re-run with <code>--suppress</code> to blacklist ${neverCount} never-engaged contact(s),
        or <code>--move-to-list</code> to move them to the re-engagement sequence instead.</p>
      </div>
    </div>`;
  } else if (suppressionDone) {
    const action = suppressionMode === "blacklist"
      ? `${suppressedCount} contact(s) blacklisted in Brevo`
      : `${movedCount} contact(s) moved to "${REENGAGEMENT_LIST_NAME}" list`;
    suppressionBanner = `
    <div class="alert" style="background:#e3f2fd;border-color:#2196f3">
      <span class="icon">✅</span>
      <div>
        <strong>Suppression complete</strong>
        <p>${action}. These contacts will not receive future campaigns unless the blacklist flag is cleared.</p>
      </div>
    </div>`;
  }

  // Campaign rows
  const campaignRows = campaigns.map((c) => {
    const s = c.statistics || {};
    const globalStats = s.globalStats || {};
    const opens   = globalStats.uniqueOpens    || 0;
    const clicks  = globalStats.uniqueClicks   || 0;
    const sent    = globalStats.sent           || 0;
    const bounces = (globalStats.hardBounces   || 0) + (globalStats.softBounces || 0);
    const unsubs  = globalStats.unsubscriptions || 0;
    const sentDate = c.sendTime ? c.sendTime.slice(0, 10) : "—";
    const trackingOk = sent > 0 && opens > 0;
    const trackingTag = trackingOk
      ? `<span style="color:#27ae60;font-size:.72rem">✓ tracking OK</span>`
      : `<span style="color:#e67e22;font-size:.72rem">⚠ tracking may be off</span>`;
    return `
      <tr>
        <td><strong>${escHtml(c.name || "—")}</strong></td>
        <td>${sentDate}</td>
        <td>${sent.toLocaleString()}</td>
        <td>${opens.toLocaleString()} <span style="color:#888;font-size:.78rem">${pct(opens, sent)}</span></td>
        <td>${clicks.toLocaleString()} <span style="color:#888;font-size:.78rem">${pct(clicks, sent)}</span></td>
        <td>${bounces.toLocaleString()}</td>
        <td>${unsubs.toLocaleString()}</td>
        <td>${trackingTag}</td>
      </tr>`;
  }).join("\n");

  // Tier rows
  function tierTable(tier, color) {
    if (!tier.contacts.length) {
      return `<p style="font-size:.8rem;color:#888;padding:12px 0">No contacts in this tier.</p>`;
    }
    const rows = tier.contacts.slice(0, 200).map(c => `
      <tr>
        <td>${escHtml(c.email)}</td>
        <td>${escHtml(c.firstName || "")} ${escHtml(c.lastName || "")}</td>
        <td>${escHtml(c.company || "")}</td>
        <td style="text-align:center">${c.opens}</td>
        <td style="text-align:center">${c.clicks}</td>
        <td>${c.listNames.join(", ")}</td>
      </tr>`).join("");
    const overflow = tier.contacts.length > 200
      ? `<p style="font-size:.75rem;color:#888;padding:8px 14px">… and ${tier.contacts.length - 200} more (capped at 200 rows in report)</p>`
      : "";
    return `
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>Email</th><th>Name</th><th>Company</th>
              <th>Opens</th><th>Clicks</th><th>Lists</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>${overflow}`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ELH Engagement Review — ${generatedAt.slice(0, 10)}</title>
<style>
  :root{--plum:#4a235a;--gold:#c9b07e;--cream:#f5f0eb;--ink:#1a1420;
    --ink-soft:#6b5f72;--light:#faf7f4;--border:#e8e0ec;
    --red:#c0392b;--green:#27ae60;--amber:#e67e22;--blue:#2980b9}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--light);color:var(--ink);font-size:14px;line-height:1.5}
  .report-header{background:var(--plum);color:var(--cream);padding:32px 40px 28px}
  .report-header h1{font-size:1.6rem;font-weight:600;margin-bottom:4px}
  .report-header .meta{font-size:.8rem;opacity:.7;letter-spacing:.06em;text-transform:uppercase}
  .report-header .badge{display:inline-block;background:var(--gold);color:var(--plum);font-size:.7rem;font-weight:700;letter-spacing:.08em;padding:3px 10px;border-radius:20px;text-transform:uppercase;margin-top:10px}
  .container{max-width:1100px;margin:0 auto;padding:32px 24px}
  .alert{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:14px 18px;margin-bottom:28px;display:flex;gap:12px;align-items:flex-start}
  .alert .icon{font-size:1.2rem;flex-shrink:0;margin-top:1px}
  .alert strong{display:block;margin-bottom:3px;font-size:.85rem}
  .alert p{font-size:.8rem;color:#856404}
  .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:32px}
  .kpi{background:#fff;border:1px solid var(--border);border-radius:10px;padding:18px 16px}
  .kpi .label{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-soft);margin-bottom:6px}
  .kpi .value{font-size:2rem;font-weight:700;line-height:1;color:var(--plum)}
  .kpi .sub{font-size:.72rem;color:var(--ink-soft);margin-top:4px}
  .kpi.good .value{color:var(--green)}
  .kpi.warn .value{color:var(--amber)}
  .kpi.bad  .value{color:var(--red)}
  .section{margin-bottom:36px}
  .section-head{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--border)}
  .section-head h2{font-size:1rem;font-weight:700;color:var(--plum)}
  .section-head .count{font-size:.75rem;color:var(--ink-soft);background:var(--cream);padding:2px 9px;border-radius:12px}
  .tbl-wrap{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff}
  table{width:100%;border-collapse:collapse}
  thead tr{background:var(--plum);color:var(--cream)}
  thead th{padding:10px 14px;font-size:.72rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;text-align:left}
  tbody tr{border-bottom:1px solid var(--border)}
  tbody tr:last-child{border-bottom:none}
  tbody tr:hover{background:#faf6ff}
  tbody td{padding:9px 14px;font-size:.82rem;vertical-align:middle}
  .tier-badge{display:inline-block;font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:12px;letter-spacing:.05em;text-transform:uppercase}
  .tier1{background:#e8f5e9;color:#1b5e20}
  .tier2{background:#e3f2fd;color:#0d47a1}
  .tier3{background:#fff9c4;color:#f57f17}
  .tier4{background:#fce4ec;color:#880e4f}
  .tier-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
  .tier-header h3{font-size:.95rem;font-weight:700;color:var(--ink)}
  .tier-header .n{font-size:.8rem;color:var(--ink-soft)}
  code{background:#f0eaf5;padding:1px 5px;border-radius:3px;font-size:.82rem}
</style>
</head>
<body>

<div class="report-header">
  <div class="meta">Eternal Life Hospice · Email Engagement Review</div>
  <h1>List Engagement Report</h1>
  <div class="badge">Generated ${generatedAt.slice(0, 16).replace("T", " ")} UTC</div>
  <div class="badge" style="margin-left:8px;background:${suppressionDone ? "#27ae60" : "#c9b07e"};color:${suppressionDone ? "#fff" : "#4a235a"}">
    ${suppressionDone ? "Suppression applied" : DRY_RUN ? "Dry-run · no changes" : "Analysis only"}
  </div>
</div>

<div class="container">

  ${suppressionBanner}

  <!-- KPIs -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="label">Campaigns analyzed</div>
      <div class="value">${campaigns.length}</div>
      <div class="sub">of ${MIN_SENDS} required for suppression</div>
    </div>
    <div class="kpi">
      <div class="label">Total contacts</div>
      <div class="value">${totalContacts.toLocaleString()}</div>
      <div class="sub">across ${activeLists.length} active list(s)</div>
    </div>
    <div class="kpi good">
      <div class="label">Engaged</div>
      <div class="value">${engagedCount.toLocaleString()}</div>
      <div class="sub">${engPct} of list — opened or clicked</div>
    </div>
    <div class="kpi ${neverPct !== "—" && parseInt(neverPct) > 50 ? "bad" : "warn"}">
      <div class="label">Never engaged</div>
      <div class="value">${neverCount.toLocaleString()}</div>
      <div class="sub">${neverPct} of list</div>
    </div>
    <div class="kpi good">
      <div class="label">Tier 1 — Clickers</div>
      <div class="value">${tier1.contacts.length.toLocaleString()}</div>
      <div class="sub">${pct(tier1.contacts.length, totalContacts)} — highest value</div>
    </div>
    <div class="kpi">
      <div class="label">Tier 2 — Active openers</div>
      <div class="value">${tier2.contacts.length.toLocaleString()}</div>
      <div class="sub">${pct(tier2.contacts.length, totalContacts)} — opened 2+×</div>
    </div>
  </div>

  <!-- Campaign table -->
  <div class="section">
    <div class="section-head">
      <h2>Campaigns</h2>
      <span class="count">${campaigns.length} sent</span>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>Campaign</th><th>Sent date</th><th>Delivered</th>
            <th>Unique opens</th><th>Unique clicks</th>
            <th>Bounces</th><th>Unsubs</th><th>Tracking</th>
          </tr>
        </thead>
        <tbody>${campaignRows}</tbody>
      </table>
    </div>
  </div>

  <!-- Tier definitions -->
  <div class="section">
    <div class="section-head">
      <h2>Engagement Tiers</h2>
      <span class="count">${totalContacts} contacts total</span>
    </div>
    <p style="font-size:.82rem;color:var(--ink-soft);margin-bottom:20px">
      Tiers are computed across all ${campaigns.length} analyzed campaign(s).
      A contact moves up a tier if they engage in ANY campaign — the best signal wins.
    </p>

    <!-- Tier 1 -->
    <div style="margin-bottom:28px">
      <div class="tier-header">
        <span class="tier-badge tier1">Tier 1</span>
        <h3>Clickers</h3>
        <span class="n">${tier1.contacts.length} contact(s) · clicked at least once</span>
      </div>
      ${tierTable(tier1)}
    </div>

    <!-- Tier 2 -->
    <div style="margin-bottom:28px">
      <div class="tier-header">
        <span class="tier-badge tier2">Tier 2</span>
        <h3>Active Openers</h3>
        <span class="n">${tier2.contacts.length} contact(s) · opened 2+ times, never clicked</span>
      </div>
      ${tierTable(tier2)}
    </div>

    <!-- Tier 3 -->
    <div style="margin-bottom:28px">
      <div class="tier-header">
        <span class="tier-badge tier3">Tier 3</span>
        <h3>Occasional Openers</h3>
        <span class="n">${tier3.contacts.length} contact(s) · opened once, never clicked</span>
      </div>
      ${tierTable(tier3)}
    </div>

    <!-- Tier 4 -->
    <div style="margin-bottom:28px">
      <div class="tier-header">
        <span class="tier-badge tier4">Tier 4</span>
        <h3>Never Engaged</h3>
        <span class="n">${tier4.contacts.length} contact(s) · zero opens, zero clicks across all ${campaigns.length} campaigns</span>
      </div>
      ${suppressionBlocked
        ? `<p style="font-size:.8rem;color:#888;margin-bottom:10px">⚠ Suppression locked until ${MIN_SENDS} campaigns are sent (currently ${campaigns.length}).</p>`
        : suppressionDone
          ? `<p style="font-size:.8rem;color:#27ae60;margin-bottom:10px">✓ These contacts have been ${suppressionMode === "blacklist" ? "blacklisted" : "moved to the re-engagement list"}.</p>`
          : `<p style="font-size:.8rem;color:#888;margin-bottom:10px">Re-run with <code>--suppress</code> or <code>--move-to-list</code> to act on these contacts.</p>`
      }
      ${tierTable(tier4)}
    </div>
  </div>

  <!-- How to use -->
  <div class="section">
    <div class="section-head"><h2>How to Use This Report</h2></div>
    <div style="background:#fff;border:1px solid var(--border);border-radius:10px;padding:20px 24px;font-size:.83rem;line-height:1.8">
      <p><strong>Tier 1 (Clickers)</strong> — your most responsive contacts. Ideal for direct follow-up phone calls,
      in-person outreach, or a targeted referral-ask sequence. Create a Brevo segment for these contacts.</p>
      <p style="margin-top:10px"><strong>Tier 2 (Active Openers)</strong> — warm contacts who read but haven't acted.
      Send a stronger CTA: a specific resource, a case study, or a direct invitation. Move them toward a click.</p>
      <p style="margin-top:10px"><strong>Tier 3 (Occasional Openers)</strong> — one touch of engagement.
      Continue with the regular weekly cadence. Monitor for a second open or click before escalating.</p>
      <p style="margin-top:10px"><strong>Tier 4 (Never Engaged)</strong> — zero engagement across ${campaigns.length} campaign(s).
      ${campaigns.length < MIN_SENDS
        ? `Wait until ${MIN_SENDS} campaigns have been sent before suppressing. B2B contacts at health systems
           sometimes have email delays or corporate spam filters — give them the full ${MIN_SENDS}-send window.`
        : `Suppress or move to re-engagement sequence. Run with <code>--suppress</code> to blacklist, or
           <code>--move-to-list</code> to shift to a lighter re-engagement drip before final suppression.`
      }</p>
      <p style="margin-top:16px;font-size:.78rem;color:var(--ink-soft)">
        <strong>Script:</strong> <code>BREVO_API=&lt;key&gt; node exports/campaign-reports/engagement-review.js [--suppress | --move-to-list] [--min-sends 6]</code>
      </p>
    </div>
  </div>

</div><!-- /container -->
</body>
</html>`;
}

function escHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const generatedAt = new Date().toISOString();
  log(`\nELH Engagement Review — ${generatedAt.slice(0, 16).replace("T", " ")} UTC`);
  log(`Mode: ${DRY_RUN ? "dry-run (analysis only)" : DO_SUPPRESS ? "SUPPRESS (blacklist)" : "MOVE TO LIST"}`);
  log(`Min sends required for suppression: ${MIN_SENDS}\n`);

  // 1. Fetch campaigns
  const campaigns = await fetchSentCampaigns();
  if (!campaigns.length) {
    log("No sent campaigns found. Nothing to analyze.");
    process.exit(0);
  }

  // 2. Fetch active lists and all their contacts
  const activeLists = await fetchActiveLists();
  if (!activeLists.length) {
    log("No active contact lists found. Nothing to analyze.");
    process.exit(0);
  }

  log("\nFetching all contacts across active lists…");
  // Map: email → { email, firstName, lastName, company, listIds: Set, opens: 0, clicks: 0 }
  const contactMap = new Map();
  const listNameMap = new Map(activeLists.map(l => [l.id, l.name]));

  for (const list of activeLists) {
    const contacts = await fetchListContacts(list.id);
    for (const c of contacts) {
      const email = (c.email || "").toLowerCase().trim();
      if (!email) continue;
      if (!contactMap.has(email)) {
        const attrs = c.attributes || {};
        contactMap.set(email, {
          email,
          firstName: attrs.FIRSTNAME || "",
          lastName:  attrs.LASTNAME  || "",
          company:   attrs.COMPANY   || "",
          listIds:   new Set([list.id]),
          opens:     0,
          clicks:    0,
        });
      } else {
        contactMap.get(email).listIds.add(list.id);
      }
    }
  }
  log(`\nTotal unique contacts across all active lists: ${contactMap.size}\n`);

  // 3. Pull per-campaign engagement and accumulate opens/clicks per contact
  log("Fetching opener and clicker lists per campaign…");
  for (const campaign of campaigns) {
    log(`  Campaign: "${campaign.name}" (id=${campaign.id})`);
    const [openers, clickers] = await Promise.all([
      fetchCampaignOpeners(campaign.id),
      fetchCampaignClickers(campaign.id),
    ]);
    log(`    Openers: ${openers.length} · Clickers: ${clickers.length}`);

    for (const email of openers) {
      if (contactMap.has(email)) contactMap.get(email).opens++;
    }
    for (const email of clickers) {
      if (contactMap.has(email)) contactMap.get(email).clicks++;
    }
  }

  // 4. Segment into tiers
  const t1 = [], t2 = [], t3 = [], t4 = [];
  for (const c of contactMap.values()) {
    const listNames = [...c.listIds].map(id => listNameMap.get(id) || `#${id}`);
    const entry = { ...c, listNames };
    if (c.clicks > 0)       t1.push(entry);
    else if (c.opens >= 2)  t2.push(entry);
    else if (c.opens === 1) t3.push(entry);
    else                    t4.push(entry);
  }

  // Sort each tier by engagement desc, then alpha
  const byEngagement = (a, b) => (b.opens + b.clicks * 2) - (a.opens + a.clicks * 2) || a.email.localeCompare(b.email);
  t1.sort(byEngagement); t2.sort(byEngagement); t3.sort(byEngagement);
  t4.sort((a, b) => a.email.localeCompare(b.email));

  const tiers = [
    { name: "Clickers",           contacts: t1 },
    { name: "Active Openers",     contacts: t2 },
    { name: "Occasional Openers", contacts: t3 },
    { name: "Never Engaged",      contacts: t4 },
  ];

  log(`\nTier results:`);
  log(`  Tier 1 Clickers:           ${t1.length}`);
  log(`  Tier 2 Active Openers:     ${t2.length}`);
  log(`  Tier 3 Occasional Openers: ${t3.length}`);
  log(`  Tier 4 Never Engaged:      ${t4.length}`);

  // 5. Suppression / move
  const suppressionBlocked = campaigns.length < MIN_SENDS;
  let suppressionDone  = false;
  let suppressionMode  = "";
  let suppressedCount  = 0;
  let movedCount       = 0;

  if ((DO_SUPPRESS || DO_MOVE) && !DRY_RUN) {
    if (suppressionBlocked) {
      log(`\n⚠ Suppression blocked: only ${campaigns.length} campaign(s) sent, ${MIN_SENDS} required.`);
    } else if (!t4.length) {
      log("\nNo never-engaged contacts to suppress.");
    } else {
      log(`\nApplying suppression to ${t4.length} never-engaged contact(s)…`);
      suppressionMode = DO_SUPPRESS ? "blacklist" : "move";

      let reengagementListId = null;
      if (DO_MOVE) {
        reengagementListId = await findOrCreateReengagementList(activeLists);
      }

      const sourceListIds = activeLists.map(l => l.id);

      for (const contact of t4) {
        try {
          if (DO_SUPPRESS) {
            await blacklistContact(contact.email);
            suppressedCount++;
          } else {
            await moveContactToList(contact.email, reengagementListId, sourceListIds);
            movedCount++;
          }
          if ((suppressedCount + movedCount) % 50 === 0) {
            log(`  … ${suppressedCount + movedCount} of ${t4.length} processed`);
          }
        } catch (e) {
          log(`  ⚠ Failed for ${contact.email}: ${e.message}`);
        }
      }
      suppressionDone = true;
      log(`  Done. ${suppressedCount + movedCount} contacts processed.`);
    }
  }

  // 6. Generate HTML report
  const html = buildHtmlReport({
    generatedAt,
    campaigns,
    activeLists,
    tiers,
    suppressionBlocked,
    suppressionMode,
    suppressionDone,
    suppressedCount,
    movedCount,
  });

  const defaultPath = path.join(
    __dirname,
    `engagement-report-${generatedAt.slice(0, 10)}.html`
  );
  const outputPath = OUTPUT_PATH || defaultPath;
  fs.writeFileSync(outputPath, html, "utf8");
  log(`\nReport written to: ${outputPath}`);

  // 7. Print summary to stdout
  const total = contactMap.size;
  log(`\n${"─".repeat(60)}`);
  log(`SUMMARY`);
  log(`${"─".repeat(60)}`);
  log(`Campaigns analyzed : ${campaigns.length} (minimum for suppression: ${MIN_SENDS})`);
  log(`Total contacts     : ${total}`);
  log(`  Tier 1 Clickers          : ${t1.length} (${pct(t1.length, total)})`);
  log(`  Tier 2 Active Openers    : ${t2.length} (${pct(t2.length, total)})`);
  log(`  Tier 3 Occasional Openers: ${t3.length} (${pct(t3.length, total)})`);
  log(`  Tier 4 Never Engaged     : ${t4.length} (${pct(t4.length, total)})`);
  if (suppressionDone) {
    log(`\nSuppression: ${suppressedCount + movedCount} contact(s) processed (${suppressionMode})`);
  } else if (suppressionBlocked) {
    log(`\nSuppression: LOCKED — re-run after send #${MIN_SENDS}`);
  } else {
    log(`\nSuppression: dry-run — re-run with --suppress or --move-to-list to act`);
  }
  log(`${"─".repeat(60)}\n`);
}

main().catch((err) => {
  console.error("Fatal error:", err.message || err);
  process.exit(1);
});
