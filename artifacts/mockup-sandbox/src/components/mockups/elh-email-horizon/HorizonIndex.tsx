import React, { useEffect, useMemo, useState } from "react";

type ApprovedMessage = {
  key: string;
  subject: string;
  text: string;
  paragraphs: string[];
  originalHtml: string;
};

const DATA_URL = "/__reviews-mockup/email-design/approved-messages.json";
const LOGO_URL = "/__reviews-mockup/images/elh-patient-guide/logo-plum.png";
const COAST_URL = "/__reviews-mockup/images/elh-patient-guide/seated-coastal-view.jpg";

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderParagraph(paragraph: string) {
  const safe = escapeHtml(paragraph).replaceAll("\n", "<br>");
  if (paragraph.startsWith("Need to speak with someone now?\n")) {
    const lines = paragraph.split("\n");
    return `<tr><td style="padding:6px 0 23px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-top:1px solid #d9cdb7;border-bottom:1px solid #d9cdb7"><tr><td style="padding:15px 0 16px"><p style="margin:0 0 5px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif">${escapeHtml(lines[0])}</p><p style="margin:0 0 12px;color:#535353;font:15px/1.55 Georgia,'Times New Roman',serif">${escapeHtml(lines[1])}</p><a href="tel:18059537273" style="display:inline-block;color:#414141;background:#f5f0eb;border:1px solid #cfc2aa;padding:10px 14px;font:bold 14px/1.2 Arial,sans-serif;text-decoration:none">${escapeHtml(lines[2])}</a></td></tr></table></td></tr>`;
  }
  if (paragraph.startsWith("Confirmation number:")) {
    return `<tr><td style="padding:12px 0 0;border-top:1px solid #e2ddd4"><p style="margin:0;color:#555;font:13px/1.6 Arial,sans-serif">${safe}</p></td></tr>`;
  }
  if (paragraph.startsWith("To help protect patient privacy") || paragraph.startsWith("If you are experiencing a medical emergency") || paragraph.startsWith("Important: This confirms receipt")) {
    return `<tr><td style="padding:8px 0 0"><p style="margin:0;color:#555;font:13px/1.6 Arial,sans-serif">${safe}</p></td></tr>`;
  }
  const greeting = /^(Dear|Hello) /.test(paragraph);
  const signoff = /^(With care,|With appreciation,|Warm regards,|Warmly,)$/.test(paragraph);
  const team = paragraph.startsWith("The Eternal Life Hospice");
  const tagline = /^(Here in Moments That Matter Most\.|Care That Honors Life\.)$/.test(paragraph);
  const style = greeting
    ? "margin:0 0 18px;color:#4b4b4b;font:16px/1.6 Georgia,'Times New Roman',serif"
    : signoff
      ? "margin:21px 0 3px;color:#4b4b4b;font:16px/1.6 Georgia,'Times New Roman',serif"
      : team
        ? "margin:0 0 4px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif"
        : tagline
          ? "margin:0 0 18px;color:#686868;font:italic 14px/1.55 Georgia,'Times New Roman',serif"
          : "margin:0 0 15px;color:#414141;font:16px/1.62 Georgia,'Times New Roman',serif";
  return `<tr><td><p style="${style}">${safe}</p></td></tr>`;
}

