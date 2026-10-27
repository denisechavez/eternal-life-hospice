import React, { useEffect, useMemo, useState } from "react";

type ApprovedMessage = {
  key: string;
  subject: string;
  text: string;
  paragraphs: string[];
  originalHtml: string;
};

const DATA_URL = "/__reviews-mockup/email-design/approved-messages.json";
const LOGO_URL = "/__reviews-mockup/email-design/logo-cream.png";

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderParagraph(paragraph: string) {
  const safe = escapeHtml(paragraph);
  if (paragraph.startsWith("Need to speak with someone now?\n")) {
    const lines = paragraph.split("\n");
    return `<tr><td style="padding:4px 0 24px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f5f2eb;border-left:3px solid #b5a279">
        <tr><td style="padding:20px 22px 18px">
          <p style="margin:0 0 6px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif">${escapeHtml(lines[0])}</p>
          <p style="margin:0 0 16px;color:#535353;font:15px/1.55 Georgia,'Times New Roman',serif">${escapeHtml(lines[1])}</p>
          <a href="tel:18059537273" style="display:inline-block;color:#3e3e3e;background:#ebe5d8;border:1px solid #d0c6b2;padding:11px 16px;font:bold 15px/1.2 Arial,sans-serif;text-decoration:none">${escapeHtml(lines[2])}</a>
        </td></tr>
      </table>
    </td></tr>`;
  }
  if (paragraph.startsWith("Confirmation number:")) {
    return `<tr><td style="padding:17px 0 12px;border-top:1px solid #e5e4de">
      <p style="margin:0;color:#555555;font:13px/1.6 Arial,sans-serif;letter-spacing:.15px">${safe}</p>
    </td></tr>`;
  }
  if (
    paragraph.startsWith("To help protect patient privacy") ||
    paragraph.startsWith("If you are experiencing a medical emergency") ||
    paragraph.startsWith("Important: This confirms receipt")
  ) {
    return `<tr><td style="padding:9px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.65 Arial,sans-serif">${safe}</p>
    </td></tr>`;
  }

  const isGreeting = /^(Dear|Hello) /.test(paragraph);
  const isSignoff = /^(With care,|With appreciation,|Warm regards,|Warmly,)$/.test(paragraph);
  const isTeam = paragraph.startsWith("The Eternal Life Hospice");
  const isTagline = /^(Here in Moments That Matter Most\.|Care That Honors Life\.)$/.test(paragraph);
  const style = isGreeting
    ? "margin:0 0 23px;color:#4b4b4b;font:16px/1.65 Georgia,'Times New Roman',serif"
    : isSignoff
      ? "margin:24px 0 3px;color:#4b4b4b;font:16px/1.65 Georgia,'Times New Roman',serif"
      : isTeam
        ? "margin:0 0 4px;color:#414141;font:bold 16px/1.5 Georgia,'Times New Roman',serif"
        : isTagline
          ? "margin:0 0 24px;color:#686868;font:italic 14px/1.6 Georgia,'Times New Roman',serif"
          : "margin:0 0 17px;color:#414141;font:16px/1.7 Georgia,'Times New Roman',serif";
  return `<tr><td><p style="${style}">${safe}</p></td></tr>`;
}

function makeEmailDocument(message: ApprovedMessage) {
  const letterRows = message.paragraphs.map(renderParagraph).join("");
  return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>@media only screen and (max-width:480px){.letter-content{padding:28px 20px 24px!important}.letter-footer{padding:0 20px 24px!important}}</style></head>
<body style="margin:0;background:#f1f0e9;color:#414141">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f1f0e9">
    <tr><td align="center" style="padding:24px 14px 38px">
      <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:100%;max-width:620px;background:#fffefa;border:1px solid #dfded5">
        <tr><td align="center" style="padding:21px 24px;background:#432440">
          <img src="${LOGO_URL}" width="142" alt="Eternal Life Hospice" style="display:block;width:142px;max-width:100%;height:auto;border:0">
        </td></tr>
        <tr><td class="letter-content" style="padding:34px 42px 30px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;color:#414141;font:16px/1.7 Georgia,'Times New Roman',serif">
            ${letterRows}
          </table>
        </td></tr>
        <tr><td class="letter-footer" style="padding:0 42px 25px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="padding-top:14px;border-top:1px solid #e5e4de;font:13px/1.5 Arial,sans-serif">
              <a href="mailto:info@eternallifehospice.com" style="color:#535353;text-decoration:none;overflow-wrap:anywhere">info@eternallifehospice.com</a>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;
}

