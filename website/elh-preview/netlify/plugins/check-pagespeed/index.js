/**
 * Netlify Build Plugin — PageSpeed Insights post-deploy check
 *
 * Runs on every successful production deploy. Queries the Google PageSpeed
 * Insights API for the live site and fails the deploy notification if the
 * mobile performance score drops below THRESHOLD.
 *
 * Required env var : GOOGLE_API_KEY      (Netlify Site → Environment variables)
 * Optional env var : PSI_THRESHOLD       (integer 0-100, default 80)
 * Optional env var : PSI_URL             (override the URL to check)
 * Optional env var : LCP_BUDGET_MS       (integer ms, default 2500)
 *                    Budget rationale: Google "Good" LCP threshold is ≤ 2.5 s.
 *                    The ELH homepage was optimised to ~1.9 s (mobile); 2.5 s
 *                    gives a 600 ms regression buffer before failing the build,
 *                    keeping us firmly in the "Good" band on Core Web Vitals.
 *
 * Alert env vars (at least one recommended):
 *   SLACK_WEBHOOK_URL  — Slack incoming webhook URL; set in Netlify env vars
 *   BREVO_API          — Brevo v3 API key for email alerts
 *   ALERT_EMAIL_TO     — recipient address for Brevo alerts (default: team@eternallifehospice.com)
 *   ALERT_EMAIL_FROM   — sender address (default: noreply@eternallifehospice.com)
 *
 * Alerts fire only on failure; passing deploys are silent.
 */

"use strict";

const https = require("https");

const PSI_HOST = "www.googleapis.com";
const PSI_PATH = "/pagespeedonline/v5/runPagespeed";
const DEFAULT_URL = "https://eternallifehospice.com";
const DEFAULT_THRESHOLD = 80;
// LCP budget: Google "Good" ceiling is 2500 ms. We enforce this to catch
// regressions from image swaps, new fonts, or third-party scripts early.
const DEFAULT_LCP_BUDGET_MS = 2500;
const DEFAULT_ALERT_TO   = "team@eternallifehospice.com";
const DEFAULT_ALERT_FROM = "noreply@eternallifehospice.com";

const AUDITS_OF_INTEREST = [
  ["largest-contentful-paint", "LCP"],
  ["first-contentful-paint",   "FCP"],
  ["speed-index",              "Speed Index"],
  ["total-blocking-time",      "TBT"],
  ["cumulative-layout-shift",  "CLS"],
  ["uses-long-cache-ttl",      "Cache TTL"],
];

// ---------------------------------------------------------------------------
// Generic JSON POST helper
// ---------------------------------------------------------------------------
function jsonPost(host, path, payload, headers = {}) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const reqHeaders = {
      "Content-Type":  "application/json",
      "Content-Length": Buffer.byteLength(body),
      ...headers,
    };
    const req = https.request(
      { method: "POST", host, path, headers: reqHeaders, timeout: 15_000 },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () =>
          resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString() })
        );
      }
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("HTTP request timed out after 15 s"));
    });
    req.write(body);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// PSI request
// ---------------------------------------------------------------------------
function psiRequest(url, strategy, apiKey) {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams({
      url,
      strategy,
      key: apiKey,
      category: "performance",
    });
    const path = `${PSI_PATH}?${params}`;
    const req = https.get({ host: PSI_HOST, path, timeout: 90_000 }, (res) => {
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => {
        const body = Buffer.concat(chunks).toString();
        if (res.statusCode !== 200) {
          return reject(new Error(`PSI API returned HTTP ${res.statusCode}: ${body.slice(0, 300)}`));
        }
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(new Error(`PSI response parse error: ${e.message}`));
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("PSI API request timed out after 90 s"));
    });
  });
}

