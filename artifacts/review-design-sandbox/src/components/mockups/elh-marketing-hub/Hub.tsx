import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  ArrowUpRight, Bell, BookOpen, CalendarDays, Check, ChevronRight, CircleHelp, Clock3,
  FileCheck2, FileText, Filter, FolderOpen, HeartHandshake, LayoutDashboard,
  Menu, MoreHorizontal, PanelLeftClose, Plus, Search, Send, Settings2,
  ShieldCheck, Sparkles, TrendingUp, Users, X, BarChart3, Cable, Globe2, MapPin,
  MessageSquare, RefreshCw, ExternalLink, Database, CircleDot, Activity, ArrowDownRight,
  Megaphone, Share2, Handshake, Link2, Download, Clipboard, Trash2, Pencil, AlertTriangle
} from "lucide-react";
import "./hub.css";
import { emailCampaigns, journalArticles, type JournalArticle } from "./contentData";

type Status = "Needs review" | "Approved" | "Scheduled" | "Draft" | "Published";
type Item = { id: string; title: string; type: string; date: string; owner: string; status: Status; excerpt: string; source?: JournalArticle; emailIndex?: number; infographicRecommendation?: string; };
type LiveSeoData = {
  live: boolean;
  generatedAt?: string;
  period?: { startDate: string; endDate: string; label: string };
  errors?: string[];
  metrics?: { sessions: number; keyEvents: number; searchClicks: number; impressions: number; ctr: number; averagePosition: number };
  trend?: Array<{ date: string; sessions: number; keyEvents: number }>;
  landingPages?: Array<{ page: string; sessions: number; engagementRate: number; keyEvents: number }>;
  queries?: Array<{ query: string; clicks: number; impressions: number; ctr: number; position: number }>;
};
type BrevoData = {
  live: boolean;
  generatedAt?: string;
  errors?: string[];
  metrics?: { campaigns: number; sentCampaigns: number; activeLists: number; subscribers: number; sent: number; delivered: number; uniqueViews: number; uniqueClicks: number; bounces: number; unsubscriptions: number };
  campaigns?: Array<{ id: number; name: string; subject: string; status: string; type: string; scheduledAt: string | null; sentDate: string | null; sent: number; delivered: number; uniqueViews: number; uniqueClicks: number; hardBounces: number; softBounces: number; unsubscriptions: number }>;
  lists?: Array<{ id: number; name: string; subscribers: number; blacklisted: number }>;
};

const journalTitles = [
  "What happens during a hospice evaluation", "10 signs it may be time to consider hospice",
  "Hospice at home in Thousand Oaks: what families can expect", "Can hospice begin after a hospital discharge?",
  "Does Medicare cover hospice care?", "Hospice vs. palliative care: what is the difference?",
  "Dementia and hospice eligibility", "Hospice care for advanced cancer", "Hospice and advanced heart failure",
  "Hospice support for advanced COPD", "The first 48 hours of hospice care", "Can a family request a hospice evaluation?",
  "Hospice care in Simi Valley: starting the conversation", "Home hospice in Camarillo: a family guide",
  "Hospice care across the Conejo Valley", "Hospice care in Moorpark: what to know",
  "Hospice in assisted living and skilled nursing facilities", "What is the family caregiver's role in home hospice?",
  "How hospice manages comfort medications", "What medical equipment can hospice provide?"
];

const baseItems: Item[] = [
  ...journalArticles.map(article => {
    const status: Status = article.date <= "2026-09-30" ? "Approved" : ["the-first-48-hours-of-hospice-care", "hospice-care-in-simi-valley-starting-the-conversation", "home-hospice-in-camarillo-a-family-guide", "hospice-care-across-the-conejo-valley"].includes(article.slug) ? "Needs review" : "Scheduled";
    return { id: `journal-${article.slug}`, title: article.title, type: "Journal", date: article.date, owner: "The Eternal Life Hospice Team", source: article, status, excerpt: article.description, infographicRecommendation: article.slug === "hospice-vs-palliative-care-what-is-the-difference" ? "Hospice Care and Palliative Care: Understanding the Difference" : undefined };
  }),
  ...emailCampaigns.map((campaign, i) => ({ id: `email-${i + 1}`, title: campaign.subject, type: "Weekly email", date: campaign.sendDate, owner: "The Eternal Life Hospice Team", emailIndex: i, status: (i === 0 ? "Needs review" : i === 1 ? "Approved" : "Draft") as Status, excerpt: campaign.preheader })),
  { id: "pub-1", title: "Hospice Is Part of Life — A Continuation of Care", type: "Care Brief", date: "Aug 28, 2026", owner: "Aleksandra D.", status: "Published", excerpt: "Issue One: hospice as a continuation of care, with guidance for care teams and families." },
  { id: "pub-2", title: "Family Guide — Starting the conversation", type: "Family Guide", date: "Sep 4, 2026", owner: "Aleksandra D.", status: "Published", excerpt: "A steady, readable guide for families considering hospice at home." },
  { id: "asset-1", title: "Referral card — 4 × 6 print", type: "Referral card", date: "Sep 9, 2026", owner: "Studio", status: "Approved", excerpt: "Double-sided referral card with 805.953.7273 and service area." },
  { id: "asset-2", title: "Social graphic — What hospice includes", type: "Social graphic", date: "Sep 11, 2026", owner: "Studio", status: "Needs review", excerpt: "Square graphic for the weekly support explainer." }
];

const nav = [
  { label: "Command center", icon: LayoutDashboard, key: "Overview" },
  { label: "Census & performance", icon: TrendingUp, key: "Census" },
  { label: "SEO analytics", note: "GA4 + Search Console", icon: BarChart3, key: "SEO" },
  { label: "Data connections", note: "Reporting layer", icon: Cable, key: "Connections" },
  { label: "Content calendar", icon: CalendarDays, key: "Calendar" },
  { label: "Review & approvals", icon: FileCheck2, key: "Reviews", count: 7 },
  { label: "Journal posts", note: "Website blog posts", icon: FileText, key: "Journal" },
  { label: "Email campaigns", note: "Weekly outbound emails", icon: Send, key: "Emails" },
  { label: "The Eternal Care Brief", note: "Every other month · Longer read", icon: BookOpen, key: "CareBrief" },
  { label: "Publications", icon: FileText, key: "Publications" },
  { label: "Collateral & assets", icon: FolderOpen, key: "Assets" }
  ,{ label: "Growth intelligence", note: "Connected sources only", icon: TrendingUp, key: "Growth" }
  ,{ label: "Advertising", note: "Awaiting source", icon: Megaphone, key: "Advertising" }
  ,{ label: "Social", note: "Awaiting source", icon: Share2, key: "Social" }
  ,{ label: "Referral development", note: "Awaiting source", icon: Handshake, key: "Referral" }
  ,{ label: "Census pipeline", note: "Aggregate · non-PHI", icon: Activity, key: "Pipeline" }
  ,{ label: "Backlinks", note: "Awaiting source", icon: Link2, key: "Backlinks" }
];

