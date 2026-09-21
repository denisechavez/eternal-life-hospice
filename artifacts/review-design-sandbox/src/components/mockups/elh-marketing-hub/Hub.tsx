import { useMemo, useState } from "react";
import {
  ArrowUpRight, Bell, BookOpen, CalendarDays, Check, ChevronRight, CircleHelp, Clock3,
  FileCheck2, FileText, Filter, FolderOpen, HeartHandshake, LayoutDashboard,
  Menu, MoreHorizontal, PanelLeftClose, Plus, Search, Send, Settings2,
  ShieldCheck, Sparkles, TrendingUp, Users, X
} from "lucide-react";
import "./hub.css";
import { emailCampaigns, journalArticles, type JournalArticle } from "./contentData";

type Status = "Needs review" | "Approved" | "Scheduled" | "Draft" | "Published";
type Item = { id: string; title: string; type: string; date: string; owner: string; status: Status; excerpt: string; source?: JournalArticle; emailIndex?: number; infographicRecommendation?: string; };

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
  { label: "Content calendar", icon: CalendarDays, key: "Calendar" },
  { label: "Review & approvals", icon: FileCheck2, key: "Reviews", count: 7 },
  { label: "Journal posts", note: "Website blog posts", icon: FileText, key: "Journal" },
  { label: "Email campaigns", note: "Weekly outbound emails", icon: Send, key: "Emails" },
  { label: "The Eternal Care Brief", note: "Every other month · Longer read", icon: BookOpen, key: "CareBrief" },
  { label: "Publications", icon: FileText, key: "Publications" },
  { label: "Collateral & assets", icon: FolderOpen, key: "Assets" }
];

function readStatuses(): Record<string, Status> {
  try { return JSON.parse(localStorage.getItem("elh-hub-statuses") || "{}"); } catch { return {}; }
}

export default function Hub() {
  const [active, setActive] = useState("Overview");
  const [items, setItems] = useState(() => baseItems.map(item => ({ ...item, status: readStatuses()[item.id] || item.status })));
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selected, setSelected] = useState<Item | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("");

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
        <div className="hub-brand"><div className="brand-mark"><HeartHandshake size={19} /></div><div><strong>Eternal Life</strong><span>Hospice operations</span></div><button className="close-nav" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button></div>
        <div className="workspace-label">WORKSPACE <span>PRODUCTION</span></div>
         <nav>{nav.map(({ label, note, icon: Icon, key, count }) => <button key={key} className={`${active === key ? "active" : ""} ${note ? "nav-product" : ""}`} onClick={() => { setActive(key); setStatusFilter("All"); setMobileNav(false); }}><Icon size={17} /><span>{label}{note && <small>{note}</small>}</span>{count && <b>{items.filter(i => i.status === "Needs review" && ["Journal", "Weekly email"].includes(i.type)).length}</b>}</button>)}</nav>
        <div className="sidebar-foot"><div className="sync"><span className="live-dot" /> All systems current <small>Today, 9:42 AM</small></div><button><Settings2 size={16} /> Workspace settings</button><div className="profile"><div className="avatar">AD</div><div><strong>Aleksandra D.</strong><span>Founder & CEO</span></div><MoreHorizontal size={17} /></div></div>
      </aside>
      {mobileNav && <button className="nav-scrim" onClick={() => setMobileNav(false)} aria-label="Close menu" />}
      <main className="hub-main">
        <header className="hub-topbar"><button className="menu-btn" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={21} /></button><div className="crumb">Eternal Life / <strong>{active === "Overview" ? "Command center" : active}</strong></div><div className="top-actions"><div className="search"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search workspace" /><kbd>⌘ K</kbd></div><button className="icon-btn" aria-label="Notifications"><Bell size={18} /><i /></button><div className="top-avatar">AM</div></div></header>
        <section className="hub-content">
          <div className="page-heading"><div><div className="eyebrow">Tuesday, September 22, 2026 <span className="rule" /> 9:42 AM PT</div><h1>{active === "Overview" ? "Good morning, Aleksandra." : active === "Journal" ? "Journal posts" : active === "Emails" ? "Email campaigns" : active === "CareBrief" ? "The Eternal Care Brief" : active}</h1><p>{active === "Overview" ? "A clear view of what is growing, what is moving, and what needs your eye." : active === "Reviews" ? "Seven pieces are waiting for a final decision before they can move forward." : active === "Journal" ? "Website blog posts for families and care partners." : active === "Emails" ? "Weekly outbound emails, kept separate from the Journal posts they may link to." : active === "CareBrief" ? "Every other month · Longer read · Issue One is a living care publication for care teams and families." : "Keep the work close, considered, and ready for the families who need it."}</p></div><button className="primary-btn" onClick={() => setNotice("New item workflow is ready for your brief")}><Plus size={16} /> New item</button></div>
          {active === "Overview" ? <Overview items={items} onOpen={openDetail} onStatus={setStatus} /> : <Worklist items={visibleItems} filter={statusFilter} setFilter={setStatusFilter} onOpen={openDetail} onStatus={setStatus} active={active} />}
        </section>
      </main>
      {selected && <Detail item={selected} onClose={() => setSelected(null)} onStatus={setStatus} />}
      {notice && <div className="toast"><Check size={16} /> {notice}</div>}
    </div>
  );
}

