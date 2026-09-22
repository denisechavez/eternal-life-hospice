import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Plugin } from 'vite';

type WhatConvertsLead = {
  lead_id?: number;
  profile_id?: number;
  lead_type?: string;
  date_created?: string;
  lead_source?: string;
  lead_medium?: string;
  landing_url?: string;
  call_duration_seconds?: number;
};

type WhatConvertsResponse = {
  leads?: WhatConvertsLead[];
  total_leads?: number;
  total_pages?: number;
  page_number?: number;
  leads_per_page?: number;
};

type WhatConvertsAccountResponse = {
  accounts?: Array<{
    account_id?: number;
    account_name?: string;
    profiles?: Array<{ profile_id?: number; profile_name?: string; website_url?: string | null; timezone?: string | null }>;
  }>;
};

const markets = [
  { name: 'Thousand Oaks', terms: ['thousand-oaks', 'thousand oaks'] },
  { name: 'Westlake Village', terms: ['westlake-village', 'westlake village'] },
  { name: 'Simi Valley', terms: ['simi-valley', 'simi valley'] },
  { name: 'Calabasas', terms: ['calabasas'] },
  { name: 'Camarillo', terms: ['camarillo'] },
  { name: 'Moorpark', terms: ['moorpark'] },
  { name: 'Ventura County', terms: ['ventura-county', 'ventura county'] },
  { name: 'Los Angeles County', terms: ['los-angeles-county', 'los angeles county'] },
];

function marketFor(value: string | undefined): string | null {
  const normalized = (value ?? '').toLowerCase();
  return markets.find((market) => market.terms.some((term) => normalized.includes(term)))?.name ?? null;
}

function addCount(map: Map<string, number>, key: string | undefined): void {
  const clean = key?.trim() || 'Unattributed';
  map.set(clean, (map.get(clean) ?? 0) + 1);
}