// ---------------------------------------------------------------------------
// Slack notification
// ---------------------------------------------------------------------------
async function sendSlackAlert({ webhookUrl, score, threshold, deployLogUrl, siteUrl, reason, extra }) {
  const url = new URL(webhookUrl);
  const emoji  = "🔴";
  const header = reason === "no-score"
    ? `${emoji} *PageSpeed check failed* — no performance score returned`
    : reason === "lcp-over-budget"
    ? `${emoji} *PageSpeed check failed* — LCP budget exceeded`
    : `${emoji} *PageSpeed check failed* — score ${score}/100 (threshold ${threshold}/100)`;

  const body = {
    blocks: [
      {
        type: "section",
        text: { type: "mrkdwn", text: header },
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*Site:*\n${siteUrl}` },
          { type: "mrkdwn", text: `*Score:*\n${score != null ? `${score}/100` : "n/a"}` },
          { type: "mrkdwn", text: `*Threshold:*\n${threshold}/100` },
          { type: "mrkdwn", text: `*Deploy log:*\n<${deployLogUrl}|View on Netlify>` },
        ],
      },
    ],
  };

  const result = await jsonPost(url.host, url.pathname + url.search, body);
  if (result.status !== 200) {
    throw new Error(`Slack webhook returned HTTP ${result.status}: ${result.body.slice(0, 200)}`);
  }
}

// ---------------------------------------------------------------------------
// Brevo (Sendinblue) email notification
// ---------------------------------------------------------------------------
async function sendBrevoAlert({ apiKey, to, from, score, threshold, deployLogUrl, siteUrl, reason, extra }) {
  const subject = reason === "no-score"
    ? "⚠️ PageSpeed check failed — no score returned"
    : reason === "lcp-over-budget"
    ? "⚠️ PageSpeed check failed — LCP budget exceeded"
    : `⚠️ PageSpeed score ${score}/100 is below threshold (${threshold}/100)`;

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:24px;margin:0">
  <table width="600" style="background:#fff;border-radius:8px;padding:32px;margin:0 auto">
    <tr><td>
      <p style="font-size:20px;font-weight:bold;color:#c0392b;margin:0 0 16px">
        🔴 PageSpeed Check Failed
      </p>
      <table width="100%" cellpadding="8" style="border-collapse:collapse;margin-bottom:24px">
        <tr style="background:#fafafa">
          <td style="font-weight:bold;width:120px;color:#555">Site</td>
          <td><a href="${siteUrl}" style="color:#2563eb">${siteUrl}</a></td>
        </tr>
        <tr>
          <td style="font-weight:bold;color:#555">Score</td>
          <td style="color:#c0392b;font-weight:bold">${score != null ? `${score}/100` : "n/a"}</td>
        </tr>
        <tr style="background:#fafafa">
          <td style="font-weight:bold;color:#555">Threshold</td>
          <td>${threshold}/100</td>
        </tr>
      </table>
      <p>
        <a href="${deployLogUrl}"
           style="background:#2563eb;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold">
          View Deploy Log on Netlify →
        </a>
      </p>
      <p style="color:#888;font-size:13px;margin-top:24px">
        This alert was sent automatically by the Netlify PageSpeed build plugin.
        Passing deploys do not generate notifications.
      </p>
    </td></tr>
  </table>
</body>
</html>`;

  const payload = {
    sender:  { name: "ELH Deploy Monitor", email: from },
    to:      [{ email: to }],
    subject,
    htmlContent,
  };

  const result = await jsonPost(
    "api.brevo.com",
    "/v3/smtp/email",
    payload,
    { "api-key": apiKey }
  );

  if (result.status < 200 || result.status >= 300) {
    throw new Error(`Brevo API returned HTTP ${result.status}: ${result.body.slice(0, 200)}`);
  }
}

// ---------------------------------------------------------------------------
// Unified alert dispatcher — fires whichever channels are configured
// ---------------------------------------------------------------------------
async function sendAlert(opts) {
  const results = [];

  // Slack
  const slackWebhook = process.env.SLACK_WEBHOOK_URL;
  if (slackWebhook) {
    try {
      await sendSlackAlert({ webhookUrl: slackWebhook, ...opts });
      results.push("Slack ✓");
    } catch (err) {
      results.push(`Slack ✗ (${err.message})`);
    }
  }

  // Brevo email
  const brevoKey = process.env.BREVO_API;
  if (brevoKey) {
    const to   = process.env.ALERT_EMAIL_TO   || DEFAULT_ALERT_TO;
    const from = process.env.ALERT_EMAIL_FROM || DEFAULT_ALERT_FROM;
    try {
      await sendBrevoAlert({ apiKey: brevoKey, to, from, ...opts });
      results.push(`Email → ${to} ✓`);
    } catch (err) {
      results.push(`Email ✗ (${err.message})`);
    }
  }

  if (results.length === 0) {
    console.log(
      "  [Alert] No notification channels configured. " +
      "Set SLACK_WEBHOOK_URL and/or BREVO_API in Netlify env vars to enable alerts."
    );
  } else {
    console.log(`  [Alert] Notifications sent — ${results.join(", ")}`);
  }
}

// ---------------------------------------------------------------------------
// Build plugin entry point
// ---------------------------------------------------------------------------
module.exports = {
  onSuccess: async ({ utils, constants }) => {
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      utils.build.failPlugin(
        "GOOGLE_API_KEY is not set — add it in Netlify Site → Environment variables."
      );
      return;
    }

    const siteUrl    = process.env.PSI_URL || DEFAULT_URL;
    const threshold  = parseInt(process.env.PSI_THRESHOLD  || String(DEFAULT_THRESHOLD),    10);
    const lcpBudget  = parseInt(process.env.LCP_BUDGET_MS  || String(DEFAULT_LCP_BUDGET_MS), 10);
    const strategy   = "mobile";

    // Build a link to the Netlify deploy log for this exact deploy
    const siteName = constants.SITE_NAME || "elh-preview";
    const deployId = constants.DEPLOY_ID || "";
    const deployLogUrl = deployId
      ? `https://app.netlify.com/sites/${siteName}/deploys/${deployId}`
      : `https://app.netlify.com/sites/${siteName}/deploys`;

    console.log(`\n${"=".repeat(60)}`);
    console.log(`  PageSpeed Insights post-deploy check`);
    console.log(`  URL      : ${siteUrl}`);
    console.log(`  Strategy : ${strategy}`);
    console.log(`  Threshold: ${threshold}/100`);
    console.log(`  LCP budget: ≤ ${lcpBudget} ms  (Google "Good" = ≤ 2500 ms)`);
    console.log(`${"=".repeat(60)}`);

    let data;
    try {
      data = await psiRequest(siteUrl, strategy, apiKey);
    } catch (err) {
      // API error — alert the team then fail the plugin
      await sendAlert({
        score: null,
        threshold,
        deployLogUrl,
        siteUrl,
        reason: "api-error",
      });
      utils.build.failPlugin(`PageSpeed API error: ${err.message}`);
      return;
    }

    const cats   = data?.lighthouseResult?.categories ?? {};
    const audits = data?.lighthouseResult?.audits ?? {};

    const perfScore = cats?.performance?.score;
    const perf = perfScore != null ? Math.round(perfScore * 100) : null;

    if (perf != null) {
      const bar = "█".repeat(Math.floor(perf / 5));
      console.log(`\n  Overall performance : ${String(perf).padStart(3)}/100  ${bar}`);
    } else {
      console.log("\n  Overall performance : n/a");
    }

    console.log();
    for (const [auditId, shortLabel] of AUDITS_OF_INTEREST) {
      const audit = audits[auditId] ?? {};
      const s     = audit.score != null ? Math.round(audit.score * 100) : null;
      const dv    = audit.displayValue ?? "";
      const sStr  = s != null ? `${String(s).padStart(3)}/100` : "  n/a ";
      console.log(`  ${shortLabel.padEnd(20)} ${sStr}   ${dv}`);
    }

    console.log(`\n${"=".repeat(60)}\n`);

    if (perf == null) {
      await sendAlert({
        score: null,
        threshold,
        deployLogUrl,
        siteUrl,
        reason: "no-score",
      });
      utils.build.failPlugin("PageSpeed returned no performance score — check the API response.");
      return;
    }

    if (perf < threshold) {
      await sendAlert({
        score: perf,
        threshold,
        deployLogUrl,
        siteUrl,
        reason: "below-threshold",
      });
      utils.build.failPlugin(
        `Performance score ${perf}/100 is below the required threshold of ${threshold}/100. ` +
        `Review recent changes for regressions.`
      );
      return;
    }

    // ------------------------------------------------------------------
    // LCP budget check
    // PSI reports numericValue in milliseconds. We enforce ≤ LCP_BUDGET_MS
    // (default 2500 ms) — the Google "Good" Core Web Vitals threshold.
    // This catches regressions from image swaps, font changes, or new
    // third-party scripts before they reach users.
    // ------------------------------------------------------------------
    const lcpAudit = audits["largest-contentful-paint"] ?? {};
    const lcpMs    = lcpAudit.numericValue != null ? Math.round(lcpAudit.numericValue) : null;
    const lcpDisplay = lcpAudit.displayValue ?? (lcpMs != null ? `${(lcpMs / 1000).toFixed(1)} s` : "n/a");

    if (lcpMs == null) {
      console.log("  [LCP] numericValue not present in PSI response — skipping LCP budget check.");
    } else if (lcpMs > lcpBudget) {
      const msg =
        `LCP ${lcpDisplay} (${lcpMs} ms) exceeds budget of ${lcpBudget} ms. ` +
        `Check for new render-blocking resources, unoptimised images, or added third-party scripts.`;
      await sendAlert({
        score: perf,
        threshold,
        deployLogUrl,
        siteUrl,
        reason: "lcp-over-budget",
        extra: msg,
      });
      utils.build.failPlugin(msg);
      return;
    } else {
      console.log(`  ✓ LCP ${lcpDisplay} (${lcpMs} ms) is within the ${lcpBudget} ms budget.`);
    }

    console.log(
      `✓ PageSpeed check passed: ${perf}/100 meets threshold ${threshold}/100.`
    );
  },
};
