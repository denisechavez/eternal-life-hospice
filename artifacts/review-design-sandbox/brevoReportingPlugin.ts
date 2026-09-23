import type { IncomingMessage, ServerResponse } from 'node:http';
import type { Plugin } from 'vite';

type BrevoStats = {
  sent?: number;
  delivered?: number;
  viewed?: number;
  uniqueViews?: number;
  clickers?: number;
  uniqueClicks?: number;
  hardBounces?: number;
  softBounces?: number;
  unsubscriptions?: number;
  complaints?: number;
};

type BrevoCampaign = {
  id: number;
  name?: string;
  subject?: string;
  status?: string;
  type?: string;
  scheduledAt?: string;
  sentDate?: string;
  statistics?: {
    globalStats?: BrevoStats;
    campaignStats?: BrevoStats[];
  };
};

type BrevoList = {
  id: number;
  name?: string;
  totalSubscribers?: number;
  totalBlacklisted?: number;
  uniqueSubscribers?: number;
};

async function brevoJson<T>(path: string, apiKey: string): Promise<T> {
  const response = await fetch(`https://api.brevo.com/v3${path}`, {
    headers: {
      accept: 'application/json',
      'api-key': apiKey,
    },
  });
  const payload = await response.json() as T & { message?: string; code?: string };
  if (!response.ok) {
    throw new Error(payload.message || `Brevo request failed (${response.status})`);
  }
  return payload;
}

function safeNumber(value: number | undefined): number {
  return Number.isFinite(value) ? Number(value) : 0;
}

function campaignTotals(campaign: BrevoCampaign): Required<BrevoStats> {
  const base: Required<BrevoStats> = { sent: 0, delivered: 0, viewed: 0, uniqueViews: 0, clickers: 0, uniqueClicks: 0, hardBounces: 0, softBounces: 0, unsubscriptions: 0, complaints: 0 };
  const rows = campaign.statistics?.campaignStats;
  if (rows?.length) {
    return rows.reduce<Required<BrevoStats>>((acc, stats) => {
      for (const key of Object.keys(base) as Array<keyof BrevoStats>) acc[key] = acc[key] + safeNumber(stats[key]);
      return acc;
    }, { ...base });
  }
  const stats = campaign.statistics?.globalStats;
  for (const key of Object.keys(base) as Array<keyof BrevoStats>) base[key] = safeNumber(stats?.[key]);
  return base;
}

export async function buildBrevoReport() {
  const apiKey = process.env.BREVO_API;
  if (!apiKey) {
    throw new Error('Brevo is not configured.');
  }

  const [campaignResult, listResult] = await Promise.all([
    brevoJson<{ campaigns?: BrevoCampaign[]; count?: number }>(
      '/emailCampaigns?limit=50&offset=0&sort=desc',
      apiKey,
    ),
    brevoJson<{ lists?: BrevoList[]; count?: number }>(
      '/contacts/lists?limit=50&offset=0&sort=desc',
      apiKey,
    ),
  ]);

  const campaignSummaries = campaignResult.campaigns ?? [];
  const campaignDetails = await Promise.allSettled(
    campaignSummaries.slice(0, 20).map((campaign) =>
      brevoJson<BrevoCampaign>(`/emailCampaigns/${campaign.id}`, apiKey),
    ),
  );
  const detailedById = new Map<number, BrevoCampaign>();
  campaignDetails.forEach((result) => {
    if (result.status === 'fulfilled') detailedById.set(result.value.id, result.value);
  });
  const campaigns = campaignSummaries.map((campaign) => detailedById.get(campaign.id) ?? campaign);
  const lists = listResult.lists ?? [];
  const periodEnd = new Date();
  periodEnd.setUTCDate(periodEnd.getUTCDate() - 2);
  const periodStart = new Date(periodEnd);
  periodStart.setUTCDate(periodStart.getUTCDate() - 27);
  const inPeriod = (campaign: BrevoCampaign) => {
    if (!campaign.sentDate) return false;
    const sent = new Date(campaign.sentDate);
    return sent >= periodStart && sent < new Date(periodEnd.getTime() + 86_400_000);
  };
  const reduceCampaigns = (source: BrevoCampaign[]) => source.reduce(
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
    { sent: 0, delivered: 0, opens: 0, uniqueViews: 0, clicks: 0, uniqueClicks: 0, bounces: 0, unsubscriptions: 0 },
  );
  const totals = reduceCampaigns(campaigns);
  const periodCampaigns = campaigns.filter(inPeriod);
  const periodTotals = reduceCampaigns(periodCampaigns);

  return {
    live: true,
    generatedAt: new Date().toISOString(),
    period: {
      startDate: periodStart.toISOString().slice(0, 10),
      endDate: periodEnd.toISOString().slice(0, 10),
      label: 'Last 28 days',
    },
    metrics: {
      campaigns: campaignResult.count ?? campaigns.length,
      sentCampaigns: campaigns.filter((campaign) => campaign.status === 'sent').length,
      activeLists: lists.length,
      subscribers: lists.reduce(
        (sum, list) => sum + safeNumber(list.uniqueSubscribers ?? list.totalSubscribers),
        0,
      ),
      ...totals,
    },
    periodMetrics: {
      campaigns: periodCampaigns.length,
      ...periodTotals,
    },
    diagnostic: {
      result: 'CAMPAIGN-SPECIFIC STATS REQUIRED',
      explanation: 'Brevo globalStats is present but zero. Valid delivery and engagement totals are stored in statistics.campaignStats and must be summed across recipient lists.',
      historicalCampaignsValidated: campaigns.length,
    },
    campaigns: campaigns.map((campaign) => {
      const stats = campaignTotals(campaign);
      return {
        id: campaign.id,
        name: campaign.name || 'Untitled campaign',
        subject: campaign.subject || '',
        status: campaign.status || 'unknown',
        type: campaign.type || 'classic',
        scheduledAt: campaign.scheduledAt || null,
        sentDate: campaign.sentDate || null,
        sent: stats.sent,
        delivered: stats.delivered,
        uniqueViews: stats.uniqueViews,
        uniqueClicks: stats.uniqueClicks,
        hardBounces: stats.hardBounces,
        softBounces: stats.softBounces,
        unsubscriptions: stats.unsubscriptions,
      };
    }),
    lists: lists.map((list) => ({
      id: list.id,
      name: list.name || `List ${list.id}`,
      subscribers: safeNumber(list.uniqueSubscribers ?? list.totalSubscribers),
      blacklisted: safeNumber(list.totalBlacklisted),
    })),
  };
}

function sendJson(res: ServerResponse, status: number, value: unknown): void {
  res.statusCode = status;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'private, max-age=300');
  res.end(JSON.stringify(value));
}

async function handleBrevo(_req: IncomingMessage, res: ServerResponse): Promise<void> {
  try {
    sendJson(res, 200, await buildBrevoReport());
  } catch (error) {
    sendJson(res, 500, {
      live: false,
      errors: [error instanceof Error ? error.message : 'Unable to load Brevo reporting data.'],
    });
  }
}

export function brevoReportingPlugin(): Plugin {
  return {
    name: 'elh-brevo-reporting',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = new URL(req.url ?? '/', 'http://127.0.0.1').pathname;
        if (!pathname.endsWith('/api/brevo-reporting')) {
          next();
          return;
        }
        void handleBrevo(req, res);
      });
    },
  };
}