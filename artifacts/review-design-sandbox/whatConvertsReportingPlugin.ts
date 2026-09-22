import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Plugin } from 'vite';

type WhatConvertsLead = {
  lead_id?: number;
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

  const response = await fetch('https://app.whatconverts.com/api/v1/leads?leads_per_page=2500&page_number=1', {
    headers: {
      accept: 'application/json',
      authorization: `Basic ${Buffer.from(`${token}:${secret}`).toString('base64')}`,
    },
  });
  const payload = await response.json() as WhatConvertsResponse & { message?: string; error?: string };
  if (!response.ok) throw new Error(payload.message || payload.error || `WhatConverts request failed (${response.status})`);

  const leads = payload.leads ?? [];
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
    if (lead.lead_type === 'phone_call') {
      calls += 1;
      callDurationSeconds += Number(lead.call_duration_seconds ?? 0);
    }
  }

  const ranked = (map: Map<string, number>, limit = 10) =>
    [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([name, count]) => ({ name, count }));

  return {
    live: true,
    generatedAt: new Date().toISOString(),
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
      'Reliable unique callers',
      'Qualified / unqualified status',
      'Referral',
      'Admission',
      'Census contribution',
    ],
    note: leads.length
      ? 'Aggregates contain attribution fields only; names, phone numbers, recordings and clinical content are excluded.'
      : 'Authentication succeeded, but the connected WhatConverts profile returned no leads.',
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