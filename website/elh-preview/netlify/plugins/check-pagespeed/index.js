/**
 * Netlify Build Plugin — PageSpeed Insights post-deploy check
 *
 * Runs on every successful production deploy. Queries the Google PageSpeed
 * Insights API for the live site and fails the deploy notification if the
 * mobile performance score drops below THRESHOLD.
 *
 * Required env var: GOOGLE_API_KEY  (set in Netlify Site → Environment variables)
 * Optional env var: PSI_THRESHOLD   (integer 0-100, default 80)
 * Optional env var: PSI_URL         (override the URL to check)
 */

"use strict";

const https = require("https");

const PSI_HOST = "www.googleapis.com";
const PSI_PATH = "/pagespeedonline/v5/runPagespeed";
const DEFAULT_URL = "https://eternallifehospice.com";
const DEFAULT_THRESHOLD = 80;

const AUDITS_OF_INTEREST = [
  ["largest-contentful-paint", "LCP"],
  ["first-contentful-paint",   "FCP"],
  ["speed-index",              "Speed Index"],
  ["total-blocking-time",      "TBT"],
  ["cumulative-layout-shift",  "CLS"],
  ["uses-long-cache-ttl",      "Cache TTL"],
];

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

module.exports = {
  onSuccess: async ({ utils, constants }) => {
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      utils.build.failPlugin(
        "GOOGLE_API_KEY is not set — add it in Netlify Site → Environment variables."
      );
      return;
    }

    const siteUrl   = process.env.PSI_URL || DEFAULT_URL;
    const threshold = parseInt(process.env.PSI_THRESHOLD || String(DEFAULT_THRESHOLD), 10);
    const strategy  = "mobile";

    console.log(`\n${"=".repeat(60)}`);
    console.log(`  PageSpeed Insights post-deploy check`);
    console.log(`  URL      : ${siteUrl}`);
    console.log(`  Strategy : ${strategy}`);
    console.log(`  Threshold: ${threshold}/100`);
    console.log(`${"=".repeat(60)}`);

    let data;
    try {
      data = await psiRequest(siteUrl, strategy, apiKey);
    } catch (err) {
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
      utils.build.failPlugin("PageSpeed returned no performance score — check the API response.");
      return;
    }

    if (perf < threshold) {
      utils.build.failPlugin(
        `Performance score ${perf}/100 is below the required threshold of ${threshold}/100. ` +
        `Review recent changes for regressions.`
      );
      return;
    }

    console.log(
      `✓ PageSpeed check passed: ${perf}/100 meets threshold ${threshold}/100.`
    );
  },
};
