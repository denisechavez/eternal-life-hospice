// brevoReportingPlugin.ts
async function brevoJson(path, apiKey) {
  const response = await fetch(`https://api.brevo.com/v3${path}`, {
    headers: {
      accept: "application/json",
      "api-key": apiKey
    }
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || `Brevo request failed (${response.status})`);
  }
  return payload;
}
function safeNumber(value) {
  return Number.isFinite(value) ? Number(value) : 0;
}
function campaignTotals(campaign) {
  const base = { sent: 0, delivered: 0, viewed: 0, uniqueViews: 0, clickers: 0, uniqueClicks: 0, hardBounces: 0, softBounces: 0, unsubscriptions: 0, complaints: 0 };
  const rows = campaign.statistics?.campaignStats;
  if (rows?.length) {
    return rows.reduce((acc, stats2) => {
      for (const key of Object.keys(base)) acc[key] = acc[key] + safeNumber(stats2[key]);
      return acc;
    }, { ...base });
  }
  const stats = campaign.statistics?.globalStats;
  for (const key of Object.keys(base)) base[key] = safeNumber(stats?.[key]);
  return base;
}
async function buildBrevoReport() {
  const apiKey = process.env.BREVO_API;
  if (!apiKey) {
    throw new Error("Brevo is not configured.");
  }
  const [campaignResult, listResult] = await Promise.all([
    brevoJson(
      "/emailCampaigns?limit=50&offset=0&sort=desc",
      apiKey
    ),
    brevoJson(
      "/contacts/lists?limit=50&offset=0&sort=desc",
      apiKey
    )
  ]);
  const campaignSummaries = campaignResult.campaigns ?? [];
  const campaignDetails = await Promise.allSettled(
    campaignSummaries.slice(0, 20).map(
      (campaign) => brevoJson(`/emailCampaigns/${campaign.id}`, apiKey)
    )
  );
  const detailedById = /* @__PURE__ */ new Map();
  campaignDetails.forEach((result) => {
    if (result.status === "fulfilled") detailedById.set(result.value.id, result.value);
  });
  const campaigns = campaignSummaries.map((campaign) => detailedById.get(campaign.id) ?? campaign);
  const lists = listResult.lists ?? [];
  const periodEnd = /* @__PURE__ */ new Date();
  periodEnd.setUTCDate(periodEnd.getUTCDate() - 2);
  const periodStart = new Date(periodEnd);
  periodStart.setUTCDate(periodStart.getUTCDate() - 27);
  const inPeriod = (campaign) => {
    if (!campaign.sentDate) return false;
    const sent = new Date(campaign.sentDate);
    return sent >= periodStart && sent < new Date(periodEnd.getTime() + 864e5);
  };
  const reduceCampaigns = (source2) => source2.reduce(
    (acc, campaign) => {
      const stats = campaignTotals(campaign);
      acc.sent += stats.sent;
      acc.delivered += stats.delivered;
      acc.opens += stats.viewed;
      acc.uniqueViews += stats.uniqueViews;
      acc.clicks += stats.clickers;
      acc.uniqueClicks += stats.uniqueClicks;
      acc.bounces += stats.hardBounces + stats.softBounces;
      acc.unsubscriptions += stats.unsubscriptions;
      return acc;
    },
    { sent: 0, delivered: 0, opens: 0, uniqueViews: 0, clicks: 0, uniqueClicks: 0, bounces: 0, unsubscriptions: 0 }
  );
  const totals = reduceCampaigns(campaigns);
  const periodCampaigns = campaigns.filter(inPeriod);
  const periodTotals = reduceCampaigns(periodCampaigns);
  return {
    live: true,
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    period: {
      startDate: periodStart.toISOString().slice(0, 10),
      endDate: periodEnd.toISOString().slice(0, 10),
      label: "Last 28 days"
    },
    metrics: {
      campaigns: campaignResult.count ?? campaigns.length,
      sentCampaigns: campaigns.filter((campaign) => campaign.status === "sent").length,
      activeLists: lists.length,
      subscribers: lists.reduce(
        (sum, list) => sum + safeNumber(list.uniqueSubscribers ?? list.totalSubscribers),
        0
      ),
      ...totals
    },
    periodMetrics: {
      campaigns: periodCampaigns.length,
      ...periodTotals
    },
    diagnostic: {
      result: "CAMPAIGN-SPECIFIC STATS REQUIRED",
      explanation: "Brevo globalStats is present but zero. Valid delivery and engagement totals are stored in statistics.campaignStats and must be summed across recipient lists.",
      historicalCampaignsValidated: campaigns.length
    },
    campaigns: campaigns.map((campaign) => {
      const stats = campaignTotals(campaign);
      return {
        id: campaign.id,
        name: campaign.name || "Untitled campaign",
        subject: campaign.subject || "",
        status: campaign.status || "unknown",
        type: campaign.type || "classic",
        scheduledAt: campaign.scheduledAt || null,
        sentDate: campaign.sentDate || null,
        sent: stats.sent,
        delivered: stats.delivered,
        uniqueViews: stats.uniqueViews,
        uniqueClicks: stats.uniqueClicks,
        hardBounces: stats.hardBounces,
        softBounces: stats.softBounces,
        unsubscriptions: stats.unsubscriptions
      };
    }),
    lists: lists.map((list) => ({
      id: list.id,
      name: list.name || `List ${list.id}`,
      subscribers: safeNumber(list.uniqueSubscribers ?? list.totalSubscribers),
      blacklisted: safeNumber(list.totalBlacklisted)
    }))
  };
}