function readStatuses(): Record<string, Status> {
  try { return JSON.parse(localStorage.getItem("elh-hub-statuses") || "{}"); } catch { return {}; }
}

export default function Hub() {
  const [active, setActive] = useState(() => new URLSearchParams(window.location.search).get("view") || "Overview");
  const [items, setItems] = useState(() => baseItems.map(item => ({ ...item, status: readStatuses()[item.id] || item.status })));
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selected, setSelected] = useState<Item | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("");
  const [connections, setConnections] = useState({ ga4: false, gsc: false });
  const [connectTarget, setConnectTarget] = useState<"ga4" | "gsc" | null>(null);

  const setStatus = (id: string, status: Status) => {
    setItems(prev => prev.map(item => item.id === id ? { ...item, status } : item));
    const next = { ...readStatuses(), [id]: status };
    localStorage.setItem("elh-hub-statuses", JSON.stringify(next));
    setSelected(prev => prev?.id === id ? { ...prev, status } : prev);
    setNotice(status === "Approved" ? "Approved and saved" : `Moved to ${status}`);
    window.setTimeout(() => setNotice(""), 2400);
  };

  const visibleItems = useMemo(() => items.filter(item =>
    (active === "Journal" ? item.type === "Journal" :
      active === "Emails" ? item.type === "Weekly email" :
      active === "CareBrief" ? item.type === "Care Brief" :
      active === "Reviews" ? ["Journal", "Weekly email"].includes(item.type) && item.status === "Needs review" :
      active === "Calendar" ? ["Journal", "Weekly email"].includes(item.type) :
      active === "Publications" ? ["Care Brief", "Family Guide"].includes(item.type) :
      active === "Assets" ? ["Referral card", "Social graphic"].includes(item.type) : true) &&
    (statusFilter === "All" || item.status === statusFilter) &&
    `${item.title} ${item.type}`.toLowerCase().includes(query.toLowerCase())
  ), [active, items, query, statusFilter]);

  const openDetail = (item: Item) => setSelected(item);
  return (
    <div className="hub-shell">
      <aside className={`hub-sidebar ${mobileNav ? "is-open" : ""}`}>
         <div className="hub-brand"><img className="hub-logo" src="/__reviews-mockup/elh-logo-header-cream.png" alt="Eternal Life Hospice" /><button className="close-nav" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button></div>
        <div className="workspace-label">WORKSPACE <span>PRODUCTION</span></div>
         <nav>{nav.map(({ label, note, icon: Icon, key, count }) => <button key={key} className={`${active === key ? "active" : ""} ${note ? "nav-product" : ""}`} onClick={() => { setActive(key); setStatusFilter("All"); setMobileNav(false); }}><Icon size={17} /><span>{label}{note && <small>{note}</small>}</span>{count && <b>{items.filter(i => i.status === "Needs review" && ["Journal", "Weekly email"].includes(i.type)).length}</b>}</button>)}</nav>
         <div className="sidebar-foot"><div className="sync"><span className="live-dot" /> Connected sources only <small>Source status available in Data connections</small></div><button><Settings2 size={16} /> Workspace settings</button><div className="profile"><div className="avatar">AD</div><div><strong>Aleksandra D.</strong><span>Founder & CEO</span></div><MoreHorizontal size={17} /></div></div>
      </aside>
      {mobileNav && <button className="nav-scrim" onClick={() => setMobileNav(false)} aria-label="Close menu" />}
      <main className="hub-main">
        <header className="hub-topbar"><button className="menu-btn" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={21} /></button><div className="crumb">Eternal Life / <strong>{active === "Overview" ? "Command center" : active}</strong></div><div className="top-actions"><div className="search"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search workspace" /><kbd>⌘ K</kbd></div><button className="icon-btn" aria-label="Notifications"><Bell size={18} /><i /></button><div className="top-avatar">AM</div></div></header>
        <section className="hub-content">
           <div className="page-heading"><div><div className="eyebrow">Private operations workspace <span className="rule" /> connected data only</div><h1>{active === "Overview" ? "Good morning, Aleksandra." : active === "Journal" ? "Journal posts" : active === "Emails" ? "Email campaigns" : active === "CareBrief" ? "The Eternal Care Brief" : active}</h1><p>{active === "Overview" ? "A clear view of connected reporting and the work awaiting review." : active === "Census" ? "Connect an aggregate, non-PHI source for referrals, admissions, discharges and census." : active === "SEO" ? "Live website and search reporting from connected Google sources." : active === "Connections" ? "Choose which authoritative sources can contribute to the private reporting layer." : active === "Reviews" ? "Editorial pieces awaiting a final decision before they can move forward." : active === "Journal" ? "Website blog posts for families and care partners." : active === "Emails" ? "Live Brevo reporting and weekly outbound email planning." : active === "CareBrief" ? "Every other month · Longer read · A living care publication for care teams and families." : "No unsupported operating figures are shown."}</p></div>{!["Census","SEO","Connections"].includes(active) && <button className="primary-btn" onClick={() => setNotice("New item workflow is ready for your brief")}><Plus size={16} /> New item</button>}</div>
            {active === "Overview" ? <Overview items={items} onOpen={openDetail} onStatus={setStatus} onNavigate={setActive} /> :
            active === "Census" ? <CensusView onNavigate={setActive} /> :
            active === "SEO" ? <SeoView connections={connections} onConnect={setConnectTarget} /> :
            active === "Connections" ? <ConnectionsView connections={connections} onConnect={setConnectTarget} /> :
             active === "Emails" ? <BrevoEmailView items={visibleItems} filter={statusFilter} setFilter={setStatusFilter} onOpen={openDetail} onStatus={setStatus} /> :
             ["Growth","Advertising","Social","Referral","Pipeline","Backlinks"].includes(active) ? <GrowthView domain={active} /> :
            <Worklist items={visibleItems} filter={statusFilter} setFilter={setStatusFilter} onOpen={openDetail} onStatus={setStatus} active={active} />}
        </section>
      </main>
      {selected && <Detail item={selected} onClose={() => setSelected(null)} onStatus={setStatus} />}
      {connectTarget && <ConnectionDialog target={connectTarget} onClose={() => setConnectTarget(null)} onConnect={() => { setConnections(prev => ({ ...prev, [connectTarget]: true })); setConnectTarget(null); setNotice(`${connectTarget === "ga4" ? "GA4" : "Search Console"} connection saved for this prototype`); window.setTimeout(() => setNotice(""), 2600); }} />}
      {notice && <div className="toast"><Check size={16} /> {notice}</div>}
    </div>
  );
}