function emailDocument(message: ApprovedMessage) {
  const rows = message.paragraphs.map(renderParagraph).join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{margin:0;padding:0;width:100%;background:#f5f0eb}*{box-sizing:border-box}@media(max-width:480px){.outer{padding:0!important}.shell{border-left:0!important;border-right:0!important}.photo{height:122px!important}.brand{padding:15px 13px!important}.logo{width:118px!important}.copy{padding:21px 20px 17px!important}.foot{padding:0 20px 22px!important}}</style></head><body style="margin:0;background:#f5f0eb;color:#414141"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f0eb"><tr><td class="outer" align="center" style="padding:17px 12px 24px"><table role="presentation" class="shell" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#fffefa;border:1px solid #ddd5c8"><tr><td width="39%" class="photo" valign="middle" style="height:156px;padding:0;background:#d8d0c3"><img src="${COAST_URL}" width="234" height="156" alt="Quiet coastal view" style="display:block;width:100%;height:156px;object-fit:cover;border:0"></td><td width="61%" class="brand" valign="middle" style="padding:22px 25px;background:#f4f0e9;border-bottom:3px solid #b5a279"><img class="logo" src="${LOGO_URL}" width="142" alt="Eternal Life Hospice" style="display:block;width:142px;max-width:100%;height:auto;border:0"></td></tr><tr><td colspan="2" class="copy" style="padding:25px 48px 21px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="color:#414141;font:16px/1.62 Georgia,'Times New Roman',serif">${rows}</table></td></tr><tr><td colspan="2" class="foot" style="padding:0 48px 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%"><tr><td style="padding-top:12px;border-top:1px solid #e2ddd4;font:13px/1.5 Arial,sans-serif"><a href="mailto:info@eternallifehospice.com" style="color:#535353;text-decoration:none;overflow-wrap:anywhere">info@eternallifehospice.com</a><br><span style="display:inline-block;padding-top:8px;color:#555;font:12px/1.55 Arial,sans-serif">Eternal Life Hospice<br>4165 E Thousand Oaks Blvd, Suite 325B<br>Westlake Village, CA 91362</span></td></tr></table></td></tr></table></td></tr></table></body></html>`;
}

const styles = `
.hi{--plum:#432440;--ink:#40393b;--muted:#827a72;--gold:#b5a279;--line:#e2d9cc;--paper:#f5f0eb;min-height:100dvh;background:#eee8df;color:var(--ink);font-family:'DM Sans','Avenir Next',sans-serif;padding:25px 30px 34px}
.hi *{box-sizing:border-box}.hi .frame{max-width:1440px;margin:0 auto}.hi .mast{height:38px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #d7cbb9;color:#766d65;font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
.hi .brandline{display:flex;align-items:center;gap:9px;color:#534a49}.hi .seal{width:23px;height:23px;border:1px solid var(--gold);border-radius:50%;display:grid;place-items:center;color:var(--plum);font:italic 14px Georgia,serif;letter-spacing:0}
.hi .heading{display:flex;align-items:end;justify-content:space-between;padding:24px 0 18px}.hi .kicker{font-size:10px;font-weight:700;letter-spacing:.19em;text-transform:uppercase;color:#9a8967;margin-bottom:7px}.hi h1{margin:0;color:var(--plum);font:500 34px/1.05 'Cormorant Garamond',Georgia,serif;letter-spacing:-.025em}.hi .headnote{max-width:300px;text-align:right;color:#786f69;font:italic 15px/1.4 'Cormorant Garamond',Georgia,serif}
.hi .library{display:grid;grid-template-columns:315px minmax(0,1fr);min-height:690px;border:1px solid #d8cebf;background:#f8f4ee;box-shadow:0 14px 34px rgba(67,36,64,.07)}
.hi .index{border-right:1px solid #ddd3c4;padding:20px 16px 15px;background:#f2ede6;display:flex;flex-direction:column;min-width:0}
.hi .index-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}.hi .index-title{font:500 22px/1.1 'Cormorant Garamond',Georgia,serif;color:var(--plum)}.hi .count{font:10px 'DM Mono',monospace;letter-spacing:.08em;color:#8b8074}
.hi .search{width:100%;height:39px;border:1px solid #d7cbbb;background:#faf8f4;padding:0 12px;color:#514949;font:13px 'DM Sans',sans-serif;outline:none}.hi .search:focus{border-color:#9d8969;box-shadow:0 0 0 2px rgba(181,162,121,.16)}.hi .search::placeholder{color:#a39a8e}
.hi .list-label{margin:20px 0 8px;color:#988b78;font-size:9px;font-weight:700;letter-spacing:.17em;text-transform:uppercase}
.hi .list{overflow:auto;display:grid;gap:5px}.hi .item{position:relative;display:grid;grid-template-columns:29px minmax(0,1fr);gap:9px;text-align:left;width:100%;padding:11px 10px;border:1px solid transparent;background:transparent;color:#514a47;cursor:pointer;transition:background .18s ease,border-color .18s ease,transform .18s ease}.hi .item:hover{background:#f9f6f1;border-color:#e3d9cb;transform:translateX(2px)}.hi .item.active{background:#fbf9f4;border-color:#d7cbbb}.hi .item.active:before{content:"";position:absolute;left:-1px;top:8px;bottom:8px;width:2px;background:var(--gold)}.hi .number{padding-top:2px;color:#a08f70;font:10px 'DM Mono',monospace}.hi .item-title{font:600 12px/1.35 'DM Sans',sans-serif;color:#514849;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hi .item-sub{margin-top:4px;color:#898078;font:11px/1.35 'DM Sans',sans-serif;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hi .index-foot{margin-top:auto;padding-top:13px;border-top:1px solid #ddd3c4;color:#8a8177;font:11px/1.55 'DM Sans',sans-serif}
.hi .reading{min-width:0;display:flex;flex-direction:column;background:#f8f4ee}.hi .readhead{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding:22px 27px 17px;border-bottom:1px solid #e0d7ca}.hi .read-eyebrow{color:#9a8967;font-size:9px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;margin-bottom:7px}.hi .readhead h2{margin:0;max-width:700px;color:var(--plum);font:500 24px/1.14 'Cormorant Garamond',Georgia,serif}.hi .record{flex:none;color:#91877b;font:10px 'DM Mono',monospace;letter-spacing:.06em;padding-top:4px}
.hi .recipient{display:flex;gap:8px;align-items:center;padding:11px 27px;border-bottom:1px solid #e8e0d5;color:#81776d;font-size:11px}.hi .recipient strong{font-weight:600;color:#5b5250}.hi .recipient .dot{height:3px;width:3px;border-radius:50%;background:#b8a77f}
.hi .letter{margin:19px 27px 0;border:1px solid #ddd5c8;background:#f5f0eb;box-shadow:0 9px 22px rgba(67,36,64,.06);overflow:hidden}.hi iframe{display:block;width:100%;border:0;background:#f5f0eb}
.hi .readfoot{display:flex;align-items:center;justify-content:space-between;padding:13px 27px 17px;color:#8b8177;font:10px 'DM Mono',monospace;letter-spacing:.035em}.hi .readfoot span:last-child{font-family:'DM Sans',sans-serif;letter-spacing:0;font-size:11px}
.hi .state{margin:auto;padding:22px;color:#6b625c;font-size:13px}.hi .retry{margin-left:10px;border:1px solid var(--plum);background:var(--plum);color:#f5f0eb;padding:7px 11px;font:600 11px 'DM Sans',sans-serif;cursor:pointer}.hi .empty{padding:20px 10px;color:#82786e;font:12px/1.5 'DM Sans',sans-serif}
@media(max-width:780px){.hi{padding:16px 14px 24px}.hi .mast .edition{display:none}.hi .heading{padding:19px 0 15px}.hi .headnote{max-width:200px;font-size:14px}.hi .library{grid-template-columns:1fr;min-height:0}.hi .index{border-right:0;border-bottom:1px solid #ddd3c4;padding:15px}.hi .list{display:flex;overflow-x:auto;padding-bottom:5px}.hi .item{flex:0 0 200px}.hi .index-foot{display:none}.hi .list-label{margin-top:13px}.hi .reading{min-height:600px}.hi .readhead{padding:18px 17px 14px}.hi .recipient{padding:10px 17px}.hi .letter{margin:14px 10px 0}.hi .readfoot{padding:12px 17px}}
@media(max-width:520px){.hi h1{font-size:30px}.hi .headnote{display:none}.hi .readhead h2{font-size:22px}.hi .record{font-size:9px}.hi .reading{min-height:570px}.hi .index-top{margin-bottom:11px}}
@media(prefers-reduced-motion:reduce){.hi *{transition:none!important}}
`;

export function HorizonIndex() {
  const [messages, setMessages] = useState<ApprovedMessage[]>([]);
  const [activeKey, setActiveKey] = useState(() => new URLSearchParams(window.location.search).get("email") || "physician");
  const [query, setQuery] = useState("");
  const [loadError, setLoadError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [frameHeight, setFrameHeight] = useState(600);

  useEffect(() => {
    let mounted = true;
    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load approved messages");
        return response.json();
      })
      .then((data: ApprovedMessage[]) => {
        if (mounted) {
          setMessages(data);
          setLoadError(false);
        }
      })
      .catch(() => {
        if (mounted) setLoadError(true);
      });
    return () => { mounted = false; };
  }, [attempt]);

  const visibleMessages = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return messages;
    return messages.filter((message) =>
      `${message.key} ${message.subject} ${message.text}`.toLowerCase().includes(term),
    );
  }, [messages, query]);
  const activeMessage = messages.find((message) => message.key === activeKey);
  const activeIndex = messages.findIndex((message) => message.key === activeKey);

  const selectMessage = (key: string) => {
    setActiveKey(key);
    const url = new URL(window.location.href);
    url.searchParams.set("email", key);
    window.history.replaceState({}, "", url);
  };

  return (
    <main className="hi">
      <style>{styles}</style>
      <div className="frame">
        <div className="mast">
          <div className="brandline"><span className="seal">e</span><span>Eternal Life Hospice</span></div>
          <span className="edition">Correspondence library&nbsp; · &nbsp;unpublished preview</span>
        </div>
        <header className="heading">
          <div><div className="kicker">Review by request type</div><h1>Approved correspondence</h1></div>
          <div className="headnote">A quiet index for finding the right words, then staying with the whole letter.</div>
        </header>
        <section className="library" aria-label="Approved email correspondence">
          <aside className="index" aria-label="Message index">
            <div className="index-top"><div className="index-title">Message index</div><div className="count">{String(messages.length).padStart(2, "0")} RECORDS</div></div>
            <input className="search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a message…" aria-label="Search approved messages" />
            <div className="list-label">All approved messages</div>
            {loadError ? (
              <div className="state">The message library is unavailable.<button className="retry" type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button></div>
            ) : messages.length === 0 ? (
              <div className="empty">Gathering approved correspondence…</div>
            ) : visibleMessages.length ? (
              <nav className="list" aria-label="Choose a message">
                {visibleMessages.map((message) => {
                  const index = messages.findIndex((item) => item.key === message.key);
                  const active = activeKey === message.key;
                  return (
                    <button key={message.key} type="button" className={`item${active ? " active" : ""}`} aria-current={active ? "true" : undefined} onClick={() => selectMessage(message.key)}>
                      <span className="number">{String(index + 1).padStart(2, "0")}</span>
                      <span><span className="item-title">{message.key.replaceAll("-", " ")}</span><span className="item-sub">{message.subject}</span></span>
                    </button>
                  );
                })}
              </nav>
            ) : <div className="empty">No messages match “{query}”. Try another word or subject.</div>}
            <div className="index-foot">Choose a request to open its complete approved wording.</div>
          </aside>
          <section className="reading" aria-label="Selected message preview">
            {activeMessage ? (
              <>
                <div className="readhead">
                  <div><div className="read-eyebrow">Selected message · {activeMessage.key.replaceAll("-", " ")}</div><h2>{activeMessage.subject}</h2></div>
                  <div className="record">{String(activeIndex + 1).padStart(2, "0")} / {String(messages.length).padStart(2, "0")}</div>
                </div>
                <div className="recipient"><span>TO</span><strong>[Recipient]</strong><span className="dot" /><span>Approved wording</span></div>
                <div className="letter">
                  <iframe title={`${activeMessage.subject} — email preview`} srcDoc={emailDocument(activeMessage)} sandbox="allow-same-origin allow-popups allow-top-navigation-by-user-activation" style={{ height: `${frameHeight}px` }} onLoad={(event) => {
                    const height = event.currentTarget.contentDocument?.documentElement.scrollHeight;
                    if (height) setFrameHeight(Math.max(540, height));
                  }} />
                </div>
                <div className="readfoot"><span>ETERNAL LIFE HOSPICE</span><span>End of approved message</span></div>
              </>
            ) : loadError ? (
              <div className="state">A message preview will appear when the library can be reached.</div>
            ) : (
              <div className="state">Preparing the selected letter…</div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

export default HorizonIndex;