// liveReportingPlugin.ts
import { createSign } from "node:crypto";
var cachedToken = null;
function base64Url(value) {
  return Buffer.from(value).toString("base64").replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}
async function getAccessToken(account) {
  if (cachedToken && cachedToken.expiresAt > Date.now() + 6e4) {
    return cachedToken.value;
  }
  const now = Math.floor(Date.now() / 1e3);
  const header = base64Url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claims = base64Url(JSON.stringify({
    iss: account.client_email,
    scope: [
      "https://www.googleapis.com/auth/analytics.readonly",
      "https://www.googleapis.com/auth/webmasters.readonly"
    ].join(" "),
    aud: account.token_uri ?? "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600
  }));
  const unsigned = `${header}.${claims}`;
  const signer = createSign("RSA-SHA256");
  signer.update(unsigned);
  const signature = signer.sign(account.private_key, "base64url");
  const assertion = `${unsigned}.${signature}`;
  const response = await fetch(account.token_uri ?? "https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion
    })
  });
  const payload = await response.json();
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description || `Google token request failed (${response.status})`);
  }
  cachedToken = {
    value: payload.access_token,
    expiresAt: Date.now() + (payload.expires_in ?? 3600) * 1e3
  };
  return cachedToken.value;
}
function isoDate(date) {
  return date.toISOString().slice(0, 10);
}
function reportingDates(period2) {
  const today = /* @__PURE__ */ new Date();
  const end = new Date(today);
  end.setUTCDate(end.getUTCDate() - 2);
  const start = new Date(end);
  if (period2 === "previous") {
    end.setUTCDate(end.getUTCDate() - 28);
    start.setTime(end.getTime());
    start.setUTCDate(start.getUTCDate() - 27);
    return { startDate: isoDate(start), endDate: isoDate(end), label: "Previous 28 days" };
  }
  if (period2 === "ytd") {
    start.setUTCMonth(0, 1);
    return { startDate: isoDate(start), endDate: isoDate(end), label: "Year to date" };
  }
  start.setUTCDate(start.getUTCDate() - 27);
  return { startDate: isoDate(start), endDate: isoDate(end), label: "Last 28 days" };
}
async function googleJson(url, token, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json"
    },
    body: JSON.stringify(body)
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error?.message || `Google API request failed (${response.status})`);
  }
  return payload;
}
function metric(row, index) {
  return Number(row?.metricValues?.[index]?.value ?? 0);
}
async function buildReport(period2) {
  const rawCredential = process.env.GOOGLE_REPORTING_SERVICE_ACCOUNT_JSON_V2;
  const propertyId = process.env.GA4_PROPERTY_ID;
  if (!rawCredential || !propertyId) {
    throw new Error("Google reporting credentials or GA4 property ID are not configured.");
  }
  const account = JSON.parse(rawCredential);
  if (!account.client_email || !account.private_key) {
    throw new Error("The Google service-account JSON is incomplete.");
  }
  const token = await getAccessToken(account);
  const dates = reportingDates(period2);
  const gaUrl = `https://analyticsdata.googleapis.com/v1beta/properties/${encodeURIComponent(propertyId)}:runReport`;
  const gscUrl = `https://searchconsole.googleapis.com/webmasters/v3/sites/${encodeURIComponent("https://eternallifehospice.com/")}/searchAnalytics/query`;
  const [gaOverview, gaLanding, gscOverview, gscQueries, gscPages] = await Promise.allSettled([
    googleJson(gaUrl, token, {
      dateRanges: [{ startDate: dates.startDate, endDate: dates.endDate }],
      dimensions: [{ name: "date" }],
      metrics: [{ name: "sessions" }, { name: "keyEvents" }],
      orderBys: [{ dimension: { dimensionName: "date" } }],
      metricAggregations: ["TOTAL"]
    }),
    googleJson(gaUrl, token, {
      dateRanges: [{ startDate: dates.startDate, endDate: dates.endDate }],
      dimensions: [{ name: "landingPagePlusQueryString" }],
      metrics: [{ name: "sessions" }, { name: "engagementRate" }, { name: "keyEvents" }],
      limit: 1e3,
      orderBys: [{ metric: { metricName: "sessions" }, desc: true }]
    }),
    googleJson(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: [], rowLimit: 1 }
    ),
    googleJson(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: ["query"], rowLimit: 10 }
    ),
    googleJson(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: ["page"], rowLimit: 1e3 }
    )
  ]);
  const errors = [];
  if (gaOverview.status === "rejected") errors.push(`GA4: ${gaOverview.reason instanceof Error ? gaOverview.reason.message : String(gaOverview.reason)}`);
  if (gscOverview.status === "rejected") errors.push(`Search Console: ${gscOverview.reason instanceof Error ? gscOverview.reason.message : String(gscOverview.reason)}`);
  const gaTotal = gaOverview.status === "fulfilled" ? gaOverview.value.totals?.[0] : void 0;
  const searchTotal = gscOverview.status === "fulfilled" ? gscOverview.value.rows?.[0] : void 0;
  const marketDefinitions = [
    { market: "Thousand Oaks", terms: ["thousand-oaks", "thousand oaks"] },
    { market: "Westlake Village", terms: ["westlake-village", "westlake village"] },
    { market: "Simi Valley", terms: ["simi-valley", "simi valley"] },
    { market: "Calabasas", terms: ["calabasas"] },
    { market: "Camarillo", terms: ["camarillo"] },
    { market: "Moorpark", terms: ["moorpark"] },
    { market: "Ventura County", terms: ["ventura-county", "ventura county"] },
    { market: "Los Angeles County", terms: ["los-angeles-county", "los angeles county"] }
  ];
  const gaRows = gaLanding.status === "fulfilled" ? gaLanding.value.rows ?? [] : [];
  const searchRows = gscPages.status === "fulfilled" ? gscPages.value.rows ?? [] : [];
  const visibilityMarkets = marketDefinitions.map(({ market, terms }) => {
    const gaMatches = gaRows.filter((row) => terms.some((term) => (row.dimensionValues?.[0]?.value ?? "").toLowerCase().includes(term)));
    const searchMatches = searchRows.filter((row) => terms.some((term) => (row.keys?.[0] ?? "").toLowerCase().includes(term)));
    const sessions = gaMatches.reduce((sum, row) => sum + metric(row, 0), 0);
    const clicks = searchMatches.reduce((sum, row) => sum + (row.clicks ?? 0), 0);
    const impressions = searchMatches.reduce((sum, row) => sum + (row.impressions ?? 0), 0);
    return { market, sessions, clicks, impressions };
  }).filter((row) => row.sessions > 0 || row.clicks > 0 || row.impressions > 0).sort((a, b) => b.impressions + b.sessions - (a.impressions + a.sessions));
  return {
    live: errors.length === 0,
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    period: dates,
    errors,
    sources: {
      ga4: gaOverview.status === "fulfilled",
      gsc: gscOverview.status === "fulfilled"
    },
    metrics: {
      sessions: metric(gaTotal, 0),
      keyEvents: metric(gaTotal, 1),
      searchClicks: searchTotal?.clicks ?? 0,
      impressions: searchTotal?.impressions ?? 0,
      ctr: searchTotal?.ctr ?? 0,
      averagePosition: searchTotal?.position ?? 0
    },
    trend: gaOverview.status === "fulfilled" ? (gaOverview.value.rows ?? []).map((row) => ({
      date: row.dimensionValues?.[0]?.value ?? "",
      sessions: metric(row, 0),
      keyEvents: metric(row, 1)
    })) : [],
    landingPages: gaLanding.status === "fulfilled" ? (gaLanding.value.rows ?? []).map((row) => ({
      page: row.dimensionValues?.[0]?.value || "/",
      sessions: metric(row, 0),
      engagementRate: metric(row, 1),
      keyEvents: metric(row, 2)
    })) : [],
    queries: gscQueries.status === "fulfilled" ? (gscQueries.value.rows ?? []).map((row) => ({
      query: row.keys?.[0] ?? "",
      clicks: row.clicks ?? 0,
      impressions: row.impressions ?? 0,
      ctr: row.ctr ?? 0,
      position: row.position ?? 0
    })) : [],
    visibilityMarkets
  };
}