function Overview({ items, onOpen, onStatus }: { items: Item[]; onOpen: (i: Item) => void; onStatus: (id: string, s: Status) => void }) {
  const review = items.filter(i => i.status === "Needs review");
  return <div className="overview">
    <div className="metric-grid"><Metric label="Current census" value="47" detail="+6 this month" trend="up" icon={Users} /><Metric label="Referral conversion" value="31.8%" detail="+4.2% vs. Aug" trend="up" icon={TrendingUp} /><Metric label="Published this month" value="14" detail="of 30 Journal articles" trend="neutral" icon={FileText} /><Metric label="Awaiting your review" value={review.length.toString().padStart(2, "0")} detail="7 journal + email pieces" trend="attention" icon={Clock3} /></div>
    <div className="main-grid"><section className="panel performance"><div className="panel-head"><div><span className="panel-kicker">Census & performance</span><h2>Steady growth, thoughtfully held</h2></div><button className="text-btn">View report <ArrowUpRight size={14} /></button></div><div className="chart"><div className="chart-y"><span>50</span><span>40</span><span>30</span><span>20</span></div><div className="chart-area"><div className="gridlines"><i /><i /><i /><i /></div><svg viewBox="0 0 600 180" preserveAspectRatio="none" aria-label="Census trend"><path className="area" d="M0 148 C52 143 57 131 93 136 S145 116 184 120 S230 108 270 111 S320 80 360 93 S408 73 445 78 S495 48 530 55 S572 30 600 34 V180 H0Z" /><path className="line" d="M0 148 C52 143 57 131 93 136 S145 116 184 120 S230 108 270 111 S320 80 360 93 S408 73 445 78 S495 48 530 55 S572 30 600 34" /></svg><div className="chart-x"><span>Aug 01</span><span>Aug 15</span><span>Sep 01</span><span>Sep 15</span><span>Today</span></div></div></div><div className="legend"><span><i className="legend-plum" />Census</span><span><i className="legend-gold" />47 patients today</span><strong>+14.6% <small>month over month</small></strong></div></section>
      <section className="panel review-panel"><div className="panel-head"><div><span className="panel-kicker">Review queue</span><h2>Needs your eye</h2></div><button className="round-btn" onClick={() => onOpen(review[0])} aria-label="Open review queue"><ChevronRight size={17} /></button></div><div className="queue-list">{review.slice(0, 4).map(item => <button className="queue-item" key={item.id} onClick={() => onOpen(item)}><div className="type-icon"><FileCheck2 size={15} /></div><div><strong>{item.title}</strong><span>{item.type} · {item.date}</span></div><ChevronRight size={15} /></button>)}</div><button className="panel-link" onClick={() => onOpen(review[0])}>Open full review queue <ArrowUpRight size={14} /></button></section></div>
    <div className="lower-grid"><section className="panel calendar-strip"><div className="panel-head"><div><span className="panel-kicker">Content calendar</span><h2>Next up in the Journal</h2></div><button className="text-btn">Open calendar <ArrowUpRight size={14} /></button></div><div className="days">{items.filter(i => i.type === "Journal").slice(0, 6).map((i, idx) => <button key={i.id} onClick={() => onOpen(i)} className={`day ${idx === 0 ? "today" : ""}`}><span>{idx === 0 ? "Today" : i.date.split(" ")[0]}</span><b>{i.date.split(" ")[1]?.replace(",", "")}</b><i>{i.status === "Needs review" ? "Review" : i.status}</i><strong>{i.title}</strong></button>)}</div></section><section className="panel quick-panel"><span className="panel-kicker">Publishing health</span><h2>30-day Journal</h2><div className="progress-wrap"><div className="progress"><i style={{ width: "47%" }} /></div><strong>14 <small>/ 30 live</small></strong></div><p>Four weekly emails are mapped to the campaign. Two are ready for final approval.</p><button className="text-btn">View campaign plan <ArrowUpRight size={14} /></button></section></div>
  </div>;
}

function Metric({ label, value, detail, trend, icon: Icon }: { label: string; value: string; detail: string; trend: string; icon: typeof Users }) { return <div className="metric"><div className="metric-icon"><Icon size={17} /></div><span>{label}</span><strong>{value}</strong><small className={trend}>{trend === "up" ? "↗ " : trend === "attention" ? "• " : ""}{detail}</small></div>; }

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