export function RefinedLetter() {
  const [messages, setMessages] = useState<ApprovedMessage[]>([]);
  const [activeKey, setActiveKey] = useState(() => {
    const queryKey = new URLSearchParams(window.location.search).get("email");
    return queryKey || "physician";
  });
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load approved email records");
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
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!messages.length) return;
    if (!messages.some((item) => item.key === activeKey)) setActiveKey("physician");
  }, [activeKey, messages]);

  const activeMessage = useMemo(
    () => messages.find((item) => item.key === activeKey),
    [messages, activeKey],
  );
  const setEmail = (key: string) => {
    setActiveKey(key);
    const url = new URL(window.location.href);
    url.searchParams.set("email", key);
    window.history.replaceState({}, "", url);
  };
  const currentIndex = messages.findIndex((item) => item.key === activeKey);

  return (
    <main className="elh-review">
      <style>{`
        .elh-review{--ink:#343e39;--muted:#77817b;--line:#d9ded6;--paper:#fbfaf5;--sage:#486152;min-height:100dvh;background:#e9ebe4;color:var(--ink);font-family:'DM Sans', 'Avenir Next', sans-serif;padding:34px 42px 48px;box-sizing:border-box}
        .elh-review *{box-sizing:border-box}
        .elh-review .shell{max-width:1420px;margin:0 auto}
        .elh-review .topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;color:#728078;font-size:10px;font-weight:700;letter-spacing:.17em;text-transform:uppercase}
        .elh-review .brand{display:flex;align-items:center;gap:10px}
        .elh-review .brand-mark{height:27px;width:27px;border:1px solid #849287;border-radius:50%;display:grid;place-items:center;color:#53685b;font:italic 15px Georgia,serif}
        .elh-review .header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;border-bottom:1px solid #d2d8d0;padding:0 0 22px;margin-bottom:28px}
        .elh-review .eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.19em;color:#708077;font-weight:700;margin-bottom:9px}
        .elh-review h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:39px;line-height:1.02;letter-spacing:-.025em;margin:0;color:#354139}
        .elh-review .header-note{font:italic 17px/1.3 'Cormorant Garamond',Georgia,serif;color:#6b776e;max-width:240px;text-align:right}
        .elh-review .layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:30px;align-items:start}
        .elh-review .rail{padding:17px 0 0}
        .elh-review .rail-label{font-size:10px;font-weight:700;letter-spacing:.16em;color:#7c877f;text-transform:uppercase;margin:0 0 13px 12px}
        .elh-review .nav{display:flex;flex-direction:column;gap:3px}
        .elh-review .nav button{width:100%;border:0;background:transparent;text-align:left;padding:11px 12px;border-radius:7px;cursor:pointer;color:#59655e;display:flex;align-items:center;gap:11px;font:500 13px/1.3 'DM Sans','Avenir Next',sans-serif;transition:background .18s ease,color .18s ease}
        .elh-review .nav button:hover{background:#e0e5dd;color:#39483e}
        .elh-review .nav button.active{background:#dce4da;color:#344b3d;font-weight:700}
        .elh-review .nav-index{font:11px 'DM Mono',monospace;color:#87928a;min-width:17px}
        .elh-review .nav button.active .nav-index{color:#536d5b}
        .elh-review .rail-rule{height:1px;background:#d5dbd3;margin:20px 12px}
        .elh-review .rail-note{margin:0 12px;color:#7e8880;font:12px/1.65 'DM Sans','Avenir Next',sans-serif}
        .elh-review .workspace{min-width:0}
        .elh-review .mail-meta{background:#f5f6f0;border:1px solid #d9ded6;border-bottom:0;padding:17px 22px 16px;display:grid;grid-template-columns:70px minmax(0,1fr);gap:7px 12px}
        .elh-review .meta-label{font-size:10px;letter-spacing:.11em;text-transform:uppercase;color:#859087;font-weight:700;padding-top:3px}
        .elh-review .meta-value{font-size:13px;line-height:1.45;color:#4b554f;overflow-wrap:anywhere}
        .elh-review .meta-value.subject{font-weight:600;color:#36443b}
        .elh-review .paper-frame{border:1px solid #d9ded6;background:#f1f0e9;box-shadow:0 12px 28px rgba(53,67,57,.07)}
        .elh-review iframe{display:block;border:0;width:100%;height:965px;background:#f1f0e9}
        .elh-review .below{display:flex;align-items:center;justify-content:space-between;padding:15px 2px 0;color:#7b867e;font:11px 'DM Mono',monospace;letter-spacing:.04em}
        .elh-review .pager{display:flex;gap:8px}
        .elh-review .pager button{border:1px solid #cbd3ca;background:#f5f6f0;color:#526258;border-radius:5px;padding:7px 11px;font:600 11px 'DM Sans',sans-serif;cursor:pointer}
        .elh-review .pager button:disabled{opacity:.42;cursor:not-allowed}
        .elh-review .state{margin:20px 0;background:#f5f6f0;border:1px solid #d9ded6;padding:20px;color:#5d675f;font-size:14px}
        .elh-review .retry{margin-left:10px;background:#405849;color:#fff;border:0;border-radius:4px;padding:8px 12px;cursor:pointer}
        @media(max-width:850px){.elh-review{padding:25px 22px 36px}.elh-review .layout{grid-template-columns:1fr;gap:18px}.elh-review .rail{padding:0}.elh-review .rail-label{margin-left:0}.elh-review .nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}.elh-review .nav button{background:#f2f4ee;border:1px solid #dce1d9}.elh-review .rail-note,.elh-review .rail-rule{display:none}.elh-review .header{align-items:flex-start}.elh-review .header-note{max-width:160px}}
        @media(max-width:560px){.elh-review{padding:18px 13px 28px}.elh-review .topline{margin-bottom:18px}.elh-review .topline .edition{display:none}.elh-review .header{display:block;padding-bottom:17px;margin-bottom:19px}.elh-review h1{font-size:34px}.elh-review .header-note{text-align:left;margin-top:9px;max-width:none;font-size:16px}.elh-review .nav{grid-template-columns:1fr 1fr;max-height:235px;overflow:auto}.elh-review .nav button{padding:10px 8px;font-size:11px;gap:6px}.elh-review .nav-index{font-size:10px;min-width:15px}.elh-review .mail-meta{grid-template-columns:49px minmax(0,1fr);padding:14px 13px}.elh-review .meta-value{font-size:12px}.elh-review iframe{height:1100px}.elh-review .below{font-size:10px}}
        @media(prefers-reduced-motion:reduce){.elh-review *{transition:none!important}}
      `}</style>
      <div className="shell">
        <div className="topline">
          <div className="brand"><span className="brand-mark">e</span><span>Eternal Life Hospice</span></div>
          <span className="edition">Acknowledgment correspondence · design review</span>
        </div>
        <header className="header">
          <div>
            <div className="eyebrow">Unpublished preview · refined letter</div>
            <h1>Care begins with listening.</h1>
          </div>
          <div className="header-note">Approved messages, thoughtfully composed.</div>
        </header>
        <div className="layout">
          <aside className="rail" aria-label="Email request types">
            <p className="rail-label">Request type</p>
            {loadError ? (
              <div className="state">
                Approved messages could not be loaded.
                <button className="retry" onClick={() => window.location.reload()}>Retry</button>
              </div>
            ) : messages.length === 0 ? (
              <div className="state">Loading approved messages…</div>
            ) : (
              <>
                <nav className="nav">
                  {messages.map((message, index) => (
                    <button
                      key={message.key}
                      type="button"
                      className={message.key === activeKey ? "active" : ""}
                      aria-current={message.key === activeKey ? "page" : undefined}
                      onClick={() => setEmail(message.key)}
                    >
                      <span className="nav-index">{String(index + 1).padStart(2, "0")}</span>
                      <span>{message.key.replaceAll("-", " ")}</span>
                    </button>
                  ))}
                </nav>
                <div className="rail-rule" />
                <p className="rail-note">A single composed letter for each request. Select a message to review its approved wording and supporting notices.</p>
              </>
            )}
          </aside>
          <section className="workspace" aria-label="Email preview">
            {activeMessage ? (
              <>
                <div className="mail-meta">
                  <span className="meta-label">Subject</span>
                  <span className="meta-value subject">{activeMessage.subject}</span>
                  <span className="meta-label">To</span>
                  <span className="meta-value">[Recipient]</span>
                </div>
                <div className="paper-frame">
                  <iframe
                    title={`${activeMessage.subject} — email preview`}
                    srcDoc={makeEmailDocument(activeMessage)}
                    sandbox="allow-same-origin allow-popups allow-top-navigation-by-user-activation"
                    onLoad={(event) => {
                      const frame = event.currentTarget;
                      frame.style.height = "1px";
                      frame.style.height = `${Math.max(640, frame.contentDocument?.documentElement.scrollHeight || 965)}px`;
                    }}
                  />
                </div>
                <div className="below">
                  <span>{String(currentIndex + 1).padStart(2, "0")} / {String(messages.length).padStart(2, "0")}</span>
                  <div className="pager">
                    <button type="button" disabled={currentIndex <= 0} onClick={() => currentIndex > 0 && setEmail(messages[currentIndex - 1].key)}>Previous</button>
                    <button type="button" disabled={currentIndex >= messages.length - 1} onClick={() => currentIndex < messages.length - 1 && setEmail(messages[currentIndex + 1].key)}>Next</button>
                  </div>
                </div>
              </>
            ) : loadError ? null : (
              <div className="state">Preparing approved correspondence…</div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