// whatConvertsReportingPlugin.ts
var markets = [
  { name: "Thousand Oaks", terms: ["thousand-oaks", "thousand oaks"] },
  { name: "Westlake Village", terms: ["westlake-village", "westlake village"] },
  { name: "Simi Valley", terms: ["simi-valley", "simi valley"] },
  { name: "Calabasas", terms: ["calabasas"] },
  { name: "Camarillo", terms: ["camarillo"] },
  { name: "Moorpark", terms: ["moorpark"] },
  { name: "Ventura County", terms: ["ventura-county", "ventura county"] },
  { name: "Los Angeles County", terms: ["los-angeles-county", "los angeles county"] }
];
function marketFor(value) {
  const normalized = (value ?? "").toLowerCase();
  return markets.find((market) => market.terms.some((term) => normalized.includes(term)))?.name ?? null;
}
function addCount(map, key) {
  const clean = key?.trim() || "Unattributed";
  map.set(clean, (map.get(clean) ?? 0) + 1);
}
async function buildReport2() {
  const token = process.env.WHATCONVERTS_TOKEN;
  const secret = process.env.WHATCONVERTS_SECRET;
  if (!token || !secret) throw new Error("WhatConverts credentials are not configured.");
  const authorization = `Basic ${Buffer.from(`${token}:${secret}`).toString("base64")}`;
  const today = /* @__PURE__ */ new Date();
  const periodEnd = new Date(today);
  periodEnd.setUTCDate(periodEnd.getUTCDate() - 2);
  const periodStart = new Date(periodEnd);
  periodStart.setUTCDate(periodStart.getUTCDate() - 27);
  const diagnosticStart = new Date(periodEnd);
  diagnosticStart.setUTCDate(diagnosticStart.getUTCDate() - 399);
  const iso = (date) => date.toISOString().slice(0, 10);
  const fetchLeads = async (startDate, endDate) => {
    const query = new URLSearchParams({ start_date: startDate, end_date: endDate, leads_per_page: "2500", page_number: "1" });
    const response = await fetch(`https://app.whatconverts.com/api/v1/leads?${query}`, {
      headers: { accept: "application/json", authorization }
    });
    const payload2 = await response.json();
    if (!response.ok) throw new Error(payload2.message || payload2.error || `WhatConverts request failed (${response.status})`);
    return payload2;
  };
  const [payload, diagnosticPayload, accountResponse] = await Promise.all([
    fetchLeads(iso(periodStart), iso(periodEnd)),
    fetchLeads(iso(diagnosticStart), iso(periodEnd)),
    fetch("https://app.whatconverts.com/api/v1/accounts", {
      headers: { accept: "application/json", authorization }
    })
  ]);
  const accounts = await accountResponse.json();
  if (!accountResponse.ok) throw new Error(accounts.error_message || `WhatConverts account request failed (${accountResponse.status})`);
  const leads = payload.leads ?? [];
  const diagnosticLeads = diagnosticPayload.leads ?? [];
  const sources = /* @__PURE__ */ new Map();
  const media = /* @__PURE__ */ new Map();
  const landingPages = /* @__PURE__ */ new Map();
  const marketCounts = /* @__PURE__ */ new Map();
  let calls = 0;
  let callDurationSeconds = 0;
  for (const lead of leads) {
    addCount(sources, lead.lead_source);
    addCount(media, lead.lead_medium);
    if (lead.landing_url) addCount(landingPages, lead.landing_url);
    const market = marketFor(lead.landing_url);
    if (market) addCount(marketCounts, market);
    if ((lead.lead_type ?? "").toLowerCase().replaceAll(" ", "_") === "phone_call") {
      calls += 1;
      callDurationSeconds += Number(lead.call_duration_seconds ?? 0);
    }
  }
  const ranked = (map, limit = 10) => [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([name, count]) => ({ name, count }));
  const account = accounts.accounts?.[0];
  const profile = account?.profiles?.[0];
  const typeCounts = diagnosticLeads.reduce((map, lead) => {
    addCount(map, lead.lead_type);
    return map;
  }, /* @__PURE__ */ new Map());
  const diagnosticDates = diagnosticLeads.map((lead) => lead.date_created).filter((date) => Boolean(date)).sort();
  return {
    live: true,
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    period: { startDate: iso(periodStart), endDate: iso(periodEnd), label: "Last 28 days" },
    metrics: {
      totalLeads: payload.total_leads ?? leads.length,
      calls,
      averageCallDurationSeconds: calls ? Math.round(callDurationSeconds / calls) : 0,
      attributedMarkets: marketCounts.size
    },
    bySource: ranked(sources),
    byMedium: ranked(media),
    landingPages: ranked(landingPages),
    inquiryMarkets: ranked(marketCounts, markets.length).map(({ name, count }) => ({ market: name, inquiries: count })),
    fieldsAvailable: [
      "Total leads",
      "Lead type",
      "Created date",
      "Source",
      "Medium",
      "Landing URL",
      "Call duration"
    ],
    fieldsUnavailable: [
      "Configured qualified / unqualified status",
      "Referral",
      "Admission",
      "Census contribution"
    ],
    diagnostic: {
      result: diagnosticLeads.length ? "REPORTING CONFIGURATION ISSUE" : "CONFIRMED ZERO LEADS",
      accountId: account?.account_id ?? null,
      accountName: account?.account_name ?? null,
      profileId: profile?.profile_id ?? diagnosticLeads[0]?.profile_id ?? null,
      profileName: profile?.profile_name ?? null,
      websiteUrl: profile?.website_url ?? null,
      timezone: profile?.timezone ?? "Not returned by API",
      queryWindow: { startDate: iso(diagnosticStart), endDate: iso(periodEnd), maximumDays: 400 },
      totalLeads: diagnosticPayload.total_leads ?? diagnosticLeads.length,
      leadTypes: ranked(typeCounts),
      earliestLeadDate: diagnosticDates[0] ?? null,
      latestLeadDate: diagnosticDates.at(-1) ?? null,
      explanation: "The earlier zero used the API default date because no start_date or end_date was supplied."
    },
    note: "Aggregates contain business attribution only; names, phone numbers, recordings, transcripts and call content are excluded."
  };
}

// reportingCli.ts
var source = process.argv[2];
var period = process.argv[3] ?? "last28";
try {
  const report = source === "google" ? await buildReport(period) : source === "whatconverts" ? await buildReport2() : source === "brevo" ? await buildBrevoReport() : null;
  if (!report) {
    throw new Error("Unknown Growth Intelligence reporting source.");
  }
  process.stdout.write(JSON.stringify(report));
} catch (error) {
  process.stdout.write(JSON.stringify({
    live: false,
    errors: [error instanceof Error ? error.message : "Unable to load reporting data."]
  }));
  process.exitCode = 1;
}