function Overview({ items, onOpen, onStatus, onNavigate }: { items: Item[]; onOpen: (i: Item) => void; onStatus: (id: string, s: Status) => void; onNavigate: (key: string) => void }) {
  const review = items.filter(i => i.status === "Needs review");
  const published = items.filter(i => i.status === "Published");
  const [report, setReport] = useState<LiveSeoData | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.BASE_URL}api/elh-reporting?period=last28`, { signal: controller.signal })
      .then(response => response.json())
      .then((data: LiveSeoData) => setReport(data))
      .catch(() => setReport({ live: false }));
    return () => controller.abort();
  }, []);
  const metrics = report?.metrics;
  const trend = report?.trend?.slice(-12) ?? [];
  const maxSessions = Math.max(1, ...trend.map(point => point.sessions));
  return <div className="overview">
    <div className="metric-grid"><Metric label="Website sessions" value={metrics ? metrics.sessions.toLocaleString() : "…"} detail="GA4 · last 28 days" trend="neutral" icon={Globe2} /><Metric label="Google search clicks" value={metrics ? metrics.searchClicks.toLocaleString() : "…"} detail={metrics ? `${metrics.impressions.toLocaleString()} impressions` : "Search Console · loading"} trend="neutral" icon={Search} /><Metric label="Published items" value={published.length.toString()} detail="Computed from this workspace" trend="neutral" icon={FileText} /><Metric label="Awaiting your review" value={review.length.toString().padStart(2, "0")} detail="Computed from this workspace" trend="attention" icon={Clock3} /></div>
     <div className="main-grid"><section className="panel performance"><div className="panel-head"><div><span className="panel-kicker">Live website reporting · last 28 days</span><h2>Website discovery and action</h2></div><button className="text-btn" onClick={() => onNavigate("SEO")}>View SEO report <ArrowUpRight size={14} /></button></div><div className="mini-chart"><div className="mini-bars">{trend.length ? trend.map(point => <i title={`${point.sessions} sessions`} style={{height:`${Math.max(3, point.sessions / maxSessions * 100)}%`}} key={point.date} />) : <span className="chart-empty">Loading live GA4 trend…</span>}</div><div className="mini-axis"><span>{report?.period?.startDate || "—"}</span><span>{report?.period?.endDate || "—"}</span></div></div><div className="legend"><span><i className="legend-plum" />GA4 sessions</span><span><i className="legend-gold" />Search Console clicks</span><strong>{metrics ? metrics.searchClicks.toLocaleString() : "—"} <small>organic clicks</small></strong></div></section>
      <section className="panel review-panel"><div className="panel-head"><div><span className="panel-kicker">Review queue</span><h2>Needs your eye</h2></div><button className="round-btn" onClick={() => onOpen(review[0])} aria-label="Open review queue"><ChevronRight size={17} /></button></div><div className="queue-list">{review.slice(0, 4).map(item => <button className="queue-item" key={item.id} onClick={() => onOpen(item)}><div className="type-icon"><FileCheck2 size={15} /></div><div><strong>{item.title}</strong><span>{item.type} · {item.date}</span></div><ChevronRight size={15} /></button>)}</div><button className="panel-link" onClick={() => onOpen(review[0])}>Open full review queue <ArrowUpRight size={14} /></button></section></div>
    <div className="lower-grid"><section className="panel calendar-strip"><div className="panel-head"><div><span className="panel-kicker">Content calendar</span><h2>Next up in the Journal</h2></div><button className="text-btn">Open calendar <ArrowUpRight size={14} /></button></div><div className="days">{items.filter(i => i.type === "Journal").slice(0, 6).map((i, idx) => <button key={i.id} onClick={() => onOpen(i)} className={`day ${idx === 0 ? "today" : ""}`}><span>{idx === 0 ? "Next" : i.date.split(" ")[0]}</span><b>{i.date.split(" ")[1]?.replace(",", "")}</b><i>{i.status === "Needs review" ? "Review" : i.status}</i><strong>{i.title}</strong></button>)}</div></section><section className="panel quick-panel"><span className="panel-kicker">Publishing health</span><h2>Workspace inventory</h2><div className="progress-wrap"><div className="progress"><i style={{ width: `${items.length ? published.length / items.length * 100 : 0}%` }} /></div><strong>{published.length} <small>/ {items.length} published</small></strong></div><p>This summary is computed only from the editorial records currently shown in this workspace.</p><button className="text-btn">View campaign plan <ArrowUpRight size={14} /></button></section></div>
  </div>;
}

function Metric({ label, value, detail, trend, icon: Icon }: { label: string; value: string; detail: string; trend: string; icon: typeof Users }) { return <div className="metric"><div className="metric-icon"><Icon size={17} /></div><span>{label}</span><strong>{value}</strong><small className={trend}>{trend === "up" ? "↗ " : trend === "attention" ? "• " : ""}{detail}</small></div>; }

function BrevoEmailView({ items, filter, setFilter, onOpen, onStatus }: { items: Item[]; filter: string; setFilter: (s: string) => void; onOpen: (i: Item) => void; onStatus: (id: string, s: Status) => void }) {
  const [data, setData] = useState<BrevoData | null>(null);
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    fetch(`${import.meta.env.BASE_URL}api/brevo-reporting`)
      .then(async response => {
        const payload = await response.json() as BrevoData;
        if (!response.ok) throw new Error(payload.errors?.join(" ") || "Brevo reporting request failed.");
        setData(payload);
      })
      .catch(error => setData({ live: false, errors: [error instanceof Error ? error.message : String(error)] }))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);
  const metrics = data?.metrics;
  const pct = (numerator: number | undefined, denominator: number | undefined) => denominator ? `${(100 * (numerator || 0) / denominator).toFixed(1)}%` : "—";
  return <div className="analytics-view">
    <div className={`data-note ${data?.live ? "is-live" : ""}`}><Send size={15}/><strong>{loading ? "Connecting to Brevo" : data?.live ? "Brevo connected" : "Brevo connection needs attention"}</strong><span>{loading ? "Loading campaign and audience reporting…" : data?.live ? `Live campaign reporting · refreshed ${new Date(data.generatedAt || "").toLocaleTimeString([], {hour:"numeric",minute:"2-digit"})}` : data?.errors?.join(" ")}</span><button onClick={load}><RefreshCw size={13}/> Refresh</button></div>
    <div className="metric-grid four"><Metric label="Campaigns" value={loading ? "…" : (metrics?.campaigns ?? 0).toLocaleString()} detail={`${metrics?.sentCampaigns ?? 0} sent in returned history`} trend="neutral" icon={Send}/><Metric label="Delivered emails" value={loading ? "…" : (metrics?.delivered ?? 0).toLocaleString()} detail={`${pct(metrics?.delivered, metrics?.sent)} delivery rate`} trend="neutral" icon={Check}/><Metric label="Unique opens" value={loading ? "…" : (metrics?.uniqueViews ?? 0).toLocaleString()} detail={`${pct(metrics?.uniqueViews, metrics?.delivered)} open rate`} trend="neutral" icon={BookOpen}/><Metric label="Unique clicks" value={loading ? "…" : (metrics?.uniqueClicks ?? 0).toLocaleString()} detail={`${pct(metrics?.uniqueClicks, metrics?.delivered)} click rate`} trend="neutral" icon={ExternalLink}/></div>
    <section className="panel seo-table brevo-table"><div className="panel-head"><div><span className="panel-kicker">Live Brevo reporting</span><h2>Recent email campaigns</h2></div><span className="connection-status"><i/>{data?.live ? "Connected" : "Unavailable"}</span></div><div className="table-grid brevo-grid">{["Campaign","Status","Sent","Delivered","Unique opens","Unique clicks"].map(h=><span className="table-heading" key={h}>{h}</span>)}{(data?.campaigns ?? []).slice(0,12).flatMap(campaign => [<span className="table-primary" key={`${campaign.id}-name`}><strong>{campaign.name}</strong><small>{campaign.subject || campaign.sentDate || campaign.scheduledAt || "No subject"}</small></span>,<span className="table-cell" key={`${campaign.id}-status`}><StatusPill status={(campaign.status === "sent" ? "Published" : campaign.status === "draft" ? "Draft" : "Scheduled") as Status}/></span>,<span className="table-cell" key={`${campaign.id}-sent`}>{campaign.sent.toLocaleString()}</span>,<span className="table-cell" key={`${campaign.id}-delivered`}>{campaign.delivered.toLocaleString()}</span>,<span className="table-cell" key={`${campaign.id}-views`}>{campaign.uniqueViews.toLocaleString()}</span>,<span className="table-cell" key={`${campaign.id}-clicks`}>{campaign.uniqueClicks.toLocaleString()}</span>])}</div>{!loading && !(data?.campaigns?.length) && <div className="empty"><Send size={27}/><strong>No Brevo campaigns returned</strong><span>Confirm the API key has campaign-read access.</span></div>}</section>
    <section className="panel brevo-lists"><div className="panel-head"><div><span className="panel-kicker">Audience health</span><h2>Brevo lists</h2></div><strong>{metrics?.subscribers.toLocaleString() ?? "—"} <small>list memberships</small></strong></div><div className="capability-grid">{(data?.lists ?? []).slice(0,8).map(list=><div key={list.id}><Send size={17}/><strong>{list.name}</strong><span>{list.subscribers.toLocaleString()} subscribers</span><small>{list.blacklisted.toLocaleString()} blacklisted · List {list.id}</small></div>)}</div></section>
    <Worklist items={items} filter={filter} setFilter={setFilter} onOpen={onOpen} onStatus={onStatus} active="Emails"/>
  </div>;
}

function CensusView({ onNavigate }: { onNavigate: (key: string) => void }) {
  return <div className="analytics-view">
    <div className="data-note"><Database size={15} /><strong>Operational source required</strong><span>No census, referral, admission, discharge or EMR source is connected. No sample figures are shown as real.</span><button onClick={() => onNavigate("Connections")}>Review connections <ArrowUpRight size={13} /></button></div>
    <section className="panel connection-empty"><Database size={28} /><h2>Connect the authoritative census source</h2><p>This view will remain empty until Eternal identifies the system that owns daily census, referrals, evaluations, admissions and discharges. Only aggregate, non-PHI reporting should be connected here.</p><button className="secondary-btn" onClick={() => onNavigate("Connections")}><Cable size={14} /> Review data connections</button></section>
  </div>;
}

function SeoView({ connections, onConnect }: { connections: { ga4: boolean; gsc: boolean }; onConnect: (target: "ga4" | "gsc") => void }) {
  const [range, setRange] = useState("Last 28 days");
  const [tab, setTab] = useState("Overview");
  const [report, setReport] = useState<LiveSeoData | null>(null);
  const [loading, setLoading] = useState(true);
  const tabs = ["Overview", "Landing pages", "Search queries", "Indexing health"];
  useEffect(() => {
    const controller = new AbortController();
    const period = range === "Previous 28 days" ? "previous" : range === "Year to date" ? "ytd" : "last28";
    setLoading(true);
    fetch(`${import.meta.env.BASE_URL}api/elh-reporting?period=${period}`, { signal: controller.signal })
      .then(async response => {
        const data = await response.json() as LiveSeoData;
        if (!response.ok) throw new Error(data.errors?.join(" ") || "Live reporting request failed.");
        setReport(data);
      })
      .catch(error => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setReport({ live: false, errors: [error instanceof Error ? error.message : String(error)] });
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [range]);
  const metrics = report?.metrics;
  const format = (value: number | undefined) => loading ? "…" : value === undefined ? "—" : Math.round(value).toLocaleString();
  const bars = report?.trend?.slice(-12) ?? [];
  const maxSessions = Math.max(1, ...bars.map(point => point.sessions));
  return <div className="analytics-view">
    <div className={`data-note ${report?.live ? "is-live" : ""}`}><Activity size={15} /><strong>{loading ? "Loading live reporting" : report?.live ? "Live Google reporting" : "Reporting connection needs attention"}</strong><span>{loading ? "Requesting GA4 and Search Console data…" : report?.live ? `GA4 and Search Console · ${report.period?.startDate}–${report.period?.endDate} · refreshed ${new Date(report.generatedAt || "").toLocaleTimeString([], {hour:"numeric", minute:"2-digit"})}` : report?.errors?.join(" ")}</span><button onClick={() => window.location.reload()}><RefreshCw size={13} /> Refresh</button></div>
    <div className="view-toolbar"><div><span className="panel-kicker">Website discovery & action</span><h2>SEO analytics that ends in a useful question</h2></div><select aria-label="SEO date range" value={range} onChange={e => setRange(e.target.value)}><option>Last 28 days</option><option>Previous 28 days</option><option>Year to date</option></select></div>
    <div className="metric-grid four"><Metric label="Website sessions" value={format(metrics?.sessions)} detail="GA4 sessions" trend="neutral" icon={Globe2} /><Metric label="Key events" value={format(metrics?.keyEvents)} detail="GA4 configured key events" trend="neutral" icon={HeartHandshake} /><Metric label="Search clicks" value={format(metrics?.searchClicks)} detail={`${format(metrics?.impressions)} impressions`} trend="neutral" icon={Search} /><Metric label="Avg. position" value={loading ? "…" : metrics ? metrics.averagePosition.toFixed(1) : "—"} detail={metrics ? `${(metrics.ctr * 100).toFixed(1)}% search CTR` : "Search Console"} trend="neutral" icon={TrendingUp} /></div>
    <div className="tab-strip" role="tablist">{tabs.map(item => <button role="tab" aria-selected={tab === item} className={tab === item ? "selected" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}</div>
    {tab === "Overview" && <div className="two-panel"><section className="panel"><div className="panel-head"><div><span className="panel-kicker">Live GA4 trend · {range}</span><h2>Traffic and meaningful actions</h2></div><BarChart3 size={18} className="muted-icon" /></div><div className="mini-chart"><div className="mini-bars">{bars.length ? bars.map((point, i) => <i title={`${point.sessions} sessions`} style={{height:`${Math.max(3, point.sessions / maxSessions * 100)}%`}} key={`${point.date}-${i}`} />) : <span className="chart-empty">{loading ? "Loading trend…" : "No GA4 trend data returned"}</span>}</div><div className="mini-axis"><span>{report?.period?.startDate || "—"}</span><span>{report?.period?.endDate || "—"}</span></div></div><div className="legend"><span><i className="legend-plum" />Sessions</span><strong>{format(metrics?.keyEvents)} <small>GA4 key events</small></strong></div></section><section className="panel"><div className="panel-head"><div><span className="panel-kicker">Search Console · live</span><h2>Organic search visibility</h2></div></div><div className="action-list">{[["Clicks",format(metrics?.searchClicks)],["Impressions",format(metrics?.impressions)],["Click-through rate",metrics ? `${(metrics.ctr * 100).toFixed(1)}%` : "—"],["Average position",metrics ? metrics.averagePosition.toFixed(1) : "—"]].map(([label,value]) => <div key={label}><span>{label}</span><b>{value}</b></div>)}</div></section></div>}
    {tab === "Landing pages" && <SeoTable title="Top landing pages" headers={["Landing page","Sessions","Engaged","Key events"]} rows={(report?.landingPages ?? []).map(row => [row.page,row.sessions.toLocaleString(),`${(row.engagementRate * 100).toFixed(1)}%`,row.keyEvents.toLocaleString()])} empty={!loading && !(report?.landingPages?.length)} live />}
    {tab === "Search queries" && <SeoTable title="Top Google Search queries" headers={["Query","Clicks","Impressions","Position"]} rows={(report?.queries ?? []).map(row => [row.query,row.clicks.toLocaleString(),row.impressions.toLocaleString(),row.position.toFixed(1)])} empty={!loading && !(report?.queries?.length)} live />}
    {tab === "Indexing health" && <div className="two-panel"><section className="panel connection-empty"><Globe2 size={24} /><h2>Indexing health awaits Search Console</h2><p>Once connected, this view will show indexed pages, excluded pages, crawl signals, and issues that could keep a family from finding the right guide.</p><button className="secondary-btn" onClick={() => onConnect("gsc")}><Cable size={14} /> Connect Search Console</button></section><section className="panel capability-list"><span className="panel-kicker">Supported reporting</span>{["Indexed pages and exclusions","Clicks, impressions, CTR, position","Queries by service area","Landing pages and conversion actions"].map(x => <div key={x}><Check size={14} />{x}</div>)}</section></div>}
  </div>;
}

function SeoTable({ title, headers, rows, empty = false, live = false }: { title: string; headers: string[]; rows: string[][]; empty?: boolean; live?: boolean }) { return <section className="panel seo-table"><div className="panel-head"><div><span className="panel-kicker">{empty ? "No data returned" : live ? "Live Google reporting" : "Reporting"}</span><h2>{title}</h2></div><button className="filter-btn"><Filter size={14} /> Filter</button></div><div className="table-grid" style={{gridTemplateColumns:`minmax(180px,2fr) repeat(${headers.length - 1},1fr)`}}>{headers.map(h => <span className="table-heading" key={h}>{h}</span>)}{rows.map(row => row.map((cell, i) => <span className={i === 0 ? "table-primary" : "table-cell"} key={`${row[0]}-${i}`}>{cell}</span>))}{empty && <span className="table-primary">No reporting rows are available for this period.</span>}</div></section>; }

function ConnectionsView({ connections, onConnect }: { connections: { ga4: boolean; gsc: boolean }; onConnect: (target: "ga4" | "gsc") => void }) {
  return <div className="analytics-view"><div className="connection-hero"><div><span className="panel-kicker">Private reporting layer</span><h2>Only connected sources become reporting</h2><p>Keep the distinction clear: instrumented is not connected, and sample is never presented as live.</p></div><ShieldCheck size={28} /></div><div className="connection-grid"><ConnectionCard icon={BarChart3} name="Google Analytics 4" code="GA4" status={connections.ga4 ? "Connected" : "Instrumented on website"} detail={connections.ga4 ? "Website events can now be reviewed in this prototype." : "The website has GA4 instrumentation. This console is not yet receiving its reporting feed."} action={connections.ga4 ? "Connected" : "Connect reporting"} onClick={() => onConnect("ga4")} live={connections.ga4} /><ConnectionCard icon={Search} name="Google Search Console" code="GSC" status={connections.gsc ? "Connected" : "Available to connect"} detail={connections.gsc ? "Search queries, indexing, clicks, impressions, and position are available." : "Connect to bring search demand and indexing health into the command center."} action={connections.gsc ? "Connected" : "Connect Search Console"} onClick={() => onConnect("gsc")} live={connections.gsc} /></div><div className="capability-panel panel"><div className="panel-head"><div><span className="panel-kicker">Operational capabilities</span><h2>Directory, GBP, reviews & social</h2></div><span className="awaiting-tag">Not connected</span></div><div className="capability-grid">{[["Directory listings",MapPin,"Presence checks and referral consistency"],["Google Business Profile",Globe2,"Profile health, calls, direction requests"],["Reviews",MessageSquare,"Review volume, response rhythm, sentiment"],["Social distribution",ExternalLink,"Outbound publishing and referral context"]].map(([name,Icon,detail]) => <div key={name as string}><Icon size={17} /><strong>{name as string}</strong><span>{detail as string}</span><small>Capability area · awaiting connection</small></div>)}</div></div></div>;
}

function ConnectionCard({ icon: Icon, name, code, status, detail, action, onClick, live }: { icon: typeof Search; name: string; code: string; status: string; detail: string; action: string; onClick: () => void; live: boolean }) { return <section className={`connection-card ${live ? "is-live" : ""}`}><div className="connection-icon"><Icon size={20} /></div><div className="connection-code">{code}</div><h2>{name}</h2><div className="connection-status"><i />{status}</div><p>{detail}</p><button className={live ? "secondary-btn" : "primary-btn"} onClick={onClick}>{live ? <><Settings2 size={14} /> Manage</> : <><Cable size={14} /> {action}</>}</button></section>; }

function ConnectionDialog({ target, onClose, onConnect }: { target: "ga4" | "gsc"; onClose: () => void; onConnect: () => void }) { const ga = target === "ga4"; return <div className="detail-backdrop" onClick={onClose}><div className="connect-dialog panel" role="dialog" aria-modal="true" aria-labelledby="connect-title" onClick={e => e.stopPropagation()}><button className="icon-btn dialog-close" onClick={onClose} aria-label="Close connection dialog"><X size={18} /></button><div className="connection-icon large">{ga ? <BarChart3 size={22} /> : <Search size={22} />}</div><span className="panel-kicker">Prototype connection</span><h2 id="connect-title">Connect {ga ? "Google Analytics 4" : "Google Search Console"}</h2><p>{ga ? "GA4 is already instrumented on the Eternal Life website. This step represents authorizing the reporting layer to read those events." : "Search Console will provide queries, clicks, impressions, average position, and indexing health once authorized."}</p><label>Property or site URL<input defaultValue={ga ? "eternallifehospice.com" : "https://eternallifehospice.com"} aria-label="Property or site URL" /></label><div className="dialog-note"><ShieldCheck size={15} /> No credentials are sent in this local prototype.</div><div className="detail-actions"><button className="secondary-btn" onClick={onClose}>Cancel</button><button className="approve-btn" onClick={onConnect}><Cable size={15} /> Save connection</button></div></div></div>; }

type GrowthRow = { id: string; [key: string]: string | number };
const adRows: GrowthRow[] = [];
const legacy = "Awaiting authoritative source";
const socialRows: GrowthRow[] = [];
const partnerRows: GrowthRow[] = [];
const backlinkRows: GrowthRow[] = [];
const oppDefaults: GrowthRow[] = [];
function storedRows<T>(key:string, fallback:T): T { try { const raw=localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch { return fallback; } }

function LegacyBadge({ children = "Awaiting authoritative source" }: { children?: string }) { return <span className="legacy-badge"><CircleDot size={11} />{children}</span>; }
function GrowthView({ domain }: { domain: string }) {
  const [range, setRange] = useState("This Month");
  const [ad, setAd] = useState(() => storedRows("elh_growth_ads_connected_v1", adRows)); const [social, setSocial] = useState(() => storedRows("elh_growth_social_connected_v1", socialRows)); const [partners, setPartners] = useState(() => storedRows("elh_growth_partners_connected_v1", partnerRows));
  const [backlinks, setBacklinks] = useState(() => storedRows("elh_bl_domains_connected_v1", backlinkRows)); const [tab, setTab] = useState("Overview"); const [notice, setNotice] = useState("");
  useEffect(() => { localStorage.setItem("elh_growth_ads_connected_v1", JSON.stringify(ad)); }, [ad]);
  useEffect(() => { localStorage.setItem("elh_growth_social_connected_v1", JSON.stringify(social)); }, [social]);
  useEffect(() => { localStorage.setItem("elh_growth_partners_connected_v1", JSON.stringify(partners)); }, [partners]);
  useEffect(() => { localStorage.setItem("elh_bl_domains_connected_v1", JSON.stringify(backlinks)); }, [backlinks]);
  const add = (kind: string) => {
    const id = `${kind}-${Date.now()}`;
    if (kind === "ad") setAd(x => [...x, { id, campaign:"New campaign", spend:"$0", clicks:0, cpc:"$0", calls:0, forms:0, leads:0, cpl:"$0", status:"Draft" }]);
    if (kind === "social") setSocial(x => [...x, { id, post:"New post", platform:"Facebook", reach:"0", engagement:"0%", clicks:0, date:"Today" }]);
    if (kind === "partner") setPartners(x => [...x, { id, partner:"New partner", type:"Hospital", period:0, ytd:0, contact:"Today", status:"Prospect" }]);
    setNotice("New row added locally"); window.setTimeout(() => setNotice(""), 1800);
  };
  const title = domain === "Growth" ? "Growth intelligence" : domain === "Pipeline" ? "Census pipeline" : domain === "Referral" ? "Referral development" : domain;
  if (domain === "Growth") {
    if (["SEO","Advertising","Social","Referral","Pipeline","Backlinks"].includes(tab)) return <GrowthView domain={tab}/>;
    return <div className="analytics-view"><div className="growth-banner"><div><span className="panel-kicker">Consolidated workspace</span><h2>Marketing & census, held in one place</h2><p>The former dashboard's reporting categories are preserved, but no historical or sample values are loaded.</p></div><TrendingUp size={28}/></div><div className="growth-launcher">{["SEO","Advertising","Social","Referral","Pipeline","Backlinks"].map((x,i)=><button key={x} onClick={() => setTab(x)}><span>{["Search visibility","Paid demand","Distribution","Partner network","Aggregate operations","Authority & outreach"][i]}</span><strong>{x}</strong><small>Open intelligence view <ArrowUpRight size={13}/></small></button>)}</div><div className="panel legacy-panel"><AlertTriangle size={16}/><strong>Reporting period: {range}</strong><span>Connected and manual values must identify their authoritative source. Unsupported figures remain empty.</span><select value={range} onChange={e=>setRange(e.target.value)}><option>This Month</option><option>Last Month</option><option>Last 30 Days</option><option>Last 90 Days</option><option>Year to Date</option></select></div></div>;
  }
  const blank = "—";
  const kpis = domain === "Advertising" ? [["Total spend",blank,"Awaiting advertising source"],["Avg. CPC",blank,"Awaiting advertising source"],["Phone calls",blank,"Awaiting advertising source"],["Form submissions",blank,"Awaiting advertising source"],["Qualified leads",blank,"Awaiting advertising source"],["Cost per lead",blank,"Awaiting advertising source"]] : domain === "Social" ? [["Posts published",blank,"Awaiting social source"],["Total reach",blank,"Awaiting social source"],["Social traffic",blank,"Awaiting social source"],["Engagement rate",blank,"Awaiting social source"],["Followers gained",blank,"Awaiting social source"],["Care Brief clicks",blank,"Awaiting social source"]] : domain === "Referral" ? [["Total referrals",blank,"Awaiting referral source"],["Active partners",blank,"Awaiting referral source"],["New partners",blank,"Awaiting referral source"],["Outreach visits",blank,"Awaiting referral source"]] : domain === "Pipeline" ? [["Current census",blank,"Awaiting aggregate source"],["Admissions (period)",blank,"Awaiting aggregate source"],["Inquiries",blank,"Awaiting aggregate source"],["Conversion rate",blank,"Computed when connected"],["Lost referrals",blank,"Awaiting aggregate source"],["In evaluation",blank,"Awaiting aggregate source"]] : [["Total backlinks",blank,"Awaiting backlink source"],["Referring domains",blank,"Awaiting backlink source"],["Dofollow ratio",blank,"Awaiting backlink source"],["Lost links (period)",blank,"Awaiting backlink source"],["Domain authority",blank,"Manual entry only"]];
  const renderRows = domain === "Advertising" ? <GrowthTable headers={["Campaign","Spend","Clicks","CPC","Calls","Forms","Qual. leads","CPL","Status"]} rows={ad} keys={["campaign","spend","clicks","cpc","calls","forms","leads","cpl","status"]} editable onDelete={id=>setAd(x=>x.filter(r=>r.id!==id))} /> : domain === "Social" ? <GrowthTable headers={["Post","Platform","Reach","Eng.","Link clicks","Date"]} rows={social} keys={["post","platform","reach","engagement","clicks","date"]} editable onDelete={id=>setSocial(x=>x.filter(r=>r.id!==id))} /> : domain === "Referral" ? <GrowthTable headers={["Partner / organization","Type","Period","YTD","Last contact","Status"]} rows={partners} keys={["partner","type","period","ytd","contact","status"]} editable onDelete={id=>setPartners(x=>x.filter(r=>r.id!==id))} /> : domain === "Backlinks" ? <BacklinkView tab={tab} rows={backlinks} setRows={setBacklinks} /> : <PipelineEmpty />;
  return <div className="analytics-view"><div className="growth-title"><div><span className="panel-kicker">{legacy}</span><h2>{title}</h2><p>No values appear until a connected source or clearly labeled manual aggregate entry is available.</p></div><select value={range} onChange={e=>setRange(e.target.value)}><option>This Month</option><option>Last Month</option><option>Last 30 Days</option><option>Last 90 Days</option><option>Year to Date</option></select></div><div className="metric-grid growth-kpis">{kpis.map(([l,v,d])=><Metric key={l} label={l} value={v} detail={d} trend="neutral" icon={Activity}/>)}</div>{domain === "Pipeline" && <div className="legacy-warning"><AlertTriangle size={17}/><strong>Aggregate reporting only.</strong><span>No patient names, identifiers, diagnoses or other PHI may be stored in this workspace.</span></div>}{domain === "Backlinks" ? <><div className="tab-strip">{["Overview","Audit","Opportunities","Outreach CRM","Disavow"].map(x=><button className={tab===x?"selected":""} onClick={()=>setTab(x)} key={x}>{x}</button>)}</div>{renderRows}</> : <>{domain === "Advertising" && <SnapshotChart title="Spend vs qualified leads"/>} {domain === "Social" && <><SnapshotChart title="Reach over time — all platforms"/><PlatformBreakdown/></>} {domain === "Referral" && <SourceSnapshot/>}{domain === "Pipeline" && <FunnelSnapshot/>}<section className="panel growth-table-panel"><div className="panel-head"><div><span className="panel-kicker">{legacy}</span><h2>{domain==="Advertising"?"Campaign performance":domain==="Social"?"Top posts":domain==="Referral"?"Top referral partners":"Aggregate census periods"}</h2></div>{domain !== "Pipeline" && <button className="primary-btn" onClick={()=>add(domain==="Advertising"?"ad":domain==="Social"?"social":"partner")}><Plus size={14}/> Add {domain==="Advertising"?"campaign":domain==="Social"?"post":"partner"}</button>}</div>{renderRows}</section></>}</div>;
}
function PlatformBreakdown() { return <section className="panel platform-snapshot"><div className="panel-head"><div><span className="panel-kicker">Awaiting authoritative source</span><h2>Platform breakdown</h2></div></div>{["GBP","LinkedIn","TikTok","X","Facebook","YouTube"].map(x=><div className="platform-line" key={x}><strong>{x}</strong><i><b style={{width:"0%"}}/></i><span>— reach</span><span>— eng.</span><span>— posts</span></div>)}</section>; }
function SnapshotChart({ title }: { title:string; bars?:number[] }) { return <section className="panel snapshot-chart"><div className="panel-head"><div><span className="panel-kicker">Awaiting authoritative source</span><h2>{title}</h2></div><BarChart3 size={17}/></div><div className="chart-empty">No connected data for this chart.</div></section>; }
function SourceSnapshot() { return <div className="source-snapshot">{["Physician","Hospital","RCFE","SNF","Professional"].map(x=><div className="source-chip" key={x}><span>{x}</span><strong>—</strong><small>Awaiting authoritative source</small></div>)}</div>; }
function FunnelSnapshot() { return <section className="panel funnel-snapshot"><div className="panel-head"><div><span className="panel-kicker">Awaiting authoritative source</span><h2>Aggregate admission funnel</h2></div></div><div className="funnel-inline">{["Inquiry","Qualified referral","Evaluation","Admission"].map(x=><div key={x}><strong>—</strong><span>{x}</span></div>)}</div><div className="loss-line">Loss reasons will appear after an aggregate, non-PHI source is connected.</div></section>; }
function PipelineEmpty() { return <div className="analytics-view"><div className="legacy-warning"><AlertTriangle size={17}/><strong>Awaiting authoritative source.</strong><span>Census capture is aggregate and non-PHI only: reporting period, inquiries, qualified referrals, evaluations, admissions, non-admits, discharges, current census, and net movement.</span></div><section className="panel connection-empty"><Database size={26}/><h2>No aggregate census data connected</h2><p>Connect an authoritative operational source or add a manual aggregate reporting period. No patient-level records are stored in this workspace.</p><button className="secondary-btn"><Plus size={14}/> Add aggregate period</button></section></div>; }
function GrowthTable({ headers, rows, keys, editable=false, onDelete }: { headers:string[]; rows:GrowthRow[]; keys:string[]; editable?:boolean; onDelete?:(id:string)=>void }) { return <div className="growth-table-wrap"><table className="growth-table"><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}{editable&&<th />}</tr></thead><tbody>{rows.map(row=><tr key={row.id}>{keys.map(k=><td key={k}><span contentEditable={editable} suppressContentEditableWarning className={k===keys[0]?"strong":""}>{String(row[k] ?? "")}</span></td>)}{editable&&<td><button className="row-more" onClick={()=>onDelete?.(row.id)} aria-label="Delete row"><Trash2 size={14}/></button></td>}</tr>)}</tbody></table></div>; }
function BacklinkView({ tab, rows, setRows }: { tab:string; rows:GrowthRow[]; setRows:Dispatch<SetStateAction<GrowthRow[]>> }) { const [disavow,setDisavow]=useState(""); const [crm,setCrm]=useState<GrowthRow[]>([]); if(tab==="Disavow") return <section className="panel disavow-panel"><span className="panel-kicker">Awaiting source</span><h2>Disavow list</h2><p>Enter domains only after an authoritative backlink audit is connected.</p><textarea value={disavow} onChange={e=>setDisavow(e.target.value)}/><div className="detail-actions"><button className="secondary-btn" onClick={()=>navigator.clipboard?.writeText(disavow)}><Clipboard size={14}/> Copy to clipboard</button><button className="primary-btn" onClick={()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([disavow],{type:"text/plain"}));a.download="elh-disavow.txt";a.click();}}><Download size={14}/> Download text</button></div></section>; if(tab==="Opportunities") return <section className="panel"><div className="panel-head"><div><span className="panel-kicker">Awaiting source</span><h2>Link prospects</h2></div><button className="primary-btn" onClick={()=>setRows(x=>[...x,{id:`b${Date.now()}`,domain:"Manual entry",type:"",da:"",links:"",anchor:"",status:"Not started",notes:""}])}><Plus size={14}/> Add prospect</button></div><GrowthTable headers={["Site / organization","Type","DA","Links","Anchor text","Status","Notes"]} rows={[]} keys={["domain","type","da","links","anchor","status","notes"]}/></section>; if(tab==="Outreach CRM") return <section className="panel"><div className="bl-form-row"><input placeholder="Contact name"/><input placeholder="Organization / site"/><button className="primary-btn" onClick={()=>setCrm(x=>[...x,{id:`c${Date.now()}`,contact:"Manual entry",org:"",status:"Not contacted",notes:""}])}><Plus size={14}/> Add outreach</button></div><GrowthTable headers={["Contact","Organization","Status","Notes"]} rows={crm} keys={["contact","org","status","notes"]} editable onDelete={id=>setCrm(x=>x.filter(r=>r.id!==id))}/></section>; return <div className="analytics-view"><SnapshotChart title="Authority and referring domains"/><section className="panel"><div className="panel-head"><div><span className="panel-kicker">Awaiting source</span><h2>Tracked domains</h2></div><button className="secondary-btn" onClick={()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["domain,type,da,links,anchor,status,notes"],{type:"text/csv"}));a.download="elh-backlink-audit.csv";a.click();}}><Download size={14}/> Export CSV</button></div><GrowthTable headers={["Domain","Type","DA","Links","Anchor text","Status","Notes"]} rows={rows} keys={["domain","type","da","links","anchor","status","notes"]} /></section></div>; }

function Worklist({ items, filter, setFilter, onOpen, onStatus, active }: { items: Item[]; filter: string; setFilter: (s: string) => void; onOpen: (i: Item) => void; onStatus: (id: string, s: Status) => void; active: string }) {
  const identity = active === "Journal" ? "Website blog post" : active === "Emails" ? "Weekly outbound email" : active === "CareBrief" ? "Every other month · Longer read" : "";
  return <div className={`worklist panel ${active === "CareBrief" ? "care-brief-list" : ""}`}>{identity && <div className="list-identity"><BookOpen size={16} /><strong>{identity}</strong><span>{active === "CareBrief" ? "A distinct publication series — not a Journal post or email campaign." : active === "Emails" ? "Campaigns can link to Journal posts, but remain separate outbound sends." : "Articles published to the Eternal Journal website."}</span></div>}<div className="list-toolbar"><div className="list-tabs"><button className={filter === "All" ? "on" : ""} onClick={() => setFilter("All")}>All <b>{items.length}</b></button>{["Needs review", "Approved", "Scheduled", "Draft"].map(s => <button key={s} className={filter === s ? "on" : ""} onClick={() => setFilter(s)}>{s} <b>{items.filter(i => i.status === s).length}</b></button>)}</div><button className="filter-btn"><Filter size={15} /> Filters</button></div><div className="list-head"><span>Item</span><span>Channel</span><span>Owner</span><span>Scheduled</span><span>Status</span><span /></div><div className="item-list">{items.length ? items.map(item => <div className="list-row" key={item.id} onClick={() => onOpen(item)}><div className="item-name"><div className={`mini-type ${item.type === "Journal" ? "journal" : item.type === "Weekly email" ? "email" : "asset"}`}><FileText size={15} /></div><div><strong>{item.title}</strong><small>{item.excerpt}</small></div></div><span className="channel">{item.type}</span><span className="owner"><i>{item.owner.split(" ").map(s => s[0]).join("")}</i>{item.owner}</span><span className="date">{item.date}</span><StatusPill status={item.status} /><button className="row-more" onClick={e => { e.stopPropagation(); onStatus(item.id, item.status === "Needs review" ? "Approved" : "Needs review"); }} aria-label="Change status"><MoreHorizontal size={17} /></button></div>) : <div className="empty"><FolderOpen size={27} /><strong>{active === "CareBrief" ? "No Care Brief issues in this view" : active === "Journal" ? "No Journal posts in this view" : active === "Emails" ? "No email campaigns in this view" : "No items in this view"}</strong><span>Try another status or clear your search.</span></div>}</div><div className="list-footer">Showing <strong>{items.length}</strong> items <span>Last synced just now</span></div></div>;
}

function StatusPill({ status }: { status: Status }) { return <span className={`status ${status.toLowerCase().replace(" ", "-")}`}><i />{status}</span>; }

function Detail({ item, onClose, onStatus }: { item: Item; onClose: () => void; onStatus: (id: string, s: Status) => void }) {
  const [full, setFull] = useState(false);
  const article = item.source;
  const campaign = item.emailIndex === undefined ? undefined : emailCampaigns[item.emailIndex];
  return <div className="detail-backdrop" onClick={onClose}>
    <aside className={`detail-drawer ${full ? "full-review" : ""}`} onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={`${item.type} review`}>
      <header><div><span className="panel-kicker">{item.type}</span><h2>{full ? "Full review" : "Item preview"}</h2></div><button className="icon-btn" onClick={onClose} aria-label="Close preview"><X size={19} /></button></header>
      <div className="detail-body"><StatusPill status={item.status} /><h1>{item.title}</h1><p className="detail-excerpt">{item.excerpt}</p>
        <div className="meta-grid"><div><span>Owner</span><strong>{item.owner}</strong></div><div><span>Scheduled</span><strong>{item.date}</strong></div></div>
        {campaign ? <div className="email-review">
          <div className="email-preview-label"><span>Rendered email</span><small>Sandboxed preview · links disabled</small></div>
          <iframe title={`Rendered preview of ${item.title}`} sandbox="" srcDoc={campaign.html.replaceAll("https://eternallifehospice.com", "about:blank")} />
          <div className="campaign-details"><h3>Campaign details</h3><dl><dt>Subject</dt><dd>{campaign.subject}</dd><dt>Preheader</dt><dd>{campaign.preheader}</dd><dt>Plain-text version</dt><dd><pre>{campaign.plainText}</pre></dd></dl></div>
         </div> : article ? <div className="article-review">
          <div className="article-byline"><span>{article.category}</span><span>{article.readMinutes} min read</span><span>{article.date}</span><button className="read-full-btn" onClick={() => setFull(true)}>Read the full piece <ArrowUpRight size={14} /></button></div>
           {item.infographicRecommendation && <div className="editorial-callout"><strong>Selective infographic recommendation</strong><span>{item.infographicRecommendation}</span><small>Article #6 only · visual asset not generated</small></div>}
          <p className="article-lede">{article.lede}</p>
          {article.sections.map(section => <section key={section.heading}><h3>{section.heading}</h3>{section.paragraphs.map((paragraph, index) => <p key={`${section.heading}-${index}`}>{paragraph}</p>)}</section>)}
          <div className="article-cta"><strong>{article.ctaHeading}</strong><p>{article.ctaCopy}</p></div>
        </div> : <div className="preview-paper"><div className="paper-brand"><HeartHandshake size={15} /> ETERNAL LIFE</div><div className="paper-line" /><span>EDITORIAL PREVIEW</span><h3>{item.title}</h3><p>{item.excerpt}</p></div>}
        <div className="detail-actions">{item.status === "Needs review" ? <button className="approve-btn" onClick={() => onStatus(item.id, "Approved")}><Check size={16} /> Approve item</button> : <button className="secondary-btn" onClick={() => onStatus(item.id, "Needs review")}><Clock3 size={16} /> Return to review</button>}<button className="secondary-btn" onClick={() => onStatus(item.id, item.status === "Scheduled" ? "Draft" : "Scheduled")}><Send size={15} /> {item.status === "Scheduled" ? "Move to draft" : "Schedule"}</button></div>
      </div>
    </aside>
  </div>;
}