async function buildReport() {
  const token = process.env.WHATCONVERTS_TOKEN;
  const secret = process.env.WHATCONVERTS_SECRET;
  if (!token || !secret) throw new Error('WhatConverts credentials are not configured.');

  const authorization = `Basic ${Buffer.from(`${token}:${secret}`).toString('base64')}`;
  const today = new Date();
  const periodEnd = new Date(today);
  periodEnd.setUTCDate(periodEnd.getUTCDate() - 2);
  const periodStart = new Date(periodEnd);
  periodStart.setUTCDate(periodStart.getUTCDate() - 27);
  const diagnosticStart = new Date(periodEnd);
  diagnosticStart.setUTCDate(diagnosticStart.getUTCDate() - 399);
  const iso = (date: Date) => date.toISOString().slice(0, 10);
  const fetchLeads = async (startDate: string, endDate: string) => {
    const query = new URLSearchParams({ start_date: startDate, end_date: endDate, leads_per_page: '2500', page_number: '1' });
    const response = await fetch(`https://app.whatconverts.com/api/v1/leads?${query}`, {
      headers: { accept: 'application/json', authorization },
    });
    const payload = await response.json() as WhatConvertsResponse & { message?: string; error?: string };
    if (!response.ok) throw new Error(payload.message || payload.error || `WhatConverts request failed (${response.status})`);
    return payload;
  };

  const [payload, diagnosticPayload, accountResponse] = await Promise.all([
    fetchLeads(iso(periodStart), iso(periodEnd)),
    fetchLeads(iso(diagnosticStart), iso(periodEnd)),
    fetch('https://app.whatconverts.com/api/v1/accounts', {
      headers: { accept: 'application/json', authorization },
    }),
  ]);
  const accounts = await accountResponse.json() as WhatConvertsAccountResponse & { error_message?: string };
  if (!accountResponse.ok) throw new Error(accounts.error_message || `WhatConverts account request failed (${accountResponse.status})`);

  const leads = payload.leads ?? [];
  const diagnosticLeads = diagnosticPayload.leads ?? [];
  const sources = new Map<string, number>();
  const media = new Map<string, number>();
  const landingPages = new Map<string, number>();
  const marketCounts = new Map<string, number>();
  let calls = 0;
  let callDurationSeconds = 0;

  for (const lead of leads) {
    addCount(sources, lead.lead_source);
    addCount(media, lead.lead_medium);
    if (lead.landing_url) addCount(landingPages, lead.landing_url);
    const market = marketFor(lead.landing_url);
    if (market) addCount(marketCounts, market);
    if ((lead.lead_type ?? '').toLowerCase().replaceAll(' ', '_') === 'phone_call') {
      calls += 1;
      callDurationSeconds += Number(lead.call_duration_seconds ?? 0);
    }
  }

  const ranked = (map: Map<string, number>, limit = 10) =>
    [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([name, count]) => ({ name, count }));

  const account = accounts.accounts?.[0];
  const profile = account?.profiles?.[0];
  const typeCounts = diagnosticLeads.reduce((map, lead) => {
    addCount(map, lead.lead_type);
    return map;
  }, new Map<string, number>());
  const diagnosticDates = diagnosticLeads.map((lead) => lead.date_created).filter((date): date is string => Boolean(date)).sort();

  return {
    live: true,
    generatedAt: new Date().toISOString(),
    period: { startDate: iso(periodStart), endDate: iso(periodEnd), label: 'Last 28 days' },
    metrics: {
      totalLeads: payload.total_leads ?? leads.length,
      calls,
      averageCallDurationSeconds: calls ? Math.round(callDurationSeconds / calls) : 0,
      attributedMarkets: marketCounts.size,
    },
    bySource: ranked(sources),
    byMedium: ranked(media),
    landingPages: ranked(landingPages),
    inquiryMarkets: ranked(marketCounts, markets.length).map(({ name, count }) => ({ market: name, inquiries: count })),
    fieldsAvailable: [
      'Total leads',
      'Lead type',
      'Created date',
      'Source',
      'Medium',
      'Landing URL',
      'Call duration',
    ],
    fieldsUnavailable: [
      'Configured qualified / unqualified status',
      'Referral',
      'Admission',
      'Census contribution',
    ],
    diagnostic: {
      result: diagnosticLeads.length ? 'REPORTING CONFIGURATION ISSUE' : 'CONFIRMED ZERO LEADS',
      accountId: account?.account_id ?? null,
      accountName: account?.account_name ?? null,
      profileId: profile?.profile_id ?? diagnosticLeads[0]?.profile_id ?? null,
      profileName: profile?.profile_name ?? null,
      websiteUrl: profile?.website_url ?? null,
      timezone: profile?.timezone ?? 'Not returned by API',
      queryWindow: { startDate: iso(diagnosticStart), endDate: iso(periodEnd), maximumDays: 400 },
      totalLeads: diagnosticPayload.total_leads ?? diagnosticLeads.length,
      leadTypes: ranked(typeCounts),
      earliestLeadDate: diagnosticDates[0] ?? null,
      latestLeadDate: diagnosticDates.at(-1) ?? null,
      explanation: 'The earlier zero used the API default date because no start_date or end_date was supplied.',
    },
    note: 'Aggregates contain business attribution only; names, phone numbers, recordings, transcripts and call content are excluded.',
  };
}

function sendJson(res: ServerResponse, status: number, value: unknown): void {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'private, max-age=300');
  res.end(JSON.stringify(value));
}

async function handle(_req: IncomingMessage, res: ServerResponse): Promise<void> {
  try {
    sendJson(res, 200, await buildReport());
  } catch (error) {
    sendJson(res, 500, {
      live: false,
      errors: [error instanceof Error ? error.message : 'Unable to load WhatConverts reporting.'],
    });
  }
}

export function whatConvertsReportingPlugin(): Plugin {
  return {
    name: 'elh-whatconverts-reporting',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = new URL(req.url ?? '/', 'http://127.0.0.1').pathname;
        if (!pathname.endsWith('/api/whatconverts-reporting')) return next();
        void handle(req, res);
      });
    },
  };
}