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
    return `<tr><td style="padding:6px 0 23px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;border-top:1px solid #d9cdb7;border-bottom:1px solid #d9cdb7">
        <tr><td style="padding:15px 0 16px">
          <p style="margin:0 0 5px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif">${escapeHtml(lines[0])}</p>
          <p style="margin:0 0 12px;color:#535353;font:15px/1.55 Georgia,'Times New Roman',serif">${escapeHtml(lines[1])}</p>
          <a href="tel:18059537273" style="display:inline-block;color:#414141;background:#f5f0eb;border:1px solid #cfc2aa;padding:10px 14px;font:bold 14px/1.2 Arial,sans-serif;text-decoration:none">${escapeHtml(lines[2])}</a>
        </td></tr>
      </table>
    </td></tr>`;
  }

  if (paragraph.startsWith("Confirmation number:")) {
    return `<tr><td style="padding:12px 0 0;border-top:1px solid #e2ddd4">
      <p style="margin:0;color:#555555;font:13px/1.6 Arial,sans-serif">${safe}</p>
    </td></tr>`;
  }

  if (
    paragraph.startsWith("To help protect patient privacy") ||
    paragraph.startsWith("If you are experiencing a medical emergency") ||
    paragraph.startsWith("Important: This confirms receipt")
  ) {
    return `<tr><td style="padding:8px 0 0">
      <p style="margin:0;color:#555555;font:13px/1.6 Arial,sans-serif">${safe}</p>
    </td></tr>`;
  }

  const isGreeting = /^(Dear|Hello) /.test(paragraph);
  const isSignoff = /^(With care,|With appreciation,|Warm regards,|Warmly,)$/.test(paragraph);
  const isTeam = paragraph.startsWith("The Eternal Life Hospice");
  const isTagline = /^(Here in Moments That Matter Most\.|Care That Honors Life\.)$/.test(paragraph);
  const style = isGreeting
    ? "margin:0 0 18px;color:#4b4b4b;font:16px/1.6 Georgia,'Times New Roman',serif"
    : isSignoff
      ? "margin:21px 0 3px;color:#4b4b4b;font:16px/1.6 Georgia,'Times New Roman',serif"
      : isTeam
        ? "margin:0 0 4px;color:#414141;font:bold 16px/1.45 Georgia,'Times New Roman',serif"
        : isTagline
          ? "margin:0 0 18px;color:#686868;font:italic 14px/1.55 Georgia,'Times New Roman',serif"
          : "margin:0 0 15px;color:#414141;font:16px/1.62 Georgia,'Times New Roman',serif";
  return `<tr><td><p style="${style}">${safe}</p></td></tr>`;
}

