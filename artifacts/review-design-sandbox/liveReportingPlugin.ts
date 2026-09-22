import { createSign } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Plugin } from 'vite';

type ServiceAccount = {
  client_email: string;
  private_key: string;
  token_uri?: string;
};

let cachedToken: { value: string; expiresAt: number } | null = null;

function base64Url(value: string): string {
  return Buffer.from(value)
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

async function getAccessToken(account: ServiceAccount): Promise<string> {
  if (cachedToken && cachedToken.expiresAt > Date.now() + 60_000) {
    return cachedToken.value;
  }

  const now = Math.floor(Date.now() / 1000);
  const header = base64Url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claims = base64Url(JSON.stringify({
    iss: account.client_email,
    scope: [
      'https://www.googleapis.com/auth/analytics.readonly',
      'https://www.googleapis.com/auth/webmasters.readonly',
    ].join(' '),
    aud: account.token_uri ?? 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  }));
  const unsigned = `${header}.${claims}`;
  const signer = createSign('RSA-SHA256');
  signer.update(unsigned);
  const signature = signer.sign(account.private_key, 'base64url');
  const assertion = `${unsigned}.${signature}`;

  const response = await fetch(account.token_uri ?? 'https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });
  const payload = await response.json() as { access_token?: string; expires_in?: number; error_description?: string };
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description || `Google token request failed (${response.status})`);
  }

  cachedToken = {
    value: payload.access_token,
    expiresAt: Date.now() + (payload.expires_in ?? 3600) * 1000,
  };
  return cachedToken.value;
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function reportingDates(period: string): { startDate: string; endDate: string; label: string } {
  const today = new Date();
  const end = new Date(today);
  end.setUTCDate(end.getUTCDate() - 2);
  const start = new Date(end);

  if (period === 'previous') {
    end.setUTCDate(end.getUTCDate() - 28);
    start.setTime(end.getTime());
    start.setUTCDate(start.getUTCDate() - 27);
    return { startDate: isoDate(start), endDate: isoDate(end), label: 'Previous 28 days' };
  }

  if (period === 'ytd') {
    start.setUTCMonth(0, 1);
    return { startDate: isoDate(start), endDate: isoDate(end), label: 'Year to date' };
  }

  start.setUTCDate(start.getUTCDate() - 27);
  return { startDate: isoDate(start), endDate: isoDate(end), label: 'Last 28 days' };
}

async function googleJson<T>(url: string, token: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const payload = await response.json() as T & { error?: { message?: string } };
  if (!response.ok) {
    throw new Error(payload.error?.message || `Google API request failed (${response.status})`);
  }
  return payload;
}

function metric(row: { metricValues?: Array<{ value?: string }> } | undefined, index: number): number {
  return Number(row?.metricValues?.[index]?.value ?? 0);
}

async function buildReport(period: string) {
  const rawCredential = process.env.GOOGLE_REPORTING_SERVICE_ACCOUNT_JSON_V2;
  const propertyId = process.env.GA4_PROPERTY_ID;
  if (!rawCredential || !propertyId) {
    throw new Error('Google reporting credentials or GA4 property ID are not configured.');
  }

  const account = JSON.parse(rawCredential) as ServiceAccount;
  if (!account.client_email || !account.private_key) {
    throw new Error('The Google service-account JSON is incomplete.');
  }

  const token = await getAccessToken(account);
  const dates = reportingDates(period);
  const gaUrl = `https://analyticsdata.googleapis.com/v1beta/properties/${encodeURIComponent(propertyId)}:runReport`;
  const gscUrl = `https://searchconsole.googleapis.com/webmasters/v3/sites/${encodeURIComponent('https://eternallifehospice.com/')}/searchAnalytics/query`;

  const [gaOverview, gaLanding, gscOverview, gscQueries, gscPages] = await Promise.allSettled([
    googleJson<{
      rows?: Array<{ dimensionValues?: Array<{ value?: string }>; metricValues?: Array<{ value?: string }> }>;
      totals?: Array<{ metricValues?: Array<{ value?: string }> }>;
    }>(gaUrl, token, {
      dateRanges: [{ startDate: dates.startDate, endDate: dates.endDate }],
      dimensions: [{ name: 'date' }],
      metrics: [{ name: 'sessions' }, { name: 'keyEvents' }],
      orderBys: [{ dimension: { dimensionName: 'date' } }],
      metricAggregations: ['TOTAL'],
    }),
    googleJson<{
      rows?: Array<{ dimensionValues?: Array<{ value?: string }>; metricValues?: Array<{ value?: string }> }>;
    }>(gaUrl, token, {
      dateRanges: [{ startDate: dates.startDate, endDate: dates.endDate }],
      dimensions: [{ name: 'landingPagePlusQueryString' }],
      metrics: [{ name: 'sessions' }, { name: 'engagementRate' }, { name: 'keyEvents' }],
       limit: 1000,
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
    }),
    googleJson<{ rows?: Array<{ clicks?: number; impressions?: number; ctr?: number; position?: number }> }>(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: [], rowLimit: 1 },
    ),
    googleJson<{ rows?: Array<{ keys?: string[]; clicks?: number; impressions?: number; ctr?: number; position?: number }> }>(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: ['query'], rowLimit: 10 },
    ),
    googleJson<{ rows?: Array<{ keys?: string[]; clicks?: number; impressions?: number; ctr?: number; position?: number }> }>(
      gscUrl,
      token,
      { startDate: dates.startDate, endDate: dates.endDate, dimensions: ['page'], rowLimit: 1000 },
    ),
  ]);

  const errors: string[] = [];
  if (gaOverview.status === 'rejected') errors.push(`GA4: ${gaOverview.reason instanceof Error ? gaOverview.reason.message : String(gaOverview.reason)}`);
  if (gscOverview.status === 'rejected') errors.push(`Search Console: ${gscOverview.reason instanceof Error ? gscOverview.reason.message : String(gscOverview.reason)}`);

  const gaTotal = gaOverview.status === 'fulfilled' ? gaOverview.value.totals?.[0] : undefined;
  const searchTotal = gscOverview.status === 'fulfilled' ? gscOverview.value.rows?.[0] : undefined;

  const marketDefinitions = [
    { market: 'Thousand Oaks', terms: ['thousand-oaks', 'thousand oaks'] },
    { market: 'Westlake Village', terms: ['westlake-village', 'westlake village'] },
    { market: 'Simi Valley', terms: ['simi-valley', 'simi valley'] },
    { market: 'Calabasas', terms: ['calabasas'] },
    { market: 'Camarillo', terms: ['camarillo'] },
    { market: 'Moorpark', terms: ['moorpark'] },
    { market: 'Ventura County', terms: ['ventura-county', 'ventura county'] },
    { market: 'Los Angeles County', terms: ['los-angeles-county', 'los angeles county'] },
  ];
  const gaRows = gaLanding.status === 'fulfilled' ? gaLanding.value.rows ?? [] : [];
  const searchRows = gscPages.status === 'fulfilled' ? gscPages.value.rows ?? [] : [];
  const visibilityMarkets = marketDefinitions.map(({ market, terms }) => {
    const gaMatches = gaRows.filter((row) => terms.some((term) => (row.dimensionValues?.[0]?.value ?? '').toLowerCase().includes(term)));
    const searchMatches = searchRows.filter((row) => terms.some((term) => (row.keys?.[0] ?? '').toLowerCase().includes(term)));
    const sessions = gaMatches.reduce((sum, row) => sum + metric(row, 0), 0);
    const clicks = searchMatches.reduce((sum, row) => sum + (row.clicks ?? 0), 0);
    const impressions = searchMatches.reduce((sum, row) => sum + (row.impressions ?? 0), 0);
    return { market, sessions, clicks, impressions };
  }).filter((row) => row.sessions > 0 || row.clicks > 0 || row.impressions > 0)
    .sort((a, b) => (b.impressions + b.sessions) - (a.impressions + a.sessions));

  return {
    live: errors.length === 0,
    generatedAt: new Date().toISOString(),
    period: dates,
    errors,
    sources: {
      ga4: gaOverview.status === 'fulfilled',
      gsc: gscOverview.status === 'fulfilled',
    },
    metrics: {
      sessions: metric(gaTotal, 0),
      keyEvents: metric(gaTotal, 1),
      searchClicks: searchTotal?.clicks ?? 0,
      impressions: searchTotal?.impressions ?? 0,
      ctr: searchTotal?.ctr ?? 0,
      averagePosition: searchTotal?.position ?? 0,
    },
    trend: gaOverview.status === 'fulfilled'
      ? (gaOverview.value.rows ?? []).map((row) => ({
          date: row.dimensionValues?.[0]?.value ?? '',
          sessions: metric(row, 0),
          keyEvents: metric(row, 1),
        }))
      : [],
    landingPages: gaLanding.status === 'fulfilled'
      ? (gaLanding.value.rows ?? []).map((row) => ({
          page: row.dimensionValues?.[0]?.value || '/',
          sessions: metric(row, 0),
          engagementRate: metric(row, 1),
          keyEvents: metric(row, 2),
        }))
      : [],
    queries: gscQueries.status === 'fulfilled'
      ? (gscQueries.value.rows ?? []).map((row) => ({
          query: row.keys?.[0] ?? '',
          clicks: row.clicks ?? 0,
          impressions: row.impressions ?? 0,
          ctr: row.ctr ?? 0,
          position: row.position ?? 0,
        }))
      : [],
    visibilityMarkets,
  };
}

function sendJson(res: ServerResponse, status: number, value: unknown): void {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'private, max-age=300');
  res.end(JSON.stringify(value));
}

async function handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
  try {
    const requestUrl = new URL(req.url ?? '/', 'http://127.0.0.1');
    const period = requestUrl.searchParams.get('period') ?? 'last28';
    sendJson(res, 200, await buildReport(period));
  } catch (error) {
    sendJson(res, 500, {
      live: false,
      errors: [error instanceof Error ? error.message : 'Unable to load Google reporting data.'],
    });
  }
}

export function liveReportingPlugin(): Plugin {
  return {
    name: 'elh-live-reporting',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = new URL(req.url ?? '/', 'http://127.0.0.1').pathname;
        if (!pathname.endsWith('/api/elh-reporting')) {
          next();
          return;
        }
        void handle(req, res);
      });
    },
  };
}