function makeEmailDocument(message: ApprovedMessage) {
  const letterRows = message.paragraphs.map(renderParagraph).join("");
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body{margin:0;padding:0;width:100%;background:#f5f0eb}
    *{box-sizing:border-box}
    @media only screen and (max-width:480px){
      .outer-pad{padding:0!important}
      .letter-shell{border-left:0!important;border-right:0!important}
      .brand-photo{height:122px!important}
      .brand-cell{padding:15px 13px!important}
      .brand-logo{width:118px!important}
      .letter-copy{padding:21px 20px 17px!important}
      .letter-footer{padding:0 20px 22px!important}
    }
  </style>
</head>
<body style="margin:0;background:#f5f0eb;color:#414141">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background:#f5f0eb">
    <tr><td class="outer-pad" align="center" style="padding:17px 12px 24px">
      <table role="presentation" class="letter-shell" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#fffefa;border:1px solid #ddd5c8">
        <tr>
          <td width="39%" class="brand-photo" valign="middle" style="width:39%;height:156px;padding:0;background:#d8d0c3">
            <img src="${COAST_URL}" width="234" height="156" alt="Quiet coastal view" style="display:block;width:100%;height:156px;object-fit:cover;border:0">
          </td>
          <td width="61%" class="brand-cell" valign="middle" style="width:61%;padding:22px 25px;background:#f4f0e9;border-bottom:3px solid #b5a279">
            <img class="brand-logo" src="${LOGO_URL}" width="142" alt="Eternal Life Hospice" style="display:block;width:142px;max-width:100%;height:auto;border:0">
          </td>
        </tr>
        <tr><td colspan="2" class="letter-copy" style="padding:25px 48px 21px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;color:#414141;font:16px/1.62 Georgia,'Times New Roman',serif">
            ${letterRows}
          </table>
        </td></tr>
        <tr><td colspan="2" class="letter-footer" style="padding:0 48px 24px">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%">
            <tr><td style="padding-top:12px;border-top:1px solid #e2ddd4;font:13px/1.5 Arial,sans-serif">
              <a href="mailto:info@eternallifehospice.com" style="color:#535353;text-decoration:none;overflow-wrap:anywhere">info@eternallifehospice.com</a><br>
              <span style="display:inline-block;padding-top:8px;color:#555555;font:12px/1.55 Arial,sans-serif">
                Eternal Life Hospice<br>
                4165 E Thousand Oaks Blvd, Suite 325B<br>
                Westlake Village, CA 91362
              </span>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;
}

export function QuietHorizon() {
  const [messages, setMessages] = useState<ApprovedMessage[]>([]);
  const [activeKey, setActiveKey] = useState(() => new URLSearchParams(window.location.search).get("email") || "physician");
  const [loadError, setLoadError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [frameHeight, setFrameHeight] = useState(720);

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
  }, [attempt]);

  useEffect(() => {
    if (messages.length && !messages.some((message) => message.key === activeKey)) setActiveKey("physician");
  }, [activeKey, messages]);

  useEffect(() => {
    const onResize = () => {
      const frame = document.getElementById("quiet-horizon-email") as HTMLIFrameElement | null;
      const height = frame?.contentDocument?.documentElement.scrollHeight;
      if (height) setFrameHeight(Math.max(540, height));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const activeMessage = useMemo(
    () => messages.find((message) => message.key === activeKey),
    [messages, activeKey],
  );
  const currentIndex = messages.findIndex((message) => message.key === activeKey);

  const setEmail = (key: string) => {
    setActiveKey(key);
    const url = new URL(window.location.href);
    url.searchParams.set("email", key);
    window.history.replaceState({}, "", url);
  };

  return (
    <main className="qh-review">
      <style>{`
        .qh-review{--ink:#4a4545;--muted:#7d756d;--line:#ded5c8;--paper:#f5f0eb;--plum:#432440;--gold:#b5a279;min-height:100dvh;background:#f5f0eb;color:var(--ink);font-family:'DM Sans','Avenir Next',sans-serif;padding:30px 38px 42px;box-sizing:border-box}
        .qh-review *{box-sizing:border-box}
        .qh-review .shell{max-width:1320px;margin:0 auto}
        .qh-review .topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:21px;color:#81796f;font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
        .qh-review .brand{display:flex;align-items:center;gap:9px;color:#554b49}
        .qh-review .brand-mark{height:25px;width:25px;border:1px solid #b5a279;border-radius:50%;display:grid;place-items:center;color:#432440;font:italic 14px Georgia,serif}
        .qh-review .header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;border-bottom:1px solid #d9cdb7;padding:0 0 19px;margin-bottom:24px}
        .qh-review .eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.18em;color:#9a8967;font-weight:700;margin-bottom:8px}
        .qh-review h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:500;font-size:36px;line-height:1.04;letter-spacing:-.02em;margin:0;color:#432440}
        .qh-review .header-note{font:italic 16px/1.35 'Cormorant Garamond',Georgia,serif;color:#746b66;max-width:245px;text-align:right}
        .qh-review .layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:26px;align-items:start}
        .qh-review .rail{padding:12px 0 0}
        .qh-review .rail-label{font-size:10px;font-weight:700;letter-spacing:.16em;color:#887d6f;text-transform:uppercase;margin:0 0 10px}
        .qh-review .selector{width:100%;border:1px solid #d5c9b6;border-radius:3px;background:#fffefa;color:#514b48;padding:11px 32px 11px 12px;font:500 13px/1.3 'DM Sans','Avenir Next',sans-serif}
        .qh-review .rail-note{margin:15px 0 0;padding-top:14px;border-top:1px solid #ddd3c3;color:#7c746b;font:12px/1.65 'DM Sans','Avenir Next',sans-serif}
        .qh-review .workspace{min-width:0}
        .qh-review .mail-meta{background:#f5f0eb;border:1px solid #dfd8cc;border-bottom:0;padding:14px 19px 13px;display:grid;grid-template-columns:62px minmax(0,1fr);gap:6px 11px}
        .qh-review .meta-label{font-size:10px;letter-spacing:.11em;text-transform:uppercase;color:#8b8175;font-weight:700;padding-top:3px}
        .qh-review .meta-value{font-size:13px;line-height:1.45;color:#514b48;overflow-wrap:anywhere}
        .qh-review .meta-value.subject{font-weight:600;color:#432440}
        .qh-review .paper-frame{border:1px solid #dfd8cc;background:#f5f0eb;box-shadow:0 12px 28px rgba(67,36,64,.07)}
        .qh-review iframe{display:block;border:0;width:100%;background:#f5f0eb}
        .qh-review .below{display:flex;align-items:center;justify-content:space-between;padding:13px 2px 0;color:#82796f;font:11px 'DM Mono',monospace;letter-spacing:.04em}
        .qh-review .pager{display:flex;gap:8px}
        .qh-review .pager button,.qh-review .retry{border:1px solid #d5c9b6;background:#f5f0eb;color:#432440;border-radius:4px;padding:7px 11px;font:600 11px 'DM Sans',sans-serif;cursor:pointer}
        .qh-review .pager button:disabled{opacity:.42;cursor:not-allowed}
        .qh-review .state{margin:14px 0;background:#f8f4ef;border:1px solid #dfd8cc;padding:18px;color:#5d5651;font-size:14px}
        .qh-review .retry{margin-left:10px;background:#432440;color:#f5f0eb}
        @media(max-width:820px){.qh-review{padding:25px 22px 36px}.qh-review .layout{grid-template-columns:1fr;gap:17px}.qh-review .rail{padding:0}.qh-review .rail-label{margin-bottom:8px}.qh-review .selector{max-width:420px}.qh-review .rail-note{display:none}}
        @media(max-width:560px){.qh-review{padding:17px 12px 28px}.qh-review .topline{margin-bottom:16px}.qh-review .topline .edition{display:none}.qh-review .header{display:block;padding-bottom:15px;margin-bottom:17px}.qh-review h1{font-size:32px}.qh-review .header-note{text-align:left;margin-top:7px;max-width:none;font-size:15px}.qh-review .mail-meta{grid-template-columns:48px minmax(0,1fr);padding:12px}.qh-review .meta-value{font-size:12px}.qh-review .below{font-size:10px}}
        @media(prefers-reduced-motion:reduce){.qh-review *{transition:none!important}}
      `}</style>
      <div className="shell">
        <div className="topline">
          <div className="brand"><span className="brand-mark">e</span><span>Eternal Life Hospice</span></div>
          <span className="edition">Acknowledgment correspondence · design review</span>
        </div>
        <header className="header">
          <div>
            <div className="eyebrow">Unpublished preview · quiet horizon</div>
            <h1>A little room to breathe.</h1>
          </div>
          <div className="header-note">A coastal view offers a moment of connection before the letter begins.</div>
        </header>
        <div className="layout">
          <aside className="rail" aria-label="Email request types">
            <p className="rail-label">Approved message</p>
            {loadError ? (
              <div className="state">
                Approved messages could not be loaded.
                <button className="retry" type="button" onClick={() => setAttempt((value) => value + 1)}>Retry</button>
              </div>
            ) : messages.length === 0 ? (
              <div className="state">Loading approved messages…</div>
            ) : (
              <>
                <select
                  className="selector"
                  value={activeKey}
                  aria-label="Select approved email"
                  onChange={(event) => setEmail(event.target.value)}
                >
                  {messages.map((message, index) => (
                    <option key={message.key} value={message.key}>
                      {String(index + 1).padStart(2, "0")} · {message.key.replaceAll("-", " ")}
                    </option>
                  ))}
                </select>
                <p className="rail-note">Select a request type to inspect its approved wording in the same considered, photo-led format.</p>
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
                    id="quiet-horizon-email"
                    title={`${activeMessage.subject} — email preview`}
                    srcDoc={makeEmailDocument(activeMessage)}
                    sandbox="allow-same-origin allow-popups allow-top-navigation-by-user-activation"
                    style={{ height: `${frameHeight}px` }}
                    onLoad={(event) => {
                      const frame = event.currentTarget;
                      const height = frame.contentDocument?.documentElement.scrollHeight;
                      if (height) setFrameHeight(Math.max(540, height));
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
